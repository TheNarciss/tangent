import { useState } from "react";
import { Sparkles } from "lucide-react";

import { useTodayReview } from "@/api";
import { ReviewSheet } from "@/components/ReviewSheet";
import {
  BottomSheet,
  BottomSheetContent,
  BottomSheetHeader,
  BottomSheetTitle,
} from "@/components/ui/bottom-sheet";
import { cn } from "@/lib/utils";

const PREVIEW_MAX_CHARS = 200;

/**
 * Take everything before the first markdown `##` heading (the introductory
 * paragraph of the briefing). Falls back to the first PREVIEW_MAX_CHARS
 * chars if no heading is found. Strips leading markdown markers.
 */
function extractPreview(content: string): string {
  if (!content) return "";

  const headingMatch = content.match(/^##\s/m);
  const raw = headingMatch ? content.slice(0, content.indexOf(headingMatch[0])) : content;

  const cleaned = raw
    .replace(/^#+\s.*$/m, "")
    .replace(/^\s+|\s+$/g, "")
    .replace(/\s+/g, " ");

  if (cleaned.length > PREVIEW_MAX_CHARS) {
    return cleaned.slice(0, PREVIEW_MAX_CHARS).trimEnd() + "…";
  }
  return cleaned;
}

/**
 * AI Brief tile — shows a preview of today's review, expands to the full
 * markdown content in a bottom sheet on tap.
 *
 * States:
 *   - Loading: skeleton
 *   - Has review: preview (first paragraph, ~200 chars) + "tap for full" CTA
 *   - No review: empty state explaining when the next one arrives
 */
export function AiBriefTile() {
  const { data: review, isLoading } = useTodayReview();
  const [open, setOpen] = useState(false);

  const headerLabel = (
    <div className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
      <Sparkles className="h-3 w-3" />
      Briefing IA
    </div>
  );

  if (isLoading) {
    return (
      <div className="flex flex-col gap-2 rounded-lg border border-border bg-card p-4 md:p-5">
        {headerLabel}
        <div className="mt-2 h-12 animate-pulse rounded bg-muted/30" />
      </div>
    );
  }

  if (!review) {
    return (
      <div className="flex flex-col gap-2 rounded-lg border border-border bg-card p-4 md:p-5">
        {headerLabel}
        <p className="text-sm leading-relaxed text-muted-foreground">
          Pas encore de briefing aujourd'hui. Le prochain arrive dans la nuit, vers 3h.
        </p>
      </div>
    );
  }

  const preview = extractPreview(review.content);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={cn(
          "flex cursor-pointer flex-col gap-2 rounded-lg border border-border bg-card p-4 text-left transition-colors hover:bg-accent/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:p-5",
        )}
      >
        {headerLabel}
        <p className="line-clamp-4 text-sm leading-relaxed">{preview}</p>
        <div className="text-[10px] text-muted-foreground">Voir la review complète →</div>
      </button>

      <BottomSheet open={open} onOpenChange={setOpen}>
        <BottomSheetContent className="md:max-w-3xl">
          <BottomSheetHeader>
            <BottomSheetTitle>Ta review du jour</BottomSheetTitle>
          </BottomSheetHeader>
          <ReviewSheet review={review} />
        </BottomSheetContent>
      </BottomSheet>
    </>
  );
}
