import { initApiPassthrough } from "langgraph-nextjs-api-passthrough";

// Proxies client requests to the local `langgraph dev` server so the
// LangGraph SDK/useStream never needs to know its URL or API key.
//
// initApiPassthrough throws at module-load time if apiUrl is falsy - and
// this file's exports are evaluated at build time too (Next.js imports every
// route to collect its page data), not just at request time. Without a
// fallback here, a clean checkout with no .env.local (e.g. CI) fails the
// build entirely rather than just failing requests at runtime. The fallback
// matches this project's documented default port (see README) and is
// harmless in production, since a real LANGGRAPH_API_URL always overrides it.
export const { GET, POST, PUT, PATCH, DELETE, OPTIONS, runtime } =
  initApiPassthrough({
    apiUrl: process.env.LANGGRAPH_API_URL || "http://127.0.0.1:2025",
    apiKey: process.env.LANGSMITH_API_KEY,
    runtime: "nodejs",
    disableWarningLog: true,
  });
