"use client";

import { CallStatus } from "@/types/call";

interface CallStatusDisplayProps {
  status: CallStatus;
  duration: number;
  error: string | null;
}

export function CallStatusDisplay({
  status,
  duration,
  error,
}: CallStatusDisplayProps) {
  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const getStatusInfo = (): {
    text: string;
    color: string;
    subtext?: string;
  } => {
    switch (status) {
      case "idle":
        return {
          text: "Ready to connect",
          color: "text-zinc-500 dark:text-zinc-400",
          subtext: "Click the button to start a call",
        };
      case "connecting":
        return {
          text: "Connecting...",
          color: "text-amber-500",
          subtext: "Setting up your microphone",
        };
      case "connected":
        return {
          text: formatDuration(duration),
          color: "text-[#B19EEF]",
          subtext: "Connected • Speak now",
        };
      case "disconnecting":
        return {
          text: "Ending call...",
          color: "text-amber-500",
        };
      case "error":
        return {
          text: "Connection failed",
          color: "text-red-500",
          subtext: error || "Please try again",
        };
      default:
        return { text: "", color: "" };
    }
  };

  const { text, color, subtext } = getStatusInfo();

  return (
    <div className="flex flex-col items-center gap-2 min-h-[60px]">
      <p
        className={`text-2xl font-semibold tracking-tight transition-colors duration-300 ${color}`}
      >
        {text}
      </p>
      {subtext && (
        <p className="text-sm text-zinc-500 dark:text-zinc-400 animate-fade-in">
          {subtext}
        </p>
      )}
    </div>
  );
}
