import { useState, FormEvent } from "react";

import { ApiError, useLogin, useRegister } from "@/api";
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
        ? "Un compte existe déjà avec cet email."
        : register.error.status === 422
        ? "Email invalide ou mot de passe trop court (min 8 caractères)."
        : register.error.status === 429
        ? "Trop d'inscriptions. Réessaie dans une heure."
        : register.error.message
      : "Erreur inconnue."
    : login.error
    ? "Compte créé mais connexion impossible. Essaie de te connecter manuellement."
    : null;

  const isPending = register.isPending || login.isPending;

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="space-y-2">
        <Label htmlFor="register-name">Nom (optionnel)</Label>
        <Input
          id="register-name"
          type="text"
          placeholder="Clément"
          autoComplete="given-name"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          disabled={isPending}
          maxLength={50}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="register-email">Email</Label>
        <Input
          id="register-email"
          type="email"
          placeholder="toi@example.com"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={isPending}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="register-password">Mot de passe</Label>
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
        <p className="text-xs text-muted-foreground">8 caractères minimum.</p>
      </div>

      {errorMessage && (
        <div className="rounded-md border border-[hsl(var(--loss))] bg-card/40 p-3 text-sm text-[hsl(var(--loss))]">
          {errorMessage}
        </div>
      )}

      <Button type="submit" className="w-full" disabled={isPending}>
        {register.isPending ? "Création…" : login.isPending ? "Connexion…" : "Créer mon compte"}
      </Button>

      <div className="text-center text-sm text-muted-foreground">
        Déjà un compte ?{" "}
        <button
          type="button"
          onClick={onSwitchToLogin}
          className="text-foreground underline hover:no-underline"
        >
          Connecte-toi
        </button>
      </div>
    </form>
  );
}