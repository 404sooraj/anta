# Call Recording Data Normalization Pipeline

An automated pipeline for processing call recordings from Google Sheets/Drive with speaker diarization, transcription, and AI-powered analysis.

## Features

- **No Authentication Required**: Accesses public Google Sheets and Drive files without credentials
- **Speaker Diarization**: Automatically separates agent and partner (customer) conversations
- **Transcription**: Uses Soniox async API for accurate speech-to-text with timestamps
- **AI Analysis**: Leverages Claude (AWS Bedrock) for:
  - Conversation summary
  - Problem identification
  - Solution extraction
  - Sentiment analysis (agent & partner)
  - Customer satisfaction scoring
- **Concurrent Processing**: Handles multiple recordings simultaneously
- **Error Handling**: Robust retry logic and graceful error handling

## Prerequisites

- Node.js 18+ (for native fetch support)
- npm or yarn
- API Keys:
  - Soniox API key
  - AWS credentials (for Bedrock/Claude access)

## Installation

1. Install dependencies:

```bash
npm install
```

2. Verify build and code quality:

```bash
npm run check     # Run type-check and lint
npm run build     # Compile TypeScript
```

3. Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

3. Update `.env` with your values:

```env
# Google Sheets (No authentication needed - public sheet)
GOOGLE_SHEETS_ID=your_sheet_id
GOOGLE_SHEETS_GID=your_gid

# Soniox API
SONIOX_API_KEY=your_soniox_api_key

# AWS Bedrock for Claude
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_SESSION_TOKEN=your_aws_session_token
AWS_REGION=us-west-2
BEDROCK_MODEL_ID=anthropic.claude-3-5-haiku-20241022-v1:0

# Processing options
OUTPUT_DIR=./output
AUDIO_TEMP_DIR=./audio
MAX_CONCURRENT_PROCESSES=3
CLEANUP_AUDIO_AFTER_PROCESSING=true
```

## Usage

### Process all recordings

```bash
npm start
```

### Process specific date range

```bash
npm start -- --from "1/25/26" --to "1/29/26"
```

### Process single recording by row number

```bash
npm start -- --row 5
```

### Dry run (preview what will be processed)

```bash
npm start -- --dry-run
```

### Verbose logging

```bash
npm start -- --verbose
```

### Development mode (with auto-reload)

```bash
npm run dev
```

## Output Format

Each processed call generates a JSON file in the `output/` directory with the following structure:

```json
{
  "metadata": {
    "date": "1/29/26 1:45 PM",
    "name": "Jyoti",
    "issueType": "Swap Information Shared",
    "callingNumber": "7248888738",
    "recordingLink": "https://drive.google.com/...",
    "processedAt": "2026-01-31T10:30:00Z",
    "callDuration": 245
  },
  "transcription": {
    "agentConversation": [
      {
        "text": "Hello, how can I help you today?",
        "timestamp": 0.5,
        "speaker": "agent"
      }
    ],
    "partnerConversation": [
      {
        "text": "I need information about battery swap.",
        "timestamp": 3.2,
        "speaker": "partner"
      }
    ],
    "fullTranscript": "Agent: Hello, how can I help you today?\n\nPartner: I need information about battery swap..."
  },
  "analysis": {
    "summary": "Customer inquired about battery swap process and location of nearest station. Agent provided step-by-step instructions and shared station address.",
    "problemFaced": "Customer needed information about the battery swap process and nearest swap station location",
    "solutionPresented": "Agent provided step-by-step swap instructions and shared the nearest station address with navigation details",
    "agentSentiment": {
      "overall": "calm/composed",
      "confidence": 0.85,
      "details": "Agent maintained professional tone throughout the call"
    },
    "partnerSentiment": {
      "overall": "neutral",
      "confidence": 0.78,
      "details": "Customer was inquiring without frustration"
    },
    "partnerSatisfactionScore": {
      "score": 8,
      "maxScore": 10,
      "reasoning": "Issue resolved quickly, customer seemed satisfied with the information provided"
    }
  }
}
```

## Architecture

### Data Flow

```
Google Sheets (CSV Export)
    ↓
Fetch Metadata
    ↓
Google Drive → Download Audio
    ↓
Soniox API → Transcription + Diarization
    ↓
Speaker Classification → Agent vs Partner
    ↓
Claude (AWS Bedrock) → Analysis
    ↓
JSON Output
```

