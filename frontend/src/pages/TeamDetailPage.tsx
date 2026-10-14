import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import type { ReactNode } from "react";
import {
  ArrowLeft,
  CalendarClock,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  CircleUserRound,
  Clock3,
  MailPlus,
  Pencil,
  Plus,
  Send,
  ShieldCheck,
  Users,
  X,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";
import {
  assignTask,
  assignTaskToWorkers,
  getTeam,
  inviteMember,
  listTeamTasks,
  reviewJoinRequest,
  reviewTask,
  reviewTaskRequest,
  requestTask,
  setTeamDiscoverability,
  submitTask,
  updateDeclinedTaskRequest,
  updateTaskSchedule,
} from "../api/teams";
import { getApiError } from "../api/client";
import { Loading } from "../components/Loading";
import type { TaskRequestInput, TeamDetail, TeamTask, TeamTaskBulkInput, TeamTaskInput } from "../types/team";

export function TeamDetailPage() {
  const { teamId } = useParams();
  const numericTeamId = Number(teamId);
  const [team, setTeam] = useState<TeamDetail | null>(null);
  const [tasks, setTasks] = useState<TeamTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showInvite, setShowInvite] = useState(false);
  const [showTask, setShowTask] = useState(false);
  const [taskPage, setTaskPage] = useState(1);

  const refresh = useCallback(async () => {
    if (!Number.isSafeInteger(numericTeamId) || numericTeamId < 1) throw new Error("Team not found.");
    const [teamData, taskData] = await Promise.all([getTeam(numericTeamId), listTeamTasks(numericTeamId)]);
    setTeam(teamData);
    setTasks(taskData);
    setError("");
  }, [numericTeamId]);

  useEffect(() => {
    refresh().catch((reason: unknown) => setError(getApiError(reason))).finally(() => setLoading(false));
  }, [refresh]);

  const pendingReviews = useMemo(() => tasks.filter((task) =>
    task.status === "pending_approval"
  ).length + tasks.reduce((count, task) => count + task.assignments.filter(
    (assignment) => assignment.status === "submitted",
  ).length, 0), [tasks]);
  const sortedTasks = useMemo(() => [...tasks].sort((a, b) => {
    const completedOrder = Number(a.status === "completed") - Number(b.status === "completed");
    return completedOrder
      || Date.parse(a.start_at) - Date.parse(b.start_at)
      || Date.parse(a.deadline_at) - Date.parse(b.deadline_at)
      || a.id - b.id;
  }), [tasks]);
  const taskPageSize = 5;
  const taskPageCount = Math.ceil(sortedTasks.length / taskPageSize);
  const currentTaskPage = Math.min(taskPage, Math.max(taskPageCount, 1));
  const visibleTasks = sortedTasks.slice(
    (currentTaskPage - 1) * taskPageSize,
    currentTaskPage * taskPageSize,
  );

  async function action(work: () => Promise<unknown>): Promise<boolean> {
    setError("");
    try {
      await work();
      await refresh();
      return true;
    } catch (reason) {
      setError(getApiError(reason));
      return false;
    }
  }

  async function handleInvite(email: string) {
    await inviteMember(numericTeamId, email);
    setShowInvite(false);
    await refresh();
  }

  async function handleTaskCreate(input: TeamTaskInput | TeamTaskBulkInput | TaskRequestInput) {
    if ("assignee_ids" in input) {
      await assignTaskToWorkers(numericTeamId, input);
    } else if ("assignee_id" in input) {
      await assignTask(numericTeamId, input);
    } else {
      await requestTask(numericTeamId, input);
    }
    setShowTask(false);
    await refresh();
  }

  async function handleReview(task: TeamTask, assigneeId: number, approved: boolean) {
    const comment = approved ? undefined : window.prompt("What should be changed before resubmission?", "Please make the requested updates.");
    if (!approved && comment === null) return;
    await action(() => reviewTask(task.id, assigneeId, approved, comment ?? undefined));
  }

  async function handleTaskRequestReview(task: TeamTask, approved: boolean) {
    const comment = approved ? undefined : window.prompt("Why are you declining this task request?", "Please revise the request.");
    if (!approved && comment === null) return;
    await action(() => reviewTaskRequest(task.id, approved, comment ?? undefined));
  }

  if (loading) return <Loading label="Loading team workspace" />;
  if (!team) return <div className="mx-auto max-w-3xl"><Link to="/teams" className="mb-8 inline-flex items-center gap-2 text-sm text-slate-500 hover:text-white"><ArrowLeft size={16} /> Teams</Link><div role="alert" className="rounded-xl border border-rose-400/20 bg-rose-400/10 p-5 text-sm text-rose-200">{error || "Team not found."}</div></div>;
  const isLeader = team.role === "leader";
  const workers = team.members.filter((member) => member.role === "worker");

  return <>
    <div className="animate-enter">
      <Link to="/teams" className="mb-7 inline-flex items-center gap-2 text-xs font-medium text-slate-500 transition hover:text-white"><ArrowLeft size={15} /> All teams</Link>
      <div className="mb-8 flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
        <div>
          <span className={`mb-4 inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium ${isLeader ? "bg-forge-500/10 text-forge-300" : "bg-sky-400/10 text-sky-300"}`}>{isLeader ? <ShieldCheck size={13} /> : <CircleUserRound size={13} />}{isLeader ? "Team leader" : "Worker view"}</span>
          <h1 className="font-display text-3xl font-semibold tracking-tight text-white sm:text-4xl">{team.name}<span className="text-forge-400">.</span></h1>
          <p className="mt-2 text-sm text-slate-500">{isLeader ? "Assign work and review submitted tasks." : "Your assigned tasks and schedule."}</p>
        </div>
        {isLeader ? <div className="flex flex-wrap gap-2"><button className="btn-secondary flex items-center gap-2" onClick={() => void action(() => setTeamDiscoverability(team.id, !team.is_discoverable))}>{team.is_discoverable ? "Hide from search" : "Allow team search"}</button><button className="btn-secondary flex items-center gap-2" onClick={() => setShowInvite(true)}><MailPlus size={15} /> Invite worker</button><button className="btn-primary flex items-center gap-2" onClick={() => setShowTask(true)}><Plus size={16} /> Assign task</button></div> : <button className="btn-primary flex items-center gap-2" onClick={() => setShowTask(true)}><Plus size={16} /> Propose a task</button>}
      </div>
      {error && <div role="alert" className="mb-5 rounded-xl border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">{error}</div>}
      {isLeader && team.is_discoverable && <p className="mb-5 -mt-4 text-xs text-emerald-300/80">Workers can find this team and request to join. You approve each request.</p>}
      <div className="mb-8 grid gap-4 sm:grid-cols-3">
        <TeamMetric label="Team members" value={team.member_count} icon={<Users size={16} />} />
        <TeamMetric label="Active tasks" value={tasks.filter((task) => task.status === "assigned" || task.status === "submitted").length} icon={<CalendarClock size={16} />} />
        <TeamMetric label={isLeader ? "To review" : "Waiting for review"} value={pendingReviews} icon={<CheckCircle2 size={16} />} />
      </div>
      <section className="mb-8">
        <div className="mb-4 flex items-center justify-between"><div><h2 className="font-display text-lg font-semibold text-white">Tasks</h2><p className="mt-1 text-xs text-slate-500">Scheduled date and time, with completed tasks at the end</p></div></div>
        {tasks.length ? <>
          <div className="grid gap-4">{visibleTasks.map((task) => <TeamTaskCard key={task.id} task={task} isLeader={isLeader} onAction={action} onReview={handleReview} onRequestReview={handleTaskRequestReview} />)}</div>
          {taskPageCount > 1 && <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs text-slate-500">Showing {(currentTaskPage - 1) * taskPageSize + 1}–{Math.min(currentTaskPage * taskPageSize, sortedTasks.length)} of {sortedTasks.length} tasks</p>
            <nav aria-label="Task pages" className="flex items-center justify-end gap-2">
              <button type="button" disabled={currentTaskPage === 1} onClick={() => setTaskPage((page) => Math.max(1, page - 1))} className="btn-secondary flex items-center gap-1.5 py-2 text-xs disabled:cursor-not-allowed disabled:opacity-40"><ChevronLeft size={14} /> Previous</button>
              <span className="px-2 text-xs text-slate-400">Page {currentTaskPage} of {taskPageCount}</span>
              <button type="button" disabled={currentTaskPage === taskPageCount} onClick={() => setTaskPage((page) => Math.min(taskPageCount, page + 1))} className="btn-secondary flex items-center gap-1.5 py-2 text-xs disabled:cursor-not-allowed disabled:opacity-40">Next <ChevronRight size={14} /></button>
            </nav>
          </div>}
        </> : <div className="panel-card flex flex-col items-center px-6 py-12 text-center"><span className="mb-4 grid h-12 w-12 place-items-center rounded-xl bg-forge-500/[0.08] text-forge-300"><CalendarClock size={20} /></span><h3 className="font-display font-semibold text-white">No tasks yet</h3><p className="mt-2 text-sm text-slate-500">{isLeader ? "Invite workers, then assign your first scheduled task." : "Propose a task for your team leader to approve."}</p>{isLeader ? <button onClick={() => setShowTask(true)} className="btn-primary mt-5 flex items-center gap-2"><Plus size={15} /> Assign a task</button> : <button onClick={() => setShowTask(true)} className="btn-primary mt-5 flex items-center gap-2"><Plus size={15} /> Propose a task</button>}</div>}
      </section>
      {isLeader && team.join_requests.length > 0 && <section className="mb-8"><div className="mb-4"><h2 className="font-display text-lg font-semibold text-white">Join requests</h2><p className="mt-1 text-xs text-slate-600">Review workers who requested access</p></div><div className="panel-card divide-y divide-white/[0.05]">{team.join_requests.map((request) => <div key={request.id} className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-amber-400/10 text-sm font-semibold text-amber-200">{request.email.slice(0, 1).toUpperCase()}</span><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium text-slate-300">{request.email}</p><p className="mt-0.5 text-[11px] text-slate-600">Requested {new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(request.created_at))}</p></div><div className="flex gap-2"><button onClick={() => void action(() => reviewJoinRequest(team.id, request.id, false))} className="btn-secondary py-2 text-xs">Decline</button><button onClick={() => void action(() => reviewJoinRequest(team.id, request.id, true))} className="btn-primary flex items-center gap-1.5 py-2 text-xs"><Check size={13} /> Approve</button></div></div>)}</div></section>}
      {isLeader && <section><div className="mb-4"><h2 className="font-display text-lg font-semibold text-white">Team members</h2><p className="mt-1 text-xs text-slate-600">People who can access this team workspace</p></div><div className="panel-card divide-y divide-white/[0.05]">{team.members.map((member) => <div key={member.user_id} className="flex items-center gap-3 px-4 py-3.5"><span className="grid h-9 w-9 place-items-center rounded-full bg-forge-500/10 text-xs font-semibold text-forge-300">{member.email.slice(0, 1).toUpperCase()}</span><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium text-slate-300">{member.email}</p><p className="mt-0.5 text-[11px] text-slate-600">{member.role === "leader" ? "Team leader" : "Worker"}</p></div><span className={`rounded-full px-2.5 py-1 text-[10px] font-medium ${member.role === "leader" ? "bg-forge-500/10 text-forge-300" : "bg-slate-500/10 text-slate-400"}`}>{member.role}</span></div>)}
        {team.invites.filter((invite) => !invite.accepted).map((invite) => <div key={invite.email} className="flex items-center gap-3 px-4 py-3.5"><span className="grid h-9 w-9 place-items-center rounded-full bg-amber-400/10 text-amber-300"><MailPlus size={15} /></span><div className="min-w-0 flex-1"><p className="truncate text-sm text-slate-400">{invite.email}</p><p className="mt-0.5 text-[11px] text-amber-300/70">Invitation pending — register with this email to join</p></div><span className="rounded-full bg-amber-400/10 px-2.5 py-1 text-[10px] text-amber-300">Invited</span></div>)}</div></section>}
    </div>
    {showInvite && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowInvite(false); }}><div role="dialog" aria-modal="true" className="w-full max-w-md rounded-2xl border border-white/10 bg-[#141720] p-6 shadow-2xl sm:p-8"><InviteForm onSubmit={handleInvite} onClose={() => setShowInvite(false)} /></div></div>}
    {showTask && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowTask(false); }}><div role="dialog" aria-modal="true" aria-labelledby="assign-task-title" className="modal-panel w-full max-w-2xl rounded-3xl border border-white/10 bg-[#141720] p-5 shadow-2xl sm:p-8"><TaskForm isLeader={isLeader} workers={workers} onSubmit={handleTaskCreate} onClose={() => setShowTask(false)} /></div></div>}
  </>;
}

