import { useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LoginForm } from "@/components/auth/LoginForm";
import { RegisterForm } from "@/components/auth/RegisterForm";
import { ForgotPasswordFlow } from "@/components/auth/ForgotPasswordFlow";
import { GoogleButton } from "@/components/auth/GoogleButton";
import { AppleButton } from "@/components/auth/AppleButton";
import { useAuthProviders } from "@/api";
import { legalPath, useT } from "@/i18n";
import { OAuthCallbackHandler } from "@/components/OAuthCallback";

type Mode = "login" | "register" | "forgot";

export function AuthScreen() {
  const [mode, setMode] = useState<Mode>("login");
  const { t } = useT();
  const providers = useAuthProviders().data ?? { google: true, apple: false };
  const anyProvider = providers.google || providers.apple;

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      {/* Handles ?oauth=success / ?oauth_error=NNN in URL (cf ADR-014) */}
      <OAuthCallbackHandler />
      <div className="w-full max-w-md space-y-6">
        {/* Branding */}
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-semibold tracking-tight">Tangent</h1>
          <p className="text-sm text-muted-foreground">{t("auth.tagline")}</p>
        </div>

        {/* Card with the form */}
        <Card>
          {mode !== "forgot" && (
            <CardHeader>
              <CardTitle className="text-xl">
                {mode === "login" ? t("auth.login") : t("auth.register")}
              </CardTitle>
            </CardHeader>
          )}
          <CardContent className={mode === "forgot" ? "pt-6" : undefined}>
            {mode !== "forgot" && anyProvider && (
              <div className="space-y-4 mb-6">
                {providers.apple && <AppleButton />}
                {providers.google && <GoogleButton mode="login" />}
                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t border-border" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-card px-2 text-muted-foreground">
                      {t("auth.orByEmail")}
                    </span>
                  </div>
                </div>
              </div>
            )}
            {mode === "login" && (
              <LoginForm
                onSwitchToRegister={() => setMode("register")}
                onForgotPassword={() => setMode("forgot")}
              />
            )}
            {mode === "register" && <RegisterForm onSwitchToLogin={() => setMode("login")} />}
            {mode === "forgot" && <ForgotPasswordFlow onBack={() => setMode("login")} />}
          </CardContent>
        </Card>

        <p className="text-center text-xs text-muted-foreground">{t("auth.privacyNote")}</p>
        <p className="text-center text-xs text-muted-foreground">
          {t("auth.bySigningUp")}{" "}
          <a
            href={legalPath("terms")}
            className="underline underline-offset-2 hover:text-foreground"
          >
            {t("auth.termsLink")}
          </a>{" "}
          {t("auth.andOur")}{" "}
          <a
            href={legalPath("privacy")}
            className="underline underline-offset-2 hover:text-foreground"
          >
            {t("auth.privacyLink")}
          </a>
          .
        </p>
      </div>
    </div>
  );
}
