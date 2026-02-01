import Link from "next/link";

export default function AuthLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="min-h-screen flex flex-col bg-zinc-950">
      <nav className="w-full border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-sm">
        <div className="max-w-5xl mx-auto px-6 py-3 flex items-center justify-between">
          <Link
            href="/login"
            className="text-lg font-semibold text-zinc-100"
          >
            Antaryami
          </Link>
          <div className="flex items-center gap-4">
            <Link
              href="/user"
              className="text-sm font-medium text-zinc-400 hover:text-zinc-100"
            >
              Partner
            </Link>
            <Link
              href="/agent"
              className="text-sm font-medium text-zinc-400 hover:text-zinc-100"
            >
              Agent
            </Link>
          </div>
        </div>
      </nav>
      {children}
    </div>
  );
}
