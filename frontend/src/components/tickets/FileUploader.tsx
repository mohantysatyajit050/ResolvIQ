import { useRef, useState } from "react";
import type { ChangeEvent } from "react";
import { formatFileSize } from "../../lib/formatters";
import { ACCEPT_ATTRIBUTE, MAX_FILES, validateFiles } from "../../lib/uploads";

type FileUploaderProps = {
  files: File[]; // chosen, not uploaded yet
  onChange: (files: File[]) => void;
  disabled?: boolean;
  alreadyUploaded?: number;
};

export default function FileUploader({
  files,
  onChange,
  disabled = false,
  alreadyUploaded = 0,
}: FileUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [errors, setErrors] = useState<string[]>([]); // UI state: problems with the last pick

  function handlePick(event: ChangeEvent<HTMLInputElement>) {
    const picked = Array.from(event.target.files ?? []);
    const result = validateFiles(files, picked, alreadyUploaded);
    setErrors(result.errors);
    if (result.accepted.length > 0) {
      onChange([...files, ...result.accepted]);
    }
    event.target.value = ""; // so the same file can be picked again later
  }

  function remove(name: string) {
    onChange(files.filter((file) => file.name !== name));
    setErrors([]);
  }

  const full = alreadyUploaded + files.length >= MAX_FILES;

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ACCEPT_ATTRIBUTE}
        onChange={handlePick}
        disabled={disabled || full}
        className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-sm file:font-medium file:text-slate-700 hover:file:bg-slate-200 disabled:opacity-60"
      />
      <p className="mt-1 text-xs text-slate-500">
        JPG, PNG, WebP or PDF. Up to {MAX_FILES} files, 5 MB each.
      </p>

      {errors.length > 0 && (
        <ul role="alert" className="mt-2 space-y-1 text-sm text-red-600">
          {errors.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      )}

      {files.length > 0 && (
        <ul className="mt-3 space-y-1">
          {files.map((file) => (
            <li
              key={file.name}
              className="flex items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-1.5 text-sm"
            >
              <span className="truncate text-slate-700">
                {file.name} <span className="text-slate-400">({formatFileSize(file.size)})</span>
              </span>
              <button
                type="button"
                onClick={() => remove(file.name)}
                disabled={disabled}
                className="text-xs font-medium text-red-600 hover:underline disabled:opacity-50"
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
