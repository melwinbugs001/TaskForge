import { useEffect, useState, type FormEvent } from "react";
import { ArrowRight, BriefcaseBusiness, Check, Plus, Search, ShieldCheck, Users, X } from "lucide-react";
import { Link } from "react-router-dom";
import { createTeam, discoverTeams, listTeams, requestToJoin } from "../api/teams";
import { getApiError } from "../api/client";
import { Loading } from "../components/Loading";
import type { DiscoverableTeam, Team } from "../types/team";

export function TeamsPage() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [discoveries, setDiscoveries] = useState<DiscoverableTeam[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");
  const [view, setView] = useState<"mine" | "discover">("mine");
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [requestingTeamId, setRequestingTeamId] = useState<number | null>(null);

  async function refresh() {
    const results = await listTeams();
    setTeams(results);
  }

  useEffect(() => {
    refresh()
      .catch((reason: unknown) => setError(getApiError(reason)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (view !== "discover") return;
    setSearching(true);
    const timeout = window.setTimeout(() => {
      discoverTeams(query)
        .then(setDiscoveries)
        .catch((reason: unknown) => setError(getApiError(reason)))
        .finally(() => setSearching(false));
    }, 250);
    return () => window.clearTimeout(timeout);
  }, [view, query]);

  async function addTeam(name: string, isDiscoverable: boolean) {
    const team = await createTeam(name, isDiscoverable);
    setTeams((current) => [team, ...current]);
    setShowForm(false);
  }

  async function joinRequest(teamId: number) {
    setRequestingTeamId(teamId);
    setError("");
    try {
      await requestToJoin(teamId);
      const [updatedTeams, updatedDiscoveries] = await Promise.all([
        listTeams(),
        discoverTeams(query),
      ]);
      setTeams(updatedTeams);
      setDiscoveries(updatedDiscoveries);
    } catch (reason) {
      setError(getApiError(reason));
    } finally {
      setRequestingTeamId(null);
    }
  }

  if (loading) return <Loading label="Loading teams" />;

  return (
    <>
      <div className="animate-enter">
        <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-forge-300">Team workspace</p>
            <h1 className="font-display text-3xl font-semibold tracking-tight text-white sm:text-4xl">Teams & tasks<span className="text-forge-400">.</span></h1>
            <p className="mt-2 text-sm text-slate-500">Assign work, set clear schedules, and review what’s finished.</p>
          </div>
          <button className="btn-primary flex items-center justify-center gap-2" onClick={() => setShowForm(true)}><Plus size={17} /> Create team</button>
        </div>
        {error && <div role="alert" className="mb-5 rounded-xl border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">{error}</div>}
        <div className="mb-6 flex gap-1 border-b border-white/[0.06]">
          <button onClick={() => setView("mine")} className={`border-b-2 px-3 py-2.5 text-xs font-medium ${view === "mine" ? "border-forge-400 text-forge-300" : "border-transparent text-slate-500 hover:text-slate-300"}`}>My teams</button>
          <button onClick={() => setView("discover")} className={`flex items-center gap-2 border-b-2 px-3 py-2.5 text-xs font-medium ${view === "discover" ? "border-forge-400 text-forge-300" : "border-transparent text-slate-500 hover:text-slate-300"}`}><Search size={13} /> Find teams</button>
        </div>
        {view === "mine" && teams.length ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {teams.map((team) => <Link key={team.id} to={`/teams/${team.id}`} className="panel-card group p-5 transition hover:border-forge-400/20 hover:bg-white/[0.035]">
            <div className="mb-5 flex items-start justify-between">
              <span className="grid h-11 w-11 place-items-center rounded-xl bg-forge-500/10 text-forge-300"><BriefcaseBusiness size={20} /></span>
              <span className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${team.role === "leader" ? "bg-forge-500/10 text-forge-300" : "bg-sky-400/10 text-sky-300"}`}>{team.role === "leader" ? "Team leader" : "Worker"}</span>
            </div>
            <h2 className="font-display text-lg font-semibold text-white">{team.name}</h2>
            <div className="mt-3 flex items-center gap-2 text-xs text-slate-500"><Users size={14} />{team.member_count} {team.member_count === 1 ? "member" : "members"}{team.pending_invite_count > 0 && <span className="text-amber-300">· {team.pending_invite_count} invited</span>}</div>
            <div className="mt-5 flex items-center justify-between border-t border-white/[0.06] pt-4 text-xs text-slate-600"><span>Open workspace</span><ArrowRight size={15} className="transition group-hover:translate-x-1 group-hover:text-forge-300" /></div>
          </Link>)}
        </div> : view === "mine" ? <div className="panel-card flex flex-col items-center px-6 py-16 text-center">
          <span className="mb-5 grid h-14 w-14 place-items-center rounded-2xl border border-forge-400/10 bg-forge-500/[0.07] text-forge-300"><Users size={24} /></span>
          <h2 className="font-display text-lg font-semibold text-white">Build your team workspace</h2>
          <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">Create a team to invite workers, assign scheduled tasks, and review their submissions.</p>
          <button className="btn-primary mt-6 flex items-center gap-2" onClick={() => setShowForm(true)}><Plus size={16} /> Create your first team</button>
        </div> : <section>
          <label className="relative mb-5 block max-w-lg"><Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-600" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search public team names…" className="form-input pl-10" /></label>
          {searching ? <div className="py-10 text-center text-sm text-slate-500">Searching teams…</div> : discoveries.length ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{discoveries.map((team) => <article key={team.id} className="panel-card p-5">
            <div className="mb-4 flex items-center justify-between"><span className="grid h-10 w-10 place-items-center rounded-xl bg-forge-500/10 text-forge-300"><BriefcaseBusiness size={18} /></span><span className="rounded-full bg-emerald-400/10 px-2.5 py-1 text-[10px] font-medium text-emerald-300">Open to requests</span></div>
            <h2 className="font-display text-lg font-semibold text-white">{team.name}</h2>
            <p className="mt-2 flex items-center gap-2 text-xs text-slate-500"><Users size={14} />{team.member_count} {team.member_count === 1 ? "member" : "members"}</p>
            {team.request_status === "pending" ? <div className="mt-5 flex items-center gap-2 rounded-xl bg-amber-400/[0.08] px-3 py-2.5 text-xs text-amber-200"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-300" />Join request pending leader approval</div> : team.request_status === "approved" ? <div className="mt-5 flex items-center gap-2 rounded-xl bg-emerald-400/[0.08] px-3 py-2.5 text-xs text-emerald-200"><Check size={14} />Approved — refresh My teams</div> : <button disabled={requestingTeamId === team.id} onClick={() => void joinRequest(team.id)} className="btn-primary mt-5 w-full disabled:opacity-60">{requestingTeamId === team.id ? "Requesting…" : team.request_status === "rejected" ? "Request to join again" : "Request to join"}</button>}
          </article>)}</div> : <div className="panel-card px-6 py-14 text-center"><Search size={22} className="mx-auto mb-4 text-slate-600" /><h2 className="font-display font-semibold text-white">No teams found</h2><p className="mt-2 text-sm text-slate-500">Try another name or ask a leader to make their team discoverable.</p></div>}
        </section>}
      </div>
      {showForm && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowForm(false); }}><div role="dialog" aria-modal="true" aria-labelledby="create-team-title" className="modal-panel w-full max-w-lg overflow-hidden rounded-2xl border border-white/10 bg-[#141720] shadow-2xl"><TeamForm onSubmit={addTeam} onClose={() => setShowForm(false)} /></div></div>}
    </>
  );
}

function TeamForm({ onSubmit, onClose }: { onSubmit: (name: string, isDiscoverable: boolean) => Promise<void>; onClose: () => void }) {
  const [name, setName] = useState("");
  const [isDiscoverable, setIsDiscoverable] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await onSubmit(name.trim(), isDiscoverable);
    } catch (reason) {
      setError(getApiError(reason));
    } finally {
      setBusy(false);
    }
  }
  return <form onSubmit={handleSubmit}>
    <div className="flex items-start justify-between gap-5 border-b border-slate-200 bg-gradient-to-r from-white via-slate-50 to-emerald-50/70 px-6 py-6 sm:px-8">
      <div className="flex min-w-0 items-start gap-4">
        <span className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-emerald-100 text-emerald-700 ring-1 ring-emerald-200"><BriefcaseBusiness size={21} /></span>
        <div className="min-w-0">
          <p className="mb-1 text-[10px] font-bold uppercase tracking-[0.16em] text-emerald-700">Workspace setup</p>
          <h2 id="create-team-title" className="font-display text-xl font-semibold text-slate-900">Create a team</h2>
          <p className="mt-1 text-sm leading-5 text-slate-500">Start a shared space for scheduled work and reviews.</p>
        </div>
      </div>
      <button type="button" onClick={onClose} className="shrink-0 rounded-lg p-2 text-slate-500 transition hover:bg-white hover:text-slate-900" aria-label="Close create team"><X size={18} /></button>
    </div>
    <div className="space-y-6 px-6 py-6 sm:px-8 sm:py-7">
      {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}
      <label htmlFor="team-name" className="block text-sm font-semibold text-slate-800">Team name
        <input id="team-name" required minLength={1} maxLength={120} value={name} onChange={(event) => setName(event.target.value)} placeholder="e.g. Product crew" className="form-input mt-2.5" />
        <span className="mt-1.5 block text-xs font-normal text-slate-500">Choose a name your members will recognize.</span>
      </label>
      <div>
        <p className="mb-2 text-sm font-semibold text-slate-800">Who can find this team?</p>
        <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-slate-200 bg-slate-50/80 p-4 transition hover:border-emerald-300 hover:bg-emerald-50/50">
          <input type="checkbox" checked={isDiscoverable} onChange={(event) => setIsDiscoverable(event.target.checked)} className="mt-0.5 h-4 w-4 accent-emerald-600" />
          <span className="min-w-0 flex-1"><span className="block text-sm font-medium text-slate-800">Let workers discover this team</span><span className="mt-1 block text-xs leading-5 text-slate-500">Workers may request to join. You approve every request before they become members.</span></span>
          <ShieldCheck size={17} className="mt-0.5 shrink-0 text-emerald-700" />
        </label>
        <p className="mt-2 text-[11px] text-slate-500">{isDiscoverable ? "Your team will appear in worker search." : "Your team stays private and can be joined by invitation."}</p>
      </div>
    </div>
    <div className="flex flex-col-reverse gap-3 border-t border-slate-200 bg-slate-50/70 px-6 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-8">
      <p className="text-xs text-slate-500">You’ll be the team leader.</p>
      <div className="flex justify-end gap-2.5"><button type="button" onClick={onClose} className="btn-secondary">Cancel</button><button disabled={busy || !name.trim()} className="btn-primary inline-flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-60"><Plus size={15} />{busy ? "Creating…" : "Create team"}</button></div>
    </div>
  </form>;
}
