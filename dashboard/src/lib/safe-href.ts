// Addresses that come from web search results or fetched pages are untrusted: only http(s) links are made clickable.
export function safeHref(url: string): string | undefined {
  return /^https?:\/\//i.test(url) ? url : undefined;
}
