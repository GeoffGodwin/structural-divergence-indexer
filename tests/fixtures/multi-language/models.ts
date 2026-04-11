/**
 * TypeScript model definitions for multi-language fixture.
 * Known imports: none
 * Known symbols: User, Product, ApiConfig, Status
 */

export interface User {
  id: number;
  name: string;
  email: string;
}

export interface Product {
  sku: string;
  price: number;
  inStock: boolean;
}

export type ApiConfig = {
  baseUrl: string;
  timeout: number;
};

export type Status = 'active' | 'inactive' | 'pending';
