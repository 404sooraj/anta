# Data Ingestion (Pinecone)

Offline pipeline: read call-record JSONs → classify → embed (LangChain Bedrock) → upsert to Pinecone. Same embedding model as the server `getCallInsights` tool.

## Setup

1. **Copy env and set values**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set:
   - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` (and `AWS_SESSION_TOKEN` if using temporary creds)
   - `PINECONE_API_KEY`
   - `PINECONE_INDEX_CALL_SCENARIOS`, `PINECONE_INDEX_RESPONSE_PATTERNS`, `PINECONE_INDEX_POLICY_KNOWLEDGE` (defaults: `call_scenarios`, `response_patterns`, `policy_knowledge`)
   - Optional: `BEDROCK_EMBEDDING_MODEL_ID` (default: `amazon.titan-embed-text-v1:0`)

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Pinecone indexes**  
   The pipeline **creates the three indexes automatically** if they don't exist (serverless, dimension 1536, AWS region from `PINECONE_REGION` or `us-east-1`). Free tier supports `us-east-1` only; set `PINECONE_REGION` for other regions on paid plans. You can also create them manually in the Pinecone console; names must match the env vars above.

## Scripts to run

From the `data-ingestion` folder:

**Ingest all call JSONs from the data-normalization output folder**
```bash
npm run ingest:dir
```
This runs: `tsx src/index.ts -- --dir ../data-normalization/output`

**Same, with verbose logging (see every step: load, classify, embed, upsert)**
```bash
npm run ingest:dir:verbose
```
Or: `npm start -- --dir ../data-normalization/output --verbose` (short: `-v`)

**Ingest a single file**
```bash
npm run ingest:file -- path/to/call_xxx.json
```
Or:
```bash
npm start -- --file path/to/call_xxx.json
```

**Ingest a custom directory**
```bash
npm start -- --dir /absolute/or/relative/path/to/json/folder
```

**Help**
```bash
npm start -- --help
```

## Summary

| What you want              | Command |
|----------------------------|--------|
| Ingest all from norm output| `npm run ingest:dir` |
| Same, verbose logging      | `npm run ingest:dir:verbose` or `npm start -- --dir <path> --verbose` |
| Ingest one file            | `npm start -- --file path/to/file.json` |
| Ingest another folder      | `npm start -- --dir path/to/folder` |
| Verbose (any run)          | Add `--verbose` or `-v` to any command |

## After ingestion: next steps

1. **Verify (optional)**  
   In the [Pinecone console](https://app.pinecone.io), check that your indexes (`call-scenarios`, `response-patterns`, `policy-knowledge`) exist and have vectors. Index names use hyphens because Pinecone requires lowercase alphanumeric or `-`.

2. **Run the server**  
   The FastAPI server uses the same Pinecone indexes and Bedrock embedding model. From the **server** folder:
   ```bash
   cp .env.example .env   # if not done
   # Set PINECONE_API_KEY, AWS credentials, and BEDROCK_EMBEDDING_MODEL_ID (optional) in server/.env
   uv run main.py
   ```
   The AI will call `getCallInsights` when it needs similar past scenarios or policy (e.g. penalty disputes, battery swap, general support).

3. **Test the flow**  
   Send a user message that should trigger similar-past-cases or policy lookup (e.g. “Customer wants penalty removed after late battery return”). The response pipeline will use `getCallInsights` with a `situation_summary` and return similar scenarios, response patterns, and policy snippets to guide the reply.

4. **Re-run ingestion when needed**  
   Run the pipeline again when you add new call-record JSONs (e.g. after new data-normalization output). Upserts are by record ID; re-ingesting the same file updates existing vectors. Use `--dir`, `--file`, or row/date filters in data-normalization as needed.
