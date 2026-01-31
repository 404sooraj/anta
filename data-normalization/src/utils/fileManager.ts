/**
 * File management utilities
 */
import { mkdir, writeFile, readFile, unlink, access } from 'fs/promises';
import { dirname } from 'path';
import { constants } from 'fs';
import { logger } from './logger.js';

export class FileManager {
  /**
   * Ensure a directory exists, creating it if necessary
   */
  static async ensureDir(dirPath: string): Promise<void> {
    try {
      await access(dirPath, constants.F_OK);
    } catch {
      await mkdir(dirPath, { recursive: true });
      logger.debug(`Created directory: ${dirPath}`);
    }
  }

  /**
   * Write JSON data to a file
   */
  static async writeJSON(filePath: string, data: unknown): Promise<void> {
    try {
      // Ensure directory exists
      await this.ensureDir(dirname(filePath));
      
      // Write file
      const jsonString = JSON.stringify(data, null, 2);
      await writeFile(filePath, jsonString, 'utf-8');
      logger.debug(`Wrote JSON to: ${filePath}`);
    } catch (error) {
      logger.error(`Failed to write JSON to ${filePath}:`, error);
      throw error;
    }
  }

  /**
   * Read JSON data from a file
   */
  static async readJSON(filePath: string): Promise<unknown> {
    try {
      const content = await readFile(filePath, 'utf-8');
      return JSON.parse(content);
    } catch (error) {
      logger.error(`Failed to read JSON from ${filePath}:`, error);
      throw error;
    }
  }

  /**
   * Delete a file
   */
  static async deleteFile(filePath: string): Promise<void> {
    try {
      await unlink(filePath);
      logger.debug(`Deleted file: ${filePath}`);
    } catch (error) {
      const err = error as NodeJS.ErrnoException;
      if (err.code !== 'ENOENT') {
        logger.warn(`Failed to delete file ${filePath}:`, err.message);
      }
    }
  }

  /**
   * Check if a file exists
   */
  static async fileExists(filePath: string): Promise<boolean> {
    try {
      await access(filePath, constants.F_OK);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Generate a safe filename from a string
   */
  static sanitizeFilename(filename: string): string {
    return filename
      .replace(/[^a-z0-9_-]/gi, '_')
      .replace(/_+/g, '_')
      .toLowerCase();
  }

  /**
   * Generate output filename for processed call
   */
  static generateOutputFilename(metadata: {
    date: string;
    name: string;
    callingNumber: string;
  }): string {
    const datePart = this.sanitizeFilename(metadata.date);
    const namePart = this.sanitizeFilename(metadata.name);
    const phonePart = metadata.callingNumber.slice(-4);
    const timestamp = Date.now();
    
    return `call_${datePart}_${namePart}_${phonePart}_${timestamp}.json`;
  }
}
