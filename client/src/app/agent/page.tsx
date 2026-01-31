"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { RequireAuth } from "@/components/auth/RequireAuth";

// Types
interface PendingCall {
  session_id: string;
  user_id: string;
  reason: string;
  requested_at: string;
  wait_time_seconds: number;
}

interface ConversationMessage {
  role: "user" | "assistant";
  text: string;
}

interface CallInfo {
  session_id: string;
  user_id: string;
  reason: string;
  conversation_history: ConversationMessage[];
  wait_time_seconds: number;
}

// Message types from server
type ServerMessage =
  | {
      type: "queue_status";
      pending_calls: PendingCall[];
      total_pending: number;
    }
  | {
      type: "new_pending_call";
      session_id: string;
      user_id: string;
      reason: string;
      requested_at: string;
      queue_position: number;
    }
  | {
      type: "call_accepted";
      session_id: string;
      user_id: string;
      reason: string;
      conversation_history: ConversationMessage[];
      wait_time_seconds: number;
    }
  | { type: "call_ended"; session_id: string; ended_by: string }
  | { type: "call_accepted_by_other"; session_id: string }
  | { type: "call_cancelled"; session_id: string }
  | { type: "user_message"; text: string }
  | { type: "user_transcript"; text: string; language: string }
  | { type: "pong" }
  | { type: "error"; message: string };

// Audio configuration - match user's audio settings
const INPUT_SAMPLE_RATE = 16000;
const OUTPUT_SAMPLE_RATE = 44100;

