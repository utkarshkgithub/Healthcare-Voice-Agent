import { motion, AnimatePresence } from 'framer-motion';
import { Mic, MicOff, Volume2, Loader2 } from 'lucide-react';
import { AgentStatus } from '../../types';

interface VoiceOrbProps {
  status: AgentStatus;
  speechSupported: boolean;
  toggleMic: () => void;
  waveformBars: number[];
  barHeights: number[];
  interimTranscript: string;
}

export function VoiceOrb({
  status,
  speechSupported,
  toggleMic,
  waveformBars,
  barHeights,
  interimTranscript,
}: VoiceOrbProps) {
  const isListening = status === 'listening';
  const isThinking = status === 'thinking';
  const isSpeaking = status === 'speaking';
  const isBusy = isThinking || isSpeaking;

  const statusLabel: Record<AgentStatus, string> = {
    idle: speechSupported ? 'Click the mic to speak' : 'Type your message below',
    listening: 'Listening…',
    thinking: 'AI is thinking…',
    speaking: 'AI is speaking…',
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, delay: 0.1 }}
      className="flex flex-col items-center gap-6 py-6"
    >
      <div className="relative">
        {isListening && (
          <>
            <motion.div
              className="absolute inset-0 rounded-full border border-[#5E6AD2]/40"
              animate={{ scale: [1, 1.8], opacity: [0.6, 0] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: 'easeOut' }}
            />
            <motion.div
              className="absolute inset-0 rounded-full border border-[#5E6AD2]/25"
              animate={{ scale: [1, 2.4], opacity: [0.4, 0] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: 'easeOut', delay: 0.4 }}
            />
          </>
        )}

        <button
          id="voice-mic-button"
          onClick={toggleMic}
          disabled={isBusy || !speechSupported}
          aria-label={isListening ? 'Stop listening' : 'Start listening'}
          className={`relative w-24 h-24 rounded-full flex items-center justify-center transition-all duration-300 shadow-2xl
            ${isListening
              ? 'bg-[#5E6AD2] shadow-[#5E6AD2]/40 scale-110'
              : isBusy
                ? 'bg-white/[0.06] cursor-not-allowed opacity-50'
                : 'bg-white/[0.08] hover:bg-white/[0.12] border border-white/[0.1] hover:scale-105 cursor-pointer'
            }`}
        >
          {isThinking ? (
            <Loader2 className="w-9 h-9 text-foreground-muted animate-spin" />
          ) : isSpeaking ? (
            <Volume2 className="w-9 h-9 text-[#5E6AD2]" />
          ) : isListening ? (
            <MicOff className="w-9 h-9 text-white" />
          ) : (
            <Mic className="w-9 h-9 text-foreground-muted" />
          )}
        </button>
      </div>

      <div className="flex items-center gap-[3px] h-10">
        {waveformBars.map((_, i) => (
          <motion.div
            key={i}
            className={`w-1.5 rounded-full transition-colors duration-300 ${
              isListening ? 'bg-[#5E6AD2]' : 'bg-white/10'
            }`}
            animate={{ height: isListening ? barHeights[i] : 4 }}
            transition={{ duration: 0.08, ease: 'easeOut' }}
          />
        ))}
      </div>

      <motion.p
        key={status}
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        className={`text-sm font-medium ${
          isListening ? 'text-[#818cf8]' : isThinking || isSpeaking ? 'text-foreground-muted' : 'text-foreground-subtle'
        }`}
      >
        {statusLabel[status]}
      </motion.p>

      <AnimatePresence>
        {interimTranscript && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.95 }}
            className="px-5 py-2 rounded-full bg-white/[0.05] border border-white/[0.08] text-foreground-muted text-sm italic"
          >
            "{interimTranscript}"
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
