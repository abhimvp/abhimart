import { useEffect, useState } from "react";
import { fetchProducts } from "../api/products";
import type { Product, ProductCategory } from "../types";

const CATEGORIES: ProductCategory[] = [
  "electronics",
  "appliances",
  "fitness",
  "books",
];

export function useProducts() {
  const [products, setProducts] = useState<Product[]>([]);
  const [category, setCategory] = useState<ProductCategory | null>(null);
  const [search, setSearch] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    // Debounce so we don't fire a request on every keystroke.
    const timer = setTimeout(() => {
      setIsLoading(true);
      setError(null);
      fetchProducts({
        category,
        search,
        size: 100,
        signal: controller.signal,
      })
        .then((data) => {
          setProducts(data.items);
          setTotal(data.total);
        })
        .catch((err: unknown) => {
          if (err instanceof DOMException && err.name === "AbortError") return;
          setError(
            err instanceof Error ? err.message : "Could not load products.",
          );
          setProducts([]);
        })
        .finally(() => setIsLoading(false));
    }, 250);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [category, search]);

  return {
    products,
    total,
    category,
    setCategory,
    search,
    setSearch,
    isLoading,
    error,
    categories: CATEGORIES,
  };
}
