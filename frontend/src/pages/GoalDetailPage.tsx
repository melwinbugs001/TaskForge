import { useEffect, useState } from "react";
import { ArrowLeft, CalendarDays, CheckCircle2, Pencil, Timer, Trash2 } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { completeGoal, deleteGoal, getGoal, updateGoal } from "../api/goals";
import { getApiError } from "../api/client";
import { GoalForm } from "../components/GoalForm";
import { Loading } from "../components/Loading";
import { StatusBadge } from "../components/StatusBadge";
import { formatDate } from "./DashboardPage";
import type { Goal, GoalInput } from "../types/api";

export function GoalDetailPage() {
  const { goalId } = useParams();
  const navigate = useNavigate();
  const [goal, setGoal] = useState<Goal | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [completing, setCompleting] = useState(false);

  useEffect(() => {
    if (!goalId || !/^\d+$/.test(goalId)) {
      setError("Goal not found.");
      setBusy(false);
      return;
    }
    getGoal(Number(goalId))
      .then(setGoal)
      .catch((reason: unknown) => setError(getApiError(reason)))
      .finally(() => setBusy(false));
  }, [goalId]);

  useEffect(() => {
    if (!goal || !["draft", "running", "waiting_for_approval"].includes(goal.status) || !goal.due_at) return;
    const refreshTimer = window.setInterval(() => {
      getGoal(goal.id)
        .then(setGoal)
        .catch((reason: unknown) => setError(getApiError(reason)));
    }, 60_000);
    return () => window.clearInterval(refreshTimer);
  }, [goal]);

  async function saveChanges(input: GoalInput) {
    if (!goal) return;
    const updated = await updateGoal(goal.id, input);
    setGoal(updated);
    setEditing(false);
  }

  async function handleDelete() {
    if (!goal || !window.confirm("Delete this draft goal? This cannot be undone.")) return;
    setDeleting(true);
    setError("");
    try {
      await deleteGoal(goal.id);
      navigate("/", { replace: true });
    } catch (reason) {
      setError(getApiError(reason));
      setDeleting(false);
    }
  }

  async function handleComplete() {
    if (!goal || !window.confirm("Mark this goal as completed?")) return;
    setCompleting(true);
    setError("");
    try {
      setGoal(await completeGoal(goal.id));
    } catch (reason) {
      setError(getApiError(reason));
      setCompleting(false);
    }
  }

  if (busy) return <Loading label="Loading goal" />;
  if (error && !goal) return <div className="mx-auto max-w-3xl"><Link to="/" className="mb-8 inline-flex items-center gap-2 text-sm text-slate-500 hover:text-white"><ArrowLeft size={16} /> All goals</Link><div role="alert" className="rounded-xl border border-rose-400/20 bg-rose-400/10 p-5 text-sm text-rose-200">{error}</div></div>;
  if (!goal) return null;

  return <div className="mx-auto max-w-4xl animate-enter">
    <Link to="/" className="mb-7 inline-flex items-center gap-2 text-xs font-medium text-slate-500 transition hover:text-white"><ArrowLeft size={15} /> All goals</Link>
    {error && <div role="alert" className="mb-6 rounded-xl border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">{error}</div>}
    <div className="mb-7 flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
      <div className="min-w-0"><div className="mb-4"><StatusBadge status={goal.status} /></div><h1 className="break-words font-display text-3xl font-semibold tracking-tight text-white sm:text-4xl">{goal.title}</h1><div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-slate-600"><span className="flex items-center gap-1.5"><CalendarDays size={13} /> Created {formatDate(goal.created_at)}</span>{goal.due_at && <span className="flex items-center gap-1.5"><Timer size={13} /> Due {formatDateTime(goal.due_at)}</span>}<span>Last updated {formatDate(goal.updated_at)}</span></div></div>
      {goal.status === "draft" && <div className="flex shrink-0 flex-wrap gap-2">
        <button onClick={handleComplete} disabled={completing} className="btn-primary flex items-center gap-2 disabled:cursor-wait disabled:opacity-60"><CheckCircle2 size={15} />{completing ? "Completing…" : "Mark complete"}</button>
        <button onClick={() => setEditing((value) => !value)} className="btn-secondary flex items-center gap-2"><Pencil size={14} /> Edit</button>
        <button onClick={handleDelete} disabled={deleting || completing} className="btn-danger flex items-center gap-2"><Trash2 size={14} />{deleting ? "Deleting…" : "Delete"}</button>
      </div>}
    </div>
    {editing ? <div className="panel-card mb-6 p-6 sm:p-8"><GoalForm initial={{ title: goal.title, description: goal.description, due_at: goal.due_at }} submitLabel="Save changes" onSubmit={saveChanges} /></div> : <section className="panel-card p-6 sm:p-8"><h2 className="mb-4 text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Goal description</h2><p className="whitespace-pre-wrap text-sm leading-7 text-slate-300">{goal.description}</p></section>}
    {goal.final_report && <section className="mt-5 panel-card p-6 sm:p-8"><h2 className="mb-4 text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Final report</h2><pre className="whitespace-pre-wrap font-sans text-sm leading-7 text-slate-300">{goal.final_report}</pre></section>}
  </div>;
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
