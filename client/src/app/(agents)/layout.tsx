import Link from "next/link";

export default function AgentsLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="min-h-screen flex flex-col bg-zinc-50 dark:bg-zinc-950">
      <nav className="w-full border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/95 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link
              href="/agent"
              className="flex items-center gap-2.5 text-zinc-900 dark:text-zinc-100 font-semibold"
            >
              <div className="w-8 h-8 rounded-lg bg-linear-to-br from-violet-500 to-purple-600 flex items-center justify-center">
                <svg
                  className="w-5 h-5 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                  />
                </svg>
              </div>
              Antaryami Agent
            </Link>
            <Link
              href="/agent"
              className="text-sm font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100"
            >
              Agent Console
            </Link>
            <Link
              href="/ps2-analysis-results"
              className="text-sm font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100"
            >
              PS2 Analysis Results
            </Link>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-400">
              Agent
            </span>
            <Link
              href="/login"
              className="text-sm font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100"
            >
              Sign out
            </Link>
          </div>
        </div>
      </nav>
      {children}
    </div>
  );
}
