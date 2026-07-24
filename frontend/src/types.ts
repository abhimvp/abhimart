// This file defines the shapes of data the UI expects.

export type ChatMessageRole = "user" | "assistant" | "system";

export type ChatMessage = {
  id: string;
  role: ChatMessageRole;
  content: string;
};

export type RefundInterrupt = {
  kind: "refund_approval_required";
  action: "review_refund_request";
  refund_request_id: string;
  refund_status: string;
  order_id?: string;
  order_id_preview?: string;
  order_status?: string;
  total_amount?: string;
  customer_email?: string;
  customer_email_domain?: string;
  customer_name?: string;
  items?: Array<{
    product_name?: string;
    qty?: number;
    price?: string | number;
  }>;
  message?: string;
};

export type StreamPayload =
  | {
      text: string;
    }
  | {
      type: "interrupt";
      interrupt: RefundInterrupt;
    };

// --- Storefront ---

export type ProductCategory = "electronics" | "appliances" | "fitness" | "books";

export type Product = {
  id: string;
  name: string;
  description: string;
  // FastAPI may serialize the Decimal price as a number or a string,
  // so accept both and coerce in the UI.
  price: number | string;
  category: ProductCategory;
  sku: string;
  stock_quantity: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type ProductListResponse = {
  items: Product[];
  total: number;
  page: number;
  size: number;
  pages: number;
};