function TeamMetric({ label, value, icon }: { label: string; value: number; icon: ReactNode }) {
  return <div className="panel-card flex items-center gap-4 p-4"><span className="grid h-10 w-10 place-items-center rounded-xl bg-forge-500/10 text-forge-300">{icon}</span><div><p className="font-display text-xl font-semibold text-white">{value}</p><p className="mt-0.5 text-xs text-slate-500">{label}</p></div></div>;
}

function TeamTaskCard({ task, isLeader, onAction, onReview, onRequestReview }: {
  task: TeamTask;
  isLeader: boolean;
  onAction: (work: () => Promise<unknown>) => Promise<boolean>;
  onReview: (task: TeamTask, assigneeId: number, approved: boolean) => Promise<void>;
  onRequestReview: (task: TeamTask, approved: boolean) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [editingRequest, setEditingRequest] = useState(false);
  const currentAssignment = task.current_assignment;
  const visibleStatus = isLeader ? task.status : currentAssignment?.status ?? task.status;
  return <article className="panel-card p-5 sm:p-6">
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
      <div className="min-w-0 flex-1"><div className="mb-3 flex flex-wrap items-center gap-2"><TaskStatus status={visibleStatus} /><span className="text-[11px] text-slate-600">#{task.id}</span></div><h3 className="font-display text-base font-semibold text-white">{task.title}</h3><p className="mt-1.5 whitespace-pre-wrap text-sm leading-6 text-slate-400">{task.description}</p><p className="mt-3 flex items-center gap-1.5 text-xs text-slate-500"><CircleUserRound size={13} />Assigned to {task.assignments.length} {task.assignments.length === 1 ? "worker" : "workers"}</p></div>
      <div className="flex shrink-0 flex-col gap-2 rounded-xl border border-slate-200 bg-gradient-to-br from-slate-50 to-white px-3.5 py-3 text-xs shadow-inner">
        <span className="flex items-center gap-2 text-slate-600"><Clock3 size={13} className="text-forge-300" />Starts <strong className="font-semibold text-slate-800">{formatDateTime(task.start_at)}</strong></span>
        <span className="flex items-center gap-2 text-slate-600"><CalendarClock size={13} className="text-amber-700" />Due <strong className="font-semibold text-amber-800">{formatDateTime(task.deadline_at)}</strong></span>
      </div>
    </div>
    {isLeader && <div className="mt-4 divide-y divide-white/[0.05] rounded-xl border border-white/[0.06]">{task.assignments.map((assignment) => <div key={assignment.user_id} className="flex flex-col gap-2 px-3.5 py-3 sm:flex-row sm:items-center"><div className="min-w-0 flex-1"><p className="truncate text-xs font-medium text-slate-300">{assignment.email}</p><div className="mt-1 flex items-center gap-2"><TaskStatus status={assignment.status} />{assignment.review_comment && <span className="truncate text-[11px] text-slate-500">{assignment.review_comment}</span>}</div></div>{assignment.status === "submitted" && <div className="flex gap-2"><button onClick={() => void onReview(task, assignment.user_id, true)} className="btn-primary flex items-center gap-1.5 py-2 text-xs"><CheckCircle2 size={13} />Approve</button><button onClick={() => void onReview(task, assignment.user_id, false)} className="btn-secondary flex items-center gap-1.5 py-2 text-xs text-amber-200"><Pencil size={13} />Request changes</button></div>}</div>)}</div>}
    {!isLeader && currentAssignment?.review_comment && <div className={`mt-4 rounded-xl border px-3.5 py-3 text-xs leading-5 ${currentAssignment.status === "assigned" ? "border-amber-200 bg-amber-50 text-amber-900" : currentAssignment.status === "declined" ? "border-rose-200 bg-rose-50 text-rose-900" : "border-emerald-200 bg-emerald-50 text-emerald-900"}`}><span className="font-semibold">{currentAssignment.status === "assigned" ? "Leader feedback: " : currentAssignment.status === "declined" ? "Leader response: " : "Review note: "}</span>{currentAssignment.review_comment}</div>}
    {editingRequest && <TaskRequestEditor task={task} onClose={() => setEditingRequest(false)} onSave={async (input) => {
      const saved = await onAction(() => updateDeclinedTaskRequest(task.id, input));
      if (saved) setEditingRequest(false);
      return saved;
    }} />}
    {editing && <ScheduleEditor task={task} onClose={() => setEditing(false)} onSave={async (start_at, deadline_at) => { const saved = await onAction(() => updateTaskSchedule(task.id, { start_at, deadline_at })); if (saved) setEditing(false); return saved; }} />}
    {!editing && <div className="mt-5 flex flex-wrap gap-2 border-t border-white/[0.05] pt-4">
      {isLeader && task.status !== "completed" && <button onClick={() => setEditing(true)} className="btn-secondary flex items-center gap-2 text-xs"><Pencil size={13} /> Edit schedule</button>}
      {!isLeader && visibleStatus === "pending_approval" && <span className="flex items-center gap-2 rounded-xl bg-violet-400/[0.08] px-3.5 py-2.5 text-xs text-violet-200"><Clock3 size={14} /> Waiting for leader approval — work cannot start yet</span>}
      {isLeader && task.status === "pending_approval" && <><button onClick={() => void onRequestReview(task, true)} className="btn-primary flex items-center gap-2 text-xs"><CheckCircle2 size={14} /> Approve request</button><button onClick={() => void onRequestReview(task, false)} className="btn-secondary flex items-center gap-2 text-xs text-amber-200"><X size={13} /> Decline request</button></>}
      {!isLeader && visibleStatus === "declined" && <><span className="flex items-center gap-2 rounded-xl bg-rose-400/[0.08] px-3.5 py-2.5 text-xs text-rose-200"><X size={14} /> Task request declined</span><button onClick={() => setEditingRequest(true)} className="btn-secondary flex items-center gap-2 text-xs"><Pencil size={13} /> Edit and resubmit</button></>}
      {!isLeader && visibleStatus === "assigned" && <button onClick={() => void onAction(() => submitTask(task.id))} className="btn-primary flex items-center gap-2 text-xs"><Check size={14} /> I finished this task</button>}
      {!isLeader && visibleStatus === "submitted" && <span className="flex items-center gap-2 rounded-xl bg-amber-400/[0.08] px-3.5 py-2.5 text-xs text-amber-200"><Clock3 size={14} /> Submitted — awaiting leader review</span>}
      {visibleStatus === "completed" && <span className="flex items-center gap-2 rounded-xl bg-emerald-400/[0.08] px-3.5 py-2.5 text-xs text-emerald-200"><CheckCircle2 size={14} /> Approved and completed</span>}
    </div>}
  </article>;
}

function TaskRequestEditor({ task, onSave, onClose }: {
  task: TeamTask;
  onSave: (input: TaskRequestInput) => Promise<boolean>;
  onClose: () => void;
}) {
  const [title, setTitle] = useState(task.title);
  const [description, setDescription] = useState(task.description);
  const [start, setStart] = useState(toLocalDateTime(task.start_at));
  const [deadline, setDeadline] = useState(toLocalDateTime(task.deadline_at));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!title.trim() || !description.trim()) {
      setError("Enter a task title and description.");
      return;
    }
    if (!start || !deadline || new Date(deadline) <= new Date(start)) {
      setError("The deadline must be later than the start time.");
      return;
    }
    setBusy(true);
    try {
      const saved = await onSave({
        title: title.trim(),
        description: description.trim(),
        start_at: new Date(start).toISOString(),
        deadline_at: new Date(deadline).toISOString(),
      });
      if (!saved) setError("Could not resubmit the task request. Review the message above.");
    } catch (reason) {
      setError(getApiError(reason));
    } finally {
      setBusy(false);
    }
  }

  return <form onSubmit={submit} className="mt-4 space-y-4 rounded-xl border border-violet-200 bg-violet-50 p-4">
    <div className="flex items-center justify-between"><p className="text-sm font-semibold text-slate-800">Edit declined task request</p><button type="button" onClick={onClose} aria-label="Close task request editor" className="text-slate-500 hover:text-slate-800"><X size={15} /></button></div>
    <label className="block text-xs font-medium text-slate-700">Task title<input required maxLength={200} value={title} onChange={(event) => setTitle(event.target.value)} className="form-input mt-1.5" /></label>
    <label className="block text-xs font-medium text-slate-700">Instructions<textarea required rows={3} maxLength={10_000} value={description} onChange={(event) => setDescription(event.target.value)} className="form-input mt-1.5 resize-y" /></label>
    <div className="grid gap-3 sm:grid-cols-2"><label className="text-xs font-medium text-slate-700">Start time<input required type="datetime-local" value={start} onChange={(event) => setStart(event.target.value)} className="form-input mt-1.5" /></label><label className="text-xs font-medium text-slate-700">Deadline<input required type="datetime-local" value={deadline} onChange={(event) => setDeadline(event.target.value)} className="form-input mt-1.5" /></label></div>
    {error && <p role="alert" className="text-xs text-rose-700">{error}</p>}
    <div className="flex items-center justify-between gap-3"><p className="text-[11px] leading-5 text-slate-600">Your changes will be sent to the leader for approval again.</p><div className="flex shrink-0 gap-2"><button type="button" onClick={onClose} className="btn-secondary py-2 text-xs">Cancel</button><button disabled={busy} className="btn-primary py-2 text-xs disabled:opacity-60">{busy ? "Sending…" : "Save & resubmit"}</button></div></div>
  </form>;
}

