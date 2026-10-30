import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import type { ReactNode } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { z } from "zod";
import FileUploader from "../../components/tickets/FileUploader";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "../../components/ui/states";
import { useOrders } from "../../hooks/useOrders";
import { useCreateComplaint } from "../../hooks/useTicketActions";
import { useActiveTicketByOrder } from "../../hooks/useTickets";
import { friendlyError, getStatus } from "../../lib/errors";
import { formatDate, formatRupees, shortId } from "../../lib/formatters";
import { ORDER_STATUS_LABEL } from "../../lib/labels";
import {
  alertClass,
  buttonClass,
  errorTextClass,
  inputClass,
  labelClass,
} from "../../lib/styles";
import type { OrderSummary } from "../../types/order";

// The same rules as the server. The server still checks everything again.
const complaintSchema = z.object({
  orderId: z.string().min(1, "Choose the order this is about"),
  subject: z
    .string()
    .trim()
    .min(1, "Write a short title")
    .max(200, "Keep the title under 200 characters"),
  description: z
    .string()
    .trim()
    .min(1, "Describe what went wrong")
    .max(5000, "Keep the description under 5000 characters"),
});

type ComplaintFormValues = z.infer<typeof complaintSchema>;

function optionLabel(order: OrderSummary, taken: boolean): string {
  const base = `#${shortId(order.id)} - ${formatDate(order.ordered_at)} - ${formatRupees(order.total_paise)} - ${ORDER_STATUS_LABEL[order.status]}`;
  return taken ? `${base} (ticket already open)` : base;
}

type ComplaintFormProps = {
  orders: OrderSummary[];
  activeByOrder: Record<string, string>;
  preselectedOrderId: string;
};

function ComplaintForm({ orders, activeByOrder, preselectedOrderId }: ComplaintFormProps) {
  const navigate = useNavigate();
  const createComplaint = useCreateComplaint();
  const [files, setFiles] = useState<File[]>([]); // UI state: chosen, not uploaded yet
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register: field,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ComplaintFormValues>({
    resolver: zodResolver(complaintSchema),
    defaultValues: { orderId: preselectedOrderId, subject: "", description: "" },
  });

  async function onSubmit(values: ComplaintFormValues) {
    setFormError(null);
    try {
      const result = await createComplaint.mutateAsync({
        payload: {
          order_id: values.orderId,
          subject: values.subject,
          description: values.description,
        },
        files,
      });
      navigate(`/tickets/${result.ticket.id}`, {
        state: { failedFiles: result.failedFiles },
      });
    } catch (error) {
      const code = getStatus(error);
      if (code === 409) {
        setError("orderId", { message: "This order already has an open ticket." });
      } else if (code === 404) {
        setError("orderId", { message: "We could not find that order." });
      } else {
        setFormError(friendlyError(error));
      }
    }
  }

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      noValidate
      className="space-y-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
    >
      {formError && (
        <p role="alert" className={alertClass}>
          {formError}
        </p>
      )}

      <div>
        <label htmlFor="orderId" className={labelClass}>
          Which order is this about?
        </label>
        <select id="orderId" className={inputClass} {...field("orderId")}>
          <option value="">Choose an order...</option>
          {orders.map((order) => {
            const taken = order.id in activeByOrder;
            return (
              <option key={order.id} value={order.id} disabled={taken}>
                {optionLabel(order, taken)}
              </option>
            );
          })}
        </select>
        {errors.orderId && <p className={errorTextClass}>{errors.orderId.message}</p>}
      </div>

      <div>
        <label htmlFor="subject" className={labelClass}>
          Short title
        </label>
        <input
          id="subject"
          type="text"
          placeholder="For example: The phone screen is cracked"
          className={inputClass}
          {...field("subject")}
        />
        {errors.subject && <p className={errorTextClass}>{errors.subject.message}</p>}
      </div>

      <div>
        <label htmlFor="description" className={labelClass}>
          What went wrong?
        </label>
        <textarea
          id="description"
          rows={5}
          className={inputClass}
          {...field("description")}
        />
        {errors.description && (
          <p className={errorTextClass}>{errors.description.message}</p>
        )}
      </div>

      <div>
        <p className={labelClass}>Photos or documents (optional)</p>
        <FileUploader files={files} onChange={setFiles} disabled={isSubmitting} />
      </div>

      <button type="submit" disabled={isSubmitting} className={buttonClass}>
        {isSubmitting ? "Sending..." : "Send complaint"}
      </button>
    </form>
  );
}

export default function NewComplaintPage() {
  const [searchParams] = useSearchParams();
  const orders = useOrders(100, 0);
  const activeTickets = useActiveTicketByOrder();

  let content: ReactNode;
  if (orders.isPending || activeTickets.isPending) {
    content = <LoadingBlock text="Loading your orders..." />;
  } else if (!orders.data || !activeTickets.data) {
    content = (
      <ErrorBlock
        message={friendlyError(orders.error ?? activeTickets.error)}
        onRetry={() => {
          void orders.refetch();
          void activeTickets.refetch();
        }}
      />
    );
  } else {
    const items = orders.data.items;
    const taken = activeTickets.data;
    const free = items.filter((order) => !(order.id in taken));
    if (items.length === 0) {
      content = (
        <EmptyBlock
          title="You have no orders yet"
          text="You can report a problem once you have placed an order."
        />
      );
    } else if (free.length === 0) {
      content = (
        <EmptyBlock
          title="Every order already has an open ticket"
          text="Open the ticket to add more details."
          action={
            <Link to="/tickets" className="text-sm font-medium text-indigo-600 hover:underline">
              Go to my tickets
            </Link>
          }
        />
      );
    } else {
      const wanted = searchParams.get("orderId") ?? "";
      const preselected = free.some((order) => order.id === wanted) ? wanted : "";
      content = (
        <ComplaintForm
          orders={items}
          activeByOrder={taken}
          preselectedOrderId={preselected}
        />
      );
    }
  }

  return (
    <section className="max-w-2xl">
      <h1 className="text-xl font-semibold text-slate-900">Report a problem</h1>
      <p className="mt-1 text-sm text-slate-600">
        Tell us what went wrong with an order. Photos help us decide faster.
      </p>
      <div className="mt-4">{content}</div>
    </section>
  );
}
