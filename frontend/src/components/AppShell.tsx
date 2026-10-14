import { Bot, LayoutDashboard, LogOut, Plus, Sparkles, Users } from "lucide-react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function AppShell() {
  const { user, logout } = useAuth();
  return (
    <div className="app-shell min-h-screen bg-forge-950 text-slate-100">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 border-r border-white/[0.06] bg-[#0e1016] px-5 py-6 lg:flex lg:flex-col">
        <Link to="/" className="mb-12 flex items-center gap-3 px-2">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-forge-500 text-white shadow-glow">
            <Bot size={22} />
          </span>
          <span className="font-display text-lg font-semibold tracking-tight">TaskForge<span className="text-forge-400">.</span></span>
        </Link>
        <div className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.22em] text-slate-600">Workspace</div>
        <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? "nav-link-active" : ""}`}>
          <LayoutDashboard size={17} /> Overview
        </NavLink>
        <NavLink to="/teams" className={({ isActive }) => `nav-link ${isActive ? "nav-link-active" : ""}`}>
          <Users size={17} /> Teams & tasks
        </NavLink>
        <div className="mt-auto rounded-2xl border border-forge-400/10 bg-gradient-to-br from-forge-500/10 to-transparent p-4">
          <Sparkles size={18} className="mb-3 text-forge-300" />
          <p className="text-sm font-medium text-slate-200">Ideas into outcomes.</p>
          <p className="mt-1 text-xs leading-5 text-slate-500">Build clear goals and keep every step in view.</p>
          <Link to="/?new=1" className="mt-4 inline-flex items-center gap-1.5 text-xs font-semibold text-forge-300 hover:text-white">
            <Plus size={14} /> Create a goal
          </Link>
        </div>
        <div className="mt-5 flex items-center gap-3 border-t border-white/[0.06] px-1 pt-5">
          <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-forge-800 text-sm font-semibold text-forge-300">
            {user?.email.slice(0, 1).toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium text-slate-300">{user?.email}</p>
            <p className="text-[11px] text-slate-600">Personal workspace</p>
          </div>
          <button onClick={logout} title="Sign out" className="rounded-lg p-2 text-slate-500 transition hover:bg-white/5 hover:text-slate-200">
            <LogOut size={16} />
          </button>
        </div>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-10 flex h-[68px] items-center justify-between border-b border-white/[0.06] bg-forge-950/90 px-5 backdrop-blur-xl sm:px-8">
          <Link to="/" className="flex items-center gap-2.5 lg:hidden">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-forge-500 text-white"><Bot size={18} /></span>
            <span className="font-display font-semibold">TaskForge<span className="text-forge-400">.</span></span>
          </Link>
          <p className="hidden text-xs text-slate-500 lg:block">AI workspace <span className="mx-2 text-slate-700">/</span> Goals</p>
          <div className="flex items-center gap-3">
            <span className="hidden text-xs text-slate-500 sm:block">{user?.email}</span>
            <button onClick={logout} className="rounded-lg border border-white/[0.08] p-2 text-slate-400 hover:bg-white/5 hover:text-white lg:hidden" aria-label="Sign out">
              <LogOut size={16} />
            </button>
          </div>
        </header>
        <nav className="flex gap-2 border-b border-white/[0.06] px-5 py-2 lg:hidden sm:px-8">
          <NavLink to="/" end className={({ isActive }) => `flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium ${isActive ? "bg-forge-500/10 text-forge-300" : "text-slate-500 hover:text-slate-200"}`}>
            <LayoutDashboard size={15} /> Overview
          </NavLink>
          <NavLink to="/teams" className={({ isActive }) => `flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium ${isActive ? "bg-forge-500/10 text-forge-300" : "text-slate-500 hover:text-slate-200"}`}>
            <Users size={15} /> Teams & tasks
          </NavLink>
        </nav>
        <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8 sm:py-10"><Outlet /></main>
      </div>
    </div>
  );
}
