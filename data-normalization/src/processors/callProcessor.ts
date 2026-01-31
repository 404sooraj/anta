/**
 * Call processor - Orchestrates the entire processing pipeline
 */
import { join } from 'path';
import { logger, FileManager } from '../utils/index.js';
import {
  GoogleSheetsService,
  GoogleDriveService,
  SonioxService,
  SpeakerClassifier,
  ClaudeService,
} from '../services/index.js';
import type {
  CallRecordingMetadata,
  ProcessedCallData,
  ProcessingStats,
} from '../types/index.js';
import { env } from '../config/env.js';

export class CallProcessor {
  private sheetsService: GoogleSheetsService;
  private driveService: GoogleDriveService;
  private sonioxService: SonioxService;
  private speakerClassifier: SpeakerClassifier;
  private claudeService: ClaudeService;
  private outputDir: string;
  private cleanupAudio: boolean;

  constructor() {
    this.sheetsService = new GoogleSheetsService(
      env.googleSheetsId,
      env.googleSheetsGid
    );
    this.driveService = new GoogleDriveService(env.audioTempDir);
    this.sonioxService = new SonioxService(env.sonioxApiKey);
    this.speakerClassifier = new SpeakerClassifier();
    this.claudeService = new ClaudeService(
      env.awsAccessKeyId,
      env.awsSecretAccessKey,
      env.awsSessionToken,
      env.awsRegion,
      env.bedrockModelId
    );
    this.outputDir = env.outputDir;
    this.cleanupAudio = env.cleanupAudioAfterProcessing;
  }

  /**
   * Process all call recordings
   */
  async processAll(options: {
    fromDate?: string;
    toDate?: string;
    rowNumber?: number;
    fromRow?: number;
    toRow?: number;
    dryRun?: boolean;
  } = {}): Promise<ProcessingStats> {
    const stats: ProcessingStats = {
      totalRecordings: 0,
      processed: 0,
      failed: 0,
      skipped: 0,
      startTime: new Date(),
      errors: [],
    };

    try {
      logger.info('Starting call recording processing pipeline...');

      // Fetch call recordings from Google Sheets
      let recordings = await this.sheetsService.fetchCallRecordings();
      stats.totalRecordings = recordings.length;

      // Filter by options
      if (options.rowNumber) {
        const recording = this.sheetsService.getRecordingByRow(recordings, options.rowNumber);
        recordings = recording ? [recording] : [];
      } else if (options.fromRow != null || options.toRow != null) {
        recordings = recordings.filter((r) => {
          if (options.fromRow != null && r.rowNumber < options.fromRow) return false;
          if (options.toRow != null && r.rowNumber > options.toRow) return false;
          return true;
        });
      } else if (options.fromDate || options.toDate) {
        recordings = this.sheetsService.filterByDateRange(
          recordings,
          options.fromDate,
          options.toDate
        );
      }

      logger.info(`Processing ${recordings.length} recordings...`);

      if (options.dryRun) {
        logger.info('DRY RUN - No actual processing will be performed');
        recordings.forEach((r, i) => {
          logger.info(`${i + 1}. Row ${r.rowNumber}: ${r.name} - ${r.issueType}`);
        });
        return stats;
      }

      // Ensure output directory exists
      await FileManager.ensureDir(this.outputDir);

      // Process recordings with concurrency control
      const maxConcurrent = env.maxConcurrentProcesses;
      const chunks = this.chunkArray(recordings, maxConcurrent);

      for (const chunk of chunks) {
        await Promise.all(
          chunk.map(async (recording) => {
            try {
              await this.processSingle(recording);
              stats.processed++;
            } catch (error) {
              const err = error as Error;
              stats.failed++;
              stats.errors.push({
                rowNumber: recording.rowNumber,
                error: err.message,
                recordingLink: recording.recordingLink,
              });
              logger.error(`Failed to process row ${recording.rowNumber}:`, err.message);
            }
          })
        );
      }

      stats.endTime = new Date();
      this.logStats(stats);

      return stats;
    } catch (error) {
      const err = error as Error;
      logger.error('Processing pipeline failed:', err.message);
      throw error;
    }
  }

