type PaginationProps = {
  page: number; // starts at 0
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  isFetching?: boolean;
};

const buttonClass =
  "rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50";

export default function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
  isFetching = false,
}: PaginationProps) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  if (total <= pageSize) return null;

  return (
    <nav aria-label="Pagination" className="mt-4 flex items-center justify-between">
      <button
        type="button"
        className={buttonClass}
        disabled={page === 0 || isFetching}
        onClick={() => onPageChange(page - 1)}
      >
        Previous
      </button>
      <span className="text-sm text-slate-600">
        Page {page + 1} of {pageCount}
      </span>
      <button
        type="button"
        className={buttonClass}
        disabled={page + 1 >= pageCount || isFetching}
        onClick={() => onPageChange(page + 1)}
      >
        Next
      </button>
    </nav>
  );
}
