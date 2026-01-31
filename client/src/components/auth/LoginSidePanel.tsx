export function LoginSidePanel() {
  return (
    <div className=" h-full overflow-hidden rounded-3xl bg-zinc-900 text-white">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(16,185,129,0.3),transparent_60%)]" />
      <div className="relative z-10 flex h-full flex-col justify-between p-8">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-emerald-200/80">
            Operator Console
          </p>
          <h2 className="mt-4 text-2xl font-semibold leading-tight">
            Sign in to manage voice AI workflows and live battery swaps.
          </h2>
          <p className="mt-4 text-sm text-emerald-100/80">
            Monitor active sessions, review intent logs, and coordinate field
            support from a single dashboard.
          </p>
        </div>

        <div className="space-y-4 rounded-2xl bg-white/10 p-4 text-xs text-emerald-100/90">
          <div className="flex items-center gap-3">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            Secure access with role-based controls
          </div>
          <div className="flex items-center gap-3">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            Real-time monitoring and analytics
          </div>
          <div className="flex items-center gap-3">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            Built-in operational audit trails
          </div>
        </div>
      </div>
    </div>
  );
}