export default function AgentPage() {
  const [agentId, setAgentId] = useState<string>("");
  const [isConnected, setIsConnected] = useState(false);
  const [pendingCalls, setPendingCalls] = useState<PendingCall[]>([]);
  const [activeCall, setActiveCall] = useState<CallInfo | null>(null);
  const [conversationHistory, setConversationHistory] = useState<
    ConversationMessage[]
  >([]);
  const [messageInput, setMessageInput] = useState("");
  const [status, setStatus] = useState<string>("Disconnected");
  const [isMuted, setIsMuted] = useState(false);
  const [userTranscript, setUserTranscript] = useState<string>("");
  const [audioLevel, setAudioLevel] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Audio refs
  const localStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const outputAudioContextRef = useRef<AudioContext | null>(null);
  const audioQueueRef = useRef<Float32Array[]>([]);
  const isPlayingRef = useRef(false);
  const animationFrameRef = useRef<number | null>(null);

  // Downsample audio for sending to server (browser rate -> 16kHz)
  const downsample = (
    input: Float32Array,
    fromRate: number,
    toRate: number,
  ): Float32Array => {
    if (fromRate === toRate) return input;
    const ratio = fromRate / toRate;
    const outLength = Math.round(input.length / ratio);
    const result = new Float32Array(outLength);
    for (let i = 0; i < outLength; i++) {
      const srcIndex = i * ratio;
      const idx0 = Math.floor(srcIndex);
      const idx1 = Math.min(idx0 + 1, input.length - 1);
      const frac = srcIndex - idx0;
      result[i] = input[idx0] * (1 - frac) + input[idx1] * frac;
    }
    return result;
  };

  // Convert Float32 to Int16 PCM for sending
  const floatTo16BitPCM = (input: Float32Array): ArrayBuffer => {
    const buffer = new ArrayBuffer(input.length * 2);
    const view = new DataView(buffer);
    for (let i = 0; i < input.length; i++) {
      const s = Math.max(-1, Math.min(1, input[i]));
      view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }
    return buffer;
  };

  // Play audio queue from user
  const playAudioQueue = useCallback(async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) return;

    isPlayingRef.current = true;

    while (audioQueueRef.current.length > 0) {
      const audioData = audioQueueRef.current.shift()!;

      if (!outputAudioContextRef.current) {
        outputAudioContextRef.current = new AudioContext({
          sampleRate: OUTPUT_SAMPLE_RATE,
        });
      }

      const ctx = outputAudioContextRef.current;
      const buffer = ctx.createBuffer(1, audioData.length, OUTPUT_SAMPLE_RATE);
      // Create a new Float32Array with a regular ArrayBuffer
      const channelData = new Float32Array(audioData.length);
      channelData.set(audioData);
      buffer.copyToChannel(channelData, 0);

      const source = ctx.createBufferSource();
      source.buffer = buffer;
      source.connect(ctx.destination);

      await new Promise<void>((resolve) => {
        source.onended = () => resolve();
        source.start();
      });
    }

    isPlayingRef.current = false;
  }, []);

  // Stop audio capture
  const stopAudioCapture = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }

    if (audioProcessorRef.current) {
      audioProcessorRef.current.disconnect();
      audioProcessorRef.current = null;
    }

    if (analyserRef.current) {
      analyserRef.current.disconnect();
      analyserRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach((track) => track.stop());
      localStreamRef.current = null;
    }

    if (outputAudioContextRef.current) {
      outputAudioContextRef.current.close();
      outputAudioContextRef.current = null;
    }

    audioQueueRef.current = [];
    isPlayingRef.current = false;
    setAudioLevel(0);

    console.log("🔇 Microphone capture stopped");
  }, []);

  // Start audio capture and processing when call is accepted
  const startAudioCapture = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: INPUT_SAMPLE_RATE,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      localStreamRef.current = stream;

      // Create audio context for processing
      const audioContext = new AudioContext({ sampleRate: INPUT_SAMPLE_RATE });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);

      // Create analyser for audio level visualization
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      analyserRef.current = analyser;
      source.connect(analyser);

      // Create processor for streaming audio to server
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      audioProcessorRef.current = processor;

      processor.onaudioprocess = (e) => {
        if (
          !wsRef.current ||
          wsRef.current.readyState !== WebSocket.OPEN ||
          isMuted
        ) {
          return;
        }

        const inputData = e.inputBuffer.getChannelData(0);
        const nativeSampleRate = audioContext.sampleRate;

        // Downsample to 16kHz if needed
        const downsampled = downsample(
          inputData,
          nativeSampleRate,
          INPUT_SAMPLE_RATE,
        );
        const pcmData = floatTo16BitPCM(downsampled);

        // Send audio to server
        wsRef.current.send(pcmData);
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      // Start audio level animation
      const updateLevel = () => {
        if (analyserRef.current) {
          const dataArray = new Uint8Array(
            analyserRef.current.frequencyBinCount,
          );
          analyserRef.current.getByteFrequencyData(dataArray);
          const avg = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
          setAudioLevel(avg / 255);
        }
        animationFrameRef.current = requestAnimationFrame(updateLevel);
      };
      updateLevel();

      console.log("🎤 Microphone capture started");
    } catch (err) {
      console.error("Failed to start audio capture:", err);
      alert("Failed to access microphone. Please grant permission.");
    }
  }, [isMuted]);

  // Handle messages from server
  const handleServerMessage = useCallback(
    (message: ServerMessage) => {
      console.log("📩 Server message:", message);

      switch (message.type) {
        case "queue_status":
          setPendingCalls(message.pending_calls);
          break;

        case "new_pending_call":
          setPendingCalls((prev) => [
            ...prev.filter((c) => c.session_id !== message.session_id),
            {
              session_id: message.session_id,
              user_id: message.user_id,
              reason: message.reason,
              requested_at: message.requested_at,
              wait_time_seconds: 0,
            },
          ]);
          // Play notification sound
          try {
            new Audio("/notification.mp3").play().catch(() => {});
          } catch {}
          break;

        case "call_accepted":
          setActiveCall({
            session_id: message.session_id,
            user_id: message.user_id,
            reason: message.reason,
            conversation_history: message.conversation_history,
            wait_time_seconds: message.wait_time_seconds,
          });
          setConversationHistory(message.conversation_history);
          setStatus(`🎧 In voice call with ${message.user_id}`);
          setUserTranscript("");
          // Remove from pending
          setPendingCalls((prev) =>
            prev.filter((c) => c.session_id !== message.session_id),
          );
          // Start microphone capture for voice call
          startAudioCapture();
          break;

        case "call_ended":
          setActiveCall(null);
          setConversationHistory([]);
          setStatus("Connected - Waiting for calls");
          setUserTranscript("");
          stopAudioCapture();
          break;

        case "call_accepted_by_other":
        case "call_cancelled":
          setPendingCalls((prev) =>
            prev.filter((c) => c.session_id !== message.session_id),
          );
          break;

        case "user_message":
          setConversationHistory((prev) => [
            ...prev,
            { role: "user", text: message.text },
          ]);
          break;

        case "user_transcript":
          // Real-time transcript of what user is saying
          setUserTranscript(message.text);
          break;

        case "error":
          alert(`Error: ${message.message}`);
          break;

        case "pong":
          // Ping-pong response, ignore
          break;
      }
    },
    [startAudioCapture, stopAudioCapture],
  );

  // Connect to agent WebSocket
  const connect = useCallback(() => {
    if (!agentId.trim()) {
      alert("Please enter an Agent ID");
      return;
    }

    const backendUrl =
      process.env.NEXT_PUBLIC_BACKEND_URL || "ws://localhost:8000";
    const wsUrl = `${backendUrl.replace("http", "ws")}/agent/ws/connect?agent_id=${encodeURIComponent(agentId)}`;

    console.log(`🔌 Connecting to: ${wsUrl}`);
    setStatus("Connecting...");

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("✅ Agent WebSocket connected");
      setIsConnected(true);
      setStatus("Connected - Waiting for calls");

      // Start ping interval
      pingIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, 30000);
    };

    ws.onmessage = async (event) => {
      // Handle binary audio data from user
      if (event.data instanceof Blob) {
        const arrayBuffer = await event.data.arrayBuffer();
        const audioData = new Float32Array(arrayBuffer);
        audioQueueRef.current.push(audioData);
        playAudioQueue();
      }
      // Handle JSON messages
      else if (typeof event.data === "string") {
        try {
          const message: ServerMessage = JSON.parse(event.data);
          handleServerMessage(message);
        } catch (e) {
          console.error("Failed to parse message:", e);
        }
      }
    };

    ws.onclose = (event) => {
      console.log(`✋ Agent WebSocket closed: ${event.code} ${event.reason}`);
      setIsConnected(false);
      setStatus("Disconnected");
      setActiveCall(null);
      stopAudioCapture();

      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }
    };

    ws.onerror = (error) => {
      console.error("❌ Agent WebSocket error:", error);
      setStatus("Connection error");
    };

    wsRef.current = ws;
  }, [agentId, playAudioQueue, stopAudioCapture, handleServerMessage]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    stopAudioCapture();
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, [stopAudioCapture]);

  // Accept a pending call
  const acceptCall = (sessionId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "accept_call",
          session_id: sessionId,
        }),
      );
    }
  };

  // End current call
  const endCall = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN && activeCall) {
      wsRef.current.send(
        JSON.stringify({
          type: "end_call",
          session_id: activeCall.session_id,
        }),
      );
      stopAudioCapture();
    }
  };

  // Toggle mute
  const toggleMute = () => {
    setIsMuted((prev) => !prev);
    if (localStreamRef.current) {
      localStreamRef.current.getAudioTracks().forEach((track) => {
        track.enabled = isMuted; // Toggle to opposite
      });
    }
  };

  // Send text message to user
  const sendMessage = () => {
    if (
      wsRef.current?.readyState === WebSocket.OPEN &&
      activeCall &&
      messageInput.trim()
    ) {
      wsRef.current.send(
        JSON.stringify({
          type: "message",
          session_id: activeCall.session_id,
          text: messageInput,
        }),
      );
      setConversationHistory((prev) => [
        ...prev,
        { role: "assistant", text: messageInput },
      ]);
      setMessageInput("");
    }
  };

  // Format wait time
  const formatWaitTime = (seconds: number): string => {
    if (seconds < 60) return `${Math.floor(seconds)}s`;
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}m ${secs}s`;
  };

  // Update wait times every second
  useEffect(() => {
    const interval = setInterval(() => {
      setPendingCalls((prev) =>
        prev.map((call) => ({
          ...call,
          wait_time_seconds: call.wait_time_seconds + 1,
        })),
      );
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return (
    <RequireAuth>
      <div className="min-h-screen bg-gray-100 p-6">
        <div className="max-w-6xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-800 mb-6">
          📞 Call Center Agent Dashboard
        </h1>

        {/* Connection Panel */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Agent ID
              </label>
              <input
                type="text"
                value={agentId}
                onChange={(e) => setAgentId(e.target.value)}
                placeholder="Enter your agent ID"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isConnected}
              />
            </div>
            <div className="pt-6">
              {!isConnected ? (
                <button
                  onClick={connect}
                  className="px-6 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 transition"
                >
                  Connect
                </button>
              ) : (
                <button
                  onClick={disconnect}
                  className="px-6 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 transition"
                >
                  Disconnect
                </button>
              )}
            </div>
          </div>
          <div className="mt-2 flex items-center gap-2">
            <span
              className={`w-3 h-3 rounded-full ${
                isConnected ? "bg-green-500" : "bg-gray-400"
              }`}
            />
            <span className="text-sm text-gray-600">{status}</span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Pending Calls Queue */}
          <div className="bg-white rounded-lg shadow p-4">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">
              📋 Pending Calls ({pendingCalls.length})
            </h2>
            {pendingCalls.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No calls waiting</p>
            ) : (
              <div className="space-y-3">
                {pendingCalls.map((call) => (
                  <div
                    key={call.session_id}
                    className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-medium text-gray-800">
                          User: {call.user_id}
                        </p>
                        <p className="text-sm text-gray-600 mt-1">
                          Reason: {call.reason}
                        </p>
                        <p className="text-sm text-orange-600 mt-1">
                          ⏱️ Waiting: {formatWaitTime(call.wait_time_seconds)}
                        </p>
                      </div>
                      <button
                        onClick={() => acceptCall(call.session_id)}
                        disabled={!!activeCall}
                        className={`px-4 py-2 rounded-md text-white ${
                          activeCall
                            ? "bg-gray-400 cursor-not-allowed"
                            : "bg-blue-500 hover:bg-blue-600"
                        }`}
                      >
                        Accept
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Active Call Panel */}
          <div className="bg-white rounded-lg shadow p-4">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">
              🎧 Active Voice Call
            </h2>
            {!activeCall ? (
              <p className="text-gray-500 text-center py-8">No active call</p>
            ) : (
              <div>
                {/* Call Info & Controls */}
                <div className="bg-blue-50 rounded-lg p-4 mb-4">
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="font-medium text-gray-800">
                        🔊 Connected to: {activeCall.user_id}
                      </p>
                      <p className="text-sm text-gray-600">
                        Reason: {activeCall.reason}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {/* Audio Level Indicator */}
                      <div className="flex items-center gap-1">
                        <span className="text-xs text-gray-500">Mic:</span>
                        <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-green-500 transition-all duration-75"
                            style={{ width: `${audioLevel * 100}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Call Controls */}
                  <div className="flex gap-2 mt-3">
                    <button
                      onClick={toggleMute}
                      className={`px-4 py-2 rounded-md text-white ${
                        isMuted
                          ? "bg-yellow-500 hover:bg-yellow-600"
                          : "bg-gray-500 hover:bg-gray-600"
                      }`}
                    >
                      {isMuted ? "🔇 Unmute" : "🎤 Mute"}
                    </button>
                    <button
                      onClick={endCall}
                      className="px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 transition"
                    >
                      📴 End Call
                    </button>
                  </div>
                </div>

                {/* Live User Transcript */}
                {userTranscript && (
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
                    <p className="text-xs font-medium text-yellow-700 mb-1">
                      🎧 User is saying:
                    </p>
                    <p className="text-sm text-yellow-900 italic">
                      &quot;{userTranscript}&quot;
                    </p>
                  </div>
                )}

                {/* Conversation History */}
                <div className="mb-4">
                  <h3 className="font-medium text-gray-700 mb-2">
                    Conversation History (with AI)
                  </h3>
                  <div className="bg-gray-50 rounded-lg p-3 max-h-48 overflow-y-auto space-y-2">
                    {conversationHistory.length === 0 ? (
                      <p className="text-gray-500 text-sm">No messages yet</p>
                    ) : (
                      conversationHistory.map((msg, idx) => (
                        <div
                          key={idx}
                          className={`p-2 rounded ${
                            msg.role === "user"
                              ? "bg-blue-100 text-blue-900"
                              : "bg-green-100 text-green-900"
                          }`}
                        >
                          <span className="font-medium text-xs">
                            {msg.role === "user" ? "User" : "AI"}:
                          </span>{" "}
                          {msg.text}
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Optional Text Message Input */}
                <div className="border-t pt-4">
                  <p className="text-xs text-gray-500 mb-2">
                    Optional: Send a text message (will be read aloud to user)
                  </p>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={messageInput}
                      onChange={(e) => setMessageInput(e.target.value)}
                      onKeyPress={(e) => e.key === "Enter" && sendMessage()}
                      placeholder="Type a message..."
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                    />
                    <button
                      onClick={sendMessage}
                      className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition text-sm"
                    >
                      Send
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Instructions */}
        <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <h3 className="font-semibold text-yellow-800 mb-2">
            📝 Voice Call Instructions
          </h3>
          <ul className="text-sm text-yellow-700 list-disc list-inside space-y-1">
            <li>
              Enter your Agent ID and click Connect to start receiving calls
            </li>
            <li>
              When you accept a call, your microphone will be activated for
              voice communication
            </li>
            <li>
              You&apos;ll hear the user speaking and they&apos;ll hear you in
              real-time
            </li>
            <li>
              The &quot;User is saying&quot; box shows real-time transcription
              of user&apos;s speech
            </li>
            <li>Use the Mute button to temporarily mute your microphone</li>
            <li>Click End Call when finished to disconnect</li>
          </ul>
        </div>
      </div>
    </div>
    </RequireAuth>
  );
}
