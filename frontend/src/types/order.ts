export type OrderStatus =
  | "placed"
  | "shipped"
  | "out_for_delivery"
  | "delivered"
  | "cancelled"
  | "returned";

export type Address = {
  id: string;
  address_line: string;
  city: string;
  state: string;
  pincode: string;
};

export type ProductBrief = {
  id: string;
  name: string;
  category: string;
};

export type OrderItem = {
  id: string;
  product: ProductBrief;
  quantity: number;
  unit_price_paise: number;
  line_total_paise: number;
};

export type OrderSummary = {
  id: string;
  user_id: string;
  status: OrderStatus;
  total_paise: number;
  ordered_at: string;
  expected_delivery_date: string | null;
  delivered_at: string | null;
};

export type Order = OrderSummary & {
  shipping_address: Address;
  items: OrderItem[];
};
