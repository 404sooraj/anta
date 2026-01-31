/**
 * Upsert vectors to Pinecone indexes. Same indexes as Python getCallInsights.
 * Ensures indexes exist (creates serverless if missing) before upserting.
 */

import { Pinecone } from '@pinecone-database/pinecone';
import type { ScenarioText, PatternText, PolicyText } from './embeddings.js';

const EMBEDDING_DIM = 1536; // Titan Embeddings G1 - Text

/** Pinecone index names must be lowercase alphanumeric or hyphen only. Normalize env names (e.g. call_scenarios → call-scenarios). */
function normalizeIndexName(name: string): string {
  return name.replace(/_/g, '-').toLowerCase();
}

/**
 * Ensure Pinecone indexes exist. Create serverless indexes (dimension 1536) if missing.
 * Uses suppressConflicts so existing indexes are left as-is; waitUntilReady for new ones.
 * Index names are normalized (underscores → hyphens) per Pinecone rules.
 */
export async function ensureIndexes(
  pc: Pinecone,
  indexNames: string[],
  options: { region?: string; verbose?: boolean } = {}
): Promise<void> {
  const region = options.region ?? process.env.PINECONE_REGION ?? 'us-east-1';
  const verbose = options.verbose ?? false;
  const log = (msg: string) => {
    if (verbose) console.log(`[ingest] ${msg}`);
  };

  for (const rawName of indexNames) {
    const name = normalizeIndexName(rawName);
    try {
      log(`Ensuring index exists: ${name} (dimension=${EMBEDDING_DIM}, serverless aws/${region})...`);
      await pc.createIndex({
        name,
        dimension: EMBEDDING_DIM,
        metric: 'cosine',
        spec: {
          serverless: {
            cloud: 'aws',
            region,
          },
        },
        suppressConflicts: true,
        waitUntilReady: true,
      });
      log(`Index ${name} ready.`);
    } catch (e) {
      const err = e as Error;
      throw new Error(`Failed to ensure index "${name}": ${err.message}`);
    }
  }
}

function toPineconeMetadata(obj: Record<string, unknown>): Record<string, string | number | boolean> {
  const out: Record<string, string | number | boolean> = {};
  for (const [k, v] of Object.entries(obj)) {
    if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') out[k] = v;
    else if (v != null) out[k] = String(v);
  }
  return out;
}

export async function upsertScenario(
  pc: Pinecone,
  indexName: string,
  id: string,
  vector: number[],
  item: ScenarioText
): Promise<void> {
  const index = pc.index(normalizeIndexName(indexName));
  await index.upsert([
    {
      id,
      values: vector,
      metadata: toPineconeMetadata({ ...item.metadata, text: item.text.slice(0, 40_000) }),
    },
  ]);
}

export async function upsertPatterns(
  pc: Pinecone,
  indexName: string,
  baseId: string,
  vectors: number[][],
  items: PatternText[]
): Promise<void> {
  if (items.length === 0) return;
  const index = pc.index(normalizeIndexName(indexName));
  await index.upsert(
    items.map((item, i) => ({
      id: `${baseId}_p_${i}`,
      values: vectors[i]!,
      metadata: toPineconeMetadata({ ...item.metadata, text: item.text.slice(0, 40_000) }),
    }))
  );
}

export async function upsertPolicies(
  pc: Pinecone,
  indexName: string,
  baseId: string,
  vectors: number[][],
  items: PolicyText[]
): Promise<void> {
  if (items.length === 0) return;
  const index = pc.index(normalizeIndexName(indexName));
  await index.upsert(
    items.map((item, i) => ({
      id: `${baseId}_pol_${i}`,
      values: vectors[i]!,
      metadata: toPineconeMetadata({ ...item.metadata, text: item.text.slice(0, 40_000) }),
    }))
  );
}
