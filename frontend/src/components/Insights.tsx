import { CheckCircle2, AlertTriangle, XCircle } from "lucide-react";

import type { Insight, Severity } from "@/api";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  insights: Insight[];
}

const STYLE: Record<Severity, { icon: typeof CheckCircle2; color: string }> = {
  good: { icon: CheckCircle2, color: "text-[hsl(var(--gain))]" },
  warning: { icon: AlertTriangle, color: "text-amber-500" },
  critical: { icon: XCircle, color: "text-[hsl(var(--loss))]" },
};

export function Insights({ insights }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Diagnostic
        </CardTitle>
      </CardHeader>
      <CardContent>
        {insights.length === 0 ? (
          <p className="text-sm text-muted-foreground">Rien à signaler.</p>
        ) : (
          <ul className="space-y-3">
            {insights.map((i, idx) => {
              const { icon: Icon, color } = STYLE[i.severity];
              return (
                <li key={idx} className="flex gap-3">
                  <Icon className={cn("h-5 w-5 shrink-0 mt-0.5", color)} />
                  <div className="space-y-0.5">
                    <p className="text-sm font-medium leading-tight">{i.title}</p>
                    <p className="text-sm text-muted-foreground leading-snug">{i.detail}</p>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
