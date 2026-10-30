import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { fetchOrders } from "../api/orders";
import { queryKeys } from "../lib/queryKeys";

export function useOrders(limit: number, offset: number) {
  return useQuery({
    queryKey: queryKeys.orders.list(limit, offset),
    queryFn: () => fetchOrders(limit, offset),
    placeholderData: keepPreviousData, // keep the old page visible while the next one loads
  });
}
