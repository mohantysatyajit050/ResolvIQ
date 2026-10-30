import { useState } from "react";
import type { ReactNode } from "react";
import OrderCard from "../../components/orders/OrderCard";
import Pagination from "../../components/ui/Pagination";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "../../components/ui/states";
import { useOrders } from "../../hooks/useOrders";
import { useActiveTicketByOrder } from "../../hooks/useTickets";
import { PAGE_SIZE } from "../../lib/constants";
import { friendlyError } from "../../lib/errors";

export default function MyOrdersPage() {
  const [page, setPage] = useState(0);
  const orders = useOrders(PAGE_SIZE, page * PAGE_SIZE);
  const activeTickets = useActiveTicketByOrder();

  let content: ReactNode;
  if (orders.isPending) {
    content = <LoadingBlock text="Loading your orders..." />;
  } else if (!orders.data) {
    content = (
      <ErrorBlock
        message={friendlyError(orders.error)}
        onRetry={() => void orders.refetch()}
      />
    );
  } else if (orders.data.items.length === 0) {
    content = (
      <EmptyBlock
        title="No orders yet"
        text="When you place an order, it will show up here."
      />
    );
  } else {
    content = (
      <>
        {orders.isError && (
          <p className="mb-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
            Could not refresh your orders. Showing the last data we have.
          </p>
        )}
        <ul className="space-y-3">
          {orders.data.items.map((order) => (
            <OrderCard
              key={order.id}
              order={order}
              activeTicketId={activeTickets.data?.[order.id]}
            />
          ))}
        </ul>
        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          total={orders.data.total}
          onPageChange={setPage}
          isFetching={orders.isFetching}
        />
      </>
    );
  }

  return (
    <section>
      <h1 className="text-xl font-semibold text-slate-900">My orders</h1>
      <p className="mt-1 text-sm text-slate-600">
        Something wrong with an order? Report it and we will look into it.
      </p>
      <div className="mt-4">{content}</div>
    </section>
  );
}
