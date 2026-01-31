/**
 * Minimal call record type for ingestion. No PII, no transcripts, no timestamps.
 * Only metadata.issueType and analysis are used.
 */

export interface SentimentAnalysis {
  overall: string;
  confidence: number;
  details: string;
}

export interface SatisfactionScore {
  score: number;
  maxScore: number;
  reasoning: string;
}

export interface CallAnalysis {
  summary: string;
  problemFaced: string;
  solutionPresented: string;
  agentSentiment: SentimentAnalysis;
  partnerSentiment: SentimentAnalysis;
  partnerSatisfactionScore: SatisfactionScore;
}

export interface CallRecordForIngestion {
  metadata: {
    issueType: string;
    processedAt: string;
  };
  analysis: CallAnalysis;
}

export type ResolutionOutcome = 'resolved' | 'unresolved' | 'escalated';
export type DominantSentiment = 'neutral' | 'frustrated' | 'angry';

export interface ClassifiedCall {
  issueType: string;
  resolution: ResolutionOutcome;
  escalated: boolean;
  dominantSentiment: DominantSentiment;
  language: string;
}
