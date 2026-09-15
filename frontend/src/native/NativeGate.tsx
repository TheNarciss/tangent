import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { App } from "@capacitor/app";

import { Button } from "@/components/ui/button";
import { Logo } from "@/components/Logo";
import { useT } from "@/i18n";

import { TangentNative, isNative } from "./bridge";

/** Back from the background after this long, the app asks for Face ID again. */
const RELOCK_AFTER_MS = 60_000;

/**
 * On the phone, nothing shows before Face ID (or the passcode) says so; on
 * the site the gate is invisible. Locks again after a minute in the background.
 */
export function NativeGate({ children }: { children: ReactNode }) {
  const [locked, setLocked] = useState(isNative());
  const [asking, setAsking] = useState(false);
  const leftAt = useRef<number | null>(null);
  const { t } = useT();

  const unlock = useCallback(async () => {
    setAsking(true);
    try {
      const result = await TangentNative.unlock({ reason: t("system.gate.unlockReason") });
      setLocked(!result.success);
    } catch {
      setLocked(true);
    } finally {
      setAsking(false);
    }
  }, [t]);

  useEffect(() => {
    if (!isNative()) return;
    void unlock();
    const handle = App.addListener("appStateChange", ({ isActive }) => {
      if (!isActive) {
        leftAt.current = Date.now();
        return;
      }
      if (leftAt.current !== null && Date.now() - leftAt.current > RELOCK_AFTER_MS) {
        setLocked(true);
        void unlock();
      }
      leftAt.current = null;
    });
    return () => {
      handle.then((h) => h.remove()).catch(() => {});
    };
  }, [unlock]);

  if (!locked) return <>{children}</>;

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-background px-6">
      <Logo size={64} />
      <div className="text-center">
        <p className="text-lg font-semibold">{t("system.gate.locked")}</p>
        <p className="text-sm text-muted-foreground">{t("system.gate.protects")}</p>
      </div>
      <Button onClick={() => void unlock()} disabled={asking} className="w-full max-w-xs">
        {asking ? t("system.gate.checking") : t("system.gate.unlock")}
      </Button>
    </div>
  );
}
