import { RefObject } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles } from 'lucide-react';
import { Message, AgentStatus } from '../../types';

interface MessageListProps {
  messages: Message[];
  status: AgentStatus;
  messagesEndRef: RefObject<HTMLDivElement | null>;
}

export function MessageList({ messages, status, messagesEndRef }: MessageListProps) {
  const isThinking = status === 'thinking';

  return (
    <div className="flex-1 overflow-y-auto p-5 space-y-4">
      {messages.map((message) => (
        <motion.div
          key={message.id}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
          className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`max-w-[80%] rounded-2xl px-5 py-3 ${
              message.type === 'user'
                ? 'bg-[#5E6AD2] text-white'
                : 'bg-white/[0.06] text-foreground border border-white/[0.06]'
            }`}
          >
            {message.type === 'agent' && (
              <div className="flex items-center gap-2 mb-1.5">
                <div className="w-5 h-5 rounded-full bg-gradient-to-br from-[#5E6AD2] to-purple-600 flex items-center justify-center">
                  <Sparkles className="w-2.5 h-2.5 text-white" />
                </div>
                <span className="text-xs text-foreground-muted font-medium">AI Assistant</span>
              </div>
            )}
            <p className="text-sm leading-relaxed">{message.text}</p>
            <p className={`text-xs mt-1.5 ${message.type === 'user' ? 'text-white/60' : 'text-foreground-subtle'}`}>
              {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </p>
          </div>
        </motion.div>
      ))}

      {/* Thinking indicator */}
      <AnimatePresence>
        {isThinking && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex justify-start"
          >
            <div className="bg-white/[0.06] rounded-2xl px-5 py-3 border border-white/[0.06]">
              <div className="flex gap-1.5 items-center">
                <div className="w-2 h-2 rounded-full bg-[#5E6AD2] animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 rounded-full bg-[#5E6AD2] animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 rounded-full bg-[#5E6AD2] animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div ref={messagesEndRef} />
    </div>
  );
}
