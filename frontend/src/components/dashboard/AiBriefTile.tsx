import { useState } from "react";
import { Sparkles } from "lucide-react";

import { useCurrentUser, useReviews, useTodayReview, type PortfolioReviewResponse } from "@/api";
import { t, useT } from "@/i18n";
import { formatDate } from "@/lib/accounts";
import { useProfile } from "@/lib/profile";
import { ReviewSheet } from "@/components/ReviewSheet";
import { Button } from "@/components/ui/button";
import {
  BottomSheet,
  BottomSheetContent,
  BottomSheetHeader,
  BottomSheetTitle,
} from "@/components/ui/bottom-sheet";
import { cn } from "@/lib/utils";

const PREVIEW_MAX_CHARS = 200;
/** The nightly batch runs before the user wakes up; one message everywhere. */
export function briefingTime(): string {
  return t("dashboard.briefingTime");
}

/**
 * Take everything before the first markdown `#` heading of the body (the
 * first section), strip markdown markers, cap the length.
 */
function extractPreview(content: string): string {
  if (!content) return "";
  const body = content.replace(/^#\s[^\n]*\n/, ""); // drop the first title line
  const next = body.search(/^#{1,2}\s/m);
  const raw = next > 0 ? body.slice(0, next) : body;
  const cleaned = raw
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/[*_`>]/g, "")
    .replace(/\s+/g, " ")
    .trim();
  return cleaned.length > PREVIEW_MAX_CHARS
    ? cleaned.slice(0, PREVIEW_MAX_CHARS).trimEnd() + "…"
    : cleaned;
}

const DATE_OPTIONS: Intl.DateTimeFormatOptions = {
  weekday: "long",
  day: "numeric",
  month: "long",
};

/**
 * Briefing tile — preview of today's briefing, full text and past briefings
 * in a bottom sheet. When the nightly briefing is off, the tile is the
 * place to turn it on (one tap, saved to the profile).
 */
export function AiBriefTile() {
  const { t } = useT();
  const { data: review, isLoading } = useTodayReview();
  const { data: user } = useCurrentUser();
  const [profile, setProfile] = useProfile();
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<PortfolioReviewResponse | null>(null);
  const history = useReviews(open);
  const enabled = profile?.auto_review_enabled ?? false;

  const header = (
    <div className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
      <Sparkles className="h-3 w-3" />
      {t("dashboard.brief.title")}
    </div>
  );
  const frame = "flex flex-col gap-2 rounded-lg border border-border bg-card p-4 md:p-5";

  if (isLoading) {
    return (
      <div className={frame}>
        {header}
        <div className="mt-2 h-12 animate-pulse rounded bg-muted/30" />
      </div>
    );
  }

  if (!review) {
    return (
      <div className={frame}>
        {header}
        {enabled ? (
          <p className="text-sm leading-relaxed text-muted-foreground">
            {t("dashboard.brief.noneYet", { time: briefingTime() })}
          </p>
        ) : (
          <>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {t("dashboard.brief.pitch")}
            </p>
            {/* The nightly run costs an LLM call: only an administrator turns it on. */}
            {user?.is_superuser && (
              <>
                <Button
                  size="sm"
                  className="self-start"
                  disabled={!profile}
                  onClick={() => profile && setProfile({ ...profile, auto_review_enabled: true })}
                >
                  {t("dashboard.brief.enable")}
                </Button>
                {!profile && (
                  <p className="text-[10px] text-muted-foreground">
                    {t("dashboard.brief.needProfile")}
                  </p>
                )}
              </>
            )}
          </>
        )}
      </div>
    );
  }

  const shown = selected ?? review;
  const preview = extractPreview(review.content);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={cn(
          frame,
          "cursor-pointer text-left transition-colors hover:bg-accent/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        )}
      >
        {header}
        <p className="line-clamp-4 text-sm leading-relaxed">{preview}</p>
        <div className="text-[10px] text-muted-foreground">{t("dashboard.brief.read")}</div>
      </button>

      <BottomSheet
        open={open}
        onOpenChange={(o) => {
          setOpen(o);
          if (!o) setSelected(null);
        }}
      >
        <BottomSheetContent className="md:max-w-3xl">
          <BottomSheetHeader>
            <BottomSheetTitle>
              {shown.id === review.id
                ? t("dashboard.brief.today")
                : t("dashboard.brief.dated", { date: formatDate(shown.review_date, DATE_OPTIONS) })}
            </BottomSheetTitle>
          </BottomSheetHeader>
          <ReviewSheet review={shown} />
          {history.data && history.data.length > 1 && (
            <div className="border-t border-border px-4 pb-6 pt-4 md:px-6">
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {t("dashboard.brief.previous")}
              </h4>
              <ul className="flex flex-wrap gap-2">
                {history.data
                  .filter((r) => r.id !== shown.id)
                  .slice(0, 14)
                  .map((r) => (
                    <li key={r.id}>
                      <button
                        type="button"
                        onClick={() => setSelected(r)}
                        className="rounded-full border px-3 py-1 text-xs capitalize hover:bg-accent"
                      >
                        {formatDate(r.review_date, DATE_OPTIONS)}
                      </button>
                    </li>
                  ))}
              </ul>
            </div>
          )}
        </BottomSheetContent>
      </BottomSheet>
    </>
  );
}
