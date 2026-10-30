import { formatDateTime } from "../../lib/formatters";
import type { SenderType, TicketMessage } from "../../types/ticket";

const SENDER_LABEL: Record<SenderType, string> = {
  customer: "You",
  agent: "Support agent",
  ai: "ResolvIQ assistant",
};

const BUBBLE: Record<SenderType, string> = {
  customer: "border-indigo-200 bg-indigo-50",
  agent: "border-slate-200 bg-white",
  ai: "border-slate-200 bg-slate-50",
};

export default function TicketTimeline({ messages }: { messages: TicketMessage[] }) {
  if (messages.length === 0) {
    return <p className="text-sm text-slate-500">No messages yet.</p>;
  }
  const ordered = [...messages].sort((a, b) => a.created_at.localeCompare(b.created_at));
  return (
    <ul className="space-y-3">
      {ordered.map((message) => (
        <li
          key={message.id}
          className={`rounded-xl border p-3 ${BUBBLE[message.sender_type]}`}
        >
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
            <span className="font-semibold text-slate-700">
              {SENDER_LABEL[message.sender_type]}
            </span>
            <span>{formatDateTime(message.created_at)}</span>
          </div>
          <p className="mt-1 whitespace-pre-wrap text-sm text-slate-800">{message.body}</p>
        </li>
      ))}
    </ul>
  );
}