function TaskStatus({ status }: { status: TeamTask["status"] }) {
  const styles: Record<TeamTask["status"], string> = {
    pending_approval: "bg-violet-400/10 text-violet-200",
    assigned: "bg-sky-400/10 text-sky-300",
    submitted: "bg-amber-400/10 text-amber-200",
    completed: "bg-emerald-400/10 text-emerald-300",
    declined: "bg-rose-400/10 text-rose-200",
  };
  const label: Record<TeamTask["status"], string> = {
    pending_approval: "Approval needed",
    assigned: "Assigned",
    submitted: "Awaiting review",
    completed: "Completed",
    declined: "Declined",
  };
  return <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold ${styles[status]}`}>{label[status]}</span>;
}

function InviteForm({ onSubmit, onClose }: { onSubmit: (email: string) => Promise<void>; onClose: () => void }) {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await onSubmit(email.trim());
    } catch (reason) {
      setError(getApiError(reason));
    } finally {
      setBusy(false);
    }
  }
  return <form onSubmit={submit} className="space-y-5">
    <div className="flex items-start justify-between"><div><h2 className="font-display text-xl font-semibold text-white">Invite a worker</h2><p className="mt-1 text-sm text-slate-500">They join by registering with this email address.</p></div><button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-500 hover:bg-white/5 hover:text-white" aria-label="Close"><X size={18} /></button></div>
    {error && <div role="alert" className="rounded-xl border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">{error}</div>}
    <label className="block text-sm font-medium text-slate-300">Worker email<input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="worker@example.com" className="form-input mt-2" /></label>
    <div className="flex justify-end gap-3"><button type="button" onClick={onClose} className="btn-secondary">Cancel</button><button disabled={busy} className="btn-primary flex items-center gap-2 disabled:opacity-60">{busy ? "Inviting…" : "Send invite"}{!busy && <Send size={14} />}</button></div>
  </form>;
}

function TaskForm({ isLeader, workers, onSubmit, onClose }: {
  isLeader: boolean;
  workers: TeamDetail["members"];
  onSubmit: (task: TeamTaskInput | TeamTaskBulkInput | TaskRequestInput) => Promise<void>;
  onClose: () => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [assignee, setAssignee] = useState("");
  const [start, setStart] = useState("");
  const [deadline, setDeadline] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (isLeader && !assignee) { setError("Invite and select a worker before assigning a task."); return; }
    if (!start || !deadline || new Date(deadline) <= new Date(start)) { setError("The deadline must be later than the start time."); return; }
    setBusy(true);
    try {
      const task = {
        title: title.trim(),
        description: description.trim(),
        start_at: new Date(start).toISOString(),
        deadline_at: new Date(deadline).toISOString(),
      };
      await onSubmit(isLeader
        ? assignee === "all"
          ? { ...task, assignee_ids: workers.map((worker) => worker.user_id) }
          : { ...task, assignee_id: Number(assignee) }
        : task);
    } catch (reason) {
      setError(getApiError(reason));
    } finally {
      setBusy(false);
    }
  }
  return <form onSubmit={submit} className="space-y-6">
    <div className="flex items-start justify-between gap-4">
      <div className="flex items-start gap-4">
        <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-forge-500/15 to-indigo-400/10 text-forge-300 ring-1 ring-forge-500/10"><ClipboardList size={22} /></span>
        <div><p className="mb-1 text-[10px] font-bold uppercase tracking-[0.18em] text-forge-300">{isLeader ? "New assignment" : "Task proposal"}</p><h2 id="assign-task-title" className="font-display text-2xl font-semibold tracking-tight text-slate-900">{isLeader ? "Assign a task" : "Propose a task"}</h2><p className="mt-1 text-sm text-slate-500">{isLeader ? "Give someone a clear outcome and a realistic timeline." : "Suggest a clear outcome and timeline. Your leader must approve it before you can start."}</p></div>
      </div>
      <button type="button" onClick={onClose} className="rounded-xl p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-800" aria-label="Close"><X size={18} /></button>
    </div>
    {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}
    <div className="space-y-4 rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4 sm:p-5">
      <div><h3 className="text-sm font-semibold text-slate-800">Task details</h3><p className="mt-1 text-xs text-slate-500">Describe what success looks like.</p></div>
      <label className="block text-sm font-medium text-slate-700">Task title<input required maxLength={200} value={title} onChange={(event) => setTitle(event.target.value)} placeholder="e.g. Prepare weekly report" className="form-input mt-2" /></label>
      <label className="block text-sm font-medium text-slate-700">Instructions<textarea required rows={3} maxLength={10_000} value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Include the expected result, relevant context, and any important requirements." className="form-input mt-2 resize-y" /></label>
    </div>
    <div className="grid gap-4 sm:grid-cols-2">
      {isLeader ? <label className="block text-sm font-medium text-slate-700">
        <span className="flex items-center gap-2"><CircleUserRound size={15} className="text-forge-300" /> Assign to</span>
        <select required value={assignee} onChange={(event) => setAssignee(event.target.value)} className="form-input mt-2"><option value="">Choose a team member</option><option value="all">All workers ({workers.length})</option>{workers.map((worker) => <option key={worker.user_id} value={worker.user_id}>{worker.email}</option>)}</select>
      </label> : <div className="flex items-center gap-3 rounded-xl border border-violet-200 bg-violet-50 px-4 py-3 text-xs leading-5 text-violet-900"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-white text-violet-600 shadow-sm"><ShieldCheck size={17} /></span>Your request will be reviewed by the team leader. It will not become an active task until approved.</div>}
      <div className="flex items-center gap-3 rounded-xl border border-forge-500/10 bg-forge-500/[0.045] px-4 py-3 text-xs leading-5 text-slate-600">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-white text-forge-300 shadow-sm"><ShieldCheck size={17} /></span>
        The assignee can submit finished work for your review.
      </div>
    </div>
    <div className="rounded-2xl border border-slate-200/80 bg-white p-4 sm:p-5">
      <div className="mb-4"><h3 className="text-sm font-semibold text-slate-800">Schedule</h3><p className="mt-1 text-xs text-slate-500">Times are shown in your local timezone.</p></div>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block text-sm font-medium text-slate-700"><span className="flex items-center gap-2"><Clock3 size={15} className="text-forge-300" /> Start time</span><input required type="datetime-local" value={start} onChange={(event) => setStart(event.target.value)} className="form-input mt-2" /></label>
        <label className="block text-sm font-medium text-slate-700"><span className="flex items-center gap-2"><CalendarDays size={15} className="text-amber-600" /> Deadline</span><input required type="datetime-local" value={deadline} onChange={(event) => setDeadline(event.target.value)} className="form-input mt-2" /></label>
      </div>
    </div>
    {isLeader && workers.length === 0 && <p role="status" className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-800">Invite a worker to this team before assigning a task.</p>}
    <div className="flex flex-col-reverse gap-3 border-t border-slate-200 pt-5 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-[11px] leading-5 text-slate-500">{isLeader ? "You can review submissions and approve completion." : "The task stays pending until your team leader approves it."}</p>
      <div className="flex justify-end gap-3"><button type="button" onClick={onClose} className="btn-secondary">Cancel</button><button disabled={busy || (isLeader && workers.length === 0)} className="btn-primary flex items-center gap-2 disabled:cursor-wait disabled:opacity-60"><Check size={15} />{busy ? (isLeader ? "Assigning…" : "Submitting…") : (isLeader ? "Assign task" : "Send for approval")}</button></div>
    </div>
  </form>;
}

function ScheduleEditor({ task, onSave, onClose }: { task: TeamTask; onSave: (start: string, deadline: string) => Promise<boolean>; onClose: () => void }) {
  const [start, setStart] = useState(toLocalDateTime(task.start_at));
  const [deadline, setDeadline] = useState(toLocalDateTime(task.deadline_at));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!start || !deadline || new Date(deadline) <= new Date(start)) { setError("The deadline must be later than the start time."); return; }
    setBusy(true);
    setError("");
    try {
      const saved = await onSave(new Date(start).toISOString(), new Date(deadline).toISOString());
      if (!saved) setError("Could not save the schedule. Review the message above.");
    } catch (reason) {
      setError(getApiError(reason));
    } finally {
      setBusy(false);
    }
  }
  return <form onSubmit={submit} className="mt-4 rounded-xl border border-forge-400/10 bg-forge-500/[0.04] p-4">
    <div className="mb-3 flex items-center justify-between"><p className="flex items-center gap-2 text-xs font-semibold text-forge-200"><Pencil size={13} />Adjust schedule</p><button type="button" onClick={onClose} aria-label="Close schedule editor" className="text-slate-500 hover:text-white"><X size={15} /></button></div>
    {error && <p role="alert" className="mb-3 text-xs text-rose-200">{error}</p>}
    <div className="grid gap-3 sm:grid-cols-2"><label className="text-xs text-slate-400">Start<input required type="datetime-local" value={start} onChange={(event) => setStart(event.target.value)} className="form-input mt-1.5 text-xs [color-scheme:dark]" /></label><label className="text-xs text-slate-400">Deadline<input required type="datetime-local" value={deadline} onChange={(event) => setDeadline(event.target.value)} className="form-input mt-1.5 text-xs [color-scheme:dark]" /></label></div>
    <div className="mt-3 flex justify-end gap-2"><button type="button" onClick={onClose} className="btn-secondary py-2 text-xs">Cancel</button><button disabled={busy} className="btn-primary py-2 text-xs disabled:opacity-60">{busy ? "Saving…" : "Save times"}</button></div>
  </form>;
}

function toLocalDateTime(value: string) {
  const date = new Date(value);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(value));
}
