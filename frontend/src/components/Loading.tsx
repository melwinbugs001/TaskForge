export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex min-h-[45vh] flex-col items-center justify-center gap-4 text-slate-400">
      <span className="h-8 w-8 animate-spin rounded-full border-2 border-forge-500 border-t-transparent" />
      <span className="text-sm">{label}</span>
    </div>
  );
}
