import * as React from "react";

// Matches http(s):// and bare www. URLs, trimming trailing punctuation.
const URL_RE = /((?:https?:\/\/|www\.)[^\s<]+[^\s<.,:;!?)\]])/gi;

/**
 * Renders plain text with any URLs turned into clickable links. Links open in a
 * new tab and stop click propagation (so a link inside a clickable card doesn't
 * also trigger the card).
 */
export function Linkify({ children }: { children: string | null | undefined }) {
  const text = children ?? "";
  const parts: React.ReactNode[] = [];
  let last = 0;
  let key = 0;
  URL_RE.lastIndex = 0;

  let match: RegExpExecArray | null;
  while ((match = URL_RE.exec(text)) !== null) {
    const url = match[0];
    const start = match.index;
    if (start > last) parts.push(text.slice(last, start));
    const href = url.startsWith("http") ? url : `https://${url}`;
    parts.push(
      <a
        key={key++}
        href={href}
        target="_blank"
        rel="noopener noreferrer nofollow"
        onClick={(e) => e.stopPropagation()}
        className="break-words text-[var(--primary)] underline underline-offset-2 hover:opacity-80"
      >
        {url}
      </a>,
    );
    last = start + url.length;
  }
  if (last < text.length) parts.push(text.slice(last));

  return <>{parts}</>;
}
