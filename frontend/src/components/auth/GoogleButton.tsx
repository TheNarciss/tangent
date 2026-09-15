import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { startGoogleAssociate } from "@/api";
import { useT } from "@/i18n";
import { signInWithGoogle } from "@/native/flows";

interface GoogleButtonProps {
  /** "login" = signup OR login flow (non-authenticated user).
   *  "associate" = link a Google account to an already-authenticated user. */
  mode: "login" | "associate";
  /** Custom label override. Defaults vary by mode. */
  label?: string;
  disabled?: boolean;
}

/** Google "G" SVG — official guideline colors. */
function GoogleIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 48 48"
      className="h-4 w-4"
      aria-hidden="true"
    >
      <path
        fill="#FFC107"
        d="M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8c-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4C12.955 4 4 12.955 4 24s8.955 20 20 20s20-8.955 20-20c0-1.341-.138-2.65-.389-3.917"
      />
      <path
        fill="#FF3D00"
        d="m6.306 14.691l6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4C16.318 4 9.656 8.337 6.306 14.691"
      />
      <path
        fill="#4CAF50"
        d="M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238A11.91 11.91 0 0 1 24 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44"
      />
      <path
        fill="#1976D2"
        d="M43.611 20.083H42V20H24v8h11.303a12.04 12.04 0 0 1-4.087 5.571l.003-.002l6.19 5.238C36.971 39.205 44 34 44 24c0-1.341-.138-2.65-.389-3.917"
      />
    </svg>
  );
}

export function GoogleButton({ mode, label, disabled }: GoogleButtonProps) {
  const qc = useQueryClient();
  const { t } = useT();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const defaultLabel = mode === "login" ? t("auth.continueGoogle") : t("menu.linkGoogle");
  const displayLabel = label ?? defaultLabel;

  const handleClick = async () => {
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") {
        await signInWithGoogle(qc);
      } else {
        await startGoogleAssociate();
      }
      // On the site the page navigates away; in the app the session is now open.
      setBusy(false);
    } catch (e) {
      setBusy(false);
      setError(e instanceof Error ? e.message : t("common.unknownError"));
    }
  };

  return (
    <div className="space-y-2">
      <Button
        type="button"
        variant="outline"
        className="w-full"
        onClick={handleClick}
        disabled={disabled || busy}
      >
        <GoogleIcon />
        <span className="ml-2">{busy ? t("auth.redirecting") : displayLabel}</span>
      </Button>
      {error && <p className="text-xs text-[hsl(var(--loss))]">{error}</p>}
    </div>
  );
}
