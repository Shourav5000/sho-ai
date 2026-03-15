import { useState, useRef, useEffect } from 'react';
import './AgentWindow.css';

const TOOL_CONFIG = {
  tavily_search: { label: 'Web Search', emoji: '🔍' },
  wikipedia_search: { label: 'Wikipedia', emoji: '📖' },
  get_weather: { label: 'Weather', emoji: '🌤️' },
  get_news: { label: 'News', emoji: '📰' },
  calculator: { label: 'Calculator', emoji: '🧮' },
  get_current_date: { label: 'Date & Time', emoji: '📅' },
};

const SUGGESTIONS = [
  { text: 'What is the weather in New York?', emoji: '🌤️' },
  { text: 'Latest AI news today', emoji: '📰' },
  { text: 'Search Wikipedia for quantum computing', emoji: '📖' },
  { text: 'What is 15% of 85000?', emoji: '🧮' },
];

export default function AgentWindow() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showWelcome, setShowWelcome] = useState(true);
  const [listening, setListening] = useState(false);
  const [imagePreview, setImagePreview] = useState(null);
  const [imageFile, setImageFile] = useState(null);
  const [sessionId] = useState(() => Math.random().toString(36).slice(2));
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const fileRef = useRef(null);
  const recognitionRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // ── Speech Recognition ─────────────────────────────────
  const toggleMic = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Speech recognition not supported. Try Chrome!');
      return;
    }
    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';
    recognition.onstart = () => setListening(true);
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);
    recognition.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      setInput(prev => prev + (prev ? ' ' : '') + transcript);
    };
    recognitionRef.current = recognition;
    recognition.start();
  };

  // ── Image Upload ───────────────────────────────────────
  const handleImageUpload = (file) => {
    if (!file) return;
    setImageFile(file);
    const reader = new FileReader();
    reader.onload = (e) => setImagePreview(e.target.result);
    reader.readAsDataURL(file);
  };

  const removeImage = () => {
    setImageFile(null);
    setImagePreview(null);
  };

  // ── Send Message ───────────────────────────────────────
  const sendMessage = async (text) => {
    const userText = text || input.trim();
    if ((!userText && !imageFile) || loading) return;

    setInput('');
    setShowWelcome(false);
    setLoading(true);

    const userMsg = {
      role: 'user',
      content: userText || 'What do you see in this image?',
      image: imagePreview
    };
    setMessages(prev => [...prev, userMsg]);

    const currentImage = imageFile;
    setImageFile(null);
    setImagePreview(null);

    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 60000);

      if (currentImage) {
        // ── Image analysis ───────────────────────────────
        const formData = new FormData();
        formData.append('image', currentImage);
        formData.append('question', userText || 'Please describe this image in detail.');
        const res = await fetch('http://localhost:5002/image', {
          method: 'POST',
          body: formData,
          signal: controller.signal
        });
        clearTimeout(timeout);
        const data = await res.json();
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.reply,
          tools_used: ['🖼️ Vision']
        }]);

      } else {
        // ── Streaming chat ───────────────────────────────
        const res = await fetch('http://localhost:5002/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: userText,
            session_id: sessionId,
            stream: true
          }),
          signal: controller.signal
        });

        clearTimeout(timeout);

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let streamedText = '';
        let tools_used = [];

        // Add empty message to stream into
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: '',
          tools_used: [],
          streaming: true
        }]);

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const parsed = JSON.parse(line.slice(6));
                if (parsed.done) {
                  tools_used = parsed.tools_used || [];
                } else {
                  streamedText += parsed.chunk;
                  setMessages(prev => {
                    const updated = [...prev];
                    updated[updated.length - 1] = {
                      role: 'assistant',
                      content: streamedText,
                      tools_used: [],
                      streaming: true
                    };
                    return updated;
                  });
                }
              } catch {}
            }
          }
        }

        // Finalize streamed message
        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: 'assistant',
            content: streamedText,
            tools_used,
            streaming: false
          };
          return updated;
        });
      }

    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "Oops! I couldn't connect. Make sure the backend is running on port 5002! 🙈",
        tools_used: []
      }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const clearChat = async () => {
    await fetch('http://localhost:5002/clear', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId })
    });
    setMessages([]);
    setShowWelcome(true);
  };

  return (
    <div className="agent-shell">
      {/* Header */}
      <div className="agent-header">
        <div className="logo">
          <div className="logo-icon">✦</div>
          <div className="logo-name">
            <span className="sho">Sho</span><span className="dot">.</span><span className="ai">ai</span>
          </div>
          <div className="live-badge">● live</div>
        </div>
        <div className="header-right">
          <div className="tool-pills">
            {Object.values(TOOL_CONFIG).map((cfg, i) => (
              <span key={i} className="tool-pill" title={cfg.label}>{cfg.emoji}</span>
            ))}
            <span className="tool-pill" title="Image Analysis">🖼️</span>
            <span className="tool-pill" title="Voice Input">🎤</span>
          </div>
          <button className="clear-btn" onClick={clearChat} title="New chat">✕</button>
        </div>
      </div>

      {/* Messages */}
      <div className="messages-area">
        {showWelcome && (
          <div className="welcome">
            <div className="welcome-avatar">✦</div>
            <h2>Hey there! I'm <span>Sho.ai</span> 👋</h2>
            <p>I'm your smart AI assistant powered by Claude Opus! I can search the web, check weather, find news, look up Wikipedia, do math, analyze images, and understand your voice!</p>
            <div className="feature-row">
              <span className="feature-chip">🖼️ Image Analysis</span>
              <span className="feature-chip">🎤 Voice Input</span>
              <span className="feature-chip">🔍 Web Search</span>
              <span className="feature-chip">🌤️ Weather</span>
              <span className="feature-chip">💾 Remembers You</span>
              <span className="feature-chip">⚡ Streaming</span>
            </div>
            <div className="suggestions-grid">
              {SUGGESTIONS.map((s, i) => (
                <button key={i} className="suggestion-card" onClick={() => sendMessage(s.text)}>
                  <span>{s.emoji}</span>
                  <span>{s.text}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`msg ${msg.role}`}>
            {msg.role === 'assistant' && <div className="bot-avatar">✦</div>}
            <div className="msg-body">
              {msg.image && (
                <img src={msg.image} alt="uploaded" className="msg-image" />
              )}
              {msg.tools_used && msg.tools_used.length > 0 && (
                <div className="tools-row">
                  {msg.tools_used.map((t, j) => {
                    const cfg = TOOL_CONFIG[t];
                    return (
                      <span key={j} className="tool-chip">
                        {cfg ? `${cfg.emoji} ${cfg.label}` : t}
                      </span>
                    );
                  })}
                </div>
              )}
              <div className={`bubble ${msg.role} ${msg.streaming ? 'streaming' : ''}`}
                style={{ whiteSpace: 'pre-line' }}>
                {msg.content}
                {msg.streaming && <span className="cursor">▊</span>}
              </div>
            </div>
          </div>
        ))}

        {loading && messages.length > 0 && !messages[messages.length - 1].streaming && (
          <div className="msg assistant">
            <div className="bot-avatar">✦</div>
            <div className="bubble assistant thinking">
              <span className="dot-1">●</span>
              <span className="dot-2">●</span>
              <span className="dot-3">●</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Image Preview */}
      {imagePreview && (
        <div className="image-preview-bar">
          <img src={imagePreview} alt="preview" />
          <span>Image ready to send ✅</span>
          <button onClick={removeImage}>✕</button>
        </div>
      )}

      {/* Input */}
      <div className="input-area">
        <div className="input-row">
          <button className="action-btn" onClick={() => fileRef.current.click()} title="Upload image">
            🖼️
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            style={{ display: 'none' }}
            onChange={e => handleImageUpload(e.target.files[0])}
          />
          <button
            className={`action-btn ${listening ? 'listening' : ''}`}
            onClick={toggleMic}
            title="Voice input"
          >
            {listening ? '🔴' : '🎤'}
          </button>
          <input
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && sendMessage()}
            placeholder={
              listening ? 'Listening... 🎤' :
              imageFile ? 'Ask about the image or just send it...' :
              'Ask Sho.ai anything... 💬'
            }
            disabled={loading}
          />
          <button
            className="send-btn"
            onClick={() => sendMessage()}
            disabled={loading || (!input.trim() && !imageFile)}
          >
            ➤
          </button>
        </div>
        <p className="input-hint">✨ Powered by Claude Opus · Web · Weather · News · Wikipedia · 🖼️ Images · 🎤 Voice</p>
      </div>
    </div>
  );
}