import { Shield, BarChart3, FileCheck } from "lucide-react";

export function LoginSidePanel() {
  return (
    <div className="relative h-full min-h-[280px] overflow-hidden rounded-2xl bg-zinc-900/95 border border-zinc-800 text-white">
      <div
        className="absolute inset-0 opacity-40"
        style={{
          background:
            "radial-gradient(ellipse 80% 50% at 20% 20%, rgba(16,185,129,0.25), transparent 50%), radial-gradient(ellipse 60% 40% at 80% 80%, rgba(139,92,246,0.2), transparent 50%)",
        }}
      />
      <div className="relative z-10 flex h-full flex-col justify-between p-8">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-[0.25em] text-zinc-400">
            Operator Console
          </p>
          <h2 className="mt-5 text-xl font-semibold leading-snug text-zinc-100 sm:text-2xl">
            Sign in to manage voice AI workflows and live battery swaps.
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-zinc-400">
            Monitor active sessions, review intent logs, and coordinate field
            support from a single dashboard.
          </p>
        </div>

        <ul className="mt-8 space-y-3.5 rounded-xl border border-zinc-800 bg-zinc-800/40 p-4 backdrop-blur-sm">
          <li className="flex items-center gap-3 text-sm text-zinc-300">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-emerald-500/20 text-emerald-400">
              <Shield className="h-4 w-4" />
            </span>
            Secure access with role-based controls
          </li>
          <li className="flex items-center gap-3 text-sm text-zinc-300">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-emerald-500/20 text-emerald-400">
              <BarChart3 className="h-4 w-4" />
            </span>
            Real-time monitoring and analytics
          </li>
          <li className="flex items-center gap-3 text-sm text-zinc-300">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-emerald-500/20 text-emerald-400">
              <FileCheck className="h-4 w-4" />
            </span>
            Built-in operational audit trails
          </li>
        </ul>
      </div>
    </div>
  );
}
