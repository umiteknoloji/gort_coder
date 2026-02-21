import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Send, Settings, Plus } from 'lucide-react';
import './App.css';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  tool_used?: string;
}

interface ChatResponse {
  response: string;
  session_id: string;
  tool_used?: string;
}

const API_URL = 'http://127.0.0.1:8000';

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [loading, setLoading] = useState(false);
  const [isMultiline, setIsMultiline] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize session on mount
  useEffect(() => {
    createNewSession();
  }, []);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const createNewSession = async () => {
    try {
      const response = await axios.post(`${API_URL}/session/create`);
      setSessionId(response.data.session_id);
      setMessages([]);
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !sessionId) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const response = await axios.post<ChatResponse>(`${API_URL}/chat`, {
        message: userMessage,
        session_id: sessionId,
      });

      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: response.data.response,
          tool_used: response.data.tool_used,
        },
      ]);
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || 'Failed to get response';
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: `❌ Error: ${errorMsg}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (!isMultiline && e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(e as any);
    }
  };

  return (
    <div className="app">
      {/* Header */}
      <div className="header">
        <div className="header-title">
          <h1>🤖 Gort</h1>
          <p>AI Yazılımcı Ortağı</p>
        </div>
        <div className="header-actions">
          <button
            className="btn-icon"
            onClick={createNewSession}
            title="New conversation"
          >
            <Plus size={20} />
          </button>
          <button className="btn-icon" title="Settings">
            <Settings size={20} />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="messages-container">
        {messages.length === 0 && (
          <div className="empty-state">
            <h2>Hoşgeldin!</h2>
            <p>Gort ile konuşmaya başla</p>
            <div className="suggestions">
              <button onClick={() => setInput('Merhaba, nasılsın?')}>
                Merhaba
              </button>
              <button onClick={() => setInput('GitHub\'da repo oluştur')}>
                GitHub
              </button>
              <button onClick={() => setInput('Vercel projelerim neler?')}>
                Vercel
              </button>
            </div>
          </div>
        )}
        {messages.map((msg, idx) => (
          <div key={idx} className={`message message-${msg.role}`}>
            <div className="message-avatar">
              {msg.role === 'user' ? '👤' : '🤖'}
            </div>
            <div className="message-content">
              <p>{msg.content}</p>
              {msg.tool_used && (
                <span className="tool-badge">🔧 {msg.tool_used}</span>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="message message-assistant">
            <div className="message-avatar">🤖</div>
            <div className="message-content">
              <div className="typing">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form className="input-area" onSubmit={sendMessage}>
        <div className="input-wrapper">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              isMultiline
                ? 'Çok satırlı mesaj yazın... (Shift+Enter for newline)'
                : 'Mesajınız...'
            }
            rows={isMultiline ? 4 : 1}
            disabled={loading}
            className="input-field"
          />
          <div className="input-controls">
            <button
              type="button"
              className={`btn-multiline ${isMultiline ? 'active' : ''}`}
              onClick={() => setIsMultiline(!isMultiline)}
              title="Toggle multiline"
            >
              ⋮
            </button>
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="btn-send"
              title="Send (Ctrl+Enter)"
            >
              <Send size={20} />
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

export default App;
