"use client";

import { useEffect, useState } from "react";
import { useVoiceBot } from '@/hooks/useVoiceBot';
import {
  CallButton,
  CallStatusDisplay,
  AudioVisualizer,
  MuteButton,
} from "@/components/voicebot";

export function VoiceBotInterface() {
  const { callState, audioLevel, startCall, endCall, toggleMute, transcript, response } = useVoiceBot();

  const [mounted, setMounted] = useState(false);

  // Prevent hydration mismatch
  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <VoiceBotSkeleton />;
  }

  const isConnected = callState.status === "connected";

  return (
    <div className="flex flex-col items-center justify-center gap-8 p-8">
      {/* Audio Visualizer */}
      <div className="relative">
        {/* Glow effect behind the button when active */}
        {isConnected && (
          <div className="absolute inset-0 -z-10 flex items-center justify-center">
            <div
              className="w-40 h-40 rounded-full bg-emerald-500/20 blur-3xl transition-opacity duration-500"
              style={{ opacity: 0.3 + audioLevel * 0.7 }}
            />
          </div>
        )}

        {/* Main call button with visualizer ring */}
        <div className="relative flex items-center justify-center">
          {/* Animated rings when connected */}
          <AnimatedRings isActive={isConnected} audioLevel={audioLevel} />

          {/* Call button */}
          <CallButton
            status={callState.status}
            onStart={startCall}
            onEnd={endCall}
          />
        </div>
      </div>

      {/* Status display */}
      <CallStatusDisplay
        status={callState.status}
        duration={callState.duration}
        error={callState.error}
      />

      {/* Audio level bars */}
      <AudioVisualizer audioLevel={audioLevel} isActive={isConnected} />

      {/* Mute button (only visible when connected) */}
      <div
        className={`transition-all duration-300 ${isConnected ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4 pointer-events-none"}`}
      >
        <MuteButton
          isMuted={callState.isMuted}
          onToggle={toggleMute}
          disabled={!isConnected}
        />
      </div>

      {/* Transcript and Response Display */}
      {(transcript || response) && (
        <div className="w-full max-w-2xl space-y-4 mt-8">
          {transcript && (
            <div className="p-4 rounded-lg bg-zinc-100 dark:bg-zinc-800">
              <p className="text-sm font-semibold text-zinc-600 dark:text-zinc-400 mb-1">
                You said:
              </p>
              <p className="text-base text-zinc-900 dark:text-zinc-100">
                {transcript}
              </p>
            </div>
          )}
          {response && (
            <div className="p-4 rounded-lg bg-emerald-100 dark:bg-emerald-900/20">
              <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-400 mb-1">
                Response:
              </p>
              <p className="text-base text-emerald-900 dark:text-emerald-100">
                {response}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface AnimatedRingsProps {
  isActive: boolean;
  audioLevel: number;
}

function AnimatedRings({ isActive, audioLevel }: AnimatedRingsProps) {
  const rings = [
    { size: "w-28 h-28", delay: "0ms" },
    { size: "w-36 h-36", delay: "150ms" },
    { size: "w-44 h-44", delay: "300ms" },
  ];

  return (
    <>
      {rings.map((ring, i) => (
        <div
          key={i}
          className={`
            absolute rounded-full border transition-all duration-300
            ${
              isActive
                ? "border-emerald-500/30 scale-100"
                : "border-zinc-200 dark:border-zinc-800 scale-90"
            }
            ${ring.size}
          `}
          style={{
            transitionDelay: ring.delay,
            transform: isActive
              ? `scale(${1 + audioLevel * 0.15})`
              : "scale(0.9)",
            opacity: isActive ? 0.5 - i * 0.15 : 0.3,
          }}
        />
      ))}
    </>
  );
}

function VoiceBotSkeleton() {
  return (
    <div className="flex flex-col items-center justify-center gap-8 p-8 animate-pulse">
      <div className="w-20 h-20 rounded-full bg-zinc-200 dark:bg-zinc-800" />
      <div className="flex flex-col items-center gap-2">
        <div className="w-32 h-6 rounded bg-zinc-200 dark:bg-zinc-800" />
        <div className="w-48 h-4 rounded bg-zinc-200 dark:bg-zinc-800" />
      </div>
      <div className="flex gap-1">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="w-1.5 h-8 rounded-full bg-zinc-200 dark:bg-zinc-800"
          />
        ))}
      </div>
    </div>
  );
}
