/**
 * Soniox service - Async transcription with speaker diarization
 * Uses Soniox Async API for better accuracy
 */
import axios, { AxiosError } from 'axios';
import { createReadStream } from 'fs';
import FormData from 'form-data';
import { logger } from '../utils/logger.js';
import type { SpeakerToken, TranscriptionSegment } from '../types/index.js';

const SONIOX_API_BASE_URL = 'https://api.soniox.com';

/**
 * Result of transcription with tokens and duration
 */
export interface TranscriptionResult {
  tokens: SpeakerToken[];
  duration: number;
}

export class SonioxService {
  private apiKey: string;
  private pollInterval: number = 1000; // ms
  private maxPollAttempts: number = 300; // 5 minutes max

  constructor(apiKey: string) {
    this.apiKey = apiKey;
  }

  /**
   * Transcribe audio file with speaker diarization
   */
  async transcribeAudio(audioFilePath: string): Promise<TranscriptionResult> {
    try {
      logger.info('Starting Soniox transcription...');

      // Step 1: Upload audio file
      const fileId = await this.uploadFile(audioFilePath);

      // Step 2: Create transcription
      const transcriptionId = await this.createTranscription(fileId);

      // Step 3: Wait for completion
      await this.waitForCompletion(transcriptionId);

      // Step 4: Get transcript
      const result = await this.getTranscript(transcriptionId);

      // Step 5: Cleanup
      await this.deleteTranscription(transcriptionId);
      await this.deleteFile(fileId);

      // Calculate duration from tokens
      const duration = this.calculateDuration(result.tokens);

      logger.success('Transcription completed successfully');
      
      return {
        tokens: result.tokens,
        duration,
      };
    } catch (error) {
      const err = error as Error;
      logger.error('Soniox transcription failed:', err.message);
      throw new Error(`Transcription failed: ${err.message}`);
    }
  }

  /**
   * Upload audio file to Soniox Files API
   */
  private async uploadFile(audioFilePath: string): Promise<string> {
    logger.info('Uploading audio file to Soniox...');

    const form = new FormData();
    form.append('file', createReadStream(audioFilePath));

    try {
      const response = await axios.post(
        `${SONIOX_API_BASE_URL}/v1/files`,
        form,
        {
          headers: {
            ...form.getHeaders(),
            'Authorization': `Bearer ${this.apiKey}`,
          },
          timeout: 120000, // 2 minutes
        }
      );

      const fileId = response.data.id;
      logger.debug(`File uploaded with ID: ${fileId}`);
      
      return fileId;
    } catch (error) {
      const axiosError = error as AxiosError;
      const message = axiosError.response?.data || axiosError.message || 'Unknown error';
      throw new Error(`File upload failed: ${message}`);
    }
  }

