import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Reports and the profile note can contain text pulled from web pages and PDFs. Rendering it must not let that
// text load remote images (a tracking / exfiltration channel) or link to javascript: URLs.
export function SafeMarkdown({ children }: { children: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        img: () => null,
        a: ({ href, children: label }) =>
          href && /^(https?:|mailto:|#)/i.test(href) ? (
            <a href={href} target="_blank" rel="noopener noreferrer nofollow">
              {label}
            </a>
          ) : (
            <span>{label}</span>
          ),
      }}
    >
      {children}
    </ReactMarkdown>
  );
}
