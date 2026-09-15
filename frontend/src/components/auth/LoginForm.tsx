import { useState, FormEvent } from "react";

import { ApiError, useLogin } from "@/api";
import { useT } from "@/i18n";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface LoginFormProps {
  onSwitchToRegister: () => void;
  onForgotPassword?: () => void;
}

export function LoginForm({ onSwitchToRegister, onForgotPassword }: LoginFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const login = useLogin();
  const { t } = useT();

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    login.mutate({ email, password });
  };

  const errorMessage = login.error
    ? login.error instanceof ApiError
      ? login.error.status === 400 || login.error.status === 401
        ? t("auth.badCredentials")
        : login.error.status === 429
          ? t("auth.tooManyAttempts")
          : login.error.message
      : t("common.unknownError")
    : null;

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="space-y-2">
        <Label htmlFor="login-email">{t("auth.email")}</Label>
        <Input
          id="login-email"
          type="email"
          placeholder={t("auth.emailPlaceholder")}
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={login.isPending}
        />
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="login-password">{t("auth.password")}</Label>
          {onForgotPassword && (
            <button
              type="button"
              onClick={onForgotPassword}
              className="text-xs text-muted-foreground hover:text-foreground underline-offset-2 hover:underline transition"
            >
              {t("auth.forgotPassword")}
            </button>
          )}
        </div>
        <Input
          id="login-password"
          type="password"
          autoComplete="current-password"
          required
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={login.isPending}
        />
      </div>

      {errorMessage && (
        <div className="rounded-md border border-[hsl(var(--loss))] bg-card/40 p-3 text-sm text-[hsl(var(--loss))]">
          {errorMessage}
        </div>
      )}

      <Button type="submit" className="w-full" disabled={login.isPending}>
        {login.isPending ? t("auth.signingIn") : t("auth.signIn")}
      </Button>

      <div className="text-center text-sm text-muted-foreground">
        {t("auth.noAccountYet")}{" "}
        <button
          type="button"
          onClick={onSwitchToRegister}
          className="text-foreground underline hover:no-underline"
        >
          {t("auth.signUp")}
        </button>
      </div>
    </form>
  );
}