  /**
   * Create transcription job
   */
  private async createTranscription(fileId: string): Promise<string> {
    logger.info('Creating transcription job...');

    const config = {
      model: 'stt-async-v4', // Latest model with improved diarization
      file_id: fileId,
      language_hints: ['en', 'hi'], // English and Hindi
      enable_language_identification: true,
      enable_speaker_diarization: true,
      context: {
        general: [
          { key: 'domain', value: 'Customer Service' },
          { key: 'topic', value: 'Battery swap and vehicle support' },
        ],
        terms: [
          'battery swap',
          'DSK',
          'IC',
          'VIP pass',
          'penalty',
          'meter',
          'connector',
          'station',
        ],
      },
    };

    try {
      const response = await axios.post(
        `${SONIOX_API_BASE_URL}/v1/transcriptions`,
        config,
        {
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
            'Content-Type': 'application/json',
          },
          timeout: 30000,
        }
      );

      const transcriptionId = response.data.id;
      logger.debug(`Transcription created with ID: ${transcriptionId}`);
      
      return transcriptionId;
    } catch (error) {
      const axiosError = error as AxiosError;
      const message = axiosError.response?.data || axiosError.message || 'Unknown error';
      throw new Error(`Create transcription failed: ${message}`);
    }
  }

  /**
   * Wait for transcription to complete
   */
  private async waitForCompletion(transcriptionId: string): Promise<void> {
    logger.info('Waiting for transcription to complete...');

    for (let attempt = 1; attempt <= this.maxPollAttempts; attempt++) {
      try {
        const response = await axios.get(
          `${SONIOX_API_BASE_URL}/v1/transcriptions/${transcriptionId}`,
          {
            headers: {
              'Authorization': `Bearer ${this.apiKey}`,
            },
            timeout: 10000,
          }
        );

        const status = response.data.status;

        if (status === 'completed') {
          logger.success('Transcription completed');
          return;
        }

        if (status === 'error') {
          const errorMessage = response.data.error_message || 'Unknown error';
          throw new Error(`Transcription failed: ${errorMessage}`);
        }

        // Still processing - wait and try again
        if (attempt % 10 === 0) {
          logger.debug(`Still processing... (${attempt}s elapsed)`);
        }

        await this.sleep(this.pollInterval);
      } catch (error) {
        const axiosError = error as AxiosError;
        if (axiosError.response?.status === 404) {
          throw new Error('Transcription not found');
        }
        throw error;
      }
    }

    throw new Error('Transcription timeout - exceeded maximum wait time');
  }

  /**
   * Get transcription result
   * Soniox API returns start_ms/end_ms (milliseconds); we normalize to startTime/endTime (seconds).
   */
  private async getTranscript(transcriptionId: string): Promise<{ tokens: SpeakerToken[] }> {
    logger.info('Fetching transcript...');

    try {
      const response = await axios.get(
        `${SONIOX_API_BASE_URL}/v1/transcriptions/${transcriptionId}/transcript`,
        {
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
          },
          timeout: 30000,
        }
      );

      const rawTokens = response.data.tokens || [];
      const tokens: SpeakerToken[] = rawTokens.map((t: { text?: string; speaker?: string; start_ms?: number; end_ms?: number; is_final?: boolean }) => ({
        text: t.text ?? '',
        speaker: t.speaker != null ? String(t.speaker) : '0',
        startTime: t.start_ms != null ? t.start_ms / 1000 : undefined,
        endTime: t.end_ms != null ? t.end_ms / 1000 : undefined,
        isFinal: t.is_final,
      }));

      return { tokens };
    } catch (error) {
      const axiosError = error as AxiosError;
      const message = axiosError.response?.data || axiosError.message || 'Unknown error';
      throw new Error(`Get transcript failed: ${message}`);
    }
  }

  /**
   * Delete transcription
   */
  private async deleteTranscription(transcriptionId: string): Promise<void> {
    try {
      await axios.delete(
        `${SONIOX_API_BASE_URL}/v1/transcriptions/${transcriptionId}`,
        {
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
          },
          timeout: 10000,
        }
      );
      logger.debug(`Deleted transcription: ${transcriptionId}`);
    } catch {
      logger.warn('Failed to delete transcription (non-fatal)');
    }
  }

  /**
   * Delete uploaded file
   */
  private async deleteFile(fileId: string): Promise<void> {
    try {
      await axios.delete(
        `${SONIOX_API_BASE_URL}/v1/files/${fileId}`,
        {
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
          },
          timeout: 10000,
        }
      );
      logger.debug(`Deleted file: ${fileId}`);
    } catch {
      logger.warn('Failed to delete file (non-fatal)');
    }
  }

  /**
   * Calculate audio duration from tokens (in seconds).
   * Uses last token's endTime; if missing, falls back to last startTime.
   */
  private calculateDuration(tokens: SpeakerToken[]): number {
    if (tokens.length === 0) {
      return 0;
    }
    const lastToken = tokens[tokens.length - 1];
    if (!lastToken) return 0;
    if (lastToken.endTime != null && lastToken.endTime > 0) {
      return lastToken.endTime;
    }
    if (lastToken.startTime != null && lastToken.startTime > 0) {
      return lastToken.startTime;
    }
    return 0;
  }

  /**
   * Sleep utility
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * Parse tokens into conversation segments grouped by speaker
   */
  parseTokensToSegments(
    tokens: SpeakerToken[],
    speakerMapping: Record<string, 'agent' | 'partner'>
  ): TranscriptionSegment[] {
    const segments: TranscriptionSegment[] = [];
    let currentSegment: {
      speaker: 'agent' | 'partner';
      text: string;
      startTime: number;
    } | null = null;

    for (const token of tokens) {
      const speaker = speakerMapping[token.speaker] || 'agent';
      const timestamp = token.startTime || 0;

      // Start new segment if speaker changed
      if (!currentSegment || currentSegment.speaker !== speaker) {
        if (currentSegment) {
          segments.push({
            text: currentSegment.text.trim(),
            timestamp: currentSegment.startTime,
            speaker: currentSegment.speaker,
          });
        }

        currentSegment = {
          speaker,
          text: token.text,
          startTime: timestamp,
        };
      } else {
        // Continue current segment
        currentSegment.text += token.text;
      }
    }

    // Add final segment
    if (currentSegment) {
      segments.push({
        text: currentSegment.text.trim(),
        timestamp: currentSegment.startTime,
        speaker: currentSegment.speaker,
      });
    }

    return segments;
  }

  /**
   * Generate full transcript with speaker labels
   */
  generateFullTranscript(segments: TranscriptionSegment[]): string {
    return segments
      .map((segment) => {
        const speaker = segment.speaker === 'agent' ? 'Agent' : 'Partner';
        return `${speaker}: ${segment.text}`;
      })
      .join('\n\n');
  }
}
