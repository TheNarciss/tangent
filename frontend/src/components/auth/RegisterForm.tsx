import { useState, FormEvent } from "react";

import { ApiError, useLogin, useRegister } from "@/api";
import { useT } from "@/i18n";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface RegisterFormProps {
  onSwitchToLogin: () => void;
}

export function RegisterForm({ onSwitchToLogin }: RegisterFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const register = useRegister();
  const login = useLogin();
  const { t } = useT();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await register.mutateAsync({
        email,
        password,
        display_name: displayName.trim() || undefined,
      });
      // Auto-login right after register so the user doesn't have to do it twice
      login.mutate({ email, password });
    } catch {
      // Error surfaced via register.error below
    }
  };

  const errorMessage = register.error
    ? register.error instanceof ApiError
      ? register.error.status === 400 && register.error.message.includes("USER_ALREADY_EXISTS")
        ? t("auth.alreadyExists")
        : register.error.status === 422
          ? t("auth.invalidRegister")
          : register.error.status === 429
            ? t("auth.tooManyRegisters")
            : register.error.message
      : t("common.unknownError")
    : login.error
      ? t("auth.createdButNoLogin")
      : null;

  const isPending = register.isPending || login.isPending;

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="space-y-2">
        <Label htmlFor="register-name">{t("auth.nameOptional")}</Label>
        <Input
          id="register-name"
          type="text"
          placeholder={t("auth.namePlaceholder")}
          autoComplete="given-name"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          disabled={isPending}
          maxLength={50}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="register-email">{t("auth.email")}</Label>
        <Input
          id="register-email"
          type="email"
          placeholder={t("auth.emailPlaceholder")}
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={isPending}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="register-password">{t("auth.password")}</Label>
        <Input
          id="register-password"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={isPending}
        />
        <p className="text-xs text-muted-foreground">{t("auth.minChars")}</p>
      </div>

      {errorMessage && (
        <div className="rounded-md border border-[hsl(var(--loss))] bg-card/40 p-3 text-sm text-[hsl(var(--loss))]">
          {errorMessage}
        </div>
      )}

      <Button type="submit" className="w-full" disabled={isPending}>
        {register.isPending
          ? t("auth.creating")
          : login.isPending
            ? t("auth.signingIn")
            : t("auth.createAccount")}
      </Button>

      <div className="text-center text-sm text-muted-foreground">
        {t("auth.alreadyAccount")}{" "}
        <button
          type="button"
          onClick={onSwitchToLogin}
          className="text-foreground underline hover:no-underline"
        >
          {t("auth.logIn")}
        </button>
      </div>
    </form>
  );
}
