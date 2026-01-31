/**
 * Offline data-ingestion: read one call JSON, classify, build embeddings (LangChain), upsert to Pinecone.
 * Same embedding model as Python getCallInsights. Switch model by changing the embeddings instance (e.g. BedrockEmbeddings → OpenAIEmbeddings).
 */

import 'dotenv/config';
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { parseArgs } from 'node:util';
import { BedrockEmbeddings } from '@langchain/aws';
import { Pinecone } from '@pinecone-database/pinecone';
import { classifyCall } from './classifier.js';
import {
  buildScenarioText,
  buildPatternTexts,
  buildPolicyTexts,
  embedTexts,
  type ScenarioText,
  type PatternText,
  type PolicyText,
} from './embeddings.js';
import { ensureIndexes, upsertScenario, upsertPatterns, upsertPolicies } from './pinecone.js';
import type { CallRecordForIngestion } from './types.js';

function createEmbeddings(): BedrockEmbeddings {
  const region = process.env.AWS_REGION ?? 'us-west-2';
  const model = process.env.BEDROCK_EMBEDDING_MODEL_ID ?? 'amazon.titan-embed-text-v1:0';
  const config: { region: string; model: string; credentials?: { accessKeyId: string; secretAccessKey: string; sessionToken?: string } } = {
    region,
    model,
  };
  if (process.env.AWS_ACCESS_KEY_ID && process.env.AWS_SECRET_ACCESS_KEY) {
    config.credentials = {
      accessKeyId: process.env.AWS_ACCESS_KEY_ID,
      secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
      sessionToken: process.env.AWS_SESSION_TOKEN,
    };
  }
  return new BedrockEmbeddings(config);
}

function loadRecord(path: string): CallRecordForIngestion {
  const raw = readFileSync(path, 'utf-8');
  const data = JSON.parse(raw) as { metadata?: unknown; analysis?: unknown };
  if (!data.metadata || !data.analysis) throw new Error(`Invalid record: missing metadata or analysis at ${path}`);
  return data as CallRecordForIngestion;
}

function stableId(filePath: string, processedAt: string): string {
  const input = `${filePath}:${processedAt}`;
  return createHash('sha256').update(input).digest('hex').slice(0, 24);
}

function log(verbose: boolean, msg: string, ...args: unknown[]): void {
  if (verbose) console.log(`[ingest] ${msg}`, ...args);
}

async function ingestOne(
  filePath: string,
  embeddings: BedrockEmbeddings,
  pc: Pinecone,
  indexScenarios: string,
  indexPatterns: string,
  indexPolicy: string,
  verbose: boolean
): Promise<void> {
  log(verbose, `Processing: ${filePath}`);

  const record = loadRecord(filePath);
  log(verbose, '  Loaded record, classifying...');
  const classified = classifyCall(record);
  log(verbose, `  Classified: issue_type=${classified.issueType} resolution=${classified.resolution} escalated=${classified.escalated} sentiment=${classified.dominantSentiment}`);

  const baseId = stableId(filePath, record.metadata.processedAt);

  const scenario: ScenarioText = buildScenarioText(record, classified);
  log(verbose, '  Embedding 1 scenario...');
  const scenarioVectors = await embedTexts(embeddings, [scenario.text]);
  log(verbose, `  Upserting to ${indexScenarios} (id=cs_${baseId})`);
  await upsertScenario(pc, indexScenarios, `cs_${baseId}`, scenarioVectors[0]!, scenario);

  const patterns = buildPatternTexts(record, classified);
  if (patterns.length > 0) {
    log(verbose, `  Embedding ${patterns.length} pattern(s)...`);
    const patternTexts = patterns.map((p) => p.text);
    const patternVectors = await embedTexts(embeddings, patternTexts);
    log(verbose, `  Upserting to ${indexPatterns} (${patterns.length} vectors)`);
    await upsertPatterns(pc, indexPatterns, baseId, patternVectors, patterns);
  } else {
    log(verbose, '  No patterns to embed');
  }

  const policies = buildPolicyTexts(record);
  if (policies.length > 0) {
    log(verbose, `  Embedding ${policies.length} policy snippet(s)...`);
    const policyTexts = policies.map((p) => p.text);
    const policyVectors = await embedTexts(embeddings, policyTexts);
    log(verbose, `  Upserting to ${indexPolicy} (${policies.length} vectors)`);
    await upsertPolicies(pc, indexPolicy, baseId, policyVectors, policies);
  } else {
    log(verbose, '  No policy snippets to embed');
  }

  log(verbose, `  Done: ${filePath}`);
}

async function main(): Promise<void> {
  const { values } = parseArgs({
    options: {
      file: { type: 'string', description: 'Path to one call JSON' },
      dir: { type: 'string', description: 'Directory of call JSONs (process each)' },
      verbose: { type: 'boolean', short: 'v', description: 'Verbose logging (show every step)' },
      help: { type: 'boolean', description: 'Show help' },
    },
  });

  const verbose = Boolean(values.verbose);

  if (values.help) {
    console.log('Usage: npm start -- [options] --file <path> | --dir <path>');
    console.log('Options:');
    console.log('  --verbose, -v    Verbose logging (show every step)');
    console.log('Env: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, PINECONE_API_KEY, PINECONE_INDEX_*');
    console.log('Embeddings: LangChain BedrockEmbeddings (set BEDROCK_EMBEDDING_MODEL_ID to switch model).');
    process.exit(0);
  }

  const pineconeKey = process.env.PINECONE_API_KEY;
  const indexScenarios = process.env.PINECONE_INDEX_CALL_SCENARIOS ?? 'call_scenarios';
  const indexPatterns = process.env.PINECONE_INDEX_RESPONSE_PATTERNS ?? 'response_patterns';
  const indexPolicy = process.env.PINECONE_INDEX_POLICY_KNOWLEDGE ?? 'policy_knowledge';

  if (!pineconeKey) {
    console.error('Missing PINECONE_API_KEY');
    process.exit(1);
  }

  const embeddings = createEmbeddings();
  const pc = new Pinecone({ apiKey: pineconeKey });

  const indexNames = [indexScenarios, indexPatterns, indexPolicy];
  log(verbose, 'Ensuring Pinecone indexes exist (creating if missing)...');
  await ensureIndexes(pc, indexNames, { region: process.env.PINECONE_REGION ?? undefined, verbose });

  const files: string[] = [];
  if (values.file) files.push(values.file);
  if (values.dir) {
    const dir = values.dir;
    for (const name of readdirSync(dir)) {
      if (name.endsWith('.json')) files.push(join(dir, name));
    }
  }
  if (files.length === 0) {
    console.error('Provide --file <path> or --dir <path>');
    process.exit(1);
  }

  log(verbose, `Found ${files.length} file(s). Indexes: ${indexScenarios}, ${indexPatterns}, ${indexPolicy}`);

  for (let i = 0; i < files.length; i++) {
    const f = files[i]!;
    try {
      if (verbose && files.length > 1) log(verbose, `\n--- File ${i + 1}/${files.length} ---`);
      await ingestOne(f, embeddings, pc, indexScenarios, indexPatterns, indexPolicy, verbose);
    } catch (e) {
      console.error(`Failed ${f}:`, (e as Error).message);
      process.exit(1);
    }
  }

  if (verbose) console.log(`\n[ingest] Completed ${files.length} file(s).`);
}

main();
