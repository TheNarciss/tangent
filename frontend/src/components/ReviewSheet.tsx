import ReactMarkdown from "react-markdown";
import { Clock, ExternalLink } from "lucide-react";

import type { PortfolioReviewResponse } from "@/api";

interface ReviewSheetProps {
  review: PortfolioReviewResponse;
}

interface Source {
  title?: string;
  url: string;
}

/**
 * Renders the full markdown briefing. Date and sources only: model,
 * tokens and cost are audit data, not something the reader needs.
 */
export function ReviewSheet({ review }: ReviewSheetProps) {
  const sources = (review.sources ?? []) as Source[];
  return (
    <div className="p-4 md:p-6">
      <div className="mb-4 flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-border pb-4 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <Clock className="h-3 w-3" />
          {new Date(review.created_at).toLocaleString("fr-FR", {
            dateStyle: "long",
            timeStyle: "short",
          })}
        </span>
        {review.web_searches_count > 0 && (
          <>
            <span>·</span>
            <span>
              {review.web_searches_count} source{review.web_searches_count > 1 ? "s" : ""} consultée
              {review.web_searches_count > 1 ? "s" : ""}
            </span>
          </>
        )}
      </div>

      <div className="space-y-3 text-sm leading-relaxed">
        <ReactMarkdown
          components={{
            h1: ({ children }) => (
              <h3 className="mt-5 text-base font-semibold first:mt-0">{children}</h3>
            ),
            h2: ({ children }) => (
              <h3 className="mt-5 text-base font-semibold first:mt-0">{children}</h3>
            ),
            h3: ({ children }) => <h4 className="mt-4 text-sm font-semibold">{children}</h4>,
            p: ({ children }) => <p className="text-muted-foreground">{children}</p>,
            ul: ({ children }) => (
              <ul className="list-disc space-y-1 pl-5 text-muted-foreground">{children}</ul>
            ),
            a: ({ href, children }) => (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary underline"
              >
                {children}
              </a>
            ),
            strong: ({ children }) => <strong className="text-foreground">{children}</strong>,
          }}
        >
          {review.content}
        </ReactMarkdown>
      </div>

      {sources.length > 0 && (
        <div className="mt-6 border-t border-border pt-4">
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Sources consultées
          </h4>
          <ul className="space-y-1">
            {sources.map((s, i) => (
              <li key={i}>
                <a
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                >
                  {s.title || s.url}
                  <ExternalLink className="h-3 w-3" />
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
