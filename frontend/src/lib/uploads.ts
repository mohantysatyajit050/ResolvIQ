export const MAX_FILES = 5;
export const MAX_FILE_BYTES = 5 * 1024 * 1024; // 5 MB
export const ALLOWED_TYPES = [
  "image/jpeg",
  "image/png",
  "image/webp",
  "application/pdf",
];
export const ACCEPT_ATTRIBUTE = ALLOWED_TYPES.join(",");

type ValidationResult = { accepted: File[]; errors: string[] };

/**
 * Checks newly chosen files against the upload rules.
 * `current` are files already chosen but not uploaded; `alreadyUploaded` counts files on the server.
 */
export function validateFiles(
  current: File[],
  incoming: File[],
  alreadyUploaded = 0,
): ValidationResult {
  const accepted: File[] = [];
  const errors: string[] = [];
  const names = new Set(current.map((file) => file.name));

  for (const file of incoming) {
    if (!ALLOWED_TYPES.includes(file.type)) {
      errors.push(`${file.name}: only JPG, PNG, WebP and PDF files are allowed.`);
    } else if (file.size > MAX_FILE_BYTES) {
      errors.push(`${file.name}: files must be under 5 MB.`);
    } else if (names.has(file.name)) {
      errors.push(`${file.name}: you already added a file with this name.`);
    } else if (alreadyUploaded + current.length + accepted.length >= MAX_FILES) {
      errors.push(`${file.name}: you can add at most ${MAX_FILES} files.`);
    } else {
      names.add(file.name);
      accepted.push(file);
    }
  }
  return { accepted, errors };
}
