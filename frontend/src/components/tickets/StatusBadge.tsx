import { TICKET_STATUS_LABEL } from "../../lib/labels";
import type { TicketStatus } from "../../types/ticket";

const COLORS: Record<TicketStatus, string> = {
  open: "bg-blue-100 text-blue-800",
  investigating: "bg-indigo-100 text-indigo-800",
  waiting_for_customer: "bg-amber-100 text-amber-800",
  waiting_for_approval: "bg-purple-100 text-purple-800",
  escalated: "bg-red-100 text-red-800",
  resolved: "bg-green-100 text-green-800",
  closed: "bg-slate-100 text-slate-700",
};

export default function StatusBadge({ status }: { status: TicketStatus }) {
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${COLORS[status]}`}>
      {TICKET_STATUS_LABEL[status]}
    </span>
  );
}
