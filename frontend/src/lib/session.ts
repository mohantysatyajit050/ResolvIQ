const CSRF_COOKIE = "resolviq_csrf";

export function getCsrfToken(): string | null {
  if (typeof document === "undefined") return null;

  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${CSRF_COOKIE}=`));

  if (!cookie) return null;

  const value = cookie.slice(CSRF_COOKIE.length + 1);

  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

export function hasSessionHint(): boolean {
  return getCsrfToken() !== null;
}
