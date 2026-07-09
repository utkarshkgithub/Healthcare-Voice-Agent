import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Volume2, VolumeX, AlertCircle } from 'lucide-react';
import Navbar from '../components/Layout/Navbar';
import DarkVeil from '../components/Layout/DarkVeil';

import { VoiceOrb } from '../components/VoiceAgent/VoiceOrb';
import { MessageList } from '../components/VoiceAgent/MessageList';
import { ChatInput } from '../components/VoiceAgent/ChatInput';
import { Message, AgentStatus } from '../types';
import { voiceProvider } from '../utils/voiceProvider';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// ─── Component ────────────────────────────────────────────────────────────────
export default function VoiceAgent() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      type: 'agent',
      text: "Hello! I'm your AI health assistant. Press the microphone button and describe how you're feeling — I'm here to help.",
      timestamp: new Date(),
    },
  ]);
  const [inputText, setInputText] = useState('');
  const [status, setStatus] = useState<AgentStatus>('idle');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [micPermission, setMicPermission] = useState<'unknown' | 'granted' | 'denied'>('unknown');
  const [speechSupported] = useState(() => voiceProvider.isSupported());
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [waveformBars] = useState(() => Array.from({ length: 24 }, (_, i) => i));

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const historyRef = useRef<string[]>([]);
  const nextIdRef = useRef(2);
  const animFrameRef = useRef<number>(0);

  // ─── Waveform animation bars heights ─────────────────────────────────────
  const [barHeights, setBarHeights] = useState<number[]>(waveformBars.map(() => 4));
  const animateWaveformRef = useRef<() => void>(() => {});

  const animateWaveform = useCallback(() => {
    setBarHeights(waveformBars.map(() => Math.random() * 32 + 4));
    animFrameRef.current = requestAnimationFrame(() => {
      setTimeout(animateWaveformRef.current, 80);
    });
  }, [waveformBars]);

  useEffect(() => {
    animateWaveformRef.current = animateWaveform;
  }, [animateWaveform]);

  const stopWaveform = useCallback(() => {
    cancelAnimationFrame(animFrameRef.current);
    setBarHeights(waveformBars.map(() => 4));
  }, [waveformBars]);

  // ─── Scroll to bottom ─────────────────────────────────────────────────────
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, interimTranscript]);

  // ─── Cleanup on unmount ───────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      voiceProvider.stopListening();
      voiceProvider.cancelSpeech();
      cancelAnimationFrame(animFrameRef.current);
    };
  }, []);

  // ─── Speak reply via voiceProvider ───────────────────────────────────────
  const speakReply = useCallback(
    (text: string, onDone?: () => void) => {
      if (!ttsEnabled) {
        onDone?.();
        return;
      }
      voiceProvider.cancelSpeech();
      setStatus('speaking');
      voiceProvider.speak(text, () => {
        setStatus('idle');
        onDone?.();
      });
    },
    [ttsEnabled],
  );

  // ─── Send message to real /chat endpoint ─────────────────────────────────
  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim()) return;
      setErrorMsg(null);

      const userMsg: Message = {
        id: nextIdRef.current++,
        type: 'user',
        text: text.trim(),
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, userMsg]);

      const historySnapshot = [...historyRef.current];
      historyRef.current = [...historyRef.current, `Patient: ${text.trim()}`];

      setStatus('thinking');

      try {
        const res = await fetch(`${API_BASE}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text.trim(), history: historySnapshot }),
        });

        if (!res.ok) {
          throw new Error(`Server error ${res.status}: ${res.statusText}`);
        }

        const data = await res.json();
        const reply: string = data.reply || "I'm sorry, I couldn't generate a response.";

        historyRef.current = [...historyRef.current, `Assistant: ${reply}`];
        if (historyRef.current.length > 20) {
          historyRef.current = historyRef.current.slice(-20);
        }

        const agentMsg: Message = {
          id: nextIdRef.current++,
          type: 'agent',
          text: reply,
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, agentMsg]);

        // Save to localStorage for dashboard history
        const sessions = JSON.parse(localStorage.getItem('voice_sessions') || '[]');
        const today = new Date().toISOString().split('T')[0];
        const existing = sessions.findIndex((s: { date: string }) => s.date === today);
        if (existing >= 0) {
          sessions[existing].messageCount += 2;
          sessions[existing].lastMessage = text.trim();
        } else {
          sessions.unshift({ date: today, firstMessage: text.trim(), lastMessage: text.trim(), messageCount: 2 });
        }
        localStorage.setItem('voice_sessions', JSON.stringify(sessions.slice(0, 10)));

        speakReply(reply);
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Network error';
        setErrorMsg(`Failed to reach AI: ${msg}`);
        setStatus('idle');
      }
    },
    [speakReply],
  );

  // ─── Handle text input submit ─────────────────────────────────────────────
  const handleTextSend = () => {
    if (!inputText.trim() || status === 'thinking') return;
    const text = inputText.trim();
    setInputText('');
    sendMessage(text);
  };

  // ─── Start voice recording via voiceProvider adapter ─────────────────────
  const startListening = useCallback(() => {
    setErrorMsg(null);
    animateWaveform();

    voiceProvider.startListening(
      (text, isFinal) => {
        if (isFinal) {
          setInterimTranscript('');
          stopWaveform();
          sendMessage(text);
        } else {
          setInterimTranscript(text);
        }
      },
      statusUpdate => {
        if (statusUpdate === 'listening') {
          setStatus('listening');
          setMicPermission('granted');
        } else if (statusUpdate === 'error') {
          setMicPermission('denied');
          setErrorMsg('Microphone access was denied. Please allow mic access in your browser settings.');
          stopWaveform();
          setInterimTranscript('');
          setStatus('idle');
        } else {
          // 'idle'
          stopWaveform();
          setInterimTranscript('');
          setStatus(prev => (prev === 'listening' ? 'idle' : prev));
        }
      },
    );
  }, [animateWaveform, stopWaveform, sendMessage]);

  // ─── Stop voice recording ─────────────────────────────────────────────────
  const stopListening = useCallback(() => {
    voiceProvider.stopListening();
    stopWaveform();
    setInterimTranscript('');
    setStatus('idle');
  }, [stopWaveform]);

  // ─── Toggle TTS ───────────────────────────────────────────────────────────
  const toggleTts = () => {
    if (status === 'speaking') {
      voiceProvider.cancelSpeech();
      setStatus('idle');
    }
    setTtsEnabled(v => !v);
  };

  // ─── Toggle mic ───────────────────────────────────────────────────────────
  const toggleMic = () => {
    if (status === 'listening') {
      stopListening();
    } else if (status === 'idle') {
      startListening();
    }
  };

  const isThinking = status === 'thinking';
  const isSpeaking = status === 'speaking';
  const isBusy = isThinking || isSpeaking;

  return (
    <div className="min-h-screen flex flex-col">
      <div className="fixed inset-0 z-[-1] bg-black">
        <DarkVeil
          hueShift={0}
          noiseIntensity={0}
          scanlineIntensity={0}
          speed={0.5}
          scanlineFrequency={0}
          warpAmount={0}
        />
      </div>
      <Navbar />

      <div className="flex-1 max-w-4xl w-full mx-auto px-4 py-6 flex flex-col gap-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="flex items-center justify-between"
        >
          <div>
            <h1 className="text-3xl font-semibold text-gradient">AI Health Assistant</h1>
            <p className="text-sm text-foreground-muted mt-1">Speak freely — your voice is the interface</p>
          </div>
          <button
            onClick={toggleTts}
            title={ttsEnabled ? 'Mute AI voice' : 'Unmute AI voice'}
            className="p-2 rounded-lg bg-white/[0.05] border border-white/[0.08] text-foreground-muted hover:text-foreground hover:bg-white/[0.08] transition-all duration-200"
          >
            {ttsEnabled ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5" />}
          </button>
        </motion.div>

        {/* Warnings & Errors */}
        {!speechSupported && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-3 bg-amber-500/10 border border-amber-500/30 rounded-xl px-4 py-3 text-sm text-amber-300"
          >
            <AlertCircle className="w-4 h-4 shrink-0" />
            Voice input requires Chrome or Edge. You can still type below.
          </motion.div>
        )}

        {micPermission === 'denied' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-3 bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 text-sm text-red-300"
          >
            <AlertCircle className="w-4 h-4 shrink-0" />
            Microphone access denied. Go to browser Settings → Site Settings → allow microphone for this page.
          </motion.div>
        )}

        <AnimatePresence>
          {errorMsg && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="flex items-center gap-3 bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 text-sm text-red-300"
            >
              <AlertCircle className="w-4 h-4 shrink-0" />
              {errorMsg}
            </motion.div>
          )}
        </AnimatePresence>

        <VoiceOrb
          status={status}
          speechSupported={speechSupported}
          toggleMic={toggleMic}
          waveformBars={waveformBars}
          barHeights={barHeights}
          interimTranscript={interimTranscript}
        />

        <div className="card-glass rounded-2xl flex flex-col overflow-hidden flex-1 min-h-0" style={{ maxHeight: '420px' }}>
          <MessageList messages={messages} status={status} messagesEndRef={messagesEndRef} />
          <ChatInput
            inputText={inputText}
            setInputText={setInputText}
            handleTextSend={handleTextSend}
            isBusy={isBusy}
          />
        </div>
      </div>
    </div>
  );
}
