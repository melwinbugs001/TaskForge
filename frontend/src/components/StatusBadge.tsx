import type { GoalStatus } from "../types/api";

const styles: Record<GoalStatus, string> = {
  draft: "bg-slate-500/10 text-slate-300 ring-slate-400/20",
  running: "bg-violet-500/10 text-violet-300 ring-violet-400/20",
  waiting_for_approval: "bg-amber-500/10 text-amber-300 ring-amber-400/20",
  completed: "bg-emerald-500/10 text-emerald-300 ring-emerald-400/20",
  failed: "bg-rose-500/10 text-rose-300 ring-rose-400/20",
  cancelled: "bg-slate-500/10 text-slate-400 ring-slate-400/20",
};

const labels: Record<GoalStatus, string> = {
  draft: "Draft",
  running: "Running",
  waiting_for_approval: "Approval needed",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};

export function StatusBadge({ status }: { status: GoalStatus }) {
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${styles[status]}`}>
      <span className={`mr-1.5 mt-1 h-1.5 w-1.5 rounded-full ${status === "running" ? "animate-pulse bg-violet-300" : "bg-current"}`} />
      {labels[status]}
    </span>
  );
}
