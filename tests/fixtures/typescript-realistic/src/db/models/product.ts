// Product database model.
import type { Product } from "@/types";

export interface ProductRow {
  id: string;
  name: string;
  description: string;
  price: string;
  stock: number;
  category: string;
}

export function rowToProduct(row: ProductRow): Product {
  return {
    id: row.id,
    name: row.name,
    description: row.description,
    price: parseFloat(row.price),
    stock: row.stock,
    category: row.category,
  };
}

export function productInsertParams(p: Omit<Product, "id">) {
  return {
    name: p.name,
    description: p.description,
    price: p.price.toFixed(2),
    stock: p.stock,
    category: p.category,
  };
}

export const PRODUCT_SELECT_COLUMNS = [
  "id",
  "name",
  "description",
  "price",
  "stock",
  "category",
].join(", ");
