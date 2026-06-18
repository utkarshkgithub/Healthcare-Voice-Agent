import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, MicOff, Send, History, MessageSquare, Clock, Sparkles } from 'lucide-react';
import Navbar from '../components/Layout/Navbar';
import Background from '../components/Layout/Background';

interface Message {
  id: number;
  type: 'user' | 'agent';
  text: string;
  timestamp: Date;
}

interface HistorySession {
  id: number;
  date: string;
  summary: string;
  messagesCount: number;
  duration: string;
}

export default function VoiceAgent() {
  const [activeTab, setActiveTab] = useState<'chat' | 'history'>('chat');
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      type: 'agent',
      text: 'Hello! I\'m your AI health assistant. How can I help you today?',
      timestamp: new Date(),
    },
  ]);
  const [inputText, setInputText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const historyData: HistorySession[] = [
    { id: 1, date: '2026-07-05', summary: 'General health checkup discussion', messagesCount: 12, duration: '8 min' },
    { id: 2, date: '2026-07-03', summary: 'Headache symptoms consultation', messagesCount: 18, duration: '12 min' },
    { id: 3, date: '2026-07-01', summary: 'Medication reminder setup', messagesCount: 8, duration: '5 min' },
    { id: 4, date: '2026-06-28', summary: 'Diet and nutrition advice', messagesCount: 15, duration: '10 min' },
    { id: 5, date: '2026-06-25', summary: 'Sleep pattern analysis', messagesCount: 10, duration: '7 min' },
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = () => {
    if (!inputText.trim()) return;

    const userMessage: Message = {
      id: messages.length + 1,
      type: 'user',
      text: inputText,
      timestamp: new Date(),
    };

    setMessages([...messages, userMessage]);
    setInputText('');
    setIsTyping(true);

    // Simulate AI response
    setTimeout(() => {
      const agentMessage: Message = {
        id: messages.length + 2,
        type: 'agent',
        text: 'I understand your concern. Let me help you with that. Based on your symptoms, I recommend scheduling a consultation with a healthcare provider.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, agentMessage]);
      setIsTyping(false);
    }, 1500);
  };

  const toggleRecording = () => {
    setIsRecording(!isRecording);
    // TODO: Implement actual voice recording
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Background />
      <Navbar />
      
      <div className="flex-1 max-w-7xl w-full mx-auto px-6 py-8">
        {/* Header with Tabs */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mb-6"
        >
          <h1 className="text-4xl font-semibold text-gradient mb-6">AI Health Assistant</h1>
          
          <div className="flex gap-2 border-b border-white/[0.06]">
            <button
              onClick={() => setActiveTab('chat')}
              className={`px-6 py-3 text-sm font-medium transition-all duration-200 relative ${
                activeTab === 'chat'
                  ? 'text-foreground'
                  : 'text-foreground-muted hover:text-foreground'
              }`}
            >
              <div className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4" />
                Chat
              </div>
              {activeTab === 'chat' && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent"
                  transition={{ type: 'spring', duration: 0.5 }}
                />
              )}
            </button>
            
            <button
              onClick={() => setActiveTab('history')}
              className={`px-6 py-3 text-sm font-medium transition-all duration-200 relative ${
                activeTab === 'history'
                  ? 'text-foreground'
                  : 'text-foreground-muted hover:text-foreground'
              }`}
            >
              <div className="flex items-center gap-2">
                <History className="w-4 h-4" />
                History
              </div>
              {activeTab === 'history' && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent"
                  transition={{ type: 'spring', duration: 0.5 }}
                />
              )}
            </button>
          </div>
        </motion.div>

        {/* Content Area */}
        <AnimatePresence mode="wait">
          {activeTab === 'chat' ? (
            <motion.div
              key="chat"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.3 }}
              className="card-glass rounded-2xl overflow-hidden flex flex-col"
              style={{ height: 'calc(100vh - 280px)' }}
            >
              {/* Messages Area */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {messages.map((message) => (
                  <motion.div
                    key={message.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
                    className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[70%] rounded-2xl px-5 py-3 ${
                        message.type === 'user'
                          ? 'bg-accent text-white'
                          : 'bg-white/[0.08] text-foreground border border-white/[0.06]'
                      }`}
                    >
                      {message.type === 'agent' && (
                        <div className="flex items-center gap-2 mb-2">
                          <div className="w-6 h-6 rounded-full bg-gradient-to-br from-accent to-purple-600 flex items-center justify-center">
                            <Sparkles className="w-3 h-3 text-white" />
                          </div>
                          <span className="text-xs text-foreground-muted font-medium">AI Assistant</span>
                        </div>
                      )}
                      <p className="text-sm leading-relaxed">{message.text}</p>
                      <p className={`text-xs mt-2 ${
                        message.type === 'user' ? 'text-white/70' : 'text-foreground-subtle'
                      }`}>
                        {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                  </motion.div>
                ))}
                
                {isTyping && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex justify-start"
                  >
                    <div className="bg-white/[0.08] rounded-2xl px-5 py-3 border border-white/[0.06]">
                      <div className="flex gap-2">
                        <div className="w-2 h-2 rounded-full bg-foreground-muted animate-bounce" style={{ animationDelay: '0ms' }} />
                        <div className="w-2 h-2 rounded-full bg-foreground-muted animate-bounce" style={{ animationDelay: '150ms' }} />
                        <div className="w-2 h-2 rounded-full bg-foreground-muted animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                    </div>
                  </motion.div>
                )}
                
                <div ref={messagesEndRef} />
              </div>

              {/* Input Area */}
              <div className="border-t border-white/[0.06] p-4 bg-white/[0.02]">
                <div className="flex items-end gap-3">
                  <button
                    onClick={toggleRecording}
                    className={`p-3 rounded-xl transition-all duration-300 ${
                      isRecording
                        ? 'bg-red-500 text-white shadow-lg shadow-red-500/30 animate-pulse'
                        : 'bg-white/[0.05] hover:bg-white/[0.08] text-foreground-muted border border-white/[0.06]'
                    }`}
                  >
                    {isRecording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
                  </button>
                  
                  <div className="flex-1 relative">
                    <input
                      type="text"
                      value={inputText}
                      onChange={(e) => setInputText(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                      placeholder="Type your message or use voice..."
                      className="input-field w-full pr-12"
                    />
                    <button
                      onClick={handleSendMessage}
                      className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-lg bg-accent hover:bg-accent-bright 
                               text-white transition-all duration-200 disabled:opacity-50"
                      disabled={!inputText.trim()}
                    >
                      <Send className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                <p className="text-xs text-foreground-subtle mt-2 text-center">
                  AI responses are for informational purposes only. Consult a healthcare professional for medical advice.
                </p>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="history"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
              className="card-glass rounded-2xl p-6"
              style={{ height: 'calc(100vh - 280px)' }}
            >
              <div className="overflow-y-auto h-full space-y-3">
                {historyData.map((session, index) => (
                  <motion.div
                    key={session.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: index * 0.05 }}
                    className="bg-white/[0.02] hover:bg-white/[0.05] rounded-xl p-5 border border-white/[0.06] 
                             hover:border-white/[0.1] transition-all duration-200 cursor-pointer group"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <h3 className="text-foreground font-medium group-hover:text-accent transition-colors">
                          {session.summary}
                        </h3>
                        <div className="flex items-center gap-4 mt-2 text-sm text-foreground-muted">
                          <div className="flex items-center gap-1">
                            <Clock className="w-4 h-4" />
                            <span>{session.date}</span>
                          </div>
                          <span>•</span>
                          <span>{session.messagesCount} messages</span>
                          <span>•</span>
                          <span>{session.duration}</span>
                        </div>
                      </div>
                      <div className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/30 flex items-center justify-center
                                    group-hover:bg-accent/20 transition-colors">
                        <MessageSquare className="w-4 h-4 text-accent" />
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
