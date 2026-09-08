import { useState } from "react";
import { AlertTriangle, CheckCircle2, KeyRound, Loader2, Trash2, Unlink } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  ApiError,
  changePassword,
  deleteMyAccount,
  listOAuthAccounts,
  deleteOAuthAccount,
  useCurrentUser,
} from "@/api";
import { useProfile } from "@/lib/profile";
import { BRIEFING_TIME } from "@/components/dashboard/AiBriefTile";
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
 * 4 sections : Email, Mot de passe, Comptes liés (OAuth)
 * (Powens), Zone dangereuse (delete account).
 */
export function AccountTab() {
  return (
    <div className="space-y-12">
      <EmailSection />
      <PasswordSection />
      <OAuthSection />
      <AutoReviewSection />
      <DangerZone />
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────────── */
/*  Email (read-only)                                                       */
/* ──────────────────────────────────────────────────────────────────────── */

function EmailSection() {
  const { data: user } = useCurrentUser();
  if (!user) return null;

  return (
    <Section title="Email" description="Identifiant principal de ton compte.">
      <div className="flex items-center gap-3 rounded-md border bg-muted/30 px-3 py-2">
        <span className="font-mono text-sm">{user.email}</span>
        {user.is_superuser && (
          <span className="ml-auto text-[11px] uppercase tracking-wider text-[hsl(var(--gain))]">
            Admin
          </span>
        )}
      </div>
    </Section>
  );
}

/* ──────────────────────────────────────────────────────────────────────── */
/*  Password                                                                */
/* ──────────────────────────────────────────────────────────────────────── */

function PasswordSection() {
  const { data: user } = useCurrentUser();
  const [open, setOpen] = useState(false);

  if (!user) return null;

  const hasPassword = user.has_password ?? true;

  return (
    <Section
      title="Mot de passe"
      description="Le mot de passe est haché avec Argon2id. Jamais lisible, même par l'administrateur."
    >
      {hasPassword ? (
        <>
          <Button variant="outline" onClick={() => setOpen(true)} className="gap-2">
            <KeyRound className="h-4 w-4" />
            Changer mon mot de passe
          </Button>
          <ChangePasswordDialog open={open} onOpenChange={setOpen} />
        </>
      ) : (
        <div className="rounded-md border bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
          Tu te connectes uniquement via un fournisseur OAuth (Google). Aucun mot de passe défini
          sur ce compte.
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
      setError(e instanceof Error ? e.message : "Erreur inconnue");
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
      setError("Le nouveau mot de passe doit faire au moins 8 caractères.");
      return;
    }
    if (next !== confirm) {
      setError("Les mots de passe ne correspondent pas.");
      return;
    }
    if (next === current) {
      setError("Le nouveau mot de passe doit différer de l'ancien.");
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
          <DialogTitle>Changer mon mot de passe</DialogTitle>
          <DialogDescription>
            Renseigne ton mot de passe actuel pour confirmer ton identité, puis choisis-en un
            nouveau (8 caractères minimum).
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-2">
          <div className="space-y-1.5">
            <Label htmlFor="current_pwd" className="text-xs">
              Mot de passe actuel
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
              Nouveau mot de passe
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
              Confirme le nouveau mot de passe
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
              Mot de passe mis à jour.
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={mutation.isPending}
          >
            Annuler
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!current || !next || !confirm || mutation.isPending || success}
          >
            {mutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            {success ? "Sauvegardé" : "Enregistrer"}
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
  const accounts = useQuery({
    queryKey: ["user", "oauth-accounts"],
    queryFn: listOAuthAccounts,
  });

  const hasPassword = user?.has_password ?? true;

  return (
    <Section
      title="Comptes liés"
      description="Comptes externes que tu peux utiliser pour te connecter à Tangent."
    >
      {accounts.isLoading && <p className="text-sm text-muted-foreground">Chargement…</p>}
      {accounts.isError && (
        <p className="text-sm text-[hsl(var(--loss))]">Impossible de charger les comptes liés.</p>
      )}
      {accounts.data && accounts.data.length === 0 && (
        <div className="rounded-md border border-dashed py-6 text-center text-sm text-muted-foreground">
          Aucun compte externe lié pour l&apos;instant.
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
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => deleteOAuthAccount(accountId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["user", "oauth-accounts"] });
      setConfirming(false);
    },
    onError: (e) => {
      setError(e instanceof Error ? e.message : "Erreur inconnue");
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
              ? "Définis d'abord un mot de passe — sinon tu perdrais l'accès à ton compte"
              : `Délier ${label}`
          }
        >
          <Unlink className="h-3.5 w-3.5" />
          Délier
        </Button>
      </div>

      <Dialog open={confirming} onOpenChange={setConfirming}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Délier {label} ?</DialogTitle>
            <DialogDescription>
              Tu ne pourras plus utiliser {label} pour te connecter. Ton compte Tangent reste actif
              via ton email et ton mot de passe.
            </DialogDescription>
          </DialogHeader>
          {error && <p className="text-sm text-[hsl(var(--loss))]">{error}</p>}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setConfirming(false)}
              disabled={mutation.isPending}
            >
              Annuler
            </Button>
            <Button
              variant="destructive"
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
            >
              {mutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Délier
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

function DangerZone() {
  const [open, setOpen] = useState(false);

  return (
    <Section title="Zone dangereuse" description="Actions irréversibles.">
      <div className="rounded-md border border-[hsl(var(--loss))]/40 bg-[hsl(var(--loss))]/5 p-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-[hsl(var(--loss))] shrink-0 mt-0.5" />
          <div className="flex-1 space-y-3">
            <div>
              <p className="text-sm font-medium">Supprimer mon compte</p>
              <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                Efface définitivement ton compte Tangent et toutes les données associées
                (portfolios, comptes bancaires, transactions, jetons OAuth). Cette action est
                irréversible et conforme au droit à l&apos;effacement (RGPD).
              </p>
            </div>
            <Button variant="destructive" size="sm" onClick={() => setOpen(true)} className="gap-2">
              <Trash2 className="h-4 w-4" />
              Supprimer mon compte
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
        setError(e instanceof Error ? e.message : "Erreur inconnue");
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
            Supprimer définitivement mon compte
          </DialogTitle>
          <DialogDescription>
            Cette action est <strong>irréversible</strong>. Tous tes portfolios, comptes bancaires,
            transactions et jetons OAuth seront effacés. Aucune sauvegarde n&apos;est conservée.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-2">
          {hasPassword && (
            <div className="space-y-1.5">
              <Label htmlFor="delete_pwd" className="text-xs">
                Mot de passe actuel
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
              Tape <code className="font-mono font-semibold">DELETE</code> pour confirmer
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
            Annuler
          </Button>
          <Button variant="destructive" onClick={() => mutation.mutate()} disabled={!canSubmit}>
            {mutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Supprimer définitivement
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* ──────────────────────────────────────────────────────────────────────── */
/*  Auto-review opt-in (nightly LLM batch — ADR-018)                        */
/* ──────────────────────────────────────────────────────────────────────── */

function AutoReviewSection() {
  const [profile, setProfile] = useProfile();
  if (!profile) return null;

  const enabled = profile.auto_review_enabled ?? false;
  const toggle = () => {
    setProfile({ ...profile, auto_review_enabled: !enabled });
  };

  return (
    <Section
      title="Briefing du matin"
      description={`Chaque matin (${BRIEFING_TIME}), un court texte sur ce qui a bougé dans ton patrimoine, ce que ça veut dire et s'il y a quelque chose à faire. Écrit par une IA à partir de tes comptes ; activable et désactivable à tout moment.`}
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
          <p className="text-sm font-medium">Recevoir le briefing du matin</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {enabled
              ? "Activé — ton briefing t'attend chaque matin sur l'Aperçu."
              : "Désactivé — active pour recevoir ton premier briefing demain matin."}
          </p>
        </label>
      </div>
    </Section>
  );
}

/* ──────────────────────────────────────────────────────────────────────── */
/*  Atoms                                                                   */
/* ──────────────────────────────────────────────────────────────────────── */
