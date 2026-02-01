import Link from "next/link";

export default function PartnersLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="min-h-screen flex flex-col bg-zinc-950">
      <nav className="w-full border-b border-zinc-800 bg-zinc-950/90 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link
              href="/user"
              className="flex items-center gap-2.5 text-white font-semibold"
            >
              <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: "#B19EEF" }}>
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
                    d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                  />
                </svg>
              </div>
              Antaryami
            </Link>
            <Link
              href="/user"
              className="text-sm font-medium text-zinc-400 hover:text-white"
            >
              Voice Assistant
            </Link>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-[#B19EEF]/20 text-[#B19EEF]">
              Partner
            </span>
            <Link
              href="/login"
              className="text-sm font-medium text-zinc-400 hover:text-white"
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
