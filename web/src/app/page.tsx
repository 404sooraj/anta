"use client"

import { useVoiceBot } from "@/hooks/useVoiceBot"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Spinner } from "@/components/ui/spinner"
import { Mic, MicOff, PhoneOff } from "lucide-react"

function formatDuration(seconds: number) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, "0")}`
}

export default function Home() {
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
  } = useVoiceBot()

  const isIdle = callState.status === "idle"
  const isError = callState.status === "error"
  const isConnecting = callState.status === "connecting"
  const isConnected = callState.status === "connected"
  const canStart = isIdle || isError
  const canEnd = isConnected

  const displayTranscript = transcript || partialTranscript
  const displayResponse = response || streamingResponse

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 font-sans dark:bg-zinc-950">
      <main className="w-full max-w-2xl px-4 py-8">
        <Card className="overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between gap-4 space-y-0 border-b pb-4">
            <div>
              <CardTitle className="text-xl">Antaryami</CardTitle>
              <CardDescription>Voice assistant — start a call to talk</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              {isConnected && (
                <span className="text-muted-foreground text-sm tabular-nums">
                  {formatDuration(callState.duration)}
                </span>
              )}
              <Badge
                variant={
                  isError
                    ? "destructive"
                    : isConnected
                      ? "default"
                      : isConnecting
                        ? "secondary"
                        : "outline"
                }
              >
                {callState.status}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-6 pt-6">
            {/* Controls */}
            <div className="flex flex-wrap items-center justify-center gap-3">
              <Button
                size="icon-lg"
                variant={canEnd ? "destructive" : "default"}
                disabled={isConnecting}
                onClick={canEnd ? endCall : canStart ? startCall : undefined}
                aria-label={canEnd ? "End call" : "Start call"}
              >
                {isConnecting ? (
                  <Spinner className="size-6" />
                ) : canEnd ? (
                  <PhoneOff className="size-6" />
                ) : (
                  <Mic className="size-6" />
                )}
              </Button>
              {isConnected && (
                <Button
                  size="icon-lg"
                  variant={callState.isMuted ? "secondary" : "outline"}
                  onClick={toggleMute}
                  aria-label={callState.isMuted ? "Unmute" : "Mute"}
                >
                  {callState.isMuted ? (
                    <MicOff className="size-6" />
                  ) : (
                    <Mic className="size-6" />
                  )}
                </Button>
              )}
            </div>

            {/* Audio level */}
            {isConnected && (
              <div className="space-y-1">
                <span className="text-muted-foreground text-xs">
                  Input level
                </span>
                <Progress
                  value={Math.min(100, audioLevel * 100)}
                  className="h-2"
                />
              </div>
            )}

            {/* Error */}
            {callState.error && (
              <p className="text-destructive text-sm" role="alert">
                {callState.error}
              </p>
            )}

            {/* Transcript & Response */}
            <div className="grid gap-4 sm:grid-cols-1">
              <div className="space-y-2">
                <h3 className="text-muted-foreground text-sm font-medium">
                  You said
                </h3>
                <ScrollArea className="h-24 rounded-md border bg-muted/30 px-3 py-2">
                  <p className="text-sm">
                    {displayTranscript || (
                      <span className="text-muted-foreground">
                        {isConnected
                          ? "Speak and wait for silence..."
                          : "Start a call to see your transcript here."}
                      </span>
                    )}
                  </p>
                </ScrollArea>
              </div>
              <div className="space-y-2">
                <h3 className="text-muted-foreground text-sm font-medium">
                  Response
                </h3>
                <ScrollArea className="h-32 rounded-md border bg-muted/30 px-3 py-2">
                  <p className="text-sm">
                    {displayResponse ? (
                      displayResponse
                    ) : (
                      <span className="text-muted-foreground">
                        {isConnected
                          ? "Response will appear here after you speak."
                          : "Start a call to see the assistant response."}
                      </span>
                    )}
                  </p>
                </ScrollArea>
              </div>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
