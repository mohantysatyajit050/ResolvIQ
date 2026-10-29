import type { Page } from "../types/common";
import type { Order, OrderSummary } from "../types/order";
import { apiClient } from "./client";

export async function fetchOrders(
  limit = 20,
  offset = 0,
): Promise<Page<OrderSummary>> {
  const response = await apiClient.get<Page<OrderSummary>>("/orders", {
    params: { limit, offset },
  });
  return response.data;
}

export async function fetchOrder(orderId: string): Promise<Order> {
  const response = await apiClient.get<Order>(`/orders/${orderId}`);
  return response.data;
}
