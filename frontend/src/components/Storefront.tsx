import { useProducts } from "../hooks/useProducts";
import type { Product } from "../types";
import { ProductCard } from "./ProductCard";

export function Storefront({ onAsk }: { onAsk: (product: Product) => void }) {
  const {
    products,
    total,
    category,
    setCategory,
    search,
    setSearch,
    isLoading,
    error,
    categories,
  } = useProducts();

  return (
    <div className="storefront">
      <header className="store-header">
        <div className="store-brand">
          <span className="store-logo" aria-hidden="true">
            🛒
          </span>
          <div>
            <p className="section-label">AbhiMart</p>
            <h1 className="store-title">Shop the catalog</h1>
          </div>
        </div>

        <input
          type="search"
          className="store-search"
          placeholder="Search products…"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          aria-label="Search products"
        />
      </header>

      <div className="category-bar" role="tablist" aria-label="Product categories">
        <button
          type="button"
          className={`category-chip ${category === null ? "active" : ""}`}
          onClick={() => setCategory(null)}
        >
          All
        </button>
        {categories.map((cat) => (
          <button
            key={cat}
            type="button"
            className={`category-chip ${category === cat ? "active" : ""}`}
            onClick={() => setCategory(cat)}
          >
            {cat}
          </button>
        ))}
      </div>

      {error ? <p className="error-banner">{error}</p> : null}

      {isLoading ? (
        <div className="store-status">Loading products…</div>
      ) : products.length === 0 ? (
        <div className="store-status">
          No products found{search ? ` for “${search}”` : ""}.
        </div>
      ) : (
        <>
          <p className="result-count">
            {total} product{total === 1 ? "" : "s"}
            {category ? ` in ${category}` : ""}
          </p>
          <div className="product-grid">
            {products.map((product) => (
              <ProductCard key={product.id} product={product} onAsk={onAsk} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
