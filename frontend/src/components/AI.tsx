import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { Sparkles, RefreshCw, ExternalLink, Clock } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

import { useTodayReview, useReviewsHistory, type PortfolioReviewResponse } from "@/api";
import { streamReview } from "@/lib/streaming";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

export function AI() {
  const today = useTodayReview();
  const history = useReviewsHistory();
  const queryClient = useQueryClient();

  const [streaming, setStreaming] = useState(false);
  const [streamedContent, setStreamedContent] = useState("");
  const [streamError, setStreamError] = useState<string | null>(null);
  const [openHistoryId, setOpenHistoryId] = useState<string | null>(null);

  const start = async () => {
    setStreaming(true);
    setStreamedContent("");
    setStreamError(null);

    await streamReview({
      onChunk: (chunk) => setStreamedContent((prev) => prev + chunk),
      onDone: () => {
        setStreaming(false);
        void queryClient.invalidateQueries({ queryKey: ["reviews"] });
      },
      onError: (reason) => {
        setStreaming(false);
        setStreamError(humanError(reason));
      },
    });
  };

  // State 1: review already generated today
  if (today.data && !streaming) {
    return (
      <div className="space-y-6">
        <ReviewCard review={today.data} title="Ta review du jour" />
        <HistorySection
          history={history.data ?? []}
          excludeId={today.data.id}
          openId={openHistoryId}
          onToggle={setOpenHistoryId}
        />
      </div>
    );
  }

  // State 2: streaming in progress
  if (streaming) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="size-4 animate-pulse" />
              Génération en cours...
            </CardTitle>
            <CardDescription>
              Claude analyse ton patrimoine et consulte les sources marché. Quelques dizaines de
              secondes.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown>{streamedContent || "_En attente du premier chunk..._"}</ReactMarkdown>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // State 3: no review today -> generation button
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="size-4" />
            Review IA quotidienne
          </CardTitle>
          <CardDescription>
            Une analyse personnalisée de ton patrimoine par Claude (Sonnet 4.6), en t&apos;appuyant
            sur les tendances marché du moment. Une review par jour, max. Cette analyse est
            informative et ne se substitue pas à un conseiller agréé.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {streamError && (
            <Alert variant="destructive">
              <AlertDescription>{streamError}</AlertDescription>
            </Alert>
          )}
          <Button onClick={start} disabled={streaming || today.isLoading} size="lg">
            <Sparkles className="mr-2 size-4" />
            Générer ma review
          </Button>
          <p className="text-xs text-muted-foreground">
            Le LLM utilise web_search pour aller chercher les tendances actuelles. Sources citées en
            bas de chaque section.
          </p>
        </CardContent>
      </Card>

      <HistorySection
        history={history.data ?? []}
        excludeId={null}
        openId={openHistoryId}
        onToggle={setOpenHistoryId}
      />
    </div>
  );
}

function humanError(reason: string): string {
  if (reason.toLowerCase().includes("budget")) {
    return "Le budget LLM quotidien est atteint. Réessaye demain.";
  }
  if (reason === "daily_cost_cap_reached") {
    return "Budget quotidien atteint. Réessaye demain.";
  }
  if (reason === "already_generated_today") {
    return "Tu as déjà une review aujourd'hui.";
  }
  if (reason === "internal") {
    return "Erreur technique pendant la génération. Réessaye dans un instant.";
  }
  return reason;
}

function ReviewCard({ review, title }: { review: PortfolioReviewResponse; title: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-2">
          <span className="flex items-center gap-2">
            <Sparkles className="size-4" />
            {title}
          </span>
          <span className="text-xs font-normal text-muted-foreground flex items-center gap-1">
            <Clock className="size-3" />
            {new Date(review.created_at).toLocaleString("fr-FR", {
              dateStyle: "long",
              timeStyle: "short",
            })}
          </span>
        </CardTitle>
        <CardDescription>
          {review.model_used} - {review.input_tokens.toLocaleString()} tok in /{" "}
          {review.output_tokens.toLocaleString()} tok out - {review.web_searches_count} recherches
          web - ${review.cost_usd.toFixed(3)}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown>{review.content}</ReactMarkdown>
        </div>
        {review.sources.length > 0 && (
          <div className="mt-6 pt-4 border-t">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
              Sources consultées
            </h4>
            <ul className="space-y-1">
              {review.sources.map((s, i) => (
                <li key={i}>
                  <a
                    href={s.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-primary inline-flex items-center gap-1 hover:underline"
                  >
                    {s.title || s.url}
                    <ExternalLink className="size-3" />
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function HistorySection({
  history,
  excludeId,
  openId,
  onToggle,
}: {
  history: PortfolioReviewResponse[];
  excludeId: string | null;
  openId: string | null;
  onToggle: (id: string | null) => void;
}) {
  const items = history.filter((r) => r.id !== excludeId);
  if (items.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Historique
        </CardTitle>
        <CardDescription>{items.length} review(s) précédente(s).</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {items.map((r) => (
          <div key={r.id} className="border rounded-md">
            <button
              className="w-full flex items-center justify-between p-3 hover:bg-muted/50 transition"
              onClick={() => onToggle(openId === r.id ? null : r.id)}
            >
              <span className="text-sm">
                {new Date(r.review_date).toLocaleDateString("fr-FR", {
                  weekday: "long",
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}
              </span>
              <span className="text-xs text-muted-foreground">
                <RefreshCw
                  className={"size-3 inline transition " + (openId === r.id ? "rotate-90" : "")}
                />
              </span>
            </button>
            {openId === r.id && (
              <div className="p-4 border-t">
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <ReactMarkdown>{r.content}</ReactMarkdown>
                </div>
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
