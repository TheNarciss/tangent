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
 * Renders the full markdown review of a portfolio. Extracted from AI.tsx
 * ReviewCard so it can be reused inside the Dashboard's AiBriefTile bottom
 * sheet without duplicating markdown rendering + sources display.
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
        <span>·</span>
        <span>{review.model_used}</span>
        <span>·</span>
        <span>
          {review.input_tokens.toLocaleString("fr-FR")} tok in /{" "}
          {review.output_tokens.toLocaleString("fr-FR")} tok out
        </span>
        <span>·</span>
        <span>{review.web_searches_count} recherches web</span>
        <span>·</span>
        <span>${review.cost_usd.toFixed(3)}</span>
      </div>

      <div className="prose prose-sm dark:prose-invert max-w-none">
        <ReactMarkdown>{review.content}</ReactMarkdown>
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
