import { Building2, Plus } from "lucide-react";
import { useState } from "react";

import {
  getPowensWebviewUrl,
  startEnableBankingAuth,
  useEnableBankingStatus,
  useSyncStatus,
} from "@/api";
import {
  BottomSheet,
  BottomSheetContent,
  BottomSheetDescription,
  BottomSheetHeader,
  BottomSheetTitle,
} from "@/components/ui/bottom-sheet";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/** The bank Enable Banking carries for us; everything else goes through Powens (ADR-032). */
const ENABLEBANKING_BANK = "Revolut";

/** Header button: opens the sheet where the user picks how to connect a bank. */
export function AddBankButton() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)} className="gap-2">
        <Plus className="h-4 w-4" />
        Ajouter une banque
      </Button>
      <AddBankSheet open={open} onOpenChange={setOpen} />
    </>
  );
}

function AddBankSheet({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
}) {
  const powens = useSyncStatus();
  const enablebanking = useEnableBankingStatus();
  const [busy, setBusy] = useState<"revolut" | "other" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const go = async (which: "revolut" | "other") => {
    setBusy(which);
    setError(null);
    try {
      const url =
        which === "revolut"
          ? await startEnableBankingAuth(ENABLEBANKING_BANK)
          : await getPowensWebviewUrl();
      window.location.href = url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur inconnue");
      setBusy(null);
    }
  };

  const powensReady = powens.data?.configured ?? true;
  const revolutReady = enablebanking.data?.configured ?? true;

  return (
    <BottomSheet open={open} onOpenChange={onOpenChange}>
      <BottomSheetContent className="md:max-w-md">
        <BottomSheetHeader>
          <BottomSheetTitle>Ajouter une banque</BottomSheetTitle>
          <BottomSheetDescription>
            Tangent passe par un service agréé : on ne voit jamais tes identifiants.
          </BottomSheetDescription>
        </BottomSheetHeader>
        <div className="space-y-2 p-4 md:p-6">
          <Choice
            title="Revolut"
            detail={
              revolutReady
                ? "Via Enable Banking. Consentement valable 180 jours, puis à refaire."
                : "Enable Banking n'est pas configuré côté serveur."
            }
            disabled={!revolutReady || busy !== null}
            busy={busy === "revolut"}
            onClick={() => go("revolut")}
          />
          <Choice
            title="Une autre banque"
            detail={
              powensReady
                ? "BNP, Boursorama, Crédit Agricole… via Powens."
                : "Powens n'est pas configuré côté serveur."
            }
            disabled={!powensReady || busy !== null}
            busy={busy === "other"}
            onClick={() => go("other")}
          />
          {error && <p className="text-xs text-[hsl(var(--loss))]">{error}</p>}
        </div>
      </BottomSheetContent>
    </BottomSheet>
  );
}

function Choice({
  title,
  detail,
  disabled,
  busy,
  onClick,
}: {
  title: string;
  detail: string;
  disabled: boolean;
  busy: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "flex w-full items-center gap-3 rounded-lg border px-4 py-3 text-left transition-colors",
        "hover:bg-accent/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        "disabled:cursor-not-allowed disabled:opacity-60",
      )}
    >
      <Building2 className="h-5 w-5 shrink-0 text-muted-foreground" />
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-medium">{busy ? "Redirection…" : title}</span>
        <span className="block text-xs text-muted-foreground">{detail}</span>
      </span>
    </button>
  );
}
