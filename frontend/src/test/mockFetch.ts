import { vi } from "vitest";

type Handler = (request: Request) => unknown;

/**
 * Stub global fetch with a route table keyed by "METHOD /path".
 * A handler returns the JSON body (status 200), a Response, or throws to simulate a
 * network failure.
 */
export function mockFetch(routes: Record<string, Handler>) {
  const fn = vi.fn(async (input: Request) => {
    // Decoded, so a file path parameter ("src%2Fa.v") reads as it is written ("src/a.v").
    const key = `${input.method} ${decodeURIComponent(new URL(input.url).pathname)}`;
    const handler = routes[key];
    if (!handler) return new Response("not mocked", { status: 500 });
    const result = await handler(input);
    if (result instanceof Response) return result;
    return Response.json(result);
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}
