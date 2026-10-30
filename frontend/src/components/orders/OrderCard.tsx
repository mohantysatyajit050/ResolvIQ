import { Link } from "react-router-dom";
import { formatDate, formatRupees, shortId } from "../../lib/formatters";
import type { OrderSummary } from "../../types/order";
import OrderStatusBadge from "./OrderStatusBadge";

type OrderCardProps = {
  order: OrderSummary;
  activeTicketId?: string | undefined;
};

export default function OrderCard({ order, activeTicketId }: OrderCardProps) {
  return (
    <li className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-semibold text-slate-900">Order #{shortId(order.id)}</p>
        <OrderStatusBadge status={order.status} />
      </div>
      <p className="mt-1 text-sm text-slate-500">
        Placed {formatDate(order.ordered_at)} &middot; {formatRupees(order.total_paise)}
      </p>
      {order.delivered_at ? (
        <p className="text-sm text-slate-500">Delivered {formatDate(order.delivered_at)}</p>
      ) : (
        order.expected_delivery_date && (
          <p className="text-sm text-slate-500">
            Expected by {formatDate(order.expected_delivery_date)}
          </p>
        )
      )}
      <div className="mt-3">
        {activeTicketId ? (
          <Link
            to={`/tickets/${activeTicketId}`}
            className="text-sm font-medium text-indigo-600 hover:underline"
          >
            View your open ticket
          </Link>
        ) : (
          <Link
            to={`/tickets/new?orderId=${order.id}`}
            className="text-sm font-medium text-indigo-600 hover:underline"
          >
            Report a problem
          </Link>
        )}
      </div>
    </li>
  );
}
