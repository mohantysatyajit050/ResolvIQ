import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import OrderDetails from "../../components/orders/OrderDetails";
import AttachmentList from "../../components/tickets/AttachmentList";
import FileUploader from "../../components/tickets/FileUploader";
import StatusBadge from "../../components/tickets/StatusBadge";
import TicketTimeline from "../../components/tickets/TicketTimeline";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "../../components/ui/states";
import { useReply, useUploadFiles } from "../../hooks/useTicketActions";
import { useAttachments, useTicket } from "../../hooks/useTickets";
import { friendlyError, getStatus } from "../../lib/errors";
import { formatDate, shortId } from "../../lib/formatters";
import { TICKET_STATUS_HELP } from "../../lib/labels";
import { alertClass, errorTextClass, inputClass } from "../../lib/styles";
import type { TicketStatus } from "../../types/ticket";

function ReplyBox({ ticketId, status }: { ticketId: string; status: TicketStatus }) {
  const reply = useReply(ticketId);
  const [text, setText] = useState(""); // UI state: what is typed so far
  const [error, setError] = useState<string | null>(null);

  if (status === "closed") {
    return (
      <p className="rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-600">
        This ticket is closed, so replies are turned off.
      </p>
    );
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const body = text.trim();
    if (!body) {
      setError("Write a message first.");
      return;
    }
    setError(null);
    try {
      await reply.mutateAsync(body);
      setText("");
    } catch (failure) {
      setError(
        getStatus(failure) === 409 ? "This ticket is closed." : friendlyError(failure),
      );
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <label htmlFor="reply" className="sr-only">
        Your reply
      </label>
      <textarea
        id="reply"
        rows={3}
        maxLength={5000}
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder={
          status === "resolved"
            ? "Not fixed? Replying will reopen this ticket."
            : "Write a reply..."
        }
        className={inputClass}
      />
      {error && <p className={errorTextClass}>{error}</p>}
      <button
        type="submit"
        disabled={reply.isPending}
        className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {reply.isPending ? "Sending..." : "Send reply"}
      </button>
    </form>
  );
}

function FilesPanel({ ticketId, status }: { ticketId: string; status: TicketStatus }) {
  const attachments = useAttachments(ticketId);
  const upload = useUploadFiles(ticketId);
  const [files, setFiles] = useState<File[]>([]);
  const [failed, setFailed] = useState<string[]>([]);
  const uploaded = attachments.data?.length ?? 0;

  async function handleUpload() {
    setFailed([]);
    const failedNames = await upload.mutateAsync(files);
    setFailed(failedNames);
    // keep only the files that failed, so the customer can try again
    setFiles(files.filter((file) => failedNames.includes(file.name)));
  }

  let list;
  if (attachments.isPending) {
    list = <LoadingBlock text="Loading files..." />;
  } else if (!attachments.data) {
    list = (
      <ErrorBlock
        message={friendlyError(attachments.error)}
        onRetry={() => void attachments.refetch()}
      />
    );
  } else {
    list = <AttachmentList attachments={attachments.data} />;
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <h2 className="mb-3 font-semibold text-slate-900">Files</h2>
      {list}
      {status !== "closed" && (
        <div className="mt-4 border-t border-slate-100 pt-4">
          <FileUploader
            files={files}
            onChange={setFiles}
            disabled={upload.isPending}
            alreadyUploaded={uploaded}
          />
          {failed.length > 0 && (
            <p role="alert" className={`mt-2 ${alertClass}`}>
              These files could not be uploaded: {failed.join(", ")}. You can try again.
            </p>
          )}
          {files.length > 0 && (
            <button
              type="button"
              onClick={() => void handleUpload()}
              disabled={upload.isPending}
              className="mt-3 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {upload.isPending ? "Uploading..." : "Upload files"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default function TicketDetailPage() {
  const { ticketId = "" } = useParams<{ ticketId: string }>();
  const location = useLocation();
  const ticket = useTicket(ticketId);
  const failedFiles =
    (location.state as { failedFiles?: string[] } | null)?.failedFiles ?? [];

  if (ticket.isPending) {
    return <LoadingBlock text="Loading your ticket..." />;
  }
  if (!ticket.data) {
    if (getStatus(ticket.error) === 404) {
      return (
        <EmptyBlock
          title="Ticket not found"
          text="It may have been removed, or it is not yours."
          action={
            <Link to="/tickets" className="text-sm font-medium text-indigo-600 hover:underline">
              Back to my tickets
            </Link>
          }
        />
      );
    }
    return (
      <ErrorBlock
        message={friendlyError(ticket.error)}
        onRetry={() => void ticket.refetch()}
      />
    );
  }

  const data = ticket.data;
  return (
    <section>
      <Link to="/tickets" className="text-sm text-indigo-600 hover:underline">
        &larr; My tickets
      </Link>

      <div className="mt-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">{data.subject}</h1>
          <p className="mt-1 text-sm text-slate-500">
            Ticket #{shortId(data.id)} &middot; Order #{shortId(data.order_id)} &middot;
            Opened {formatDate(data.created_at)}
          </p>
        </div>
        <StatusBadge status={data.status} />
      </div>

      <p className="mt-3 rounded-lg bg-indigo-50 px-3 py-2 text-sm text-indigo-800">
        {TICKET_STATUS_HELP[data.status]}
      </p>

      {failedFiles.length > 0 && (
        <p role="alert" className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
          Your complaint was submitted, but these files could not be uploaded:{" "}
          {failedFiles.join(", ")}. You can add them again under Files.
        </p>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <h2 className="font-semibold text-slate-900">Conversation</h2>
          <TicketTimeline messages={data.messages} />
          <ReplyBox ticketId={data.id} status={data.status} />
        </div>
        <div className="space-y-4">
          <OrderDetails order={data.order} />
          <FilesPanel ticketId={data.id} status={data.status} />
        </div>
      </div>
    </section>
  );
}
