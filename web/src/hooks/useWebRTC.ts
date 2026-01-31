// 'use client';

// import { useState, useRef, useCallback, useEffect } from 'react';
// import { CallState, CallStatus, WebRTCConfig, DEFAULT_WEBRTC_CONFIG } from '@/types/call';

// interface UseWebRTCReturn {
//   callState: CallState;
//   audioLevel: number;
//   startCall: () => Promise<void>;
//   endCall: () => void;
//   toggleMute: () => void;
//   localStream: MediaStream | null;
//   peerConnection: RTCPeerConnection | null;
// }

// export function useWebRTC(config: WebRTCConfig = DEFAULT_WEBRTC_CONFIG): UseWebRTCReturn {
//   const [callState, setCallState] = useState<CallState>({
//     status: 'idle',
//     error: null,
//     duration: 0,
//     isMuted: false,
//   });
//   const [audioLevel, setAudioLevel] = useState(0);

//   const localStreamRef = useRef<MediaStream | null>(null);
//   const peerConnectionRef = useRef<RTCPeerConnection | null>(null);
//   const audioContextRef = useRef<AudioContext | null>(null);
//   const analyserRef = useRef<AnalyserNode | null>(null);
//   const animationFrameRef = useRef<number | null>(null);
//   const durationIntervalRef = useRef<NodeJS.Timeout | null>(null);

//   // Update call status helper
//   const updateStatus = useCallback((status: CallStatus, error: string | null = null) => {
//     setCallState(prev => ({ ...prev, status, error }));
//   }, []);

//   // Analyze audio levels for visualization
//   const startAudioAnalysis = useCallback((stream: MediaStream) => {
//     try {
//       audioContextRef.current = new AudioContext();
//       analyserRef.current = audioContextRef.current.createAnalyser();
//       analyserRef.current.fftSize = 512;
//       analyserRef.current.smoothingTimeConstant = 0.4;
      
//       const source = audioContextRef.current.createMediaStreamSource(stream);
//       source.connect(analyserRef.current);

//       // Use time domain data for better voice detection
//       const dataArray = new Uint8Array(analyserRef.current.fftSize);
//       let smoothedLevel = 0;

//       const analyze = () => {
//         if (analyserRef.current) {
//           analyserRef.current.getByteTimeDomainData(dataArray);
          
//           // Calculate RMS (root mean square) for accurate volume
//           let sumSquares = 0;
//           for (let i = 0; i < dataArray.length; i++) {
//             const normalized = (dataArray[i] - 128) / 128; // Center around 0
//             sumSquares += normalized * normalized;
//           }
//           const rms = Math.sqrt(sumSquares / dataArray.length);
          
//           // Apply smoothing and amplification for better visual response
//           const amplifiedLevel = Math.min(1, rms * 3); // Amplify for visibility
//           smoothedLevel = smoothedLevel * 0.7 + amplifiedLevel * 0.3; // Smooth transitions
          
//           setAudioLevel(smoothedLevel);
//         }
//         animationFrameRef.current = requestAnimationFrame(analyze);
//       };

//       analyze();
//     } catch (err) {
//       console.error('Failed to start audio analysis:', err);
//     }
//   }, []);

//   // Stop audio analysis
//   const stopAudioAnalysis = useCallback(() => {
//     if (animationFrameRef.current) {
//       cancelAnimationFrame(animationFrameRef.current);
//       animationFrameRef.current = null;
//     }
//     if (audioContextRef.current) {
//       audioContextRef.current.close();
//       audioContextRef.current = null;
//     }
//     analyserRef.current = null;
//     setAudioLevel(0);
//   }, []);

//   // Start call duration timer
//   const startDurationTimer = useCallback(() => {
//     setCallState(prev => ({ ...prev, duration: 0 }));
//     durationIntervalRef.current = setInterval(() => {
//       setCallState(prev => ({ ...prev, duration: prev.duration + 1 }));
//     }, 1000);
//   }, []);

//   // Stop call duration timer
//   const stopDurationTimer = useCallback(() => {
//     if (durationIntervalRef.current) {
//       clearInterval(durationIntervalRef.current);
//       durationIntervalRef.current = null;
//     }
//   }, []);

//   // Initialize WebRTC connection
//   const initializePeerConnection = useCallback(() => {
//     const pc = new RTCPeerConnection({
//       iceServers: config.iceServers || DEFAULT_WEBRTC_CONFIG.iceServers,
//     });

