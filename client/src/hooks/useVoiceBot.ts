'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { CallState, CallStatus } from '@/types/call';

interface UseVoiceBotReturn {
  callState: CallState;
  audioLevel: number;
  startCall: () => Promise<void>;
  endCall: () => void;
  toggleMute: () => void;
  transcript: string;
  partialTranscript: string;
  response: string;
  streamingResponse: string;
  conversationHistory: Array<{role: string, text: string}>;
  handoffStatus: 'none' | 'queued' | 'connected';
}

interface UseVoiceBotOptions {
  token?: string;
  userId?: string;
}

const WS_BASE_URL = 'ws://localhost:8000/stt/ws/audio';
const INPUT_SAMPLE_RATE = 16000;
const OUTPUT_SAMPLE_RATE = 44100;

export function useVoiceBot(options: UseVoiceBotOptions = {}): UseVoiceBotReturn {
  const { token, userId } = options;
  
  // Store auth options in refs to ensure they're always current when startCall is called
  const tokenRef = useRef(token);
  const userIdRef = useRef(userId);
  
  // Keep refs in sync with props
  useEffect(() => {
    tokenRef.current = token;
    userIdRef.current = userId;
  }, [token, userId]);
  
  const [callState, setCallState] = useState<CallState>({
    status: 'idle',
    error: null,
    duration: 0,
    isMuted: false,
  });
  const [audioLevel, setAudioLevel] = useState(0);
  const [transcript, setTranscript] = useState('');
  const [partialTranscript, setPartialTranscript] = useState('');
  const [response, setResponse] = useState('');
  const [streamingResponse, setStreamingResponse] = useState('');
  const [conversationHistory, setConversationHistory] = useState<Array<{role: string, text: string}>>([]);
  const [isNewSpeech, setIsNewSpeech] = useState(true);
  const [handoffStatus, setHandoffStatus] = useState<'none' | 'queued' | 'connected'>('none');

  const wsRef = useRef<WebSocket | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const durationIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const audioProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const audioQueueRef = useRef<Float32Array[]>([]);
  const isPlayingRef = useRef(false);
  const outputAudioContextRef = useRef<AudioContext | null>(null);

  // Update call status helper
  const updateStatus = useCallback((status: CallStatus, error: string | null = null) => {
    setCallState(prev => ({ ...prev, status, error }));
  }, []);

  // Downsample float32 audio to target sample rate (linear interpolation)
  const downsample = (input: Float32Array, fromRate: number, toRate: number): Float32Array => {
    if (fromRate === toRate) return input;
    const ratio = fromRate / toRate;
    const outLength = Math.round(input.length / ratio);
    const result = new Float32Array(outLength);
    for (let i = 0; i < outLength; i++) {
      const srcIndex = i * ratio;
      const idx0 = Math.floor(srcIndex);
      const idx1 = Math.min(idx0 + 1, input.length - 1);
      const t = srcIndex - idx0;
      result[i] = input[idx0] * (1 - t) + input[idx1] * t;
    }
    return result;
  };

  // Convert Float32 to Int16 PCM
  const float32ToInt16 = (buffer: Float32Array): ArrayBuffer => {
    const int16 = new Int16Array(buffer.length);
    for (let i = 0; i < buffer.length; i++) {
      const s = Math.max(-1, Math.min(1, buffer[i]));
      int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return int16.buffer;
  };

  // Play audio from queue
  const playAudioQueue = useCallback(async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) return;
    
    isPlayingRef.current = true;

    try {
      if (!outputAudioContextRef.current) {
        outputAudioContextRef.current = new AudioContext({ sampleRate: OUTPUT_SAMPLE_RATE });
      }

      const ctx = outputAudioContextRef.current;
      
      while (audioQueueRef.current.length > 0) {
        const audioData = audioQueueRef.current.shift();
        if (!audioData) break;

        const audioBuffer = ctx.createBuffer(1, audioData.length, OUTPUT_SAMPLE_RATE);
        audioBuffer.copyToChannel(new Float32Array(audioData), 0);

        const source = ctx.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(ctx.destination);

        await new Promise<void>((resolve) => {
          source.onended = () => resolve();
          source.start();
        });
      }
    } catch (error) {
      console.error('Error playing audio:', error);
    } finally {
      isPlayingRef.current = false;
    }
  }, []);

  // Analyze audio levels for visualization
  const startAudioAnalysis = useCallback((stream: MediaStream) => {
    try {
      if (!audioContextRef.current) {
        // Use default sample rate so MediaStream and context match (browser requirement)
        audioContextRef.current = new AudioContext();
      }

      const ctx = audioContextRef.current;
      analyserRef.current = ctx.createAnalyser();
      analyserRef.current.fftSize = 512;
      analyserRef.current.smoothingTimeConstant = 0.4;
      
      const source = ctx.createMediaStreamSource(stream);
      source.connect(analyserRef.current);

      const dataArray = new Uint8Array(analyserRef.current.fftSize);
      let smoothedLevel = 0;

      const analyze = () => {
        if (analyserRef.current) {
          analyserRef.current.getByteTimeDomainData(dataArray);
          
          let sumSquares = 0;
          for (let i = 0; i < dataArray.length; i++) {
            const normalized = (dataArray[i] - 128) / 128;
            sumSquares += normalized * normalized;
          }
          const rms = Math.sqrt(sumSquares / dataArray.length);
          
          const amplifiedLevel = Math.min(1, rms * 3);
          smoothedLevel = smoothedLevel * 0.7 + amplifiedLevel * 0.3;
          
          setAudioLevel(smoothedLevel);
        }
        animationFrameRef.current = requestAnimationFrame(analyze);
      };

      analyze();
    } catch (err) {
      console.error('Failed to start audio analysis:', err);
    }
  }, []);

  // Stop audio analysis
  const stopAudioAnalysis = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (audioProcessorRef.current) {
      audioProcessorRef.current.disconnect();
      audioProcessorRef.current = null;
    }
    analyserRef.current = null;
    setAudioLevel(0);
  }, []);

  // Start call duration timer
  const startDurationTimer = useCallback(() => {
    setCallState(prev => ({ ...prev, duration: 0 }));
    durationIntervalRef.current = setInterval(() => {
      setCallState(prev => ({ ...prev, duration: prev.duration + 1 }));
    }, 1000);
  }, []);

  // Stop call duration timer
  const stopDurationTimer = useCallback(() => {
    if (durationIntervalRef.current) {
      clearInterval(durationIntervalRef.current);
      durationIntervalRef.current = null;
    }
  }, []);

  // Setup audio processing to send to WebSocket
  const setupAudioProcessing = useCallback((stream: MediaStream) => {
    if (!audioContextRef.current) return;

    const ctx = audioContextRef.current;
    const source = ctx.createMediaStreamSource(stream);
    
    // Create processor (512 samples per chunk; downsampled to 16kHz before send)
    const processor = ctx.createScriptProcessor(512, 1, 1);
    audioProcessorRef.current = processor;

    processor.onaudioprocess = (e) => {
      if (wsRef.current?.readyState === WebSocket.OPEN && !callState.isMuted) {
        const inputData = e.inputBuffer.getChannelData(0);
        const at16k = downsample(inputData, ctx.sampleRate, INPUT_SAMPLE_RATE);
        const pcmData = float32ToInt16(at16k);
        wsRef.current.send(pcmData);
      }
    };

    source.connect(processor);
    processor.connect(ctx.destination);
  }, [callState.isMuted]);

  // Update user location on backend (backend handles reverse geocoding)
  const updateUserLocation = useCallback(async () => {
    if (!userIdRef.current && !tokenRef.current) {
      console.log('📍 Skipping location update - not logged in');
      return;
    }

    try {
      // Get current position from browser
      const position = await new Promise<GeolocationPosition>((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 60000, // Accept cached location up to 1 minute old
        });
      });

      const { latitude, longitude, accuracy } = position.coords;
      console.log(`📍 Got location: ${latitude}, ${longitude} (accuracy: ${accuracy}m)`);

      // Send coordinates to backend - backend will do reverse geocoding
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (tokenRef.current) {
        headers['Authorization'] = `Bearer ${tokenRef.current}`;
      }
      if (userIdRef.current) {
        headers['X-User-ID'] = userIdRef.current;
      }

      const response = await fetch('http://localhost:8000/api/location/update', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          latitude,
          longitude,
          accuracy,
          // No address - backend will geocode using secure API key
        }),
      });

      if (response.ok) {
        const data = await response.json();
        console.log('✅ Location updated on server:', data.location?.address || 'No address');
      } else {
        console.warn('⚠️ Failed to update location:', await response.text());
      }
    } catch (error) {
      // Don't fail the call if location fails
      if (error instanceof GeolocationPositionError) {
        console.warn('📍 Geolocation error:', error.message);
      } else {
        console.warn('📍 Location update failed:', error);
      }
    }
  }, []);

  // Start the call
  const startCall = useCallback(async () => {
    try {
      updateStatus('connecting');

      // Update location before connecting (don't await - let it run in parallel)
      updateUserLocation();

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: INPUT_SAMPLE_RATE,
          channelCount: 1,
        },
        video: false,
      });

      localStreamRef.current = stream;

      // Build WebSocket URL with auth params (use refs to get current values)
      const params = new URLSearchParams();
      if (tokenRef.current) {
        params.set('token', tokenRef.current);
      }
      if (userIdRef.current) {
        params.set('user_id', userIdRef.current);
      }
      const wsUrl = params.toString() ? `${WS_BASE_URL}?${params.toString()}` : WS_BASE_URL;
      console.log('🔗 Connecting to WebSocket:', wsUrl.replace(/token=[^&]+/, 'token=***'));
      console.log('🔑 Auth - token:', tokenRef.current ? 'present' : 'missing', ', userId:', userIdRef.current || 'missing');

      // Connect to WebSocket
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('✅ Connected to voice bot');
        updateStatus('connected');
        startDurationTimer();
        
        // Start audio analysis and processing
        startAudioAnalysis(stream);
        setupAudioProcessing(stream);
      };

      ws.onmessage = async (event) => {
        // Handle binary audio data
        if (event.data instanceof Blob) {
          const arrayBuffer = await event.data.arrayBuffer();
          const audioData = new Float32Array(arrayBuffer as ArrayBuffer);
          audioQueueRef.current.push(audioData);
          playAudioQueue();
        } 
        // Handle JSON messages
        else if (typeof event.data === 'string') {
          try {
            const data = JSON.parse(event.data);
            
            if (data.type === 'partial_transcript') {
              // Real-time streaming transcripts
              // Clear old messages when new speech starts
              if (isNewSpeech) {
                setTranscript('');
                setResponse('');
                setStreamingResponse('');
                setIsNewSpeech(false);
              }
              setPartialTranscript(data.text || '');
              // Also update transcript so it persists after partial ends
              setTranscript(data.text || '');
            } else if (data.type === 'response_stream') {
              // Streaming response text word-by-word
              setStreamingResponse(data.text || '');
            } else if (data.type === 'llm_response') {
              console.log('📄 Transcript:', data.transcript);
              console.log('🤖 Response:', data.response);
              // DON'T update transcript - keep what user saw while speaking
              // setTranscript(data.transcript || '');
              // Clear partial after a brief delay to show the final transcript first
              setTimeout(() => setPartialTranscript(''), 100);
              setResponse(data.response || '');
              setStreamingResponse('');  // Clear streaming response
              setIsNewSpeech(true);  // Ready for next speech
              // Update conversation history if provided
              if (data.conversation_history) {
                setConversationHistory(data.conversation_history);
              }
            } else if (data.type === 'audio_start') {
              console.log('🔊 Receiving TTS audio...');
            } else if (data.type === 'audio_end') {
              console.log('✅ TTS audio complete');
            } else if (data.type === 'interrupted') {
              console.log('⚠️  TTS interrupted');
              // Clear audio queue on interruption
              audioQueueRef.current = [];
              isPlayingRef.current = false;
              setStreamingResponse('');  // Clear streaming response on interruption
              setIsNewSpeech(true);  // Ready for next speech
            } else if (data.type === 'handoff_queued') {
              // User has been added to the queue for human agent
              console.log('📞 Handoff queued:', data.session_id);
              setResponse(data.message || 'You have been added to the queue for a customer service agent.');
              setStreamingResponse('');
              setHandoffStatus('queued');
            } else if (data.type === 'agent_connected') {
              // Human agent has connected
              console.log('🎧 Agent connected:', data.agent_id);
              setResponse(data.message || 'You are now connected to a customer service agent.');
              setStreamingResponse('');
              setHandoffStatus('connected');
            } else if (data.type === 'agent_message') {
              // Message from human agent
              console.log('💬 Agent message:', data.text);
              setResponse(data.text || '');
              setStreamingResponse('');
            } else if (data.type === 'call_ended') {
              // Call with agent ended
              console.log('📴 Call ended:', data.ended_by);
              setResponse(data.message || 'The call with the agent has ended.');
              setStreamingResponse('');
              setHandoffStatus('none');
            }
          } catch (err) {
            console.error('Failed to parse message:', err);
          }
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateStatus('error', 'Connection error');
      };

      ws.onclose = () => {
        console.log('WebSocket closed');
        if (callState.status !== 'disconnecting') {
          updateStatus('error', 'Connection closed unexpectedly');
        }
      };

    } catch (err) {
      console.error('Failed to start call:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to access microphone';
      updateStatus('error', errorMessage);
      
      // Cleanup on error
      if (localStreamRef.current) {
        localStreamRef.current.getTracks().forEach(track => track.stop());
        localStreamRef.current = null;
      }
    }
  }, [updateStatus, startAudioAnalysis, setupAudioProcessing, startDurationTimer, playAudioQueue, callState.status]);

  // End the call
  const endCall = useCallback(() => {
    updateStatus('disconnecting');

    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    // Stop all local tracks
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => track.stop());
      localStreamRef.current = null;
    }

    // Stop audio contexts
    stopAudioAnalysis();
    if (outputAudioContextRef.current) {
      outputAudioContextRef.current.close();
      outputAudioContextRef.current = null;
    }

    // Clear audio queue
    audioQueueRef.current = [];
    isPlayingRef.current = false;

    // Stop duration timer
    stopDurationTimer();

    // Reset state
    setCallState({
      status: 'idle',
      error: null,
      duration: 0,
      isMuted: false,
    });
    setTranscript('');
    setPartialTranscript('');
    setResponse('');
    setStreamingResponse('');
    setConversationHistory([]);
    setIsNewSpeech(true);
  }, [updateStatus, stopAudioAnalysis, stopDurationTimer]);

  // Toggle mute
  const toggleMute = useCallback(() => {
    if (localStreamRef.current) {
      const audioTrack = localStreamRef.current.getAudioTracks()[0];
      if (audioTrack) {
        audioTrack.enabled = !audioTrack.enabled;
        setCallState(prev => ({ ...prev, isMuted: !audioTrack.enabled }));
      }
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (localStreamRef.current) {
        localStreamRef.current.getTracks().forEach(track => track.stop());
      }
      stopAudioAnalysis();
      stopDurationTimer();
      if (outputAudioContextRef.current) {
        outputAudioContextRef.current.close();
      }
    };
  }, [stopAudioAnalysis, stopDurationTimer]);

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
    handoffStatus,
  };
}
