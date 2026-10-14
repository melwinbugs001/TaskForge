import { useState, type FormEvent } from "react";
import { ArrowRight, Bot, Check, LockKeyhole, Mail, Sparkles } from "lucide-react";
import { Link, Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { getApiError } from "../api/client";

export function AuthPage({ mode }: { mode: "login" | "register" }) {
  const isRegister = mode === "register";
  const { user, login, register } = useAuth();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const destination = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? "/";

  if (user) return <Navigate to="/" replace />;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (isRegister) await register(email, password);
      else await login(email, password);
    } catch (reason) {
      setError(getApiError(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-screen relative flex min-h-screen overflow-hidden bg-[#101322]">
      <div className="pointer-events-none absolute -left-40 top-10 h-[500px] w-[500px] rounded-full bg-forge-500/10 blur-[120px]" />
      <div className="pointer-events-none absolute -bottom-64 right-0 h-[600px] w-[600px] rounded-full bg-indigo-500/[0.08] blur-[140px]" />
      <div className="relative mx-auto grid min-h-screen w-full max-w-7xl lg:grid-cols-2">
        <section className="hidden flex-col justify-between p-12 lg:flex xl:p-20">
          <Link to="/" className="flex items-center gap-3">
            <span className="grid h-11 w-11 place-items-center rounded-xl bg-forge-500 text-white shadow-glow"><Bot size={24} /></span>
            <span className="font-display text-xl font-semibold text-white">TaskForge<span className="text-forge-400">.</span></span>
          </Link>
          <div className="max-w-lg">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-forge-400/20 bg-forge-500/10 px-3 py-1.5 text-xs font-medium text-forge-300"><Sparkles size={14} /> Your AI workflow workspace</div>
            <h1 className="font-display text-5xl font-semibold leading-[1.12] tracking-tight text-white xl:text-6xl">Turn big ideas into <span className="text-gradient">clear next steps.</span></h1>
            <p className="mt-6 max-w-md text-base leading-7 text-slate-400">Plan, organize, and keep track of AI-assisted work — with every goal and its progress in one place.</p>
            <div className="mt-10 space-y-4">
              {["Keep goals organized in one workspace", "Build plans before you decide to run them", "Know what’s happening at every step"].map((item) => <div key={item} className="flex items-center gap-3 text-sm text-slate-300"><span className="grid h-6 w-6 place-items-center rounded-full bg-emerald-400/10 text-emerald-300"><Check size={14} /></span>{item}</div>)}
            </div>
          </div>
          <p className="text-xs text-slate-600">A more thoughtful way to work with AI.</p>
        </section>
        <section className="flex items-center justify-center px-5 py-10 sm:px-8">
          <div className="w-full max-w-[420px]">
            <Link to="/" className="mb-12 flex items-center justify-center gap-2.5 lg:hidden"><span className="grid h-9 w-9 place-items-center rounded-xl bg-forge-500 text-white"><Bot size={20} /></span><span className="font-display text-lg font-semibold text-white">TaskForge<span className="text-forge-400">.</span></span></Link>
            <div className="mb-8">
              <p className="mb-3 text-xs font-bold uppercase tracking-[0.2em] text-forge-300">{isRegister ? "Get started" : "Welcome back"}</p>
              <h2 className="font-display text-3xl font-semibold tracking-tight text-white">{isRegister ? "Create your account" : "Sign in to TaskForge"}</h2>
              <p className="mt-2 text-sm text-slate-500">{isRegister ? "Set up your personal AI workspace." : "Pick up where you left off."}</p>
            </div>
            {error && <div role="alert" className="mb-5 rounded-xl border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">{error}</div>}
            <form onSubmit={handleSubmit} className="space-y-5">
              <label className="block text-sm font-medium text-slate-300">Email address
                <span className="relative mt-2 block"><Mail size={17} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-600" /><input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" className="form-input pl-11" /></span>
              </label>
              <label className="block text-sm font-medium text-slate-300">Password
                <span className="relative mt-2 block"><LockKeyhole size={17} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-600" /><input type="password" autoComplete={isRegister ? "new-password" : "current-password"} required minLength={isRegister ? 8 : 1} maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} placeholder={isRegister ? "At least 8 characters" : "Your password"} className="form-input pl-11" /></span>
              </label>
              <button disabled={busy} className="btn-primary flex w-full items-center justify-center gap-2 py-3.5 disabled:opacity-60">{busy ? "Please wait…" : isRegister ? "Create account" : "Sign in"}{!busy && <ArrowRight size={16} />}</button>
            </form>
            <p className="mt-7 text-center text-sm text-slate-500">{isRegister ? "Already have an account?" : "New to TaskForge?"}{" "}<Link to={isRegister ? "/login" : "/register"} state={{ from: destination }} className="font-medium text-forge-300 hover:text-white">{isRegister ? "Sign in" : "Create an account"}</Link></p>
            <p className="mt-10 text-center text-[11px] leading-5 text-slate-600">Your account is stored securely. Passwords are never displayed in your workspace.</p>
          </div>
        </section>
      </div>
    </div>
  );
}
