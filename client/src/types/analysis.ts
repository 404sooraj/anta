/**
 * Types for PS2 call analysis JSON (data-normalization output).
 * Mirrors data-normalization/src/types/index.ts for type-safe UI.
 */

export interface TranscriptionSegment {
  text: string;
  timestamp: number;
  speaker: "agent" | "partner";
}

export interface SentimentAnalysis {
  overall:
    | "calm/composed"
    | "happy"
    | "neutral"
    | "concerned"
    | "frustrated"
    | "sad"
    | "angry"
    | "infuriated";
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

export interface ProcessedCallData {
  metadata: {
    date: string;
    name: string;
    issueType: string;
    callingNumber: string;
    recordingLink: string;
    processedAt: string;
    callDuration: number;
  };
  transcription: {
    agentConversation: TranscriptionSegment[];
    partnerConversation: TranscriptionSegment[];
    fullTranscript: string;
  };
  analysis: CallAnalysis;
}

/** List item returned by GET /api/ps2-analysis (no id = list) */
export interface Ps2AnalysisListItem {
  id: string;
  filename: string;
  metadata: ProcessedCallData["metadata"];
  partnerSatisfactionScore: SatisfactionScore;
}
