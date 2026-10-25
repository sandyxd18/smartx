/** Explain a non-2xx answer. 502–504 come from the dev proxy when the backend is down. */
export function httpErrorMessage(status: number): string {
  return status >= 502 && status <= 504
    ? `Backend tidak bisa dihubungi (HTTP ${status}).`
    : `Backend menjawab HTTP ${status}.`;
}

export const UNREACHABLE = "Backend tidak bisa dihubungi.";

/** The backend's own explanation (`detail`), falling back to the HTTP status. */
export function apiErrorMessage(error: unknown, status: number): string {
  if (typeof error === "object" && error !== null && "detail" in error) {
    const { detail } = error;
    if (typeof detail === "string") return detail;
    // FastAPI validation errors: [{msg, loc, ...}]
    if (Array.isArray(detail) && detail.length > 0) {
      const first: unknown = detail[0];
      if (typeof first === "object" && first !== null && "msg" in first) {
        return String(first.msg).replace(/^Value error, /, "");
      }
    }
  }
  return httpErrorMessage(status);
}
