import { formatDate, formatRupees, shortId } from "../../lib/formatters";
import type { Order } from "../../types/order";
import OrderStatusBadge from "./OrderStatusBadge";

export default function OrderDetails({ order }: { order: Order }) {
  const address = order.shipping_address;
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="font-semibold text-slate-900">Order #{shortId(order.id)}</h2>
        <OrderStatusBadge status={order.status} />
      </div>
      <p className="text-sm text-slate-500">Placed {formatDate(order.ordered_at)}</p>

      <ul className="mt-3 divide-y divide-slate-100">
        {order.items.map((item) => (
          <li key={item.id} className="flex justify-between gap-3 py-2 text-sm">
            <span className="text-slate-700">
              {item.product.name} &times; {item.quantity}
            </span>
            <span className="text-slate-900">{formatRupees(item.line_total_paise)}</span>
          </li>
        ))}
      </ul>

      <p className="mt-2 flex justify-between border-t border-slate-200 pt-2 text-sm font-semibold text-slate-900">
        <span>Total</span>
        <span>{formatRupees(order.total_paise)}</span>
      </p>

      <p className="mt-3 text-xs text-slate-500">
        Ships to {address.address_line}, {address.city}, {address.state} {address.pincode}
      </p>
    </div>
  );
}
