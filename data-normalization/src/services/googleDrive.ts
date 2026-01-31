/**
 * Google Drive service - Downloads audio files from public share links
 * No authentication required since files are publicly shared
 */
import axios from 'axios';
import { createWriteStream } from 'fs';
import { join } from 'path';
import { pipeline } from 'stream/promises';
import { logger } from '../utils/logger.js';
import { FileManager } from '../utils/fileManager.js';

export class GoogleDriveService {
  private audioTempDir: string;
  private maxRetries: number = 3;
  private retryDelay: number = 2000; // ms

  constructor(audioTempDir: string) {
    this.audioTempDir = audioTempDir;
  }

  /**
   * Extract file ID from Google Drive share link
   */
  private extractFileId(driveLink: string): string {
    // Format: https://drive.google.com/file/d/{FILE_ID}/view
    const match = driveLink.match(/\/d\/([a-zA-Z0-9_-]+)/);
    if (!match || !match[1]) {
      throw new Error(`Invalid Google Drive link format: ${driveLink}`);
    }
    return match[1];
  }

  /**
   * Download audio file from Google Drive
   */
  async downloadAudio(driveLink: string, outputFilename: string): Promise<string> {
    const fileId = this.extractFileId(driveLink);

    // Ensure audio directory exists
    await FileManager.ensureDir(this.audioTempDir);

    const outputPath = join(this.audioTempDir, outputFilename);

    // Check if file already exists
    if (await FileManager.fileExists(outputPath)) {
      logger.debug(`Audio file already exists: ${outputPath}`);
      return outputPath;
    }

    logger.info(`Downloading audio from Google Drive (ID: ${fileId})...`);

    for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
      try {
        await this.downloadWithRetry(fileId, outputPath);
        logger.success(`Downloaded audio to: ${outputPath}`);
        return outputPath;
      } catch (error) {
        const err = error as Error;
        logger.warn(`Download attempt ${attempt}/${this.maxRetries} failed:`, err.message);
        
        if (attempt < this.maxRetries) {
          const delay = this.retryDelay * Math.pow(2, attempt - 1);
          logger.info(`Retrying in ${delay}ms...`);
          await this.sleep(delay);
        } else {
          throw new Error(`Failed to download audio after ${this.maxRetries} attempts: ${err.message}`);
        }
      }
    }

    // This line should never be reached due to the throw in the loop
    throw new Error('Download failed after all retries');
  }

  /**
   * Perform the actual download with stream handling
   */
  private async downloadWithRetry(fileId: string, outputPath: string): Promise<void> {
    // Direct download URL for public files
    const downloadUrl = `https://drive.google.com/uc?export=download&id=${fileId}`;
    
    try {
      // First request to get the file or confirmation page
      const response = await axios.get(downloadUrl, {
        responseType: 'stream',
        timeout: 60000,
        maxRedirects: 5,
        validateStatus: (status) => status === 200 || status === 302 || status === 303,
      });

      // Check if we got a confirmation page (for large files)
      const contentType = response.headers['content-type'];
      
      if (contentType && contentType.includes('text/html')) {
        // Large file - need to extract confirmation token
        logger.debug('Large file detected, extracting confirmation token...');
        
        // For large files, we need to use a different approach
        // We'll use the confirm parameter
        const confirmUrl = `https://drive.google.com/uc?export=download&id=${fileId}&confirm=t`;
        
        const confirmedResponse = await axios.get(confirmUrl, {
          responseType: 'stream',
          timeout: 120000,
          maxRedirects: 5,
        });

        await pipeline(confirmedResponse.data, createWriteStream(outputPath));
      } else {
        // Small file - direct download
        await pipeline(response.data, createWriteStream(outputPath));
      }

    } catch (error) {
      // Clean up partial download
      await FileManager.deleteFile(outputPath);
      const err = error as Error;
      throw new Error(`Download failed: ${err.message}`);
    }
  }

  /**
   * Delete downloaded audio file
   */
  async deleteAudio(filePath: string): Promise<void> {
    await FileManager.deleteFile(filePath);
  }

  /**
   * Sleep utility for retry delays
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * Generate a safe filename for the audio file
   */
  generateAudioFilename(metadata: { name: string; callingNumber: string }): string {
    const namePart = FileManager.sanitizeFilename(metadata.name);
    const phonePart = metadata.callingNumber.slice(-4);
    const timestamp = Date.now();
    
    return `audio_${namePart}_${phonePart}_${timestamp}.m4a`;
  }
}
