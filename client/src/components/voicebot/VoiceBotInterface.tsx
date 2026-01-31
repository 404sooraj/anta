"use client";

import { useEffect, useState } from "react";
import { useVoiceBot } from "@/hooks/useVoiceBot";
import {
  CallButton,
  CallStatusDisplay,
  AudioVisualizer,
  MuteButton,
} from "@/components/voicebot";

export function VoiceBotInterface() {
  const [authToken, setAuthToken] = useState<string | undefined>(undefined);
  const [authUserId, setAuthUserId] = useState<string | undefined>(undefined);

  // Load auth from localStorage on mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("auth_token") || undefined;
      const userId = localStorage.getItem("user_id") || undefined;
      setAuthToken(token);
      setAuthUserId(userId);
    }
  }, []);

  const {
    callState,
    audioLevel,
    startCall,
    endCall,
    toggleMute,
    transcript,
    partialTranscript,
    response,
    streamingResponse,
    conversationHistory,
    handoffStatus,
  } = useVoiceBot({
    token: authToken,
    userId: authUserId,
  });

  const [mounted, setMounted] = useState(false);
  const [userName, setUserName] = useState<string | null>(null);

  // Prevent hydration mismatch
  useEffect(() => {
    setMounted(true);
  }, []);

  // Load user name from localStorage
  useEffect(() => {
    if (typeof window !== "undefined") {
      const name = localStorage.getItem("user_name");
      setUserName(name);
    }
  }, [authUserId]);

  if (!mounted) {
    return <VoiceBotSkeleton />;
  }

  const isConnected = callState.status === "connected";
  const isLoggedIn = !!authToken && !!authUserId;

  return (
    <div className="flex flex-col items-center justify-center gap-8 p-8">
      {/* Auth status indicator */}
      <div className="text-center">
        {isLoggedIn ? (
          <div className="flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span>
              Logged in as <strong>{userName || authUserId}</strong>
            </span>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <div className="flex items-center gap-2 text-sm text-amber-600 dark:text-amber-400">
              <span className="w-2 h-2 rounded-full bg-amber-500"></span>
              <span>
                Not logged in - Tool calls won&apos;t have user context
              </span>
            </div>
            <a
              href="/login"
              className="text-xs text-emerald-600 hover:underline"
            >
              Login to enable personalized responses
            </a>
          </div>
        )}
      </div>

      {/* Handoff Status Indicator */}
      {handoffStatus !== "none" && (
        <div
          className={`px-4 py-2 rounded-lg text-center ${
            handoffStatus === "queued"
              ? "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300"
              : "bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300"
          }`}
        >
          <div className="flex items-center justify-center gap-2">
            <span
              className={`w-2 h-2 rounded-full animate-pulse ${
                handoffStatus === "queued" ? "bg-amber-500" : "bg-purple-500"
              }`}
            />
            <span className="text-sm font-medium">
              {handoffStatus === "queued"
                ? "📞 Waiting for agent..."
                : "🎧 Connected to human agent"}
            </span>
          </div>
        </div>
      )}

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
      {(transcript ||
        partialTranscript ||
        response ||
        streamingResponse ||
        conversationHistory.length > 0) && (
        <div className="w-full max-w-2xl space-y-4 mt-8">
          {/* Current Transcript */}
          {(transcript || partialTranscript) && (
            <div className="p-4 rounded-lg bg-zinc-100 dark:bg-zinc-800">
              <p className="text-sm font-semibold text-zinc-600 dark:text-zinc-400 mb-1">
                You said:
              </p>
              <p className="text-base text-zinc-900 dark:text-zinc-100">
                {(() => {
                  // Concatenate all consecutive user messages from the end of conversation history
                  // that haven't been responded to yet
                  const userMessages: string[] = [];
                  for (let i = conversationHistory.length - 1; i >= 0; i--) {
                    if (conversationHistory[i].role === "user") {
                      userMessages.unshift(conversationHistory[i].text);
                    } else {
                      break; // Stop at the last agent message
                    }
                  }

                  // If we have user messages from history, concatenate them
                  // Otherwise show current transcript or partial
                  return userMessages.length > 0
                    ? userMessages.join(" ")
                    : transcript || partialTranscript;
                })()}
                {partialTranscript && !transcript && (
                  <span className="inline-block ml-1 w-1 h-4 bg-zinc-400 animate-pulse" />
                )}
              </p>
            </div>
          )}

          {/* Streaming or Final Response */}
          {(response || streamingResponse) && (
            <div className="p-4 rounded-lg bg-emerald-100 dark:bg-emerald-900/20">
              <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-400 mb-1">
                Response:
              </p>
              <p className="text-base text-emerald-900 dark:text-emerald-100">
                {response || streamingResponse}
                {streamingResponse && !response && (
                  <span className="inline-block ml-1 w-1 h-4 bg-emerald-500 animate-pulse" />
                )}
              </p>
            </div>
          )}

          {/* Conversation History */}
          {conversationHistory.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-semibold text-zinc-600 dark:text-zinc-400">
                Conversation History:
              </p>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {conversationHistory.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`p-3 rounded-lg text-sm ${
                      msg.role === "user"
                        ? "bg-zinc-50 dark:bg-zinc-900 text-zinc-800 dark:text-zinc-200"
                        : "bg-emerald-50 dark:bg-emerald-900/10 text-emerald-800 dark:text-emerald-200"
                    }`}
                  >
                    <span className="font-semibold">
                      {msg.role === "user" ? "You" : "Agent"}:
                    </span>{" "}
                    {msg.text}
                  </div>
                ))}
              </div>
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
