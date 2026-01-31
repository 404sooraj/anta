/**
 * Build embedding-ready strings (no PII) and embed via LangChain.
 * Use same model as Python getCallInsights. Switch embedding model by swapping the LangChain embeddings instance (e.g. BedrockEmbeddings, OpenAIEmbeddings).
 */

import type { CallRecordForIngestion, ClassifiedCall } from './types.js';

/** Minimal interface so we can swap BedrockEmbeddings, OpenAIEmbeddings, etc. */
export interface EmbeddingsLike {
  embedDocuments(documents: string[]): Promise<number[][]>;
}

export interface ScenarioText {
  text: string;
  metadata: { issue_type: string; resolution: string; escalated: boolean; dominant_sentiment: string; language: string };
}

export interface PatternText {
  text: string;
  metadata: { pattern_type: 'anti_pattern' | 'best_practice'; issue_type: string; effect: string };
}

export interface PolicyText {
  text: string;
  metadata: { policy_domain: string; can_override: string };
}

/** One sentence each from analysis; no PII. */
function oneSentence(s: string): string {
  const trimmed = s.trim().replace(/\s+/g, ' ');
  const end = trimmed.search(/[.!?]\s/);
  return end > 0 ? trimmed.slice(0, end + 1) : trimmed.slice(0, 200);
}

export function buildScenarioText(record: CallRecordForIngestion, classified: ClassifiedCall): ScenarioText {
  const { summary, problemFaced, solutionPresented } = record.analysis;
  const issue = oneSentence(summary || problemFaced);
  const claim = oneSentence(problemFaced || summary);
  const policy = oneSentence(solutionPresented || summary);
  const outcome = classified.resolution;
  const reason = oneSentence(record.analysis.partnerSatisfactionScore?.reasoning || solutionPresented || summary);
  const text = `Issue: ${issue}. Customer claim: ${claim}. Policy involved: ${policy}. Outcome: ${outcome}. Key failure or success reason: ${reason}.`;
  return {
    text,
    metadata: {
      issue_type: classified.issueType,
      resolution: classified.resolution,
      escalated: classified.escalated,
      dominant_sentiment: classified.dominantSentiment,
      language: classified.language,
    },
  };
}

/** Extract one anti-pattern or best-practice from solution/reasoning. */
export function buildPatternTexts(record: CallRecordForIngestion, classified: ClassifiedCall): PatternText[] {
  const { solutionPresented, partnerSatisfactionScore } = record.analysis;
  const reasoning = partnerSatisfactionScore?.reasoning ?? solutionPresented ?? record.analysis.summary;
  const texts: PatternText[] = [];
  if (classified.escalated || classified.resolution === 'unresolved') {
    const situation = oneSentence(record.analysis.problemFaced);
    const behavior = oneSentence(solutionPresented);
    const outcome = 'escalation or unresolved';
    const better = 'Acknowledge emotion, explain policy once, offer next step (e.g. escalation path or payment option).';
    texts.push({
      text: `When ${situation}, doing ${behavior} leads to ${outcome}. Better approach: ${better}.`,
      metadata: { pattern_type: 'anti_pattern', issue_type: classified.issueType, effect: 'escalation' },
    });
  }
  if (classified.resolution === 'resolved' || (record.analysis.partnerSatisfactionScore?.score ?? 0) >= 6) {
    const situation = oneSentence(record.analysis.problemFaced);
    const behavior = oneSentence(solutionPresented);
    texts.push({
      text: `When ${situation}, doing ${behavior} leads to positive outcome. Better approach: Continue same clarity and empathy.`,
      metadata: { pattern_type: 'best_practice', issue_type: classified.issueType, effect: 'deescalation' },
    });
  }
  if (texts.length === 0) {
    texts.push({
      text: `When ${oneSentence(record.analysis.summary)}, agent behavior led to ${classified.resolution}. Better approach: Provide clear policy and one actionable next step.`,
      metadata: { pattern_type: 'anti_pattern', issue_type: classified.issueType, effect: 'clarity' },
    });
  }
  return texts;
}

/** Extract policy statements from solution/summary (factual only). */
export function buildPolicyTexts(record: CallRecordForIngestion): PolicyText[] {
  const { solutionPresented, summary } = record.analysis;
  const combined = `${solutionPresented} ${summary}`.toLowerCase();
  const policies: PolicyText[] = [];
  if (/penalty cannot be removed|we cannot remove|here from.*not.*remove|नहीं हटा सकते/i.test(combined)) {
    policies.push({
      text: 'Policy: Penalty applied for late/non-return of battery cannot be removed by agent. Condition: When penalty was applied per policy. Override allowed: no.',
      metadata: { policy_domain: 'penalty', can_override: 'false' },
    });
  }
  if (/10.*(?:baje|o\'clock|am)|same day|swap.*same day|जमा करवाना होता है/i.test(combined)) {
    policies.push({
      text: 'Policy: Battery must be swapped/returned same day; before 10 AM return can avoid penalty. Condition: Same-day swap or early return. Override allowed: unknown.',
      metadata: { policy_domain: 'battery_swap', can_override: 'unknown' },
    });
  }
  if (/rent|रेंट|we cannot remove|यहाँ से नहीं हटा/i.test(combined)) {
    policies.push({
      text: 'Policy: Rent charges applied cannot be removed by agent. Condition: When rent applies per terms. Override allowed: no.',
      metadata: { policy_domain: 'rent', can_override: 'false' },
    });
  }
  return policies;
}

const EMBEDDING_DIM = 1536; // Titan Embeddings G1 - Text; change if you switch model

/** Embed texts using any LangChain embeddings (e.g. BedrockEmbeddings, OpenAIEmbeddings). */
export async function embedTexts(embeddings: EmbeddingsLike, texts: string[]): Promise<number[][]> {
  if (texts.length === 0) return [];
  return embeddings.embedDocuments(texts);
}

export { EMBEDDING_DIM };
