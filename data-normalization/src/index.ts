/**
 * Main entry point for call recording data normalization pipeline
 */
import { parseArgs } from 'node:util';
import { logger, LogLevel } from './utils/index.js';
import { CallProcessor } from './processors/callProcessor.js';
import { env } from './config/env.js';

async function main() {
  // Parse command line arguments
  const { values: args } = parseArgs({
    options: {
      from: {
        type: 'string',
        description: 'Process recordings from this date (e.g., "1/25/26")',
      },
      to: {
        type: 'string',
        description: 'Process recordings up to this date (e.g., "1/29/26")',
      },
      row: {
        type: 'string',
        description: 'Process a specific row number',
      },
      'from-row': {
        type: 'string',
        description: 'Process from this row number to the end (or to --to-row if set)',
      },
      'to-row': {
        type: 'string',
        description: 'Process up to this row number (use with --from-row for a range)',
      },
      'dry-run': {
        type: 'boolean',
        description: 'Fetch metadata only, no actual processing',
      },
      verbose: {
        type: 'boolean',
        description: 'Enable verbose logging',
      },
      help: {
        type: 'boolean',
        description: 'Show help message',
      },
    },
  });

  // Show help
  if (args.help) {
    showHelp();
    return;
  }

  // Set log level
  if (args.verbose) {
    logger.setLevel(LogLevel.DEBUG);
  }

  // Show configuration
  const separator = '='.repeat(60);
  logger.info(`\n${separator}`);
  logger.info('CALL RECORDING DATA NORMALIZATION PIPELINE');
  logger.info(separator);
  logger.info(`Google Sheets ID: ${env.googleSheetsId}`);
  logger.info(`Google Sheets GID: ${env.googleSheetsGid}`);
  logger.info(`Output directory: ${env.outputDir}`);
  logger.info(`Audio temp directory: ${env.audioTempDir}`);
  logger.info(`Max concurrent processes: ${env.maxConcurrentProcesses}`);
  logger.info(`Cleanup audio after processing: ${env.cleanupAudioAfterProcessing}`);
  logger.info(`${separator}\n`);

  try {
    // Create processor
    const processor = new CallProcessor();

    // Process recordings
    const stats = await processor.processAll({
      fromDate: args.from,
      toDate: args.to,
      rowNumber: args.row ? parseInt(args.row, 10) : undefined,
      fromRow: args['from-row'] ? parseInt(args['from-row'], 10) : undefined,
      toRow: args['to-row'] ? parseInt(args['to-row'], 10) : undefined,
      dryRun: args['dry-run'],
    });

    // Exit with appropriate code
    if (stats.failed > 0) {
      logger.warn(`\nCompleted with ${String(stats.failed)} errors`);
      process.exit(1);
    } else {
      logger.success('\nAll recordings processed successfully!');
      process.exit(0);
    }
  } catch (error) {
    const err = error as Error;
    logger.error('\nFatal error:', err.message);
    if (args.verbose && err.stack) {
      logger.error(err.stack);
    }
    process.exit(1);
  }
}

function showHelp() {
  console.log(`
Call Recording Data Normalization Pipeline

Usage:
  npm start                      Process all recordings
  npm start -- [options]         Process with specific options

Options:
  --from <date>                  Process recordings from this date (e.g., "1/25/26")
  --to <date>                    Process recordings up to this date (e.g., "1/29/26")
  --row <number>                 Process a specific row number
  --from-row <number>            Process from this row number to the end
  --to-row <number>              Process up to this row (use with --from-row for a range)
  --dry-run                      Fetch metadata only, no actual processing
  --verbose                      Enable verbose logging
  --help                         Show this help message

Examples:
  # Process all recordings
  npm start

  # Process specific date range
  npm start -- --from "1/25/26" --to "1/29/26"

  # Process single recording
  npm start -- --row 5

  # Process from row 21 to the end
  npm start -- --from-row 21

  # Process rows 21 to 50
  npm start -- --from-row 21 --to-row 50

  # Dry run (preview what will be processed)
  npm start -- --dry-run

  # Verbose mode
  npm start -- --verbose

Environment Variables:
  See .env.example for required environment variables

Output:
  Processed JSON files will be saved to: ${env.outputDir}/
  Format: call_<date>_<name>_<phone>_<timestamp>.json

Each output file contains:
  - Metadata (date, name, issue type, calling number, duration)
  - Transcription (agent conversation, partner conversation, full transcript)
  - Analysis (summary, problem, solution, sentiments, satisfaction score)
`);
}

// Run main function
main().catch((error) => {
  console.error('Unhandled error:', error);
  process.exit(1);
});
