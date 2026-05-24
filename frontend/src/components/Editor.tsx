import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";

import { type Portfolio, type Position, useUpdatePortfolio } from "@/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface Props {
  portfolio: Portfolio;
}

const EMPTY_POSITION: Position = { ticker: "", quantity: 0, avg_cost: 0 };

export function Editor({ portfolio }: Props) {
  const [open, setOpen] = useState(false);
  const [positions, setPositions] = useState<Position[]>(portfolio.positions);
  const update = useUpdatePortfolio();

  const reset = () => setPositions(portfolio.positions);

  const handleOpenChange = (next: boolean) => {
    if (next) reset();
    setOpen(next);
  };

  const setField = <K extends keyof Position>(idx: number, key: K, value: Position[K]) => {
    setPositions((prev) => prev.map((p, i) => (i === idx ? { ...p, [key]: value } : p)));
  };

  const addRow = () => setPositions((prev) => [...prev, { ...EMPTY_POSITION }]);
  const removeRow = (idx: number) => setPositions((prev) => prev.filter((_, i) => i !== idx));

  const save = async () => {
    const cleaned = positions
      .map((p) => ({ ...p, ticker: p.ticker.trim().toUpperCase() }))
      .filter((p) => p.ticker && p.quantity > 0 && p.avg_cost > 0);
    await update.mutateAsync({ positions: cleaned, cash: portfolio.cash });
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          Modifier les positions
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Positions du portefeuille</DialogTitle>
          <DialogDescription>
            Ticker au format Yahoo Finance (ex. <span className="font-mono">CW8.PA</span>).
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2">
          <div className="grid grid-cols-[1fr_1fr_1fr_auto] gap-2 px-1 text-xs text-muted-foreground">
            <Label>Ticker</Label>
            <Label>Quantité</Label>
            <Label>Prix moyen</Label>
            <span />
          </div>
          {positions.map((p, idx) => (
            <div key={idx} className="grid grid-cols-[1fr_1fr_1fr_auto] gap-2">
              <Input
                value={p.ticker}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setField(idx, "ticker", e.target.value)
                }
                placeholder="CW8.PA"
                className="font-mono"
              />
              <Input
                type="number"
                value={p.quantity || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setField(idx, "quantity", Number(e.target.value))
                }
                step="any"
                min={0}
              />
              <Input
                type="number"
                value={p.avg_cost || ""}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setField(idx, "avg_cost", Number(e.target.value))
                }
                step="any"
                min={0}
              />
              <Button
                variant="ghost"
                size="icon"
                onClick={() => removeRow(idx)}
                aria-label="Supprimer"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
          <Button variant="ghost" size="sm" onClick={addRow} className="w-full">
            <Plus className="h-4 w-4 mr-2" />
            Ajouter une ligne
          </Button>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Annuler
          </Button>
          <Button onClick={save} disabled={update.isPending}>
            {update.isPending ? "Enregistrement…" : "Enregistrer"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
