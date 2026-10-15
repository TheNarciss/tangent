import { useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  KeyRound,
  Loader2,
  Sparkles,
  Tags,
  Trash2,
  Unlink,
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  ApiError,
  adminCategorizeNow,
  generateReviewNow,
  changePassword,
  deleteMyAccount,
  exportEverything,
  listOAuthAccounts,
  deleteOAuthAccount,
  useCurrentUser,
} from "@/api";
import { useProfile } from "@/lib/profile";
import { isNative } from "@/native/bridge";
import { disablePush, enablePush, pushState } from "@/native/push";
import { cn } from "@/lib/utils";
import {
  LOCALES,
  detectLocale,
  setLocalePreference,
  useLocalePreference,
  useT,
  type LocalePreference,
} from "@/i18n";
import { briefingTime } from "@/components/dashboard/AiBriefTile";
import { Button } from "@/components/ui/button";
import { Section } from "@/components/ui/section";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/**
 * Mon compte — gestion du compte Tangent et de ses connexions externes.
 *
 * Sections : Email, Langue, Mot de passe, Comptes liés (OAuth), Briefing,
 * Export, Administration, Zone dangereuse (delete account).
 */
export function AccountTab() {
  return (
    <div className="space-y-12">
      <EmailSection />
      <LanguageSection />
      <PasswordSection />
      <OAuthSection />
      <AutoReviewSection />
      <ExportSection />
      <AdminSection />
      <DangerZone />
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────────── */
/*  Admin                                                                   */
/* ──────────────────────────────────────────────────────────────────────── */

function AdminSection() {
  const { data: user } = useCurrentUser();
  const { t, tn } = useT();
  const qc = useQueryClient();
  const run = useMutation({
    mutationFn: adminCategorizeNow,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["spending"] });
      qc.invalidateQueries({ queryKey: ["transactions"] });
    },
  });
  const brief = useMutation({
    mutationFn: generateReviewNow,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reviews"] }),
  });
  if (!user?.is_superuser) return null;

  return (
    <Section title={t("account.adminSection.title")} description={t("account.adminSection.desc")}>
      <div className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          onClick={() => brief.mutate()}
          disabled={brief.isPending}
          className="gap-2"
        >
          <Sparkles className="h-4 w-4" />
          {brief.isPending
            ? t("account.adminSection.generating")
            : t("account.adminSection.generate")}
        </Button>
        <Button
          variant="outline"
          onClick={() => run.mutate()}
          disabled={run.isPending}
          className="gap-2"
        >
          <Tags className="h-4 w-4" />
          {run.isPending
            ? t("account.adminSection.categorizing")
            : t("account.adminSection.categorize")}
        </Button>
      </div>
      {brief.isSuccess && (
        <p className="mt-2 text-xs text-muted-foreground">{t("account.adminSection.briefReady")}</p>
      )}
      {brief.error && (
        <p className="mt-2 text-xs text-[hsl(var(--loss))]">
          {brief.error instanceof Error ? brief.error.message : t("common.unknownError")}
        </p>
      )}
      {run.data && (
        <p className="mt-2 text-xs text-muted-foreground">
          {tn("account.adminSection.learned", run.data.learned)}
          {run.data.batch
            ? tn("account.adminSection.sent", run.data.batch.n_requests)
            : t("account.adminSection.nothingSent")}
          .
        </p>
      )}
      {run.error && (
        <p className="mt-2 text-xs text-[hsl(var(--loss))]">
          {run.error instanceof Error ? run.error.message : t("common.unknownError")}
        </p>
      )}
    </Section>
  );
}

/* ──────────────────────────────────────────────────────────────────────── */
/*  Email (read-only)                                                       */
/* ──────────────────────────────────────────────────────────────────────── */

