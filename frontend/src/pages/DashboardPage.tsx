import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Activity, AlertCircle, ArrowDownUp, ArrowUpRight, CheckCircle2, CircleDot, Clock3, Plus, Search, Sparkles, Target, Timer } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { createGoal, listGoals } from "../api/goals";
import { getApiError } from "../api/client";
import { GoalForm } from "../components/GoalForm";
import { StatusBadge } from "../components/StatusBadge";
import { Loading } from "../components/Loading";
import { PushNotificationsControl } from "../components/PushNotificationsControl";
import type { Goal, GoalStatus } from "../types/api";

type Filter = "all" | GoalStatus;
type SortOption = "updated-desc" | "created-desc" | "created-asc" | "title-asc";

const filters: { label: string; value: Filter }[] = [
  { label: "All goals", value: "all" },
  { label: "Draft", value: "draft" },
  { label: "Running", value: "running" },
  { label: "Approval needed", value: "waiting_for_approval" },
  { label: "Completed", value: "completed" },
  { label: "Failed", value: "failed" },
  { label: "Cancelled", value: "cancelled" },
];

export function DashboardPage() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [total, setTotal] = useState(0);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortOption>("updated-desc");
  const [showCreate, setShowCreate] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();

  async function refresh() {
    setError("");
    const response = await listGoals();
    setGoals(response.items);
    setTotal(response.total);
  }

  useEffect(() => {
    refresh().catch((reason: unknown) => setError(getApiError(reason))).finally(() => setBusy(false));
    const refreshTimer = window.setInterval(() => {
      refresh().catch((reason: unknown) => setError(getApiError(reason)));
    }, 60_000);
    return () => window.clearInterval(refreshTimer);
  }, []);

  useEffect(() => {
    if (searchParams.get("new") === "1") {
      setShowCreate(true);
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  const counts = useMemo(() => goals.reduce<Record<GoalStatus, number>>((result, goal) => {
    result[goal.status] += 1;
    return result;
  }, {
    draft: 0,
    running: 0,
    waiting_for_approval: 0,
    completed: 0,
    failed: 0,
    cancelled: 0,
  }), [goals]);

  const visibleGoals = useMemo(() => {
    const query = search.toLowerCase().trim();
    return [...goals.filter((goal) => {
      const matchesFilter = filter === "all" || goal.status === filter;
      return matchesFilter && (!query || `${goal.title} ${goal.description}`.toLowerCase().includes(query));
    })].sort((a, b) => {
      if (sort === "title-asc") return a.title.localeCompare(b.title);
      const dateA = new Date(sort === "updated-desc" ? a.updated_at : a.created_at).getTime();
      const dateB = new Date(sort === "updated-desc" ? b.updated_at : b.created_at).getTime();
      return sort === "created-asc" ? dateA - dateB : dateB - dateA;
    });
  }, [goals, filter, search, sort]);

  async function handleCreate(input: { title: string; description: string }) {
    await createGoal(input);
    setShowCreate(false);
    await refresh();
  }

  if (busy) return <Loading label="Loading your workspace" />;
  if (error) return <div className="animate-enter">
    <div className="mb-8"><p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-forge-300">Your workspace</p><h1 className="font-display text-3xl font-semibold tracking-tight text-white sm:text-4xl">Good work starts here<span className="text-forge-400">.</span></h1><p className="mt-2 text-sm text-slate-500">Organize your goals and keep your next steps in focus.</p></div>
    <div role="alert" className="flex items-center gap-3 rounded-xl border border-rose-400/20 bg-rose-400/10 px-4 py-4 text-sm text-rose-200"><AlertCircle size={17} />{error}<button onClick={() => { setBusy(true); refresh().catch((reason: unknown) => setError(getApiError(reason))).finally(() => setBusy(false)); }} className="ml-auto shrink-0 font-semibold underline">Retry</button></div>
  </div>;

  return (
    <>
      <div className="animate-enter">
        <div className="mb-8 flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
          <div><p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-forge-300">Your workspace</p><h1 className="font-display text-3xl font-semibold tracking-tight text-white sm:text-4xl">Good work starts here<span className="text-forge-400">.</span></h1><p className="mt-2 text-sm text-slate-500">Organize your goals and keep your next steps in focus.</p></div>
          <div className="flex flex-wrap gap-2">
            <PushNotificationsControl />
            <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center justify-center gap-2"><Plus size={17} /> New goal</button>
          </div>
        </div>
        <div className="mb-9 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Total goals" value={total} detail="Across your workspace" icon={<Target size={17} />} tone="violet" />
          <StatCard label="In progress" value={counts.running} detail="Currently active" icon={<Activity size={17} />} tone="blue" />
          <StatCard label="Completed" value={counts.completed} detail="Goals finished" icon={<CheckCircle2 size={17} />} tone="green" />
          <StatCard label="Needs attention" value={counts.failed} detail="Failed goals" icon={<AlertCircle size={17} />} tone="amber" />
        </div>
        <div className="mb-4 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div><h2 className="font-display text-lg font-semibold text-white">Your goals</h2><p className="mt-1 text-xs text-slate-600">Showing {visibleGoals.length} of {total} {total === 1 ? "goal" : "goals"}</p></div>
          <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
            <label className="relative block w-full sm:w-64"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search goals..." className="form-input h-10 pl-9 text-xs" /></label>
            <label className="relative flex h-10 shrink-0 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-xs text-slate-500 shadow-sm">
              <ArrowDownUp size={14} />
              <span className="sr-only">Sort goals</span>
              <select value={sort} onChange={(event) => setSort(event.target.value as SortOption)} className="h-full cursor-pointer appearance-none bg-transparent pr-1 text-xs font-medium text-slate-700 outline-none">
                <option value="updated-desc">Recently updated</option>
                <option value="created-desc">Newest first</option>
                <option value="created-asc">Oldest first</option>
                <option value="title-asc">Title A–Z</option>
              </select>
            </label>
          </div>
        </div>
        <div className="mb-5 flex flex-wrap gap-2">
          {filters.map((item) => <button key={item.value} onClick={() => setFilter(item.value)} aria-pressed={filter === item.value} className={`inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs font-medium transition ${filter === item.value ? "border-forge-500/20 bg-forge-500/10 text-forge-300 shadow-sm" : "border-slate-200 bg-white/70 text-slate-500 hover:border-slate-300 hover:bg-white hover:text-slate-800"}`}>
            {item.label}
            <span className={`min-w-5 rounded-full px-1.5 py-0.5 text-[10px] ${filter === item.value ? "bg-forge-500/10 text-forge-300" : "bg-slate-100 text-slate-500"}`}>{item.value === "all" ? goals.length : counts[item.value]}</span>
          </button>)}
        </div>
        {visibleGoals.length ? <div className="grid gap-3">
          {visibleGoals.map((goal, index) => <GoalRow key={goal.id} goal={goal} index={index} />)}
        </div> : <EmptyState hasGoals={total > 0} onCreate={() => setShowCreate(true)} />}
        <div className="mt-6 flex items-center gap-2 text-[11px] text-slate-600"><CircleDot size={13} className="text-forge-400" />Goals stay drafts until you act. Unfinished goals with deadlines are marked failed when overdue.</div>
      </div>
      {showCreate && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowCreate(false); }}><div role="dialog" aria-modal="true" aria-labelledby="create-goal-title" className="modal-panel w-full max-w-xl rounded-2xl border border-white/10 bg-[#141720] p-6 shadow-2xl sm:p-8"><GoalForm submitLabel="Save as draft" onSubmit={handleCreate} onClose={() => setShowCreate(false)} /></div></div>}
    </>
  );
}

