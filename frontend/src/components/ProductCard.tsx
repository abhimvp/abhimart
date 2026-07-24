import type { Product } from "../types";

const CATEGORY_EMOJI: Record<string, string> = {
  electronics: "🎧",
  appliances: "🔌",
  fitness: "🏋️",
  books: "📚",
};

function formatPrice(price: number | string) {
  const value = typeof price === "string" ? Number(price) : price;
  if (Number.isNaN(value)) return String(price);
  return value.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
  });
}

export function ProductCard({
  product,
  onAsk,
}: {
  product: Product;
  onAsk: (product: Product) => void;
}) {
  const inStock = product.stock_quantity > 0;
  const lowStock = inStock && product.stock_quantity <= 5;

  return (
    <article className="product-card">
      <div className="product-thumb" aria-hidden="true">
        {CATEGORY_EMOJI[product.category] ?? "🛍️"}
      </div>

      <div className="product-body">
        <p className="product-category">{product.category}</p>
        <h3 className="product-name">{product.name}</h3>
        <p className="product-description">{product.description}</p>
      </div>

      <div className="product-footer">
        <div className="product-meta">
          <span className="product-price">{formatPrice(product.price)}</span>
          <span
            className={`stock-badge ${
              inStock ? (lowStock ? "low" : "in") : "out"
            }`}
          >
            {inStock
              ? lowStock
                ? `Only ${product.stock_quantity} left`
                : "In stock"
              : "Out of stock"}
          </span>
        </div>
        <button
          type="button"
          className="ask-button"
          onClick={() => onAsk(product)}
        >
          Ask AI about this
        </button>
      </div>
    </article>
  );
}
