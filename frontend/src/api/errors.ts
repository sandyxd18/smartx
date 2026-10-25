/** Explain a non-2xx answer. 502–504 come from the dev proxy when the backend is down. */
export function httpErrorMessage(status: number): string {
  return status >= 502 && status <= 504
    ? `Backend tidak bisa dihubungi (HTTP ${status}).`
    : `Backend menjawab HTTP ${status}.`;
}

export const UNREACHABLE = "Backend tidak bisa dihubungi.";