function EmailSection() {
  const { data: user } = useCurrentUser();
  const { t } = useT();
  if (!user) return null;

  return (
    <Section title={t("account.email.title")} description={t("account.email.desc")}>
      <div className="flex items-center gap-3 rounded-md border bg-muted/30 px-3 py-2">
        <span className="font-mono text-sm">{user.email}</span>
        {user.is_superuser && (
          <span className="ml-auto text-[11px] uppercase tracking-wider text-[hsl(var(--gain))]">
            {t("account.admin")}
          </span>
        )}
      </div>
    </Section>
  );
}

/* ──────────────────────────────────────────────────────────────────────── */
/*  Language                                                                */
/* ──────────────────────────────────────────────────────────────────────── */

function LanguageSection() {
  const { t } = useT();
  const preference = useLocalePreference();
  const detected = detectLocale(typeof navigator === "undefined" ? [] : navigator.languages);
  const choices: { value: LocalePreference; label: string; hint?: string }[] = [
    {
      value: "auto",
      label: t("account.language.auto"),
      hint: t("account.language.autoHint", { language: t(`account.language.${detected}`) }),
    },
    ...LOCALES.map((l) => ({ value: l, label: t(`account.language.${l}`) })),
  ];

  return (
    <Section title={t("account.language.title")} description={t("account.language.desc")}>
      <div className="flex flex-col gap-2 sm:flex-row" role="radiogroup">
        {choices.map((c) => {
          const selected = preference === c.value;
          return (
            <button
              key={c.value}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => setLocalePreference(c.value)}
              className={cn(
                "flex min-h-[44px] flex-1 flex-col items-start rounded-md border px-3 py-2 text-left text-sm transition-colors",
                selected
                  ? "border-primary bg-primary/10 font-medium"
                  : "border-border hover:bg-accent/50",
              )}
            >
              <span>{c.label}</span>
              {c.hint && <span className="text-xs text-muted-foreground">{c.hint}</span>}
            </button>
          );
        })}
      </div>
    </Section>
  );
}

/* ──────────────────────────────────────────────────────────────────────── */
/*  Password                                                                */
/* ──────────────────────────────────────────────────────────────────────── */

function PasswordSection() {
  const { data: user } = useCurrentUser();
  const { t } = useT();
  const [open, setOpen] = useState(false);

  if (!user) return null;

  const hasPassword = user.has_password ?? true;

  return (
    <Section title={t("account.password.title")} description={t("account.password.desc")}>
      {hasPassword ? (
        <>
          <Button variant="outline" onClick={() => setOpen(true)} className="gap-2">
            <KeyRound className="h-4 w-4" />
            {t("account.password.change")}
          </Button>
          <ChangePasswordDialog open={open} onOpenChange={setOpen} />
        </>
      ) : (
        <div className="rounded-md border bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
          {t("account.password.none")}
        </div>
      )}
    </Section>
  );
}

function ChangePasswordDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const { t } = useT();

  const mutation = useMutation({
    mutationFn: () => changePassword(current, next),
    onSuccess: () => {
      setSuccess(true);
      setTimeout(() => {
        onOpenChange(false);
        reset();
      }, 1500);
    },
    onError: (e) => {
      setError(e instanceof Error ? e.message : t("common.unknownError"));
    },
  });

  const reset = () => {
    setCurrent("");
    setNext("");
    setConfirm("");
    setError(null);
    setSuccess(false);
  };

  const handleSubmit = () => {
    setError(null);
    if (next.length < 8) {
      setError(t("account.password.tooShort"));
      return;
    }
    if (next !== confirm) {
      setError(t("account.password.differ"));
      return;
    }
    if (next === current) {
      setError(t("account.password.sameAsOld"));
      return;
    }
    mutation.mutate();
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!v) reset();
        onOpenChange(v);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("account.password.change")}</DialogTitle>
          <DialogDescription>{t("account.password.dialogDesc")}</DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-2">
          <div className="space-y-1.5">
            <Label htmlFor="current_pwd" className="text-xs">
              {t("account.password.current")}
            </Label>
            <Input
              id="current_pwd"
              type="password"
              autoComplete="current-password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              disabled={mutation.isPending || success}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="new_pwd" className="text-xs">
              {t("account.password.new")}
            </Label>
            <Input
              id="new_pwd"
              type="password"
              autoComplete="new-password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
              disabled={mutation.isPending || success}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="confirm_pwd" className="text-xs">
              {t("account.password.confirmNew")}
            </Label>
            <Input
              id="confirm_pwd"
              type="password"
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              disabled={mutation.isPending || success}
            />
          </div>

          {error && <p className="text-sm text-[hsl(var(--loss))]">{error}</p>}
          {success && (
            <div className="flex items-center gap-2 text-sm text-[hsl(var(--gain))]">
              <CheckCircle2 className="h-4 w-4" />
              {t("account.password.updated")}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={mutation.isPending}
          >
            {t("common.cancel")}
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!current || !next || !confirm || mutation.isPending || success}
          >
            {mutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            {success ? t("common.saved") : t("common.save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* ──────────────────────────────────────────────────────────────────────── */
/*  OAuth accounts                                                          */
/* ──────────────────────────────────────────────────────────────────────── */

function OAuthSection() {
  const { data: user } = useCurrentUser();
  const { t } = useT();
  const accounts = useQuery({
    queryKey: ["user", "oauth-accounts"],
    queryFn: listOAuthAccounts,
  });

  const hasPassword = user?.has_password ?? true;

  return (
    <Section title={t("account.oauth.title")} description={t("account.oauth.desc")}>
      {accounts.isLoading && <p className="text-sm text-muted-foreground">{t("common.loading")}</p>}
      {accounts.isError && (
        <p className="text-sm text-[hsl(var(--loss))]">{t("account.oauth.loadFailed")}</p>
      )}
      {accounts.data && accounts.data.length === 0 && (
        <div className="rounded-md border border-dashed py-6 text-center text-sm text-muted-foreground">
          {t("account.oauth.none")}
        </div>
      )}
      {accounts.data && accounts.data.length > 0 && (
        <div className="space-y-2">
          {accounts.data.map((acc) => (
            <OAuthRow
              key={acc.id}
              accountId={acc.id}
              provider={acc.oauth_name}
              email={acc.account_email}
              canUnlink={hasPassword || accounts.data.length > 1}
            />
          ))}
        </div>
      )}
    </Section>
  );
}

function OAuthRow({
  accountId,
  provider,
  email,
  canUnlink,
}: {
  accountId: string;
  provider: string;
  email: string | null;
  canUnlink: boolean;
}) {
  const qc = useQueryClient();
  const { t } = useT();
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => deleteOAuthAccount(accountId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["user", "oauth-accounts"] });
      setConfirming(false);
    },
    onError: (e) => {
      setError(e instanceof Error ? e.message : t("common.unknownError"));
    },
  });

  const label = provider.charAt(0).toUpperCase() + provider.slice(1);

  return (
    <>
      <div className="flex items-center gap-3 rounded-md border px-3 py-2">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium">{label}</p>
          {email && <p className="text-xs text-muted-foreground truncate">{email}</p>}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setConfirming(true)}
          disabled={!canUnlink}
          className="gap-2 text-muted-foreground hover:text-[hsl(var(--loss))]"
          title={
            !canUnlink
              ? t("account.oauth.unlinkBlocked")
              : t("account.oauth.unlinkNamed", { provider: label })
          }
        >
          <Unlink className="h-3.5 w-3.5" />
          {t("account.oauth.unlink")}
        </Button>
      </div>

      <Dialog open={confirming} onOpenChange={setConfirming}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("account.oauth.unlinkTitle", { provider: label })}</DialogTitle>
            <DialogDescription>
              {t("account.oauth.unlinkDesc", { provider: label })}
            </DialogDescription>
          </DialogHeader>
          {error && <p className="text-sm text-[hsl(var(--loss))]">{error}</p>}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setConfirming(false)}
              disabled={mutation.isPending}
            >
              {t("common.cancel")}
            </Button>
            <Button
              variant="destructive"
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
            >
              {mutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {t("account.oauth.unlink")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

/* ──────────────────────────────────────────────────────────────────────── */
/*  Danger zone — delete account                                            */
/* ──────────────────────────────────────────────────────────────────────── */

/* ──────────────────────────────────────────────────────────────────────── */
/*  Export                                                                  */
/* ──────────────────────────────────────────────────────────────────────── */
function ExportSection() {
  const { t } = useT();
  const [error, setError] = useState<string | null>(null);
  const download = useMutation({
    mutationFn: exportEverything,
    onMutate: () => setError(null),
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `tangent-export-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    },
    onError: (e) => setError(e instanceof Error ? e.message : t("account.export.failed")),
  });

  return (
    <Section title={t("account.export.title")} description={t("account.export.desc")}>
      <Button
        variant="outline"
        onClick={() => download.mutate()}
        disabled={download.isPending}
        className="gap-2"
      >
        {download.isPending ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Download className="h-4 w-4" />
        )}
        {download.isPending ? t("account.export.preparing") : t("account.export.download")}
      </Button>
      {error && <p className="mt-2 text-sm text-destructive">{error}</p>}
    </Section>
  );
}

function DangerZone() {
  const { t } = useT();
  const [open, setOpen] = useState(false);

  return (
    <Section title={t("account.danger.title")} description={t("account.danger.desc")}>
      <div className="rounded-md border border-[hsl(var(--loss))]/40 bg-[hsl(var(--loss))]/5 p-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-[hsl(var(--loss))] shrink-0 mt-0.5" />
          <div className="flex-1 space-y-3">
            <div>
              <p className="text-sm font-medium">{t("account.danger.delete")}</p>
              <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                {t("account.danger.deleteDesc")}
              </p>
            </div>
            <Button variant="destructive" size="sm" onClick={() => setOpen(true)} className="gap-2">
              <Trash2 className="h-4 w-4" />
              {t("account.danger.delete")}
            </Button>
          </div>
        </div>
      </div>
      <DeleteAccountDialog open={open} onOpenChange={setOpen} />
    </Section>
  );
}

function DeleteAccountDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const { data: user } = useCurrentUser();
  const { t } = useT();
  const [confirmation, setConfirmation] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const hasPassword = user?.has_password ?? true;

  const mutation = useMutation({
    mutationFn: () =>
      deleteMyAccount({
        confirmation,
        current_password: hasPassword ? password : null,
      }),
    onSuccess: () => {
      // Reload pour forcer un logout + retour à AuthScreen
      window.location.href = "/?account_deleted=1";
    },
    onError: (e) => {
      if (e instanceof ApiError) {
        setError(e.message);
      } else {
        setError(e instanceof Error ? e.message : t("common.unknownError"));
      }
    },
  });

  const canSubmit =
    confirmation === "DELETE" && (!hasPassword || password.length > 0) && !mutation.isPending;

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!v) {
          setConfirmation("");
          setPassword("");
          setError(null);
        }
        onOpenChange(v);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="text-[hsl(var(--loss))]">
            {t("account.danger.dialogTitle")}
          </DialogTitle>
          <DialogDescription>
            {t("account.danger.dialogBefore")}
            <strong>{t("account.danger.irreversible")}</strong>
            {t("account.danger.dialogAfter")}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-2">
          {hasPassword && (
            <div className="space-y-1.5">
              <Label htmlFor="delete_pwd" className="text-xs">
                {t("account.danger.currentPassword")}
              </Label>
              <Input
                id="delete_pwd"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={mutation.isPending}
              />
            </div>
          )}
          <div className="space-y-1.5">
            <Label htmlFor="delete_confirm" className="text-xs">
              {t("account.danger.typeToConfirm")}{" "}
              <code className="font-mono font-semibold">DELETE</code>{" "}
              {t("account.danger.toConfirm")}
            </Label>
            <Input
              id="delete_confirm"
              type="text"
              autoComplete="off"
              autoCapitalize="off"
              spellCheck={false}
              value={confirmation}
              onChange={(e) => setConfirmation(e.target.value)}
              placeholder="DELETE"
              disabled={mutation.isPending}
              className="font-mono"
            />
          </div>

          {error && <p className="text-sm text-[hsl(var(--loss))]">{error}</p>}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={mutation.isPending}
          >
            {t("common.cancel")}
          </Button>
          <Button variant="destructive" onClick={() => mutation.mutate()} disabled={!canSubmit}>
            {mutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            {t("account.danger.deleteForever")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* ──────────────────────────────────────────────────────────────────────── */
/*  Auto-review opt-in (nightly LLM batch — ADR-018)                        */
/* ──────────────────────────────────────────────────────────────────────── */

function BriefingNotification() {
  const { t } = useT();
  const [state, setState] = useState<{ on: boolean; denied: boolean } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!isNative()) return;
    void pushState().then(({ granted, askable, token }) =>
      setState({ on: granted && !!token, denied: !granted && !askable }),
    );
  }, []);

  if (!isNative() || state === null) return null;

  const toggle = async () => {
    setBusy(true);
    if (state.on) {
      await disablePush();
      setState({ on: false, denied: state.denied });
    } else {
      const { granted, token } = await enablePush();
      setState({ on: granted && !!token, denied: !granted });
    }
    setBusy(false);
  };

  return (
    <div className="mt-2 flex items-start gap-3 rounded-md border bg-muted/30 px-3 py-3">
      <input
        id="briefing-push-toggle"
        type="checkbox"
        checked={state.on}
        onChange={() => void toggle()}
        disabled={busy || state.denied}
        className="mt-0.5 h-4 w-4 rounded border-input accent-primary cursor-pointer"
      />
      <label htmlFor="briefing-push-toggle" className="flex-1 cursor-pointer">
        <p className="text-sm font-medium">{t("account.briefing.notify")}</p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {state.denied
            ? t("account.briefing.notifyDenied")
            : state.on
              ? t("account.briefing.notifyOn")
              : t("account.briefing.notifyOff")}
        </p>
      </label>
    </div>
  );
}

function AutoReviewSection() {
  const { data: user } = useCurrentUser();
  const { t } = useT();
  const [profile, setProfile] = useProfile();
  // The nightly run costs an LLM call: only an administrator sees the switch.
  if (!profile || !user?.is_superuser) return null;

  const enabled = profile.auto_review_enabled ?? false;
  const toggle = () => {
    setProfile({ ...profile, auto_review_enabled: !enabled });
  };

  return (
    <Section
      title={t("account.briefing.title")}
      description={t("account.briefing.desc", { time: briefingTime() })}
    >
      <div className="flex items-start gap-3 rounded-md border bg-muted/30 px-3 py-3 hover:bg-muted/50 transition">
        <input
          id="auto-review-toggle"
          type="checkbox"
          checked={enabled}
          onChange={toggle}
          className="mt-0.5 h-4 w-4 rounded border-input accent-primary cursor-pointer"
        />
        <label htmlFor="auto-review-toggle" className="flex-1 cursor-pointer">
          <p className="text-sm font-medium">{t("account.briefing.receive")}</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {enabled ? t("account.briefing.on") : t("account.briefing.off")}
          </p>
        </label>
      </div>
      {enabled && <BriefingNotification />}
    </Section>
  );
}

/* ──────────────────────────────────────────────────────────────────────── */
/*  Atoms                                                                   */
/* ──────────────────────────────────────────────────────────────────────── */
