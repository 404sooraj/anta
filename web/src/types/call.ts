export type CallStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "disconnecting"
  | "error"

export interface CallState {
  status: CallStatus
  error: string | null
  duration: number
  isMuted: boolean
}
