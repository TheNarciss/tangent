import { useState } from "react";

import { useRequestReset, useVerifyResetCode, useConfirmReset } from "@/api";
import { useT } from "@/i18n";
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
  const { t } = useT();

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
      setError(t("reset.codeSixDigits"));
      return;
    }
    try {
      const res = await verifyCode.mutateAsync({ email: email.trim().toLowerCase(), code });
      setResetToken(res.reset_token);
      setStep("password");
    } catch {
      setError(t("reset.codeInvalid"));
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (newPassword.length < 8) {
      setError(t("reset.passwordTooShort"));
      return;
    }
    if (newPassword !== confirmPassword) {
      setError(t("reset.passwordsDiffer"));
      return;
    }
    try {
      await confirmReset.mutateAsync({ reset_token: resetToken, new_password: newPassword });
      setStep("success");
    } catch {
      setError(t("reset.failed"));
    }
  };

  return (
    <div className="space-y-6">
      <div className="space-y-1.5">
        <h2 className="text-xl font-semibold tracking-tight">{t("reset.title")}</h2>
        <p className="text-sm text-muted-foreground">
          {step === "email" && t("reset.stepEmail")}
          {step === "code" && t("reset.stepCode", { email })}
          {step === "password" && t("reset.stepPassword")}
          {step === "success" && t("reset.stepSuccess")}
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
            <Label htmlFor="reset-email">{t("reset.emailLabel")}</Label>
            <Input
              id="reset-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              autoFocus
              required
              placeholder={t("reset.emailPlaceholder")}
            />
          </div>
          <Button type="submit" className="w-full" disabled={requestReset.isPending}>
            {requestReset.isPending ? t("reset.sending") : t("reset.sendCode")}
          </Button>
        </form>
      )}

      {step === "code" && (
        <form onSubmit={handleVerifyCode} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="reset-code">{t("reset.codeLabel")}</Label>
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
              {verifyCode.isPending ? t("reset.verifying") : t("reset.verifyCode")}
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
              {t("reset.changeEmail")}
            </Button>
          </div>
        </form>
      )}

      {step === "password" && (
        <form onSubmit={handleResetPassword} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="new-password">{t("reset.newPassword")}</Label>
            <Input
              id="new-password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
              autoFocus
              required
              minLength={8}
              placeholder={t("reset.newPasswordPlaceholder")}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="confirm-password">{t("reset.confirm")}</Label>
            <Input
              id="confirm-password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
              required
              minLength={8}
            />
          </div>
          <Button type="submit" className="w-full" disabled={confirmReset.isPending}>
            {confirmReset.isPending ? t("reset.resetting") : t("reset.resetPassword")}
          </Button>
        </form>
      )}

      {step === "success" && (
        <div className="space-y-4">
          <Alert>
            <AlertDescription>{t("reset.done")}</AlertDescription>
          </Alert>
          <Button onClick={onBack} className="w-full">
            {t("reset.backToLogin")}
          </Button>
        </div>
      )}

      {step !== "success" && (
        <button
          type="button"
          onClick={onBack}
          className="text-xs text-muted-foreground hover:text-foreground transition w-full text-center"
        >
          {t("reset.backToLoginArrow")}
        </button>
      )}
    </div>
  );
}
