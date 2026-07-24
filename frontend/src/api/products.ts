import type { ProductCategory, ProductListResponse } from "../types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export type FetchProductsParams = {
  page?: number;
  size?: number;
  category?: ProductCategory | null;
  search?: string | null;
  signal?: AbortSignal;
};

export async function fetchProducts({
  page = 1,
  size = 20,
  category = null,
  search = null,
  signal,
}: FetchProductsParams = {}): Promise<ProductListResponse> {
  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("size", String(size));
  if (category) params.set("category", category);
  if (search && search.trim()) params.set("search", search.trim());

  const response = await fetch(`${API_BASE_URL}/v1/products?${params.toString()}`, {
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    throw new Error(`Failed to load products (status ${response.status}).`);
  }

  return (await response.json()) as ProductListResponse;
}
