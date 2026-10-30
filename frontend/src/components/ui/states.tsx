import type { ReactNode } from "react";

export function LoadingBlock({ text = "Loading..." }: { text?: string }) {
  return (
    <p role="status" className="py-8 text-center text-sm text-slate-500">
      {text}
    </p>
  );
}

type ErrorBlockProps = { message: string; onRetry?: () => void };

export function ErrorBlock({ message, onRetry }: ErrorBlockProps) {
  return (
    <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-center">
      <p className="text-sm text-red-800">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded-lg bg-white px-3 py-1.5 text-sm font-medium text-red-700 ring-1 ring-red-200 hover:bg-red-100"
        >
          Try again
        </button>
      )}
    </div>
  );
}

type EmptyBlockProps = { title: string; text?: string; action?: ReactNode };

export function EmptyBlock({ title, text, action }: EmptyBlockProps) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center">
      <p className="font-semibold text-slate-900">{title}</p>
      {text && <p className="mt-1 text-sm text-slate-600">{text}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
