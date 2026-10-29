import { useQuery } from "@tanstack/react-query";
import { fetchOrders } from "../../api/orders";
import { useAuth } from "../../hooks/useAuth";

// A temporary demo page: it shows what TanStack Query does for you.
export default function MyOrdersPage() {
  const { user } = useAuth();
  const query = useQuery({
    queryKey: ["orders", { limit: 5, offset: 0 }],
    queryFn: () => fetchOrders(5, 0),
  });

  return (
    <section>
      <h1 className="text-xl font-semibold text-slate-900">
        My orders (server state demo)
      </h1>
      <p className="mt-1 text-slate-600">Hello {user?.name}.</p>

      <dl className="mt-4 grid max-w-sm grid-cols-2 gap-1 text-sm text-slate-700">
        <dt className="font-medium">status</dt>
        <dd>{query.status}</dd>
        <dt className="font-medium">isFetching</dt>
        <dd>{String(query.isFetching)}</dd>
        <dt className="font-medium">last updated</dt>
        <dd>
          {query.dataUpdatedAt
            ? new Date(query.dataUpdatedAt).toLocaleTimeString()
            : "never"}
        </dd>
        <dt className="font-medium">total orders</dt>
        <dd>{query.data?.total ?? "-"}</dd>
      </dl>

      <button
        type="button"
        onClick={() => void query.refetch()}
        className="mt-4 rounded-lg border border-slate-300 px-3 py-1 text-sm text-slate-700 hover:bg-slate-100"
      >
        Refetch
      </button>

      {query.isError && (
        <p className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          Could not load orders{query.data ? " (showing older data)" : ""}.
        </p>
      )}

      <ul className="mt-4 space-y-1 text-sm text-slate-700">
        {query.data?.items.map((order) => (
          <li key={order.id}>
            {order.status}: {order.total_paise / 100} rupees
          </li>
        ))}
      </ul>
    </section>
  );
}
