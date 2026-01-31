import { RequireAuth } from "@/components/auth/RequireAuth";
import { VoiceBotInterface } from "@/components/voicebot";

export default function PartnersHome() {
  return (
    <RequireAuth>
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-12">
        <div className="w-full max-w-md mx-auto text-center">
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Voice Assistant
          </h1>
          <p className="mt-2 text-sm text-zinc-400">
            AI-powered customer support at your service.
          </p>

          {/* Card Container — matches login form panel */}
          <div className="mt-8 rounded-2xl border border-zinc-800 bg-zinc-900/80 overflow-hidden">
            <VoiceBotInterface />

            {/* Card Footer */}
            <div className="px-6 pb-6 pt-4">
              <div className="flex items-center justify-center gap-2 text-xs text-zinc-400">
                <span className="flex items-center gap-1.5">
                  <span
                    className="w-1.5 h-1.5 rounded-full animate-pulse"
                    style={{ backgroundColor: "#B19EEF" }}
                  />
                  Powered by AI
                </span>
                <span>·</span>
                <span>Secure connection</span>
              </div>
            </div>
          </div>

          {/* Info text below card */}
          <p className="mt-6 text-xs text-zinc-500 px-4">
            This prototype uses WebRTC for real-time audio streaming.
            <br />
            Your voice data is processed securely.
          </p>
        </div>
      </main>
      <footer className="w-full border-t border-zinc-800 py-4 mt-auto">
        <div className="max-w-4xl mx-auto px-6 flex items-center justify-center">
          <p className="text-xs text-zinc-500">Built for Hackathon 2026</p>
        </div>
      </footer>
    </RequireAuth>
  );
}
