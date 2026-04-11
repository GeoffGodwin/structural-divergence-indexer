/**
 * TypeScript API module for multi-language fixture.
 * Known imports: ./models, ./client, react
 * Known symbols: UserApi, fetchUser, createUser
 * Pattern instances: error_handling (try/catch)
 */

import { User, Product } from './models';
import type { ApiConfig } from './types';
import { HttpClient } from './client';

export class UserApi {
  private client: HttpClient;

  constructor(config: ApiConfig) {
    this.client = new HttpClient(config.baseUrl);
  }

  async fetchUser(id: number): Promise<User | null> {
    try {
      const data = await this.client.get(`/users/${id}`);
      return data as User;
    } catch (err) {
      console.error('Failed to fetch user:', err);
      return null;
    }
  }
}

export function createUser(name: string, email: string): User {
  return { id: Date.now(), name, email } as unknown as User;
}
