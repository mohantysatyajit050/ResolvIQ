import { ORDER_STATUS_LABEL } from "../../lib/labels";
import type { OrderStatus } from "../../types/order";

const COLORS: Record<OrderStatus, string> = {
  placed: "bg-slate-100 text-slate-700",
  shipped: "bg-blue-100 text-blue-800",
  out_for_delivery: "bg-indigo-100 text-indigo-800",
  delivered: "bg-green-100 text-green-800",
  cancelled: "bg-red-100 text-red-800",
  returned: "bg-amber-100 text-amber-800",
};

export default function OrderStatusBadge({ status }: { status: OrderStatus }) {
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${COLORS[status]}`}>
      {ORDER_STATUS_LABEL[status]}
    </span>
  );
}
