'use client';

import { useState, useRef, useEffect } from 'react';

type ConnectionStatus = 'idle' | 'connecting' | 'connected' | 'processing' | 'complete' | 'error';

interface StatusMessage {
  status?: string;
  type?: string;
  chunks?: number;
  error?: string;
}

export default function TestTTSPage() {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('idle');
  const [messages, setMessages] = useState<string[]>([]);
  const [audioChunks, setAudioChunks] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [textToSend, setTextToSend] = useState('Hello, this is a test message for TTS');
  const [streamingSpeed, setStreamingSpeed] = useState(50); // milliseconds between chunks
  const [selectedLanguage, setSelectedLanguage] = useState<'auto' | 'en' | 'hi'>('auto');
  const [voiceId, setVoiceId] = useState<string>(''); // Optional voice ID
  
  // Default voice IDs for each language
  const DEFAULT_VOICE_IDS = {
    en: 'f9836c6e-a0bd-460e-9d3c-f7299fa60f94', // English voice
    hi: '47f3bbb1-e98f-4e0c-92c5-5f0325e1e206', // Hindi voice
  };
  
  // Get the effective voice ID based on language selection
  const getEffectiveVoiceId = (): string | undefined => {
    if (voiceId.trim()) {
      return voiceId.trim(); // Use custom voice ID if provided
    }
    // Auto-select voice based on language
    if (selectedLanguage === 'hi') {
      return DEFAULT_VOICE_IDS.hi;
    } else if (selectedLanguage === 'en') {
      return DEFAULT_VOICE_IDS.en;
    }
    // For 'auto', don't set voice ID - let server use default
    return undefined;
  };
  
  const wsRef = useRef<WebSocket | null>(null);
  const audioChunksRef = useRef<number>(0);
  const audioBufferRef = useRef<Uint8Array[]>([]);
  
  // Web Audio API refs for real-time playback
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioQueueRef = useRef<Float32Array[]>([]);
  const isPlayingRef = useRef<boolean>(false);
  const [isPlaying, setIsPlaying] = useState(false);
  
  // Track when current sentence audio finishes (for sequential sentence playback)
  const sentenceAudioCompleteRef = useRef<Promise<void> | null>(null);
  const sentenceAudioResolveRef = useRef<(() => void) | null>(null);
  const sentenceChunkCountRef = useRef<number>(0);
  const sentenceChunksPlayedRef = useRef<number>(0);
  
  // Track context ID for seamless streaming
  const contextIdRef = useRef<string | null>(null);
  
  // Helper function to generate unique context ID
  const generateContextId = () => {
    return `ctx-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  };

  // Initialize AudioContext
  useEffect(() => {
    if (typeof window !== 'undefined' && !audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
    }
    
    return () => {
      // Cleanup
      if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Function to play audio chunks in real-time
  const playAudioChunk = async (audioData: ArrayBuffer | Blob) => {
    if (!audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
    }

    const audioContext = audioContextRef.current;
    
    // Resume audio context if suspended (browser autoplay policy)
    if (audioContext.state === 'suspended') {
      await audioContext.resume();
    }

    try {
      // Convert ArrayBuffer/Blob to ArrayBuffer
      let arrayBuffer: ArrayBuffer;
      if (audioData instanceof ArrayBuffer) {
        arrayBuffer = audioData;
      } else {
        arrayBuffer = await audioData.arrayBuffer();
      }

      // Convert PCM float32 bytes to Float32Array
      // Server sends: PCM float32 little-endian, 44100 Hz, mono
      const float32Data = new Float32Array(arrayBuffer.byteLength / 4);
      const uint8View = new Uint8Array(arrayBuffer);
      
      // Convert bytes to float32 (little-endian)
      for (let i = 0; i < float32Data.length; i++) {
        const byteOffset = i * 4;
        const bytes = uint8View.slice(byteOffset, byteOffset + 4);
        const view = new DataView(bytes.buffer);
        float32Data[i] = view.getFloat32(0, true); // true = little-endian
      }

      // Create AudioBuffer (44100 Hz, mono channel)
      const sampleRate = 44100;
      const audioBuffer = audioContext.createBuffer(1, float32Data.length, sampleRate);
      audioBuffer.copyToChannel(float32Data, 0);

      // Create and play audio source
      const source = audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContext.destination);
      
      source.onended = () => {
        // Increment chunks played for current sentence
        sentenceChunksPlayedRef.current += 1;
        
        // Check if there are more chunks to play
        if (audioQueueRef.current.length > 0) {
          const nextChunk = audioQueueRef.current.shift();
          if (nextChunk) {
            // Convert Float32Array back to ArrayBuffer for playback
            // Create a new ArrayBuffer from the Float32Array
            const buffer = new ArrayBuffer(nextChunk.byteLength);
            const view = new Uint8Array(buffer);
            view.set(new Uint8Array(nextChunk.buffer, nextChunk.byteOffset, nextChunk.byteLength));
            playAudioChunk(buffer);
          }
        } else {
          setIsPlaying(false);
          isPlayingRef.current = false;
          
          // Check if all chunks for the current sentence have finished playing
          if (sentenceChunksPlayedRef.current >= sentenceChunkCountRef.current) {
            // All chunks for this sentence have finished - resolve promise
            if (sentenceAudioResolveRef.current) {
              sentenceAudioResolveRef.current();
              sentenceAudioResolveRef.current = null;
              sentenceAudioCompleteRef.current = null;
            }
            // Reset counters
            sentenceChunkCountRef.current = 0;
            sentenceChunksPlayedRef.current = 0;
          }
        }
      };

      source.start();
      setIsPlaying(true);
      isPlayingRef.current = true;
    } catch (error) {
      console.error('Error playing audio chunk:', error);
      addMessage(`Error playing audio: ${error}`);
    }
  };

  const addMessage = (msg: string) => {
    setMessages(prev => [...prev, `${new Date().toLocaleTimeString()}: ${msg}`]);
  };

  const connectWebSocket = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      addMessage('WebSocket already connected');
      return;
    }

    setConnectionStatus('connecting');
    setError(null);
    setMessages([]);
    setAudioChunks(0);
    setIsPlaying(false);
    audioChunksRef.current = 0;
    audioBufferRef.current = [];
    audioQueueRef.current = [];
    isPlayingRef.current = false;

    try {
      const ws = new WebSocket('ws://localhost:8000/tts/ws');
      wsRef.current = ws;

      ws.onopen = () => {
        setConnectionStatus('connected');
        addMessage('WebSocket connected');
      };

      ws.onmessage = async (event) => {
        // Check if message is binary (audio) or text (JSON)
        if (event.data instanceof ArrayBuffer || event.data instanceof Blob) {
          // Audio chunk received
          audioChunksRef.current += 1;
          setAudioChunks(audioChunksRef.current);
          
          // Store audio chunk for potential download
          let byteLength: number | string = 'unknown';
          if (event.data instanceof ArrayBuffer) {
            byteLength = event.data.byteLength;
            audioBufferRef.current.push(new Uint8Array(event.data));
          } else {
            byteLength = event.data.size;
            event.data.arrayBuffer().then((buf: ArrayBuffer) => {
              audioBufferRef.current.push(new Uint8Array(buf));
            });
          }
          
          addMessage(`Audio chunk #${audioChunksRef.current} received (${byteLength} bytes)`);
          
          // Play audio chunk in real-time
          if (isPlayingRef.current) {
            // If already playing, queue this chunk
            const arrayBuffer = event.data instanceof ArrayBuffer 
              ? event.data 
              : await event.data.arrayBuffer();
            const float32Data = new Float32Array(arrayBuffer.byteLength / 4);
            const uint8View = new Uint8Array(arrayBuffer);
            for (let i = 0; i < float32Data.length; i++) {
              const byteOffset = i * 4;
              const bytes = uint8View.slice(byteOffset, byteOffset + 4);
              const view = new DataView(bytes.buffer);
              float32Data[i] = view.getFloat32(0, true);
            }
            audioQueueRef.current.push(float32Data);
          } else {
            // Start playing immediately
            playAudioChunk(event.data);
          }
        } else {
          // Text message (JSON status)
          try {
            const data: StatusMessage = JSON.parse(event.data);
            if (data.type === 'status') {
              if (data.status === 'processing') {
                setConnectionStatus('processing');
                addMessage('Server is processing TTS...');
              } else             if (data.status === 'complete') {
                setConnectionStatus('complete');
                const chunksReceived = data.chunks || audioChunksRef.current;
                addMessage(`TTS complete! Received ${chunksReceived} audio chunks`);
                
                // Update sentence chunk count for sequential sentence playback
                if (sentenceChunkCountRef.current === 0) {
                  sentenceChunkCountRef.current = chunksReceived;
                }
              }
            } else if (data.type === 'error') {
              setConnectionStatus('error');
              setError(data.error || 'Unknown error');
              addMessage(`Error: ${data.error}`);
            }
          } catch (e) {
            addMessage(`Received text: ${event.data}`);
          }
        }
      };

      ws.onerror = (err) => {
        setConnectionStatus('error');
        setError('WebSocket error occurred');
        addMessage('WebSocket error');
        console.error('WebSocket error:', err);
      };

      ws.onclose = () => {
        setConnectionStatus('idle');
        addMessage('WebSocket disconnected');
      };
    } catch (err) {
      setConnectionStatus('error');
      setError(err instanceof Error ? err.message : 'Failed to connect');
      addMessage(`Connection error: ${err}`);
    }
  };

  const sendTextStream = async () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      addMessage('WebSocket not connected. Please connect first.');
      return;
    }

    const text = textToSend.trim();
    if (!text) {
      addMessage('No text to send');
      return;
    }

    setConnectionStatus('processing');
    addMessage(`Starting to stream text word by word: "${text}"`);

    // Generate new context ID for this streaming session
    contextIdRef.current = generateContextId();
    addMessage(`Using context ID: ${contextIdRef.current}`);

    // Split text into words (including spaces as separate items)
    const words = text.split(/(\s+)/).filter(w => w.length > 0); // Split but keep spaces, remove empty

    // Send each word separately with context-based streaming
    for (let i = 0; i < words.length; i++) {
      const word = words[i];
      const isLast = i === words.length - 1;
      
      // Send with context_id and continue flag
      const effectiveVoiceId = getEffectiveVoiceId();
      const message: any = {
        transcript: word,
        context_id: contextIdRef.current,
        continue: !isLast,
        language: selectedLanguage,
      };
      if (effectiveVoiceId) {
        message.voice_id = effectiveVoiceId;
      }
      wsRef.current.send(JSON.stringify(message));
      addMessage(`Sent word ${i + 1}/${words.length}: "${word}" (continue: ${!isLast})`);

      // Wait before sending next word (streaming effect)
      if (i < words.length - 1) {
        await new Promise(resolve => setTimeout(resolve, streamingSpeed));
      }
    }

    addMessage('Finished streaming all words');
    contextIdRef.current = null; // Clear context ID after completion
  };

  const sendTextAsSentences = async () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      addMessage('WebSocket not connected. Please connect first.');
      return;
    }

    const text = textToSend.trim();
    if (!text) {
      addMessage('No text to send');
      return;
    }

    setConnectionStatus('processing');
    addMessage(`Starting to stream text as sentences: "${text}"`);

    // Generate new context ID for this streaming session
    contextIdRef.current = generateContextId();
    addMessage(`Using context ID: ${contextIdRef.current}`);

    // Split text by sentence delimiters (. ! ?) while keeping the delimiters
    // This regex splits on . ! ? but keeps them with the sentence
    const sentences = text.split(/([.!?]+[\s]*)/).filter(s => s.trim().length > 0);
    
    // Group sentences with their punctuation
    const sentenceGroups: string[] = [];
    for (let i = 0; i < sentences.length; i++) {
      const part = sentences[i].trim();
      if (part.length > 0) {
        // Check if this part ends with punctuation
        if (/[.!?]+$/.test(part)) {
          // This part is a complete sentence with punctuation
          sentenceGroups.push(part);
        } else if (i + 1 < sentences.length && /^[.!?]+/.test(sentences[i + 1])) {
          // Next part is punctuation, combine them
          sentenceGroups.push(part + sentences[i + 1].trim());
          i++; // Skip the next part as we've combined it
        } else {
          // Regular text part
          sentenceGroups.push(part);
        }
      }
    }

    // Send each sentence separately with context-based streaming, waiting for audio to complete before next
    for (let i = 0; i < sentenceGroups.length; i++) {
      const sentence = sentenceGroups[i].trim();
      
      if (sentence.length === 0) continue;

      // Reset counters for this sentence
      sentenceChunkCountRef.current = 0;
      sentenceChunksPlayedRef.current = 0;

      // Create a promise that resolves when this sentence's audio finishes
      sentenceAudioCompleteRef.current = new Promise<void>((resolve) => {
        sentenceAudioResolveRef.current = resolve;
      });

      const isLast = i === sentenceGroups.length - 1;
      
      // Send with context_id and continue flag
      const effectiveVoiceId = getEffectiveVoiceId();
      const message: any = {
        transcript: sentence,
        context_id: contextIdRef.current,
        continue: !isLast,
        language: selectedLanguage,
      };
      if (effectiveVoiceId) {
        message.voice_id = effectiveVoiceId;
      }
      wsRef.current.send(JSON.stringify(message));
      addMessage(`Sent sentence ${i + 1}/${sentenceGroups.length}: "${sentence}" (continue: ${!isLast})`);

      // Wait for this sentence's audio to finish before sending next sentence
      // This ensures sequential playback without overlapping voices
      // The promise will resolve when all audio chunks for this sentence finish playing
      if (i < sentenceGroups.length - 1) {
        await sentenceAudioCompleteRef.current;
        addMessage(`Sentence ${i + 1} audio complete, sending next sentence...`);
      }
    }

    // Wait for the last sentence's audio to finish
    if (sentenceAudioCompleteRef.current) {
      await sentenceAudioCompleteRef.current;
    }

    addMessage('Finished streaming all sentences');
    contextIdRef.current = null; // Clear context ID after completion
  };

  const sendTextAllAtOnce = () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      addMessage('WebSocket not connected. Please connect first.');
      return;
    }

    const text = textToSend.trim();
    if (!text) {
      addMessage('No text to send');
      return;
    }

    setConnectionStatus('processing');
    addMessage(`Sending complete text: "${text}"`);

    // Generate context ID for this single-shot request
    contextIdRef.current = generateContextId();
    addMessage(`Using context ID: ${contextIdRef.current}`);

    // Send with context format (continue: false since it's a single message)
    const effectiveVoiceId = getEffectiveVoiceId();
    const message: any = {
      transcript: text,
      context_id: contextIdRef.current,
      continue: false,
      language: selectedLanguage,
    };
    if (effectiveVoiceId) {
      message.voice_id = effectiveVoiceId;
    }
    wsRef.current.send(JSON.stringify(message));
    addMessage('Text sent (all at once)');
    contextIdRef.current = null; // Clear context ID after sending
  };

  const disconnect = () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnectionStatus('idle');
    addMessage('Disconnected');
  };

  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'bg-green-500';
      case 'connecting':
      case 'processing':
        return 'bg-yellow-500';
      case 'error':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-100 mb-8">
          TTS WebSocket Test Page
        </h1>

        {/* Connection Status */}
        <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6 mb-6">
          <div className="flex items-center gap-4 mb-4">
            <div className={`w-4 h-4 rounded-full ${getStatusColor()} animate-pulse`} />
            <span className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
              Status: {connectionStatus.toUpperCase()}
            </span>
          </div>
          
          {error && (
            <div className="text-red-500 mb-4">
              Error: {error}
            </div>
          )}

          <div className="text-sm text-zinc-600 dark:text-zinc-400 mb-4 space-y-1">
            <div>Audio Chunks Received: {audioChunks}</div>
            <div className={isPlaying ? 'text-green-500' : 'text-gray-500'}>
              {isPlaying ? '🔊 Playing audio...' : '🔇 Audio stopped'}
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={connectWebSocket}
              disabled={connectionStatus === 'connecting' || connectionStatus === 'connected'}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              Connect
            </button>
            <button
              onClick={disconnect}
              disabled={connectionStatus === 'idle'}
              className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              Disconnect
            </button>
          </div>
        </div>

        {/* Text Input */}
        <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6 mb-6">
          <label className="block text-sm font-medium text-zinc-900 dark:text-zinc-100 mb-2">
            Text to Send:
          </label>
          <textarea
            value={textToSend}
            onChange={(e) => setTextToSend(e.target.value)}
            className="w-full p-3 border border-zinc-300 dark:border-zinc-700 rounded bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 mb-4"
            rows={3}
            placeholder="Enter text to convert to speech..."
          />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-zinc-900 dark:text-zinc-100 mb-2">
                Language:
              </label>
              <select
                value={selectedLanguage}
                onChange={(e) => {
                  const newLang = e.target.value as 'auto' | 'en' | 'hi';
                  setSelectedLanguage(newLang);
                  // Auto-set voice ID when language is selected (if voice ID field is empty)
                  if (!voiceId.trim()) {
                    if (newLang === 'hi') {
                      setVoiceId(DEFAULT_VOICE_IDS.hi);
                    } else if (newLang === 'en') {
                      setVoiceId(DEFAULT_VOICE_IDS.en);
                    } else {
                      setVoiceId(''); // Clear for auto-detect
                    }
                  }
                }}
                className="w-full p-2 border border-zinc-300 dark:border-zinc-700 rounded bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100"
              >
                <option value="auto">Auto (Detect)</option>
                <option value="en">English</option>
                <option value="hi">Hindi 🇮🇳</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-zinc-900 dark:text-zinc-100 mb-2">
                Voice ID (Optional):
              </label>
              <input
                type="text"
                value={voiceId}
                onChange={(e) => setVoiceId(e.target.value)}
                placeholder={selectedLanguage === 'hi' ? `Hindi voice: ${DEFAULT_VOICE_IDS.hi}` : selectedLanguage === 'en' ? `English voice: ${DEFAULT_VOICE_IDS.en}` : 'Leave empty for default voice'}
                className="w-full p-2 border border-zinc-300 dark:border-zinc-700 rounded bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100"
              />
              {selectedLanguage === 'hi' && !voiceId.trim() && (
                <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
                  Using Hindi voice: {DEFAULT_VOICE_IDS.hi}
                </p>
              )}
              {selectedLanguage === 'en' && !voiceId.trim() && (
                <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
                  Using English voice: {DEFAULT_VOICE_IDS.en}
                </p>
              )}
            </div>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-zinc-900 dark:text-zinc-100 mb-2">
              Streaming Speed (ms between chunks): {streamingSpeed}ms
            </label>
            <input
              type="range"
              min="10"
              max="500"
              value={streamingSpeed}
              onChange={(e) => setStreamingSpeed(Number(e.target.value))}
              className="w-full"
            />
          </div>

          <div className="flex gap-2 flex-wrap">
            <button
              onClick={sendTextStream}
              disabled={connectionStatus !== 'connected' && connectionStatus !== 'idle'}
              className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              Send as Stream (Word by Word)
            </button>
            <button
              onClick={sendTextAsSentences}
              disabled={connectionStatus !== 'connected' && connectionStatus !== 'idle'}
              className="px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              Send as Sentences
            </button>
            <button
              onClick={sendTextAllAtOnce}
              disabled={connectionStatus !== 'connected' && connectionStatus !== 'idle'}
              className="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              Send All at Once
            </button>
          </div>
        </div>

        {/* Messages Log */}
        <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 mb-4">
            Messages Log
          </h2>
          <div className="bg-zinc-100 dark:bg-zinc-800 rounded p-4 h-96 overflow-y-auto">
            {messages.length === 0 ? (
              <p className="text-zinc-500 dark:text-zinc-400">No messages yet...</p>
            ) : (
              <div className="space-y-1">
                {messages.map((msg, idx) => (
                  <div key={idx} className="text-sm text-zinc-700 dark:text-zinc-300 font-mono">
                    {msg}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
