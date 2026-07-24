import React, { useState } from 'react';
import { Send, Paperclip, Loader2 } from 'lucide-react';

interface ChatInputBoxProps {
  onSendMessage: (text: string) => void;
  disabled?: boolean;
}

export const ChatInputBox: React.FC<ChatInputBoxProps> = ({ onSendMessage, disabled }) => {
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || disabled) return;
    onSendMessage(input.trim());
    setInput('');
  };

  return (
    <form onSubmit={handleSubmit} className="p-4 border-t border-border bg-card/40">
      <div className="flex items-center space-x-2 bg-muted/30 p-2 rounded-2xl border border-border focus-within:border-primary transition-all">
        <button
          type="button"
          className="p-2 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
          title="Attach RAG Document"
        >
          <Paperclip className="w-5 h-5" />
        </button>

        <textarea
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
          placeholder="Ask agentic-resolution-platform or submit task..."
          className="flex-1 bg-transparent border-none text-sm text-foreground placeholder:text-muted-foreground focus:outline-none resize-none py-1.5 max-h-32"
        />

        <button
          type="submit"
          aria-label="Send message"
          disabled={!input.trim() || disabled}
          className="p-2.5 rounded-xl bg-primary text-primary-foreground disabled:opacity-40 hover:opacity-90 transition-all shadow-md shadow-blue-500/20"
        >
          {disabled ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </button>
      </div>
    </form>
  );
};
