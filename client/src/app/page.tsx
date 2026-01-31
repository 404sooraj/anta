import { VoiceBotInterface } from "@/components/voicebot";

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-b from-zinc-50 to-white dark:from-zinc-950 dark:to-zinc-900">
      {/* Header */}
      <header className="w-full border-b border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-950/80 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
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
            <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
              Antaryami
            </h1>
          </div>
          <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">
            Prototype
          </span>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center px-6">
        <div className="w-full max-w-md">
          {/* Card Container */}
          <div className="bg-white dark:bg-zinc-900 rounded-3xl shadow-xl shadow-zinc-200/50 dark:shadow-none border border-zinc-200 dark:border-zinc-800 overflow-hidden">
            {/* Card Header */}
            <div className="px-8 pt-8 pb-4 text-center">
              <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100 mb-2">
                Voice Assistant
              </h2>
              <p className="text-sm text-zinc-500 dark:text-zinc-400">
                AI-powered customer support at your service
              </p>
            </div>

            {/* Voice Bot Interface */}
            <VoiceBotInterface />

            {/* Card Footer */}
            <div className="px-8 pb-8 pt-4">
              <div className="flex items-center justify-center gap-2 text-xs text-zinc-400 dark:text-zinc-500">
                <span className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  Powered by AI
                </span>
                <span>•</span>
                <span>Secure connection</span>
              </div>
            </div>
          </div>

          {/* Info text below card */}
          <p className="text-center text-xs text-zinc-400 dark:text-zinc-500 mt-6 px-4">
            This prototype uses WebRTC for real-time audio streaming.
            <br />
            Your voice data is processed securely.
          </p>
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full border-t border-zinc-200 dark:border-zinc-800 py-4">
        <div className="max-w-4xl mx-auto px-6 flex items-center justify-center">
          <p className="text-xs text-zinc-400 dark:text-zinc-500">
            Built for Hackathon 2026
          </p>
        </div>
      </footer>
    </div>
  );
}