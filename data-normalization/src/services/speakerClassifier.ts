/**
 * Speaker classification - Identifies which speaker is agent vs partner
 */
import { logger } from '../utils/logger.js';
import type { SpeakerToken } from '../types/index.js';

export class SpeakerClassifier {
  /**
   * Classify speakers as agent or partner
   * Uses simple heuristic: first speaker is likely the agent (they answer the call)
   */
  classifySpeakers(tokens: SpeakerToken[]): Record<string, 'agent' | 'partner'> {
    if (tokens.length === 0) {
      return {};
    }

    // Get unique speakers in order of appearance
    const speakersInOrder: string[] = [];
    const seenSpeakers = new Set<string>();

    for (const token of tokens) {
      if (token.speaker && !seenSpeakers.has(token.speaker)) {
        speakersInOrder.push(token.speaker);
        seenSpeakers.add(token.speaker);
      }
    }

    logger.debug(`Found ${speakersInOrder.length} speakers: ${speakersInOrder.join(', ')}`);

    // Simple heuristic: first speaker is agent, second is partner
    const mapping: Record<string, 'agent' | 'partner'> = {};

    if (speakersInOrder.length >= 1 && speakersInOrder[0]) {
      mapping[speakersInOrder[0]] = 'agent';
    }

    if (speakersInOrder.length >= 2 && speakersInOrder[1]) {
      mapping[speakersInOrder[1]] = 'partner';
    }

    // If more than 2 speakers, classify remaining as partner
    for (let i = 2; i < speakersInOrder.length; i++) {
      const speaker = speakersInOrder[i];
      if (speaker) {
        mapping[speaker] = 'partner';
      }
    }

    logger.info('Speaker classification:', mapping);

    return mapping;
  }

  /**
   * Alternative: LLM-based classification (more accurate but requires extra API call)
   * This can be implemented later if the simple heuristic doesn't work well
   */
  async classifySpeakersWithLLM(
    tokens: SpeakerToken[],
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    llmAnalyzer: any
  ): Promise<Record<string, 'agent' | 'partner'>> {
    // Extract first few exchanges between speakers
    const firstExchanges = this.extractFirstExchanges(tokens, 4);

    // Ask LLM to classify
    const prompt = `
Analyze this customer service call transcript and identify which speaker is the agent (customer service representative) and which is the partner (customer).

The agent typically:
- Answers the call first
- Uses formal, professional language
- Asks questions to understand the issue
- Provides solutions or information
- Uses company-specific terminology

The partner typically:
- Calls for help or information
- Describes their problem or question
- May express concerns or frustration

Transcript:
${firstExchanges}

Respond with ONLY a JSON object in this format:
{"speakerMapping": {"1": "agent", "2": "partner"}}
`;

    try {
      const response = await llmAnalyzer.analyze(prompt);
      const result = JSON.parse(response);
      return result.speakerMapping;
    } catch {
      logger.warn('LLM-based classification failed, falling back to heuristic');
      return this.classifySpeakers(tokens);
    }
  }

  /**
   * Extract first few speaker exchanges for analysis
   */
  private extractFirstExchanges(tokens: SpeakerToken[], maxExchanges: number): string {
    const exchanges: string[] = [];
    let currentSpeaker: string | null = null;
    let currentText = '';
    let exchangeCount = 0;

    for (const token of tokens) {
      if (token.speaker !== currentSpeaker) {
        if (currentSpeaker !== null) {
          exchanges.push(`Speaker ${currentSpeaker}: ${currentText.trim()}`);
          exchangeCount++;
          
          if (exchangeCount >= maxExchanges) {
            break;
          }
        }
        currentSpeaker = token.speaker;
        currentText = token.text;
      } else {
        currentText += token.text;
      }
    }

    // Add final exchange
    if (currentSpeaker !== null && exchangeCount < maxExchanges) {
      exchanges.push(`Speaker ${currentSpeaker}: ${currentText.trim()}`);
    }

    return exchanges.join('\n\n');
  }
}
