/**
 * TypeScript HTTP client for multi-language fixture.
 * Known imports: type:./types (type-only import)
 * Known symbols: HttpClient
 * Pattern instances: error_handling (try/catch)
 */

import type { RequestOptions } from './types';

export class HttpClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async get(path: string, options?: RequestOptions): Promise<unknown> {
    try {
      const response = await fetch(`${this.baseUrl}${path}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      return response.json();
    } catch (err) {
      console.error('Request failed:', err);
      throw err;
    }
  }
}
