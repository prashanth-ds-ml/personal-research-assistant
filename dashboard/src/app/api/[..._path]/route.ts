import { initApiPassthrough } from "langgraph-nextjs-api-passthrough";

// Proxies client requests to the local `langgraph dev` server so the
// LangGraph SDK/useStream never needs to know its URL or API key.
export const { GET, POST, PUT, PATCH, DELETE, OPTIONS, runtime } =
  initApiPassthrough({
    apiUrl: process.env.LANGGRAPH_API_URL,
    apiKey: process.env.LANGSMITH_API_KEY,
    runtime: "nodejs",
  });
