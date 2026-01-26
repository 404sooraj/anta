"use client";

interface MuteButtonProps {
  isMuted: boolean;
  onToggle: () => void;
  disabled?: boolean;
}

export function MuteButton({ isMuted, onToggle, disabled }: MuteButtonProps) {
  return (
    <button
      onClick={onToggle}
      disabled={disabled}
      aria-label={isMuted ? "Unmute microphone" : "Mute microphone"}
      className={`
        flex items-center justify-center
        w-12 h-12 rounded-full
        transition-all duration-200 ease-out
        focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2
        disabled:cursor-not-allowed disabled:opacity-40
        ${
          isMuted
            ? "bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50 focus-visible:ring-red-400"
            : "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700 focus-visible:ring-zinc-400"
        }
      `}
    >
      {isMuted ? <MicOffIcon /> : <MicOnIcon />}
    </button>
  );
}

function MicOnIcon() {
  return (
    <svg
      className="w-5 h-5"
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
  );
}

function MicOffIcon() {
  return (
    <svg
      className="w-5 h-5"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2"
      />
    </svg>
  );
}
