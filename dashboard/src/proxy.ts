import { NextResponse, type NextRequest } from "next/server";

// Guards EVERY request (pages and /api) for a tool that holds private research and can start model runs.
//
//  * Host allow-list: only localhost / 127.0.0.1 / [::1] (plus anything in DASHBOARD_ALLOWED_HOSTS, a
//    comma-separated list of host names). This stops DNS rebinding, where a hostile page points its own
//    domain at 127.0.0.1 so that a request to it looks "same-origin" and can read the answers.
//  * Origin check: a request that carries an Origin header must come from this very site. Together with
//    the absence of any CORS headers this means other websites cannot read or trigger anything.
//  * /api refuses anything the browser labels cross-site, even the no-CORS kinds that send no Origin.
//  * Basic hardening headers (no framing, no sniffing, no referrer).
const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "[::1]"]);
const EXTRA_HOSTS = (process.env.DASHBOARD_ALLOWED_HOSTS ?? "")
  .split(",")
  .map((h) => h.trim().toLowerCase())
  .filter(Boolean);

function hostnameOf(hostHeader: string): string {
  if (hostHeader.startsWith("[")) return hostHeader.slice(0, hostHeader.indexOf("]") + 1);
  return hostHeader.split(":")[0];
}

function refuse(message: string) {
  return new NextResponse(message, { status: 403, headers: { "content-type": "text/plain" } });
}

export function proxy(request: NextRequest) {
  const host = (request.headers.get("host") ?? "").toLowerCase();
  const hostname = hostnameOf(host);
  if (!LOCAL_HOSTS.has(hostname) && !EXTRA_HOSTS.includes(hostname)) {
    return refuse("Unexpected Host header. Open the dashboard at http://localhost:3001 (or add the host name to DASHBOARD_ALLOWED_HOSTS).");
  }

  const origin = request.headers.get("origin");
  if (origin) {
    let originHost = "";
    try {
      originHost = new URL(origin).host.toLowerCase();
    } catch {
      /* malformed Origin: refused below */
    }
    if (originHost !== host) return refuse("Cross-origin requests are not allowed.");
  }

  const fetchSite = request.headers.get("sec-fetch-site");
  const isApi = request.nextUrl.pathname.startsWith("/api");
  const isRead = request.method === "GET" || request.method === "HEAD";
  if (fetchSite === "cross-site" && (isApi || !isRead)) return refuse("Cross-site requests are not allowed.");

  const response = NextResponse.next();
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("Referrer-Policy", "no-referrer");
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