//     // Handle ICE candidates
//     pc.onicecandidate = (event) => {
//       if (event.candidate) {
//         // In production, send this to the signaling server
//         console.log('ICE candidate:', event.candidate);
//       }
//     };

//     // Handle connection state changes
//     pc.onconnectionstatechange = () => {
//       console.log('Connection state:', pc.connectionState);
      
//       if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
//         updateStatus('error', 'Connection lost');
//       }
//     };

//     // Handle incoming tracks (for receiving audio from bot)
//     pc.ontrack = (event) => {
//       console.log('Received remote track:', event.track.kind);
//       // In production, play the received audio
//       const audio = new Audio();
//       audio.srcObject = event.streams[0];
//       audio.play().catch(console.error);
//     };

//     peerConnectionRef.current = pc;
//     return pc;
//   }, [config.iceServers, updateStatus]);

//   // Start the call
//   const startCall = useCallback(async () => {
//     try {
//       updateStatus('connecting');

//       // Request microphone access
//       const stream = await navigator.mediaDevices.getUserMedia({
//         audio: {
//           echoCancellation: true,
//           noiseSuppression: true,
//           autoGainControl: true,
//           sampleRate: 16000, // Optimal for speech recognition
//         },
//         video: false,
//       });

//       localStreamRef.current = stream;

//       // Initialize peer connection
//       const pc = initializePeerConnection();

//       // Add audio track to peer connection
//       stream.getAudioTracks().forEach(track => {
//         pc.addTrack(track, stream);
//       });

//       // Create and set local description (offer)
//       const offer = await pc.createOffer();
//       await pc.setLocalDescription(offer);

//       // In production, send the offer to the signaling server
//       // and wait for an answer. For now, we'll simulate a connected state.
//       console.log('Local offer created:', offer);

//       // Start audio analysis for visualization
//       startAudioAnalysis(stream);

//       // Start duration timer
//       startDurationTimer();

//       // Update status to connected
//       // In production, this would happen after receiving the answer
//       updateStatus('connected');

//     } catch (err) {
//       console.error('Failed to start call:', err);
//       const errorMessage = err instanceof Error ? err.message : 'Failed to access microphone';
//       updateStatus('error', errorMessage);
      
//       // Cleanup on error
//       if (localStreamRef.current) {
//         localStreamRef.current.getTracks().forEach(track => track.stop());
//         localStreamRef.current = null;
//       }
//     }
//   }, [updateStatus, initializePeerConnection, startAudioAnalysis, startDurationTimer]);

//   // End the call
//   const endCall = useCallback(() => {
//     updateStatus('disconnecting');

//     // Stop all local tracks
//     if (localStreamRef.current) {
//       localStreamRef.current.getTracks().forEach(track => track.stop());
//       localStreamRef.current = null;
//     }

//     // Close peer connection
//     if (peerConnectionRef.current) {
//       peerConnectionRef.current.close();
//       peerConnectionRef.current = null;
//     }

//     // Stop audio analysis
//     stopAudioAnalysis();

//     // Stop duration timer
//     stopDurationTimer();

//     // Reset state
//     setCallState({
//       status: 'idle',
//       error: null,
//       duration: 0,
//       isMuted: false,
//     });
//   }, [updateStatus, stopAudioAnalysis, stopDurationTimer]);

//   // Toggle mute
//   const toggleMute = useCallback(() => {
//     if (localStreamRef.current) {
//       const audioTrack = localStreamRef.current.getAudioTracks()[0];
//       if (audioTrack) {
//         audioTrack.enabled = !audioTrack.enabled;
//         setCallState(prev => ({ ...prev, isMuted: !audioTrack.enabled }));
//       }
//     }
//   }, []);

//   // Cleanup on unmount
//   useEffect(() => {
//     return () => {
//       if (localStreamRef.current) {
//         localStreamRef.current.getTracks().forEach(track => track.stop());
//       }
//       if (peerConnectionRef.current) {
//         peerConnectionRef.current.close();
//       }
//       stopAudioAnalysis();
//       stopDurationTimer();
//     };
//   }, [stopAudioAnalysis, stopDurationTimer]);

//   return {
//     callState,
//     audioLevel,
//     startCall,
//     endCall,
//     toggleMute,
//     localStream: localStreamRef.current,
//     peerConnection: peerConnectionRef.current,
//   };
// }