/**
 * Type definitions for the call recording analysis pipeline
 */

export interface CallRecordingMetadata {
  date: string;
  name: string;
  issueType: string;
  recordingLink: string;
  callingNumber: string;
  rowNumber: number;
}

export interface TranscriptionSegment {
  text: string;
  timestamp: number;
  speaker: 'agent' | 'partner';
}

export interface SpeakerToken {
  text: string;
  speaker: string;
  startTime?: number;
  endTime?: number;
  isFinal?: boolean;
}

export interface SentimentAnalysis {
  overall: 'calm/composed' | 'happy' | 'neutral' | 'concerned' | 'frustrated' | 'sad' | 'angry' | 'infuriated';
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

export interface ProcessingOptions {
  fromDate?: string;
  toDate?: string;
  rowNumber?: number;
  fromRow?: number;
  toRow?: number;
  resume?: boolean;
  dryRun?: boolean;
}

export interface ProcessingStats {
  totalRecordings: number;
  processed: number;
  failed: number;
  skipped: number;
  startTime: Date;
  endTime?: Date;
  errors: Array<{
    rowNumber: number;
    error: string;
    recordingLink: string;
  }>;
}
