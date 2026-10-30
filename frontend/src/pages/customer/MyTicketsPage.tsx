import { useState } from "react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import StatusBadge from "../../components/tickets/StatusBadge";
import Pagination from "../../components/ui/Pagination";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "../../components/ui/states";
import { useTickets } from "../../hooks/useTickets";
import { PAGE_SIZE } from "../../lib/constants";
import { friendlyError } from "../../lib/errors";
import { formatDate, formatDateTime, shortId } from "../../lib/formatters";
import { TICKET_STATUS_LABEL } from "../../lib/labels";
import type { TicketStatus } from "../../types/ticket";

const STATUS_OPTIONS = Object.keys(TICKET_STATUS_LABEL) as TicketStatus[];

export default function MyTicketsPage() {
  const [status, setStatus] = useState<TicketStatus | "all">("all");
  const [page, setPage] = useState(0);
  const tickets = useTickets({
    status: status === "all" ? undefined : status,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  });

  const newComplaintLink = (
    <Link
      to="/tickets/new"
      className="inline-block rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
    >
      Report a problem
    </Link>
  );

  let content: ReactNode;
  if (tickets.isPending) {
    content = <LoadingBlock text="Loading your tickets..." />;
  } else if (!tickets.data) {
    content = (
      <ErrorBlock
        message={friendlyError(tickets.error)}
        onRetry={() => void tickets.refetch()}
      />
    );
  } else if (tickets.data.items.length === 0) {
    content =
      status === "all" ? (
        <EmptyBlock
          title="You have not reported any problems yet"
          text="If something is wrong with an order, tell us and we will help."
          action={newComplaintLink}
        />
      ) : (
        <EmptyBlock title="No tickets with this status" />
      );
  } else {
    content = (
      <>
        {tickets.isError && (
          <p className="mb-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
            Could not refresh your tickets. Showing the last data we have.
          </p>
        )}
        <ul className="space-y-3">
          {tickets.data.items.map((ticket) => (
            <li key={ticket.id}>
              <Link
                to={`/tickets/${ticket.id}`}
                className="block rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:border-indigo-300"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-semibold text-slate-900">{ticket.subject}</p>
                  <StatusBadge status={ticket.status} />
                </div>
                <p className="mt-1 text-sm text-slate-500">
                  Ticket #{shortId(ticket.id)} &middot; Order #{shortId(ticket.order_id)}{" "}
                  &middot; Opened {formatDate(ticket.created_at)}
                </p>
                <p className="text-xs text-slate-400">
                  Last update {formatDateTime(ticket.updated_at)}
                </p>
              </Link>
            </li>
          ))}
        </ul>
        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          total={tickets.data.total}
          onPageChange={setPage}
          isFetching={tickets.isFetching}
        />
      </>
    );
  }

  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-slate-900">My tickets</h1>
        <div className="flex items-center gap-2">
          <label htmlFor="status-filter" className="text-sm text-slate-600">
            Show
          </label>
          <select
            id="status-filter"
            value={status}
            onChange={(event) => {
              setStatus(event.target.value as TicketStatus | "all");
              setPage(0); // a new filter starts on the first page
            }}
            className="rounded-lg border border-slate-300 px-2 py-1 text-sm"
          >
            <option value="all">All tickets</option>
            {STATUS_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {TICKET_STATUS_LABEL[option]}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="mt-4">{content}</div>
    </section>
  );
}
