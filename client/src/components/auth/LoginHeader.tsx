import Link from "next/link";

export function LoginHeader() {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
       
        <div>
          <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
            Antaryami
          </p>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            BatterySmart Assistant
          </p>
        </div>
      </div>
      <Link
        href="/"
        className="text-xs font-medium text-emerald-600 hover:text-emerald-700 dark:text-emerald-400"
      >
        Back to Home
      </Link>
    </div>
  );
}
