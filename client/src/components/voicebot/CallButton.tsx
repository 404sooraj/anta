"use client";

import { CallStatus } from "@/types/call";

interface CallButtonProps {
  status: CallStatus;
  onStart: () => void;
  onEnd: () => void;
  disabled?: boolean;
}

export function CallButton({
  status,
  onStart,
  onEnd,
  disabled,
}: CallButtonProps) {
  const isActive = status === "connected";
  const isLoading = status === "connecting" || status === "disconnecting";

  const handleClick = () => {
    if (isLoading || disabled) return;

    if (isActive) {
      onEnd();
    } else {
      onStart();
    }
  };

  return (
    <button
      onClick={handleClick}
      disabled={isLoading || disabled}
      aria-label={isActive ? "End call" : "Start call"}
      className={`
        group relative flex items-center justify-center
        w-20 h-20 rounded-full
        transition-all duration-300 ease-out
        focus:outline-none focus-visible:ring-4 focus-visible:ring-offset-2
        disabled:cursor-not-allowed disabled:opacity-60
        ${
          isActive
            ? "bg-red-500 hover:bg-red-600 focus-visible:ring-red-400 shadow-lg shadow-red-500/30"
            : "bg-emerald-500 hover:bg-emerald-600 focus-visible:ring-emerald-400 shadow-lg shadow-emerald-500/30"
        }
        ${isLoading ? "animate-pulse" : ""}
        hover:scale-105 active:scale-95
      `}
    >
      {/* Pulse ring animation when connected */}
      {isActive && (
        <>
          <span className="absolute inset-0 rounded-full bg-red-500 animate-ping opacity-20" />
          <span className="absolute inset-0 rounded-full bg-red-400 animate-pulse opacity-10" />
        </>
      )}

      {/* Icon */}
      <span className="relative z-10">
        {isLoading ? (
          <LoadingSpinner />
        ) : isActive ? (
          <HangupIcon />
        ) : (
          <PhoneIcon />
        )}
      </span>
    </button>
  );
}

function PhoneIcon() {
  return (
    <svg
      className="w-8 h-8 text-white"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
      />
    </svg>
  );
}

function HangupIcon() {
  return (
    <svg
      className="w-8 h-8 text-white"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M16 8l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2M5 3a2 2 0 00-2 2v1c0 8.284 6.716 15 15 15h1a2 2 0 002-2v-3.28a1 1 0 00-.684-.948l-4.493-1.498a1 1 0 00-1.21.502l-1.13 2.257a11.042 11.042 0 01-5.516-5.517l2.257-1.128a1 1 0 00.502-1.21L9.228 3.683A1 1 0 008.279 3H5z"
      />
    </svg>
  );
}

function LoadingSpinner() {
  return (
    <svg
      className="w-8 h-8 text-white animate-spin"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}
