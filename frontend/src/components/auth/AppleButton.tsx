import { useState } from "react";

import { Button } from "@/components/ui/button";
import { startAppleLogin } from "@/api";

/** The Apple mark, as Apple's guidelines draw it: plain, single colour. */
function AppleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden="true" fill="currentColor">
      <path d="M16.365 12.79c-.025-2.53 2.066-3.746 2.16-3.804-1.178-1.72-3.01-1.956-3.66-1.982-1.56-.158-3.043.918-3.834.918-.79 0-2.01-.896-3.303-.872-1.7.025-3.266.988-4.14 2.51-1.766 3.062-.45 7.6 1.27 10.086.84 1.216 1.84 2.582 3.153 2.533 1.265-.05 1.743-.82 3.272-.82 1.53 0 1.958.82 3.297.796 1.362-.025 2.225-1.24 3.06-2.46.965-1.412 1.363-2.78 1.387-2.85-.03-.013-2.662-1.022-2.662-4.055zM13.85 5.36c.697-.845 1.167-2.02 1.04-3.19-1.005.04-2.22.67-2.94 1.513-.646.75-1.21 1.947-1.06 3.096 1.12.087 2.264-.57 2.96-1.42z" />
    </svg>
  );
}

/** Sign in with Apple, on the site. Black on light, white on dark, as Apple asks. */
export function AppleButton({ disabled }: { disabled?: boolean }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleClick = async () => {
    setBusy(true);
    setError(null);
    try {
      await startAppleLogin();
    } catch (e) {
      setBusy(false);
      setError(e instanceof Error ? e.message : "Erreur inconnue.");
    }
  };

  return (
    <div className="space-y-2">
      <Button
        type="button"
        className="w-full bg-black text-white hover:bg-black/90 dark:bg-white dark:text-black dark:hover:bg-white/90"
        onClick={handleClick}
        disabled={disabled || busy}
      >
        <AppleIcon />
        <span className="ml-2">{busy ? "Redirection…" : "Continuer avec Apple"}</span>
      </Button>
      {error && <p className="text-xs text-[hsl(var(--loss))]">{error}</p>}
    </div>
  );
}
