# SHO.AI — Intelligent AI Agent

A full-stack AI Agent powered by Anthropic's Claude Opus, built with LangGraph, Flask, and React. SHO.AI can search the web, check weather, find news, analyze images, understand voice input, and remember conversations across sessions.

## 🌐 Live Demo
- **Frontend:** https://Shourav5000.github.io/sho-ai
- **Backend:** https://sho-ai-xxxx.onrender.com

## ✨ Features
- 🔍 **Web Search** — Real-time search powered by Tavily
- 🌤️ **Weather** — Live weather for any city
- 📰 **News Headlines** — Latest news on any topic
- 📖 **Wikipedia Search** — Instant knowledge lookup
- 🧮 **Calculator** — Smart math expressions
- 🖼️ **Image Recognition** — Upload images and ask questions (Claude Vision)
- 🎤 **Voice Input** — Speak your questions, no typing needed
- 💾 **Persistent Memory** — Remembers you between sessions
- ⚡ **Streaming Responses** — Words appear as Claude thinks
- 📝 **Conversation Summary** — Handles long chats automatically

## 🏗️ Architecture
```
Browser (React) → POST /chat → Flask API → LangGraph Agent → Claude Opus
                                         ↓
                              Tools: Tavily · Weather · Wikipedia · Calculator
```

## 🛠️ Tech Stack
- **Frontend:** React, CSS, GitHub Pages
- **Backend:** Python, Flask, Render
- **AI Framework:** LangGraph (LangChain)
- **LLM:** Anthropic Claude Opus (claude-opus-4-6)
- **Agent Tools:** Tavily Search, wttr.in Weather, Wikipedia, Calculator
- **Vision:** Anthropic Claude Vision API
- **Voice:** Web Speech API (browser native)
- **Memory:** JSON persistent storage

## 🚀 Local Setup

### Backend
```bash
pip install -r requirements.txt
```

Create `.env`:
```
ANTHROPIC_API_KEY=your-anthropic-key
TAVILY_API_KEY=your-tavily-key
```
```bash
python agent_api.py
```

### Frontend
```bash
cd frontend
npm install
npm start
```

Open `http://localhost:3000`

## 🤖 How the Agent Works
1. User sends a message
2. LangGraph agent decides which tools to use
3. Tools execute (search, weather, wiki, etc.)
4. Claude Opus synthesizes results into a response
5. Response streams back word by word
6. Conversation is summarized automatically when it gets long
7. Memory is saved between sessions

## 🔐 Security
- API keys stored server-side via environment variables
- Keys never exposed to the browser
- Frontend communicates only with the Flask backend

## 📦 Deployment
- **Frontend** deployed on GitHub Pages via `gh-pages`
- **Backend** deployed on Render (auto-deploys on every `git push`)