  /**
   * Process a single call recording
   */
  private async processSingle(
    metadata: CallRecordingMetadata
  ): Promise<void> {
    logger.info(`\n${'='.repeat(60)}`);
    logger.info(`Processing: Row ${metadata.rowNumber} - ${metadata.name} (${metadata.issueType})`);
    logger.info(`${'='.repeat(60)}`);

    try {
      // Step 1: Download audio file
      const audioFilename = this.driveService.generateAudioFilename(metadata);
      const audioPath = await this.driveService.downloadAudio(
        metadata.recordingLink,
        audioFilename
      );

      // Step 2: Transcribe with speaker diarization
      const { tokens, duration } = await this.sonioxService.transcribeAudio(audioPath);

      // Step 3: Classify speakers
      const speakerMapping = this.speakerClassifier.classifySpeakers(tokens);

      // Step 4: Parse into conversation segments
      const segments = this.sonioxService.parseTokensToSegments(tokens, speakerMapping);
      const fullTranscript = this.sonioxService.generateFullTranscript(segments);

      // Separate agent and partner conversations
      const agentSegments = segments.filter((s) => s.speaker === 'agent');
      const partnerSegments = segments.filter((s) => s.speaker === 'partner');

      const agentConversation = agentSegments.map((s) => s.text).join(' ');
      const partnerConversation = partnerSegments.map((s) => s.text).join(' ');

      // Step 5: Analyze with Claude
      const analysis = await this.claudeService.analyzeCall(
        fullTranscript,
        agentConversation,
        partnerConversation
      );

      // Step 6: Generate output JSON
      const processedData: ProcessedCallData = {
        metadata: {
          date: metadata.date,
          name: metadata.name,
          issueType: metadata.issueType,
          callingNumber: metadata.callingNumber,
          recordingLink: metadata.recordingLink,
          processedAt: new Date().toISOString(),
          callDuration: Math.round(duration),
        },
        transcription: {
          agentConversation: agentSegments,
          partnerConversation: partnerSegments,
          fullTranscript,
        },
        analysis,
      };

      // Step 7: Save to file
      const outputFilename = FileManager.generateOutputFilename(metadata);
      const outputPath = join(this.outputDir, outputFilename);
      await FileManager.writeJSON(outputPath, processedData);

      logger.success(`Saved output to: ${outputFilename}`);

      // Step 8: Cleanup audio file
      if (this.cleanupAudio) {
        await this.driveService.deleteAudio(audioPath);
      }

      logger.success(`Successfully processed row ${metadata.rowNumber}`);
    } catch (error) {
      logger.error(`Failed processing row ${metadata.rowNumber}`);
      throw error;
    }
  }

  /**
   * Split array into chunks for concurrent processing
   */
  private chunkArray<T>(array: T[], chunkSize: number): T[][] {
    const chunks: T[][] = [];
    for (let i = 0; i < array.length; i += chunkSize) {
      chunks.push(array.slice(i, i + chunkSize));
    }
    return chunks;
  }

  /**
   * Log processing statistics
   */
  private logStats(stats: ProcessingStats): void {
    const duration = stats.endTime
      ? (stats.endTime.getTime() - stats.startTime.getTime()) / 1000
      : 0;

    const separator = '='.repeat(60);
    logger.info(`\n${separator}`);
    logger.info('PROCESSING COMPLETE');
    logger.info(separator);
    logger.info(`Total recordings: ${stats.totalRecordings}`);
    logger.info(`Processed: ${stats.processed}`);
    logger.info(`Failed: ${stats.failed}`);
    logger.info(`Skipped: ${stats.skipped}`);
    logger.info(`Duration: ${Math.round(duration)}s`);

    if (stats.errors.length > 0) {
      logger.warn('\nErrors:');
      stats.errors.forEach((err, i) => {
        logger.warn(`${String(i + 1)}. Row ${String(err.rowNumber)}: ${err.error}`);
      });
    }

    logger.info(separator);
  }
}
