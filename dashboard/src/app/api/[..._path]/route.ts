// A small, deliberate proxy from the browser to the local LangGraph server.
//
// It replaces the stock `langgraph-nextjs-api-passthrough` package, which answered every request (and every
// preflight) with `Access-Control-Allow-Origin: *`, so any website open in the browser could read research
// threads and start runs. This one sends NO CORS headers at all, forwards only the LangGraph endpoints the
// dashboard uses, and relies on src/proxy.ts to refuse foreign Hosts and Origins. The server-side API key (if
// any) is added here and never reaches the browser. Streaming (server-sent events) is passed through untouched.

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const UPSTREAM = (process.env.LANGGRAPH_API_URL || "http://127.0.0.1:2025").replace(/\/$/, "");
const ALLOWED_ROOTS = new Set(["threads", "runs", "assistants", "ok", "info", "store"]);
const FORWARD_HEADERS = ["content-type", "accept", "last-event-id", "cache-control"];
const RETURN_HEADERS = ["content-type", "content-location", "location", "x-request-id"];

type Ctx = { params: Promise<{ _path: string[] }> };

function json(status: number, body: unknown) {
  return Response.json(body, { status });
}

async function handler(request: Request, ctx: Ctx): Promise<Response> {
  const { _path: segments } = await ctx.params;
  const valid =
    Array.isArray(segments) &&
    segments.length > 0 &&
    ALLOWED_ROOTS.has(segments[0]) &&
    segments.every((s) => s !== "" && s !== "." && s !== ".." && !/[\\/]/.test(s));
  if (!valid) return json(404, { error: "Not found" });

  const target = new URL(`${UPSTREAM}/${segments.map(encodeURIComponent).join("/")}`);
  target.search = new URL(request.url).search;

  const headers = new Headers();
  for (const name of FORWARD_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  const key = process.env.LANGSMITH_API_KEY;
  if (key) headers.set("x-api-key", key);

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers,
      body: hasBody ? request.body : undefined,
      // @ts-expect-error `duplex` is required by Node's fetch for a streamed request body
      duplex: hasBody ? "half" : undefined,
      redirect: "manual",
      signal: request.signal, // the browser leaving aborts the upstream read (the run itself may continue)
    });
  } catch (e) {
    if (request.signal.aborted) return new Response(null, { status: 499 });
    return json(502, { error: "The research backend is not reachable", detail: String(e).slice(0, 200) });
  }

  const out = new Headers({ "cache-control": "no-store" });
  for (const name of RETURN_HEADERS) {
    const value = upstream.headers.get(name);
    if (value) out.set(name, value);
  }
  return new Response(upstream.body, { status: upstream.status, headers: out });
}

export { handler as GET, handler as POST, handler as PUT, handler as PATCH, handler as DELETE };
