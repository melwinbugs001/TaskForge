import { useState, type FormEvent } from "react";
import { X } from "lucide-react";
import { getApiError } from "../api/client";
import type { GoalInput } from "../types/api";

interface GoalFormProps {
  initial?: GoalInput;
  submitLabel: string;
  onSubmit: (input: GoalInput) => Promise<void>;
  onClose?: () => void;
}

export function GoalForm({ initial, submitLabel, onSubmit, onClose }: GoalFormProps) {
  const [title, setTitle] = useState(initial?.title ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [dueAt, setDueAt] = useState(toLocalDateTime(initial?.due_at));
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await onSubmit({
        title: title.trim(),
        description: description.trim(),
        due_at: dueAt ? new Date(dueAt).toISOString() : null,
      });
    } catch (reason) {
      setError(getApiError(reason));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {onClose && <div className="flex items-center justify-between"><div><h2 id="create-goal-title" className="font-display text-xl font-semibold text-white">Create a goal</h2><p className="mt-1 text-sm text-slate-500">Start with the outcome you want to achieve.</p></div><button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-500 hover:bg-white/5 hover:text-white" aria-label="Close"><X size={18} /></button></div>}
      {!onClose && <div><h2 className="font-display text-xl font-semibold text-white">Edit goal</h2><p className="mt-1 text-sm text-slate-500">Update your goal details.</p></div>}
      {error && <div role="alert" className="rounded-xl border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">{error}</div>}
      <label className="block text-sm font-medium text-slate-300">
        Goal title
        <input required minLength={1} maxLength={200} value={title} onChange={(event) => setTitle(event.target.value)} placeholder="e.g. Compare open-source AI frameworks" className="form-input mt-2" />
      </label>
      <label className="block text-sm font-medium text-slate-300">
        What would you like to accomplish?
        <textarea required minLength={1} maxLength={20_000} rows={5} value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Describe the result you're looking for. You can add criteria, context, or constraints." className="form-input mt-2 resize-y" />
        <span className="mt-1 block text-right text-[11px] font-normal text-slate-600">{description.length.toLocaleString()} / 20,000</span>
      </label>
      <label className="block text-sm font-medium text-slate-300">
        Due date <span className="font-normal text-slate-500">· optional</span>
        <input type="datetime-local" min={toLocalDateTime(new Date().toISOString())} value={dueAt} onChange={(event) => setDueAt(event.target.value)} className="form-input mt-2" />
        <span className="mt-1 block text-xs font-normal leading-5 text-slate-500">Unfinished goals will be marked failed after this deadline.</span>
      </label>
      <div className="rounded-xl border border-forge-400/10 bg-forge-500/[0.06] p-3 text-xs leading-5 text-slate-400">
        Your goal will be saved as a draft. Saving it will not start execution.
      </div>
      <div className="flex justify-end gap-3">
        {onClose && <button type="button" onClick={onClose} className="btn-secondary">Cancel</button>}
        <button disabled={isSubmitting} className="btn-primary disabled:cursor-wait disabled:opacity-60">{isSubmitting ? "Saving…" : submitLabel}</button>
      </div>
    </form>
  );
}

function toLocalDateTime(value: string | null | undefined): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}
