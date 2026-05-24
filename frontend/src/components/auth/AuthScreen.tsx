import { useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LoginForm } from "@/components/auth/LoginForm";
import { RegisterForm } from "@/components/auth/RegisterForm";
import { ForgotPasswordFlow } from "@/components/auth/ForgotPasswordFlow";

type Mode = "login" | "register" | "forgot";

export function AuthScreen() {
  const [mode, setMode] = useState<Mode>("login");

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-md space-y-6">
        {/* Branding */}
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-semibold tracking-tight">Risky businesses</h1>
          <p className="text-sm text-muted-foreground">
            Ton portefeuille, optimisé.
          </p>
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
            {mode === "login" && (
              <LoginForm
                onSwitchToRegister={() => setMode("register")}
                onForgotPassword={() => setMode("forgot")}
              />
            )}
            {mode === "register" && (
              <RegisterForm onSwitchToLogin={() => setMode("login")} />
            )}
            {mode === "forgot" && (
              <ForgotPasswordFlow onBack={() => setMode("login")} />
            )}
          </CardContent>
        </Card>

        <p className="text-center text-xs text-muted-foreground">
          Tes données restent privées — chaque compte voit uniquement son portefeuille.
        </p>
      </div>
    </div>
  );
}
