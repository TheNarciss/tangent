import { useState } from "react";

import { useRequestReset, useVerifyResetCode, useConfirmReset } from "@/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface Props {
  onBack: () => void;
}

type Step = "email" | "code" | "password" | "success";

export function ForgotPasswordFlow({ onBack }: Props) {
  const [step, setStep] = useState<Step>("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const requestReset = useRequestReset();
  const verifyCode = useVerifyResetCode();
  const confirmReset = useConfirmReset();

  const handleRequestEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!email.trim()) return;
    try {
      await requestReset.mutateAsync(email.trim().toLowerCase());
      setStep("code");
    } catch {
      // Always advance — anti-enumeration: don't reveal if email exists
      setStep("code");
    }
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (code.length !== 6) {
      setError("Le code doit faire 6 chiffres.");
      return;
    }
    try {
      const res = await verifyCode.mutateAsync({ email: email.trim().toLowerCase(), code });
      setResetToken(res.reset_token);
      setStep("password");
    } catch {
      setError("Code invalide ou expiré. Vérifie ta boîte mail.");
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (newPassword.length < 12) {
      setError("Le mot de passe doit faire au moins 12 caractères.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Les mots de passe ne correspondent pas.");
      return;
    }
    try {
      await confirmReset.mutateAsync({ reset_token: resetToken, new_password: newPassword });
      setStep("success");
    } catch {
      setError("Impossible de réinitialiser. Recommence depuis le début.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="space-y-1.5">
        <h2 className="text-xl font-semibold tracking-tight">Mot de passe oublié</h2>
        <p className="text-sm text-muted-foreground">
          {step === "email" && "Entre ton adresse e-mail, on t'envoie un code."}
          {step === "code" && `Code envoyé à ${email}. Vérifie ta boîte mail.`}
          {step === "password" && "Choisis ton nouveau mot de passe (12 caractères min)."}
          {step === "success" && "C'est fait. Tu peux te reconnecter."}
        </p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {step === "email" && (
        <form onSubmit={handleRequestEmail} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="reset-email">E-mail</Label>
            <Input
              id="reset-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              autoFocus
              required
              placeholder="toi@exemple.com"
            />
          </div>
          <Button type="submit" className="w-full" disabled={requestReset.isPending}>
            {requestReset.isPending ? "Envoi…" : "Envoyer le code"}
          </Button>
        </form>
      )}

      {step === "code" && (
        <form onSubmit={handleVerifyCode} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="reset-code">Code (6 chiffres)</Label>
            <Input
              id="reset-code"
              type="text"
              inputMode="numeric"
              pattern="\d{6}"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
              autoFocus
              required
              className="text-center text-2xl tracking-[0.5em] font-mono"
              placeholder="000000"
            />
          </div>
          <div className="flex flex-col gap-2">
            <Button
              type="submit"
              className="w-full"
              disabled={verifyCode.isPending || code.length !== 6}
            >
              {verifyCode.isPending ? "Vérification…" : "Vérifier le code"}
            </Button>
            <Button
              type="button"
              variant="ghost"
              className="w-full text-xs"
              onClick={() => {
                setCode("");
                setStep("email");
                setError(null);
              }}
            >
              Changer d'e-mail
            </Button>
          </div>
        </form>
      )}

      {step === "password" && (
        <form onSubmit={handleResetPassword} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="new-password">Nouveau mot de passe</Label>
            <Input
              id="new-password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
              autoFocus
              required
              minLength={12}
              placeholder="12 caractères minimum"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="confirm-password">Confirmer</Label>
            <Input
              id="confirm-password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
              required
              minLength={12}
            />
          </div>
          <Button type="submit" className="w-full" disabled={confirmReset.isPending}>
            {confirmReset.isPending ? "Réinitialisation…" : "Réinitialiser le mot de passe"}
          </Button>
        </form>
      )}

      {step === "success" && (
        <div className="space-y-4">
          <Alert>
            <AlertDescription>
              ✓ Ton mot de passe a été mis à jour. Tu peux te reconnecter dès maintenant.
            </AlertDescription>
          </Alert>
          <Button onClick={onBack} className="w-full">
            Retour à la connexion
          </Button>
        </div>
      )}

      {step !== "success" && (
        <button
          type="button"
          onClick={onBack}
          className="text-xs text-muted-foreground hover:text-foreground transition w-full text-center"
        >
          ← Retour à la connexion
        </button>
      )}
    </div>
  );
}
