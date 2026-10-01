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
import { chatApi, triageApi, payAndBook, ApiError, type Doctor } from '../utils/api';
import { DoctorList } from '../components/VoiceAgent/DoctorList';

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

  // Structured prediction returned by the triage pipeline, and the doctors
  // discovered from it. Both feed the booking flow.
  const [prediction, setPrediction] = useState({
    condition: '',
    additionalSymptoms: [] as string[],
    remedy: '',
  });
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [triageBusy, setTriageBusy] = useState(false);
  const [bookingMsg, setBookingMsg] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const questionRoundsRef = useRef(0);
  // The server owns the transcript now; this only identifies which one.
  // Read eagerly: useRef has no lazy initialiser, so passing a function here
  // would store the function as the value and it would be truthy.
  const conversationIdRef = useRef<string | null>(
    localStorage.getItem('conversation_id'),
  );
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

  // ─── Restore the transcript after a reload ──────────────────────────────
  // History used to live only in a React ref, so a refresh lost the thread.
  useEffect(() => {
    const conversationId = conversationIdRef.current;
    if (!conversationId || !localStorage.getItem('token')) return;

    let cancelled = false;
    chatApi
      .history(conversationId)
      .then(({ messages }) => {
        if (cancelled || !messages.length) return;
        setMessages([
          ...messages.map((m, i) => ({
            id: 1000 + i,
            type: m.role === 'patient' ? ('user' as const) : ('agent' as const),
            text: m.content,
            timestamp: new Date(m.created_at),
          })),
          {
            id: 1,
            type: 'agent' as const,
            text: 'Picking up where you left off — what else would you like to tell me about?',
            timestamp: new Date(),
          },
        ]);
      })
      .catch(() => {
        // A missing or foreign conversation id just starts fresh.
        conversationIdRef.current = null;
        localStorage.removeItem('conversation_id');
      });

    return () => {
      cancelled = true;
    };
  }, []);

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
      // TTS off must still leave 'thinking'. Returning early without changing
      // status is what left the UI stuck on the thinking indicator forever.
      if (!ttsEnabled) {
        setStatus('idle');
        onDone?.();
        return;
      }

      voiceProvider.cancelSpeech();
      setStatus('speaking');

      // speechSynthesis is not dependable about telling us when it finished:
      // voices can still be loading, cancel() can swallow an utterance, and
      // Chrome halts long utterances partway without firing onend. Without a
      // deadline the UI sits in 'speaking' indefinitely.
      const words = text.trim().split(/\s+/).filter(Boolean).length;
      const budgetMs = Math.min((words / 2.8) * 1000 + 2500, 60_000);

      let finished = false;
      const finish = () => {
        // The watchdog and a late onend can both land; the caller is told once.
        if (finished) return;
        finished = true;
        clearTimeout(watchdog);
        setStatus('idle');
        onDone?.();
      };

      const watchdog = setTimeout(finish, budgetMs);
      voiceProvider.speak(text, finish);
    },
    [ttsEnabled],
  );

  // ─── Specialist mapping + doctor discovery ────────────────────────────────
  // Runs the second LangGraph pipeline: normalized symptoms -> specialties in
  // the database -> ranked specialists -> doctors with a real open slot.
  const findDoctors = useCallback(async (phrases: string[]) => {
    if (!phrases.length) return;
    setTriageBusy(true);
    setBookingMsg(null);
    setDoctors([]);
    try {
      const result = await triageApi.run(phrases);
      setDoctors(result.doctors || []);
    } catch (err) {
      setErrorMsg(
        err instanceof ApiError ? err.message : "Couldn't look up specialists right now.",
      );
    } finally {
      setTriageBusy(false);
    }
  }, []);

  const handleBook = useCallback(async (doctor: Doctor) => {
    const patientId = localStorage.getItem('patient_id');
    if (!patientId) {
      setBookingMsg('Sign in to book an appointment.');
      return;
    }

    setBookingMsg(
      `Booking with ${doctor.name} on ${doctor.next_available_date} at ${doctor.start_time}…`,
    );
    try {
      const result = await payAndBook(
        doctor,
        Number(patientId),
        prediction.condition || 'General consultation',
      );
      if (!result) {
        setBookingMsg('Payment cancelled. The slot is still available.');
        return;
      }
      setBookingMsg(
        `Booked with ${doctor.name} on ${doctor.next_available_date} at ${doctor.start_time}.`,
      );
      // Refresh the list so the booked slot disappears from discovery.
      setDoctors((prev) => prev.filter((d) => d.slot_id !== doctor.slot_id));
    } catch (err) {
      setBookingMsg(err instanceof ApiError ? err.message : 'Booking failed. Please try again.');
    }
  }, [prediction.condition]);

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

      setStatus('thinking');

      try {
        const data = await chatApi.send(
          text.trim(),
          questionRoundsRef.current,
          conversationIdRef.current,
        );

        // Persist the id so a reload resumes the same conversation.
        if (data.conversation_id) {
          conversationIdRef.current = data.conversation_id;
          localStorage.setItem('conversation_id', data.conversation_id);
        }
        const reply: string = data.reply || "I'm sorry, I couldn't generate a response.";

        // Carry the counter forward or the clarifying-question cap never trips.
        questionRoundsRef.current = data.question_rounds ?? 0;
        setPrediction({
          condition: data.predicted_condition || '',
          additionalSymptoms: data.predicted_additional_symptoms || [],
          remedy: data.immediate_remedy || '',
        });

        // Once the pipeline commits to a condition, run specialist mapping so
        // the patient sees who they can actually see next.
        if (data.predicted_condition) {
          const phrases = [
            ...(data.predicted_additional_symptoms || []),
            data.predicted_condition,
          ];
          if (phrases.length) void findDoctors(phrases);
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
        if (err instanceof ApiError) {
          // Already a human sentence from the API client.
          setErrorMsg(err.message);
        } else {
          setErrorMsg("Couldn't reach the assistant. Check your connection.");
        }
        setStatus('idle');
      }
    },
    [speakReply, findDoctors],
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

      <div className="flex-1 w-full mx-auto px-4 py-6 max-w-6xl flex flex-col">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="flex items-center justify-between mb-6"
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

        <div className="flex-1 min-h-0 flex flex-col md:flex-row md:gap-6 lg:gap-8">
          {/* Left rail — the voice interface */}
          <div className="md:w-64 lg:w-80 xl:w-96 md:shrink-0 flex justify-center items-start md:items-center">
            <VoiceOrb
              status={status}
              speechSupported={speechSupported}
              toggleMic={toggleMic}
              waveformBars={waveformBars}
              barHeights={barHeights}
              interimTranscript={interimTranscript}
            />
          </div>

          {/* Right — the conversation */}
          <div className="flex-1 min-w-0 min-h-0 flex flex-col gap-4 mt-6 md:mt-0">
            <div className="card-glass rounded-2xl flex flex-col overflow-hidden flex-1 min-h-0 max-h-[420px] lg:max-h-none">
              <MessageList messages={messages} status={status} messagesEndRef={messagesEndRef} />
              <ChatInput
                inputText={inputText}
                setInputText={setInputText}
                handleTextSend={handleTextSend}
                isBusy={isBusy}
              />
            </div>

            <div className="shrink-0 max-h-56 overflow-y-auto">
              <DoctorList
                doctors={doctors}
                busy={triageBusy}
                message={bookingMsg}
                prediction={prediction}
                onBook={handleBook}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