function StatCard({ label, value, detail, icon, tone }: { label: string; value: number; detail: string; icon: ReactNode; tone: "violet" | "blue" | "green" | "amber" }) {
  const styles = { violet: "bg-forge-500/10 text-forge-300", blue: "bg-sky-400/10 text-sky-300", green: "bg-emerald-400/10 text-emerald-300", amber: "bg-amber-400/10 text-amber-300" };
  return <div className="panel-card p-5"><div className="flex items-start justify-between"><div><p className="text-xs font-medium text-slate-500">{label}</p><p className="mt-3 font-display text-3xl font-semibold tracking-tight text-white">{value}</p></div><span className={`grid h-9 w-9 place-items-center rounded-xl ${styles[tone]}`}>{icon}</span></div><p className="mt-3 text-[11px] text-slate-600">{detail}</p></div>;
}

function GoalRow({ goal, index }: { goal: Goal; index: number }) {
  return <Link to={`/goals/${goal.id}`} className="group panel-card animate-enter flex flex-col gap-4 p-4 transition hover:border-forge-400/20 hover:bg-white/[0.035] sm:flex-row sm:items-center sm:gap-5 sm:p-5" style={{ animationDelay: `${index * 45}ms` }}>
    <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-forge-500/[0.08] text-forge-300"><Sparkles size={18} /></span>
    <div className="min-w-0 flex-1"><h3 className="truncate text-sm font-semibold text-slate-200 transition group-hover:text-white">{goal.title}</h3><p className="mt-1 line-clamp-1 text-xs text-slate-500">{goal.description}</p><div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-slate-600"><span className="flex items-center gap-1.5"><Clock3 size={12} /> Updated {formatDate(goal.updated_at)}</span>{goal.due_at && <span className="flex items-center gap-1.5"><Timer size={12} /> Due {formatDateTime(goal.due_at)}</span>}</div></div>
    <div className="flex items-center justify-between gap-4 sm:justify-end"><StatusBadge status={goal.status} /><ArrowUpRight size={16} className="text-slate-600 transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-forge-300" /></div>
  </Link>;
}

function EmptyState({ hasGoals, onCreate }: { hasGoals: boolean; onCreate: () => void }) {
  return <div className="panel-card flex flex-col items-center px-6 py-16 text-center"><span className="mb-5 grid h-14 w-14 place-items-center rounded-2xl border border-forge-400/10 bg-forge-500/[0.07] text-forge-300">{hasGoals ? <Search size={23} /> : <Target size={23} />}</span><h3 className="font-display text-lg font-semibold text-white">{hasGoals ? "No goals match this view" : "Start with a goal"}</h3><p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">{hasGoals ? "Try another filter or search term." : "Capture the outcome you want. You can shape a plan when you're ready."}</p>{!hasGoals && <button onClick={onCreate} className="btn-primary mt-6 flex items-center gap-2"><Plus size={16} /> Create your first goal</button>}</div>;
}

export function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(new Date(value));
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(value));
}
