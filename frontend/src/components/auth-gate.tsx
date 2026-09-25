"use client";

import * as React from "react";
import { KeyRound, LockKeyhole, LogOut } from "lucide-react";

import { AppSidebar } from "@/components/app-sidebar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getSupabaseClient } from "@/lib/supabase";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = React.useState(() => !getSupabaseClient());
  const [authenticated, setAuthenticated] = React.useState(false);
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);
  const [showPasswordSetup, setShowPasswordSetup] = React.useState(false);
  const [newPassword, setNewPassword] = React.useState("");
  const [passwordConfirmation, setPasswordConfirmation] = React.useState("");
  const [passwordError, setPasswordError] = React.useState<string | null>(null);
  const [savingPassword, setSavingPassword] = React.useState(false);
  const supabase = getSupabaseClient();

  React.useEffect(() => {
    if (!supabase) return;
    void supabase.auth.getSession().then(({ data }) => {
      setAuthenticated(Boolean(data.session));
      setReady(true);
    });
    const { data } = supabase.auth.onAuthStateChange((_event, session) => {
      setAuthenticated(Boolean(session));
      setReady(true);
    });
    return () => data.subscription.unsubscribe();
  }, [supabase]);

  async function signIn(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!supabase) return;
    setSubmitting(true);
    setError(null);
    const { error: authError } = await supabase.auth.signInWithPassword({ email, password });
    if (authError) setError(authError.message);
    setSubmitting(false);
  }

  async function setAccountPassword(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!supabase) return;
    if (newPassword.length < 8) {
      setPasswordError("Use at least 8 characters.");
      return;
    }
    if (newPassword !== passwordConfirmation) {
      setPasswordError("Passwords do not match.");
      return;
    }

    setSavingPassword(true);
    setPasswordError(null);
    const { error: updateError } = await supabase.auth.updateUser({ password: newPassword });
    if (updateError) {
      setPasswordError(updateError.message);
      setSavingPassword(false);
      return;
    }

    setNewPassword("");
    setPasswordConfirmation("");
    setShowPasswordSetup(false);
    setSavingPassword(false);
  }

  if (!ready) {
    return <div className="flex min-h-screen items-center justify-center bg-slate-50 text-sm text-slate-500">Ouverture de votre espace de travail…</div>;
  }

  if (!supabase) {
    return <div className="flex min-h-screen items-center justify-center bg-slate-50 px-5 text-center text-sm text-amber-700">La connexion sécurisée doit être configurée avant l’accès à cet espace.</div>;
  }

  if (!authenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-5 text-slate-900">
        <form onSubmit={signIn} className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-7 shadow-[0_16px_50px_rgba(15,23,42,0.08)]">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white"><LockKeyhole className="h-5 w-5" /></div>
          <h1 className="mt-5 text-xl font-semibold">Bienvenue sur Ironclad</h1>
          <p className="mt-2 text-sm leading-6 text-slate-500">Accédez à votre espace de gestion documentaire sécurisé.</p>
          <label className="mt-7 block text-xs font-medium text-slate-700">Adresse e-mail</label>
          <Input value={email} onChange={(event) => setEmail(event.target.value)} type="email" autoComplete="email" required className="mt-2 h-11 border-slate-300 bg-white" />
          <label className="mt-4 block text-xs font-medium text-slate-700">Mot de passe</label>
          <Input value={password} onChange={(event) => setPassword(event.target.value)} type="password" autoComplete="current-password" required className="mt-2 h-11 border-slate-300 bg-white" />
          {error && <p className="mt-3 text-xs text-red-700">{error}</p>}
          <Button type="submit" disabled={submitting} className="mt-6 h-11 w-full bg-blue-600 text-white hover:bg-blue-700">Se connecter</Button>
        </form>
      </div>
    );
  }

  return (
    <>
      <AppSidebar />
      <main className="flex min-h-screen flex-1 flex-col overflow-hidden">
        <div className="flex h-14 items-center justify-end border-b border-slate-200 bg-white px-5">
          <Button variant="ghost" size="sm" title="Modifier le mot de passe" onClick={() => setShowPasswordSetup((open) => !open)} className="text-slate-500 hover:bg-slate-50"><KeyRound className="h-3.5 w-3.5" />Mot de passe</Button>
          <Button variant="ghost" size="sm" title="Se déconnecter" onClick={() => void supabase.auth.signOut()} className="text-slate-500 hover:bg-slate-50"><LogOut className="h-3.5 w-3.5" />Déconnexion</Button>
        </div>
        {showPasswordSetup && (
          <section className="border-b border-slate-200 bg-white px-4 py-4">
            <form onSubmit={setAccountPassword} className="mx-auto grid max-w-2xl gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
              <label className="block text-xs text-slate-600">Nouveau mot de passe
                <Input value={newPassword} onChange={(event) => setNewPassword(event.target.value)} type="password" autoComplete="new-password" required className="mt-2 border-slate-300 bg-white" />
              </label>
              <label className="block text-xs text-slate-600">Confirmer le mot de passe
                <Input value={passwordConfirmation} onChange={(event) => setPasswordConfirmation(event.target.value)} type="password" autoComplete="new-password" required className="mt-2 border-slate-300 bg-white" />
              </label>
              <Button type="submit" disabled={savingPassword} className="bg-blue-600 text-white hover:bg-blue-700">Enregistrer</Button>
              {passwordError && <p className="text-xs text-red-700 sm:col-span-3">{passwordError}</p>}
            </form>
          </section>
        )}
        {children}
      </main>
    </>
  );
}
