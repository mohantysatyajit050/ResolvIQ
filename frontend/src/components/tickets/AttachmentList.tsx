import { formatDate, formatFileSize } from "../../lib/formatters";
import type { Attachment } from "../../types/ticket";

export default function AttachmentList({ attachments }: { attachments: Attachment[] }) {
  if (attachments.length === 0) {
    return <p className="text-sm text-slate-500">No files yet.</p>;
  }
  return (
    <ul className="space-y-2">
      {attachments.map((attachment) => (
        <li key={attachment.id} className="text-sm">
          <a
            href={attachment.download_url}
            target="_blank"
            rel="noreferrer"
            className="font-medium text-indigo-600 hover:underline"
          >
            {attachment.file_name}
          </a>
          <p className="text-xs text-slate-500">
            {formatFileSize(attachment.size_bytes)} &middot; Added{" "}
            {formatDate(attachment.created_at)}
          </p>
        </li>
      ))}
    </ul>
  );
}
