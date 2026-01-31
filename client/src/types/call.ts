// Call status types for the voice bot

export type CallStatus = 
  | 'idle'           // Initial state, no call
  | 'connecting'     // Requesting mic access, setting up WebRTC
  | 'connected'      // Call is active
  | 'disconnecting'  // Ending the call
  | 'error';         // Error occurred

export interface CallState {
  status: CallStatus;
  error: string | null;
  duration: number;      // Call duration in seconds
  isMuted: boolean;
}

export interface WebRTCConfig {
  iceServers?: RTCIceServer[];
  signalingServerUrl?: string;
}

export const DEFAULT_WEBRTC_CONFIG: WebRTCConfig = {
  iceServers: [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:stun1.l.google.com:19302' },
  ],
};
