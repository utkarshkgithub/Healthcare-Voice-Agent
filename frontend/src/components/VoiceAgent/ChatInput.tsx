import { Send } from 'lucide-react';

interface ChatInputProps {
  inputText: string;
  setInputText: (text: string) => void;
  handleTextSend: () => void;
  isBusy: boolean;
}

export function ChatInput({ inputText, setInputText, handleTextSend, isBusy }: ChatInputProps) {
  return (
    <div className="border-t border-white/[0.06] p-4 bg-white/[0.01]">
      <div className="flex items-center gap-3">
        <input
          id="voice-text-input"
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleTextSend()}
          placeholder="Or type your message…"
          disabled={isBusy}
          className="input-field flex-1 text-sm"
        />
        <button
          id="voice-send-button"
          onClick={handleTextSend}
          disabled={!inputText.trim() || isBusy}
          className="p-2.5 rounded-xl bg-[#5E6AD2] hover:bg-[#6872D9] text-white transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
      <p className="text-xs text-foreground-subtle mt-2 text-center">
        AI responses are for informational guidance only — not a substitute for professional medical advice.
      </p>
    </div>
  );
}
