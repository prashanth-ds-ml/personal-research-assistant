// Where the browser reaches the dashboard's own API proxy. useStream needs an absolute URL.
// In the browser this is the page's own origin, so it works whether the app is opened as localhost or 127.0.0.1
// (a fixed localhost address made every streaming page fail with "Failed to fetch" at 127.0.0.1).
export function apiUrl(): string {
  if (typeof window !== "undefined") return `${window.location.origin}/api`;
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001/api";
}
