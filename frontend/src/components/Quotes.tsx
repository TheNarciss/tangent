import { useEffect, useState } from "react";
import { Search } from "lucide-react";

import { useQuoteSearch, type QuoteMatch } from "@/api";
import { useT, type MessageKey } from "@/i18n";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { QuotePanel } from "@/components/QuoteChart";

/**
 * « Cours » — find a share, a fund or an index by name and read its price.
 *
 * The same chart a position opens, without holding the line. Nothing here
 * is a recommendation and nothing is saved: the tab forgets the search when
 * it is left.
 */
const KIND_KEYS: Record<QuoteMatch["kind"], MessageKey> = {
  equity: "market.quotes.kind.equity",
  etf: "market.quotes.kind.etf",
  index: "market.quotes.kind.index",
};

/** Yahoo is asked once the fingers pause, not on every key. */
const DEBOUNCE_MS = 350;

export function Quotes() {
  const { t } = useT();
  const [query, setQuery] = useState("");
  const [asked, setAsked] = useState("");
  const [picked, setPicked] = useState<QuoteMatch | null>(null);
  const results = useQuoteSearch(asked);

  useEffect(() => {
    const id = window.setTimeout(() => setAsked(query), DEBOUNCE_MS);
    return () => window.clearTimeout(id);
  }, [query]);

  const searching = asked.trim().length >= 2;
  const matches = searching ? (results.data ?? []) : [];

  return (
    <div className="space-y-6">
      <section className="rounded-xl border bg-card p-4 md:p-6">
        <p className="text-sm">{t("market.quotes.intro")}</p>
        <div className="relative mt-4">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            inputMode="search"
            autoComplete="off"
            aria-label={t("market.quotes.search.aria")}
            placeholder={t("market.quotes.search.placeholder")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="h-11 pl-9 text-base"
          />
        </div>
      </section>

      {picked && (
        <section className="rounded-xl border bg-card p-4 md:p-6">
          <h2 className="mb-1 truncate text-base font-semibold">{picked.name}</h2>
          <p className="mb-4 text-xs text-muted-foreground">
            {picked.symbol} · {picked.exchange} · {t(KIND_KEYS[picked.kind])}
          </p>
          <QuotePanel key={picked.symbol} quote={{ symbol: picked.symbol, label: picked.name }} />
        </section>
      )}

      {searching &&
        (results.isLoading ? (
          <p className="text-sm text-muted-foreground">{t("market.quotes.search.searching")}</p>
        ) : matches.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("market.quotes.search.none")}</p>
        ) : (
          <ul className="divide-y rounded-md border text-sm">
            {matches.map((m) => (
              <li key={m.symbol}>
                <button
                  type="button"
                  onClick={() => setPicked(m)}
                  aria-pressed={picked?.symbol === m.symbol}
                  className={cn(
                    "flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-accent/40",
                    picked?.symbol === m.symbol && "bg-accent/30",
                  )}
                >
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-medium">{m.name}</div>
                    <div className="text-xs text-muted-foreground">
                      {m.symbol} · {m.exchange}
                    </div>
                  </div>
                  <span className="shrink-0 rounded-full border px-2 py-0.5 text-[11px] text-muted-foreground">
                    {t(KIND_KEYS[m.kind])}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        ))}
    </div>
  );
}
