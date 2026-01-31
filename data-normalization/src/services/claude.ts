/**
 * Claude analysis service - Uses AWS Bedrock for LLM analysis
 * Performs: summary, problem/solution extraction, sentiment analysis, satisfaction scoring
 */
import {
  BedrockRuntimeClient,
  InvokeModelCommand,
} from '@aws-sdk/client-bedrock-runtime';
import { logger } from '../utils/logger.js';
import type { CallAnalysis, SentimentAnalysis, SatisfactionScore } from '../types/index.js';

export class ClaudeService {
  private client: BedrockRuntimeClient;
  private modelId: string;
  private maxRetries: number = 3;
  private retryDelay: number = 2000; // ms

  constructor(
    awsAccessKeyId: string,
    awsSecretAccessKey: string,
    awsSessionToken: string,
    awsRegion: string,
    modelId: string
  ) {
    this.client = new BedrockRuntimeClient({
      region: awsRegion,
      credentials: {
        accessKeyId: awsAccessKeyId,
        secretAccessKey: awsSecretAccessKey,
        sessionToken: awsSessionToken,
      },
    });
    this.modelId = modelId;
  }

  /**
   * Analyze call transcript with Claude
   */
  async analyzeCall(
    fullTranscript: string,
    agentConversation: string,
    partnerConversation: string
  ): Promise<CallAnalysis> {
    logger.info('Starting Claude analysis...');

    try {
      // Run all analyses in parallel for efficiency
      const [
        summary,
        problemFaced,
        solutionPresented,
        agentSentiment,
        partnerSentiment,
        satisfactionScore,
      ] = await Promise.all([
        this.generateSummary(fullTranscript),
        this.identifyProblem(fullTranscript),
        this.extractSolution(fullTranscript),
        this.analyzeSentiment(agentConversation, 'agent'),
        this.analyzeSentiment(partnerConversation, 'partner'),
        this.scoreSatisfaction(fullTranscript),
      ]);

      logger.success('Claude analysis completed');

      return {
        summary,
        problemFaced,
        solutionPresented,
        agentSentiment,
        partnerSentiment,
        partnerSatisfactionScore: satisfactionScore,
      };
    } catch (error) {
      const err = error as Error;
      logger.error('Claude analysis failed:', err.message);
      throw new Error(`Analysis failed: ${err.message}`);
    }
  }

  /**
   * Generate conversation summary
   */
  private async generateSummary(transcript: string): Promise<string> {
    const prompt = `Analyze this customer service call transcript and provide a concise 2-3 sentence summary of:
- The customer's issue or inquiry
- How the agent responded
- The outcome

Transcript:
${transcript}

Respond with ONLY the summary text, no additional formatting or labels.`;

    return await this.callClaude(prompt, 'summary generation');
  }

  /**
   * Identify problem faced by partner
   */
  private async identifyProblem(transcript: string): Promise<string> {
    const prompt = `Based on this customer service call transcript, identify and describe the specific problem or issue that the partner (customer) was facing.

Be specific and concise. Focus on what the customer needed help with or what issue they reported.

Transcript:
${transcript}

Respond with ONLY the problem description, no additional formatting or labels.`;

    return await this.callClaude(prompt, 'problem identification');
  }

  /**
   * Extract solution presented by agent
   */
  private async extractSolution(transcript: string): Promise<string> {
    const prompt = `Based on this customer service call transcript, describe the solution or resolution that the agent presented to address the partner's (customer's) problem.

Be specific about what actions the agent took or what information/guidance they provided.

Transcript:
${transcript}

Respond with ONLY the solution description, no additional formatting or labels.`;

    return await this.callClaude(prompt, 'solution extraction');
  }

  /**
   * Analyze sentiment for agent or partner
   */
  private async analyzeSentiment(
    conversation: string,
    role: 'agent' | 'partner'
  ): Promise<SentimentAnalysis> {
    const prompt = `Analyze the sentiment and emotional tone of the ${role} in this call transcript.

Classify their overall sentiment as ONE of these options:
- calm/composed
- happy
- neutral
- concerned
- frustrated
- sad
- angry
- infuriated

${role === 'agent' ? 'Agent' : 'Partner'} conversation:
${conversation}

Respond with a JSON object in this EXACT format (no additional text):
{
  "overall": "<sentiment_classification>",
  "confidence": <number_between_0_and_1>,
  "details": "<brief_explanation>"
}`;

    const response = await this.callClaude(prompt, `${role} sentiment analysis`);

    try {
      const parsed = JSON.parse(response);
      return {
        overall: parsed.overall,
        confidence: parsed.confidence,
        details: parsed.details,
      };
    } catch {
      logger.warn(`Failed to parse sentiment JSON, using fallback for ${role}`);
      return {
        overall: 'neutral',
        confidence: 0.5,
        details: response.substring(0, 200),
      };
    }
  }

  /**
   * Score partner satisfaction
   */
  private async scoreSatisfaction(transcript: string): Promise<SatisfactionScore> {
    const prompt = `Based on this customer service call transcript, rate the customer's satisfaction level.

Consider:
- Was their issue resolved?
- Did they express gratitude or frustration?
- Was the agent helpful and responsive?
- Did the customer seem satisfied at the end?

Transcript:
${transcript}

Respond with a JSON object in this EXACT format (no additional text):
{
  "score": <number_between_0_and_10>,
  "reasoning": "<explanation_for_score>"
}`;

    const response = await this.callClaude(prompt, 'satisfaction scoring');

    try {
      const parsed = JSON.parse(response);
      return {
        score: parsed.score,
        maxScore: 10,
        reasoning: parsed.reasoning,
      };
    } catch {
      logger.warn('Failed to parse satisfaction JSON, using fallback');
      return {
        score: 5,
        maxScore: 10,
        reasoning: response.substring(0, 200),
      };
    }
  }

  /**
   * Call Claude via AWS Bedrock
   */
  private async callClaude(prompt: string, context: string): Promise<string> {
    for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
      try {
        logger.debug(`Claude API call: ${context} (attempt ${attempt}/${this.maxRetries})`);

        const request = {
          anthropic_version: 'bedrock-2023-05-31',
          max_tokens: 2048,
          temperature: 0.7,
          messages: [
            {
              role: 'user',
              content: prompt,
            },
          ],
        };

        const command = new InvokeModelCommand({
          modelId: this.modelId,
          contentType: 'application/json',
          accept: 'application/json',
          body: JSON.stringify(request),
        });

        const response = await this.client.send(command);

        if (!response.body) {
          throw new Error('Empty response from Claude');
        }

        const responseBody = JSON.parse(new TextDecoder().decode(response.body));

        if (responseBody.content && responseBody.content.length > 0) {
          const text = responseBody.content[0].text;
          logger.debug(`Claude response for ${context}: ${text.substring(0, 100)}...`);
          return text.trim();
        }

        throw new Error('Invalid response format from Claude');
      } catch (error) {
        const err = error as Error;
        logger.warn(`Claude API call failed (attempt ${attempt}/${this.maxRetries}):`, err.message);

        if (attempt < this.maxRetries) {
          const delay = this.retryDelay * Math.pow(2, attempt - 1);
          logger.info(`Retrying in ${delay}ms...`);
          await this.sleep(delay);
        } else {
          throw new Error(`Claude API failed after ${this.maxRetries} attempts: ${err.message}`);
        }
      }
    }

    throw new Error('Claude API call failed');
  }

  /**
   * Sleep utility
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
