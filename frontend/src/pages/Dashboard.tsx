import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Mic, MessageSquare, Clock, ChevronRight, Activity, Zap, Shield } from 'lucide-react';
import Navbar from '../components/Layout/Navbar';
import DarkVeil from '../components/Layout/DarkVeil';
import SpotlightCard from '../components/Layout/SpotlightCard';

interface StoredSession {
  date: string;
  firstMessage: string;
  lastMessage: string;
  messageCount: number;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [recentSessions] = useState<StoredSession[]>(() => {
    try {
      const raw = localStorage.getItem('voice_sessions');
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  });

  const howItWorks = [
    {
      icon: Mic,
      step: '01',
      title: 'Share Your Symptoms',
      desc: 'Simply speak into your microphone to describe what you are feeling — no typing required.',
      color: 'from-blue-500 to-indigo-500',
    },
    {
      icon: Zap,
      step: '02',
      title: 'Instant AI Analysis',
      desc: 'Our advanced AI instantly analyzes your voice and cross-references medical databases.',
      color: 'from-purple-500 to-pink-500',
    },
    {
      icon: Shield,
      step: '03',
      title: 'Get Real Guidance',
      desc: 'Receive evidence-based advice, risk assessment, and clear next steps — spoken back to you.',
      color: 'from-emerald-500 to-teal-500',
    },
  ];

  return (
    <div className="min-h-screen">
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

      <div className="max-w-5xl mx-auto px-6 py-10 space-y-12">

        {/* Hero CTA */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center space-y-6"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#5E6AD2]/10 border border-[#5E6AD2]/30 text-xs text-[#818cf8] font-medium mb-2">
            <Activity className="w-3.5 h-3.5" />
            Voice-First Healthcare AI
          </div>
          <h1 className="text-5xl font-semibold text-gradient leading-tight">
            Talk to your<br />AI health assistant
          </h1>
          <p className="text-foreground-muted text-lg max-w-xl mx-auto">
            Describe how you feel. The AI listens, triages, and guides you — in real time, with your voice.
          </p>

          <motion.button
  id="start-voice-session"
  onClick={() => navigate("/voice-agent")}
  whileHover={{ scale: 1.03, y: -2 }}
  whileTap={{ scale: 0.98 }}
  className="
    inline-flex items-center gap-4
    rounded-2xl
    bg-white
    px-8 py-4
    text-black
    font-semibold text-lg
    shadow-lg
    transition-all duration-300
    hover:bg-neutral-100
    hover:shadow-[0_12px_40px_rgba(255,255,255,0.18)]
    active:bg-neutral-200
  "
>
  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-neutral-100">
    <Mic className="h-5 w-5 text-black" />
  </div>

  <span>Start Voice Session</span>

  <ChevronRight className="h-5 w-5 text-neutral-700" />
</motion.button>
        </motion.div>

        {/* How it works */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15 }}
        >
          <h2 className="text-xl font-semibold text-foreground mb-6 text-center">How it works</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {howItWorks.map((item, i) => {
              const Icon = item.icon;
              return (
  <motion.div
    key={item.step}
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.4, delay: 0.2 + i * 0.1 }}
    className="h-full"
  >
    <SpotlightCard className="h-full">
      <div className="relative z-10 flex flex-col h-full space-y-4">


        <h3 className="text-foreground font-semibold underline">
          {item.title}
        </h3>

        <p className="text-foreground-muted text-sm leading-relaxed">
          {item.desc}
        </p>
      </div>
    </SpotlightCard>
  </motion.div>
);
            })}
          </div>
        </motion.div>

        {/* Recent sessions — from real localStorage */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
        >
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-xl font-semibold text-foreground">Recent Sessions</h2>
            <button
              onClick={() => navigate('/voice-agent')}
              className="text-sm text-[#5E6AD2] hover:text-[#818cf8] transition-colors flex items-center gap-1"
            >
              New session <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          {recentSessions.length === 0 ? (
            <div className="card-glass rounded-2xl p-10 text-center space-y-3">
              <div className="w-14 h-14 rounded-full bg-white/[0.04] border border-white/[0.08] flex items-center justify-center mx-auto">
                <MessageSquare className="w-6 h-6 text-foreground-subtle" />
              </div>
              <p className="text-foreground-muted text-sm">No sessions yet.</p>
              <p className="text-foreground-subtle text-xs">
                Your conversation history will appear here after your first voice session.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {recentSessions.map((session, i) => (
                <motion.div
                  key={session.date + i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: i * 0.05 }}
                  onClick={() => navigate('/voice-agent')}
                  className="card-glass rounded-xl p-5 flex items-center gap-4 hover:border-white/[0.12] 
                             hover:bg-white/[0.04] transition-all duration-200 cursor-pointer group"
                >
                  <div className="w-10 h-10 rounded-xl bg-[#5E6AD2]/10 border border-[#5E6AD2]/20 flex items-center justify-center shrink-0">
                    <MessageSquare className="w-5 h-5 text-[#5E6AD2]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-foreground text-sm font-medium truncate group-hover:text-[#818cf8] transition-colors">
                      "{session.firstMessage}"
                    </p>
                    <div className="flex items-center gap-3 mt-1 text-xs text-foreground-subtle">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {session.date}
                      </span>
                      <span>•</span>
                      <span>{session.messageCount} messages</span>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-foreground-subtle group-hover:text-foreground transition-colors" />
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>

      </div>
    </div>
  );
}
