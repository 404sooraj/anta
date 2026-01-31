"use client"

import { useState, useRef, useCallback, useEffect } from "react"
import { CallState, CallStatus } from "@/types/call"

export interface UseVoiceBotReturn {
  callState: CallState
  audioLevel: number
  startCall: () => Promise<void>
  endCall: () => void
  toggleMute: () => void
  transcript: string
  partialTranscript: string
  response: string
  streamingResponse: string
  conversationHistory: Array<{ role: string; text: string }>
}

const DEFAULT_WS_URL = "ws://localhost:8000/stt/ws/audio"
const WS_URL =
  typeof process !== "undefined" && process.env.NEXT_PUBLIC_WS_URL
    ? process.env.NEXT_PUBLIC_WS_URL
    : DEFAULT_WS_URL
const INPUT_SAMPLE_RATE = 16000
const OUTPUT_SAMPLE_RATE = 44100

export function useVoiceBot(): UseVoiceBotReturn {
  const [callState, setCallState] = useState<CallState>({
    status: "idle",
    error: null,
    duration: 0,
    isMuted: false,
  })
  const [audioLevel, setAudioLevel] = useState(0)
  const [transcript, setTranscript] = useState("")
  const [partialTranscript, setPartialTranscript] = useState("")
  const [response, setResponse] = useState("")
  const [streamingResponse, setStreamingResponse] = useState("")
  const [conversationHistory, setConversationHistory] = useState<
    Array<{ role: string; text: string }>
  >([])
  const [isNewSpeech, setIsNewSpeech] = useState(true)

  const wsRef = useRef<WebSocket | null>(null)
  const localStreamRef = useRef<MediaStream | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const animationFrameRef = useRef<number | null>(null)
  const durationIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const audioProcessorRef = useRef<ScriptProcessorNode | null>(null)
  const audioQueueRef = useRef<Float32Array[]>([])
  const isPlayingRef = useRef(false)
  const outputAudioContextRef = useRef<AudioContext | null>(null)
  const isMutedRef = useRef(false)
  const disconnectingRef = useRef(false)
  const isNewSpeechRef = useRef(true)

  const updateStatus = useCallback(
    (status: CallStatus, error: string | null = null) => {
      setCallState((prev) => ({ ...prev, status, error }))
    },
    []
  )

  function downsample(
    input: Float32Array,
    fromRate: number,
    toRate: number
  ): Float32Array {
    if (fromRate === toRate) return input
    const ratio = fromRate / toRate
    const outLength = Math.round(input.length / ratio)
    const result = new Float32Array(outLength)
    for (let i = 0; i < outLength; i++) {
      const srcIndex = i * ratio
      const idx0 = Math.floor(srcIndex)
      const idx1 = Math.min(idx0 + 1, input.length - 1)
      const t = srcIndex - idx0
      result[i] = input[idx0] * (1 - t) + input[idx1] * t
    }
    return result
  }

  function float32ToInt16(buffer: Float32Array): ArrayBuffer {
    const int16 = new Int16Array(buffer.length)
    for (let i = 0; i < buffer.length; i++) {
      const s = Math.max(-1, Math.min(1, buffer[i]))
      int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff
    }
    return int16.buffer
  }

  const playAudioQueue = useCallback(async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) return

    isPlayingRef.current = true

    try {
      if (!outputAudioContextRef.current) {
        outputAudioContextRef.current = new AudioContext({
          sampleRate: OUTPUT_SAMPLE_RATE,
        })
      }

      const ctx = outputAudioContextRef.current

      while (audioQueueRef.current.length > 0) {
        const audioData = audioQueueRef.current.shift()
        if (!audioData) break

        const audioBuffer = ctx.createBuffer(
          1,
          audioData.length,
          OUTPUT_SAMPLE_RATE
        )
        audioBuffer.copyToChannel(new Float32Array(audioData), 0)

        const source = ctx.createBufferSource()
        source.buffer = audioBuffer
        source.connect(ctx.destination)

        await new Promise<void>((resolve) => {
          source.onended = () => resolve()
          source.start()
        })
      }
    } catch (error) {
      console.error("Error playing audio:", error)
    } finally {
      isPlayingRef.current = false
    }
  }, [])

  const startAudioAnalysis = useCallback((stream: MediaStream) => {
    try {
      if (!audioContextRef.current) {
        audioContextRef.current = new AudioContext()
      }

      const ctx = audioContextRef.current
      analyserRef.current = ctx.createAnalyser()
      analyserRef.current.fftSize = 512
      analyserRef.current.smoothingTimeConstant = 0.4

      const source = ctx.createMediaStreamSource(stream)
      source.connect(analyserRef.current)

      const dataArray = new Uint8Array(analyserRef.current.fftSize)
      let smoothedLevel = 0

      const analyze = () => {
        if (analyserRef.current) {
          analyserRef.current.getByteTimeDomainData(dataArray)

          let sumSquares = 0
          for (let i = 0; i < dataArray.length; i++) {
            const normalized = (dataArray[i] - 128) / 128
            sumSquares += normalized * normalized
          }
          const rms = Math.sqrt(sumSquares / dataArray.length)

          const amplifiedLevel = Math.min(1, rms * 3)
          smoothedLevel = smoothedLevel * 0.7 + amplifiedLevel * 0.3

          setAudioLevel(smoothedLevel)
        }
        animationFrameRef.current = requestAnimationFrame(analyze)
      }

      analyze()
    } catch (err) {
      console.error("Failed to start audio analysis:", err)
    }
  }, [])

  const stopAudioAnalysis = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current)
      animationFrameRef.current = null
    }
    if (
      audioContextRef.current &&
      audioContextRef.current.state !== "closed"
    ) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }
    if (audioProcessorRef.current) {
      audioProcessorRef.current.disconnect()
      audioProcessorRef.current = null
    }
    analyserRef.current = null
    setAudioLevel(0)
  }, [])

  const startDurationTimer = useCallback(() => {
    setCallState((prev) => ({ ...prev, duration: 0 }))
    durationIntervalRef.current = setInterval(() => {
      setCallState((prev) => ({ ...prev, duration: prev.duration + 1 }))
    }, 1000)
  }, [])

  const stopDurationTimer = useCallback(() => {
    if (durationIntervalRef.current) {
      clearInterval(durationIntervalRef.current)
      durationIntervalRef.current = null
    }
  }, [])

  // ScriptProcessorNode is deprecated but still works; consider AudioWorklet for future upgrade.
  const setupAudioProcessing = useCallback((stream: MediaStream) => {
    if (!audioContextRef.current) return

    const ctx = audioContextRef.current
    const source = ctx.createMediaStreamSource(stream)

    const processor = ctx.createScriptProcessor(512, 1, 1)
    audioProcessorRef.current = processor

    processor.onaudioprocess = (e) => {
      if (
        wsRef.current?.readyState === WebSocket.OPEN &&
        !isMutedRef.current
      ) {
        const inputData = e.inputBuffer.getChannelData(0)
        const at16k = downsample(
          new Float32Array(inputData),
          ctx.sampleRate,
          INPUT_SAMPLE_RATE
        )
        const pcmData = float32ToInt16(at16k)
        wsRef.current.send(pcmData)
      }
    }

    source.connect(processor)
    processor.connect(ctx.destination)
  }, [])

  const startCall = useCallback(async () => {
    try {
      disconnectingRef.current = false
      updateStatus("connecting")

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: INPUT_SAMPLE_RATE,
          channelCount: 1,
        },
        video: false,
      })

      localStreamRef.current = stream

      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        console.log("✅ Connected to voice bot")
        updateStatus("connected")
        startDurationTimer()

        startAudioAnalysis(stream)
        setupAudioProcessing(stream)
      }

      ws.onmessage = async (event) => {
        if (event.data instanceof Blob) {
          const arrayBuffer = await event.data.arrayBuffer()
          const audioData = new Float32Array(arrayBuffer as ArrayBuffer)
          audioQueueRef.current.push(audioData)
          playAudioQueue()
        } else if (typeof event.data === "string") {
          try {
            const data = JSON.parse(event.data) as {
              type: string
              text?: string
              transcript?: string
              response?: string
              conversation_history?: Array<{ role: string; text: string }>
            }

            if (data.type === "partial_transcript") {
              if (isNewSpeechRef.current) {
                setTranscript("")
                setResponse("")
                setStreamingResponse("")
                isNewSpeechRef.current = false
                setIsNewSpeech(false)
              }
              setPartialTranscript(data.text ?? "")
            } else if (data.type === "response_stream") {
              setStreamingResponse(data.text ?? "")
            } else if (data.type === "llm_response") {
              setTranscript(data.transcript ?? "")
              setTimeout(() => setPartialTranscript(""), 100)
              setResponse(data.response ?? "")
              setStreamingResponse("")
              isNewSpeechRef.current = true
              setIsNewSpeech(true)
              if (data.conversation_history) {
                setConversationHistory(data.conversation_history)
              }
            } else if (data.type === "audio_start") {
              // TTS streaming started
            } else if (data.type === "audio_end") {
              // TTS streaming complete
            } else if (data.type === "interrupted") {
              audioQueueRef.current = []
              isPlayingRef.current = false
              setStreamingResponse("")
              isNewSpeechRef.current = true
              setIsNewSpeech(true)
            }
          } catch (err) {
            console.error("Failed to parse message:", err)
          }
        }
      }

      ws.onerror = () => {
        updateStatus("error", "Connection error")
      }

      ws.onclose = () => {
        if (!disconnectingRef.current) {
          updateStatus("error", "Connection closed unexpectedly")
        }
      }
    } catch (err) {
      console.error("Failed to start call:", err)
      const errorMessage =
        err instanceof Error ? err.message : "Failed to access microphone"
      updateStatus("error", errorMessage)

      if (localStreamRef.current) {
        localStreamRef.current.getTracks().forEach((track) => track.stop())
        localStreamRef.current = null
      }
    }
  }, [
    updateStatus,
    startAudioAnalysis,
    setupAudioProcessing,
    startDurationTimer,
    playAudioQueue,
  ])

  const endCall = useCallback(() => {
    disconnectingRef.current = true
    updateStatus("disconnecting")

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach((track) => track.stop())
      localStreamRef.current = null
    }

    stopAudioAnalysis()
    if (outputAudioContextRef.current) {
      outputAudioContextRef.current.close()
      outputAudioContextRef.current = null
    }

    audioQueueRef.current = []
    isPlayingRef.current = false

    stopDurationTimer()

    setCallState({
      status: "idle",
      error: null,
      duration: 0,
      isMuted: false,
    })
    setTranscript("")
    setPartialTranscript("")
    setResponse("")
    setStreamingResponse("")
    setConversationHistory([])
    isNewSpeechRef.current = true
    setIsNewSpeech(true)
  }, [updateStatus, stopAudioAnalysis, stopDurationTimer])

  const toggleMute = useCallback(() => {
    if (localStreamRef.current) {
      const audioTrack = localStreamRef.current.getAudioTracks()[0]
      if (audioTrack) {
        audioTrack.enabled = !audioTrack.enabled
        isMutedRef.current = !audioTrack.enabled
        setCallState((prev) => ({ ...prev, isMuted: !audioTrack.enabled }))
      }
    }
  }, [])

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (localStreamRef.current) {
        localStreamRef.current.getTracks().forEach((track) => track.stop())
      }
      stopAudioAnalysis()
      stopDurationTimer()
      if (outputAudioContextRef.current) {
        outputAudioContextRef.current.close()
      }
    }
  }, [stopAudioAnalysis, stopDurationTimer])

  return {
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
  }
}