### Services

- **GoogleSheetsService**: Fetches call recording metadata from public sheet (CSV export)
- **GoogleDriveService**: Downloads audio files from public share links
- **SonioxService**: Async transcription with speaker diarization
- **SpeakerClassifier**: Identifies which speaker is agent vs partner
- **ClaudeService**: AI-powered analysis (summary, sentiment, satisfaction)
- **CallProcessor**: Orchestrates the entire pipeline with concurrency control

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_SHEETS_ID` | Google Sheets ID from URL | Required |
| `GOOGLE_SHEETS_GID` | Sheet tab GID from URL | Required |
| `SONIOX_API_KEY` | Soniox API key | Required |
| `AWS_ACCESS_KEY_ID` | AWS access key | Required |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Required |
| `AWS_SESSION_TOKEN` | AWS session token | Required |
| `AWS_REGION` | AWS region | `us-west-2` |
| `BEDROCK_MODEL_ID` | Claude model ID | `anthropic.claude-3-5-haiku-20241022-v1:0` |
| `OUTPUT_DIR` | Output directory | `./output` |
| `AUDIO_TEMP_DIR` | Temporary audio directory | `./audio` |
| `MAX_CONCURRENT_PROCESSES` | Max concurrent processes | `3` |
| `CLEANUP_AUDIO_AFTER_PROCESSING` | Delete audio after processing | `true` |

## Cost Estimation

For 100 recordings (avg 5 minutes each):

- **Soniox Async STT**: ~$0.50/hour × 8.33 hours = **~$4.17**
- **AWS Bedrock Claude**: ~$0.25/million input tokens × ~500k tokens = **~$0.13**
- **Google APIs**: Free (public access)
- **Total**: **~$4.30 for 100 recordings**

## Troubleshooting

### "Failed to fetch sheet" error
- Ensure the Google Sheet is set to "Anyone with the link can view"
- Check that `GOOGLE_SHEETS_ID` and `GOOGLE_SHEETS_GID` are correct

### "Failed to download audio" error
- Ensure the Google Drive files are set to "Anyone with the link can view"
- Check your internet connection
- Try increasing retry attempts in `GoogleDriveService`

### "Soniox API error" error
- Verify your `SONIOX_API_KEY` is correct
- Check Soniox API status
- Ensure audio file format is supported

### "Claude API failed" error
- Verify AWS credentials are correct and not expired
- Check AWS session token is still valid
- Ensure Bedrock model access is enabled in your AWS account

## Development

### TypeScript Quality

This project uses **strict TypeScript** with all recommended checks enabled:

- ✅ Zero compilation errors
- ✅ No `any` types
- ✅ Full type safety
- ✅ Proper error handling with typed errors
- ✅ Barrel exports for clean imports
- ✅ Type-only imports where appropriate

See [TYPESCRIPT_IMPROVEMENTS.md](TYPESCRIPT_IMPROVEMENTS.md) for details.

### Project Structure

```
src/
├── config/
│   └── env.ts              # Environment configuration
├── services/
│   ├── index.ts            # Barrel export
│   ├── googleSheets.ts     # Google Sheets service
│   ├── googleDrive.ts      # Google Drive service
│   ├── soniox.ts           # Soniox transcription
│   ├── speakerClassifier.ts # Speaker classification
│   └── claude.ts           # Claude analysis
├── processors/
│   └── callProcessor.ts    # Main orchestration
├── types/
│   └── index.ts            # TypeScript types
├── utils/
│   ├── index.ts            # Barrel export
│   ├── logger.ts           # Logging utility
│   └── fileManager.ts      # File operations
└── index.ts                # Entry point
```

### Code Quality

```bash
# Run all checks (type-check + lint)
npm run check

# Type checking only
npm run type-check

# Linting only
npm run lint

# Auto-fix lint issues
npm run lint:fix
```

### Build

```bash
npm run build
```

### Run compiled code

```bash
node dist/index.js
```

### Code Quality Status

- ✅ **TypeScript**: Zero compilation errors (strict mode)
- ✅ **ESLint**: Zero linting errors
- ✅ **Type Safety**: 100% with strict checks
- ✅ **No `any` types**: All types explicitly defined
- ✅ **Production Ready**: Passes all quality checks

## License

ISC

## Support

For issues or questions, please check the existing logs with `--verbose` flag for more details.
