/**
 * Environment configuration loader
 */
import { config } from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

// Load .env file
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
config({ path: join(__dirname, '../../.env') });

export interface Config {
  // Google Sheets
  googleSheetsId: string;
  googleSheetsGid: string;
  
  // Soniox
  sonioxApiKey: string;
  
  // AWS Bedrock
  awsAccessKeyId: string;
  awsSecretAccessKey: string;
  awsSessionToken: string;
  awsRegion: string;
  bedrockModelId: string;
  
  // Processing options
  outputDir: string;
  audioTempDir: string;
  maxConcurrentProcesses: number;
  cleanupAudioAfterProcessing: boolean;
}

function getEnvVar(key: string, defaultValue?: string): string {
  const value = process.env[key] || defaultValue;
  if (!value) {
    throw new Error(`Environment variable ${key} is required but not set`);
  }
  return value;
}

function getEnvVarBoolean(key: string, defaultValue: boolean): boolean {
  const value = process.env[key];
  if (value === undefined) {
    return defaultValue;
  }
  return value.toLowerCase() === 'true';
}

function getEnvVarNumber(key: string, defaultValue: number): number {
  const value = process.env[key];
  if (value === undefined) {
    return defaultValue;
  }
  const parsed = parseInt(value, 10);
  if (isNaN(parsed)) {
    return defaultValue;
  }
  return parsed;
}

export const env: Config = {
  googleSheetsId: getEnvVar('GOOGLE_SHEETS_ID'),
  googleSheetsGid: getEnvVar('GOOGLE_SHEETS_GID'),
  
  sonioxApiKey: getEnvVar('SONIOX_API_KEY'),
  
  awsAccessKeyId: getEnvVar('AWS_ACCESS_KEY_ID'),
  awsSecretAccessKey: getEnvVar('AWS_SECRET_ACCESS_KEY'),
  awsSessionToken: getEnvVar('AWS_SESSION_TOKEN'),
  awsRegion: getEnvVar('AWS_REGION', 'us-west-2'),
  bedrockModelId: getEnvVar('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-haiku-20241022-v1:0'),
  
  outputDir: getEnvVar('OUTPUT_DIR', './output'),
  audioTempDir: getEnvVar('AUDIO_TEMP_DIR', './audio'),
  maxConcurrentProcesses: getEnvVarNumber('MAX_CONCURRENT_PROCESSES', 3),
  cleanupAudioAfterProcessing: getEnvVarBoolean('CLEANUP_AUDIO_AFTER_PROCESSING', true),
};
