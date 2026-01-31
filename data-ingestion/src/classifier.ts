/**
 * Classify call from metadata.issueType and analysis only.
 * No PII, no transcript. Deterministic.
 */

import type { CallRecordForIngestion, ClassifiedCall, DominantSentiment, ResolutionOutcome } from './types.js';

const ISSUE_TYPE_MAP: Record<string, string> = {
  'Penalty Information Shared': 'penalty_dispute',
  'Penalty Dispute': 'penalty_dispute',
  'Swap Information Shared': 'battery_swap',
  'Battery Swap': 'battery_swap',
  'Subscription': 'subscription',
  'Battery Issue': 'battery_issue',
  'Service Center': 'service_center',
  'General': 'general',
};

const SENTIMENT_MAP: Record<string, DominantSentiment> = {
  neutral: 'neutral',
  'calm/composed': 'neutral',
  happy: 'neutral',
  concerned: 'frustrated',
  frustrated: 'frustrated',
  sad: 'frustrated',
  angry: 'angry',
  infuriated: 'angry',
};

function normalizeIssueType(raw: string): string {
  const lower = raw.trim().toLowerCase();
  for (const [k, v] of Object.entries(ISSUE_TYPE_MAP)) {
    if (k.toLowerCase().includes(lower) || lower.includes(k.toLowerCase())) return v;
  }
  return raw.replace(/\s+/g, '_').toLowerCase() || 'general';
}

function inferResolution(record: CallRecordForIngestion): { resolution: ResolutionOutcome; escalated: boolean } {
  const { summary, solutionPresented, partnerSatisfactionScore } = record.analysis;
  const text = `${summary} ${solutionPresented}`.toLowerCase();
  const score = partnerSatisfactionScore?.score ?? 10;
  const escalated = /transfer|escalat|igf|another department|concluded the call without resolving/i.test(text) || (score <= 3 && /transfer|escalat/i.test(text));
  if (escalated) return { resolution: 'escalated', escalated: true };
  if (score >= 7) return { resolution: 'resolved', escalated: false };
  return { resolution: 'unresolved', escalated: false };
}

function dominantSentiment(record: CallRecordForIngestion): DominantSentiment {
  const overall = record.analysis.partnerSentiment?.overall ?? 'neutral';
  return SENTIMENT_MAP[overall.toLowerCase()] ?? 'neutral';
}

/** Detect language from analysis text (simple: hi if non-ASCII dominant). */
function detectLanguage(record: CallRecordForIngestion): string {
  const text = `${record.analysis.summary} ${record.analysis.problemFaced}`;
  const nonAscii = (text.match(/[^\x00-\x7F]/g) ?? []).length;
  return nonAscii > text.length / 2 ? 'hi' : 'en';
}

export function classifyCall(record: CallRecordForIngestion): ClassifiedCall {
  const { resolution, escalated } = inferResolution(record);
  return {
    issueType: normalizeIssueType(record.metadata.issueType),
    resolution,
    escalated,
    dominantSentiment: dominantSentiment(record),
    language: detectLanguage(record),
  };
}
