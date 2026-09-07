import { useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LoginForm } from "@/components/auth/LoginForm";
import { RegisterForm } from "@/components/auth/RegisterForm";
import { ForgotPasswordFlow } from "@/components/auth/ForgotPasswordFlow";
import { GoogleButton } from "@/components/auth/GoogleButton";
import { OAuthCallbackHandler } from "@/components/OAuthCallback";

type Mode = "login" | "register" | "forgot";

export function AuthScreen() {
  const [mode, setMode] = useState<Mode>("login");

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      {/* Handles ?oauth=success / ?oauth_error=NNN in URL (cf ADR-014) */}
      <OAuthCallbackHandler />
      <div className="w-full max-w-md space-y-6">
        {/* Branding */}
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-semibold tracking-tight">Tangent</h1>
          <p className="text-sm text-muted-foreground">Ton patrimoine, clairement.</p>
        </div>

        {/* Card with the form */}
        <Card>
          {mode !== "forgot" && (
            <CardHeader>
              <CardTitle className="text-xl">
                {mode === "login" ? "Connexion" : "Inscription"}
              </CardTitle>
            </CardHeader>
          )}
          <CardContent className={mode === "forgot" ? "pt-6" : undefined}>
            {mode !== "forgot" && (
              <div className="space-y-4 mb-6">
                <GoogleButton mode="login" />
                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t border-border" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-card px-2 text-muted-foreground">ou par email</span>
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

        <p className="text-center text-xs text-muted-foreground">
          Tes données restent privées — chaque compte voit uniquement son portefeuille.
        </p>
        <p className="text-center text-xs text-muted-foreground">
          En vous inscrivant, vous acceptez nos{" "}
          <a
            href="/legal/terms.html"
            className="underline underline-offset-2 hover:text-foreground"
          >
            Conditions
          </a>{" "}
          et notre{" "}
          <a
            href="/legal/privacy.html"
            className="underline underline-offset-2 hover:text-foreground"
          >
            Politique de confidentialité
          </a>
          .
        </p>
      </div>
    </div>
  );
}
