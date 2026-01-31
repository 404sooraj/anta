/**
 * Google Sheets service - Fetches call recording metadata from public sheet
 * No authentication required since the sheet is public
 */
import axios, { AxiosError } from 'axios';
import { parse } from 'csv-parse/sync';
import { logger } from '../utils/logger.js';
import type { CallRecordingMetadata } from '../types/index.js';

export class GoogleSheetsService {
  private sheetsId: string;
  private gid: string;

  constructor(sheetsId: string, gid: string) {
    this.sheetsId = sheetsId;
    this.gid = gid;
  }

  /**
   * Fetch all call recording metadata from the public Google Sheet
   */
  async fetchCallRecordings(): Promise<CallRecordingMetadata[]> {
    try {
      logger.info('Fetching call recordings from Google Sheets...');
      
      // Construct CSV export URL for public sheet
      const csvUrl = `https://docs.google.com/spreadsheets/d/${this.sheetsId}/export?format=csv&gid=${this.gid}`;
      
      logger.debug(`CSV URL: ${csvUrl}`);
      
      // Fetch CSV data
      const response = await axios.get(csvUrl, {
        responseType: 'text',
        timeout: 30000,
      });

      if (response.status !== 200) {
        throw new Error(`Failed to fetch sheet: HTTP ${response.status}`);
      }

      // Parse CSV
      const records = parse(response.data, {
        columns: true,
        skip_empty_lines: true,
        trim: true,
      });

      logger.info(`Fetched ${records.length} records from Google Sheets`);

      // Map to our metadata format
      const callRecordings: CallRecordingMetadata[] = (records as Record<string, string>[])
        .map((record, index: number) => {
          // Skip if no recording link
          if (!record['Call recording link'] || record['Call recording link'].trim() === '') {
            return null;
          }

          return {
            date: record['Date'] || '',
            name: record['Name'] || '',
            issueType: record['Issue type'] || '',
            recordingLink: record['Call recording link'] || '',
            callingNumber: record['Calling No.'] || '',
            rowNumber: index + 2, // +2 because row 1 is header, array is 0-indexed
          };
        })
        .filter((record): record is CallRecordingMetadata => record !== null);

      logger.success(`Parsed ${callRecordings.length} valid call recordings`);
      
      return callRecordings;
    } catch (error) {
      const axiosError = error as AxiosError;
      const message = axiosError.message || 'Unknown error';
      logger.error('Failed to fetch call recordings from Google Sheets:', message);
      
      if (axiosError.response) {
        logger.error(`HTTP ${axiosError.response.status}: ${axiosError.response.statusText}`);
      }
      
      throw new Error(`Google Sheets fetch failed: ${message}`);
    }
  }

  /**
   * Filter recordings by date range
   */
  filterByDateRange(
    recordings: CallRecordingMetadata[],
    fromDate?: string,
    toDate?: string
  ): CallRecordingMetadata[] {
    if (!fromDate && !toDate) {
      return recordings;
    }

    return recordings.filter((recording) => {
      const recordDate = new Date(recording.date);
      
      if (fromDate) {
        const from = new Date(fromDate);
        if (recordDate < from) {
          return false;
        }
      }
      
      if (toDate) {
        const to = new Date(toDate);
        if (recordDate > to) {
          return false;
        }
      }
      
      return true;
    });
  }

  /**
   * Get a single recording by row number
   */
  getRecordingByRow(
    recordings: CallRecordingMetadata[],
    rowNumber: number
  ): CallRecordingMetadata | undefined {
    return recordings.find((r) => r.rowNumber === rowNumber);
  }
}
