import os
import base64
import json
import requests
import wikipedia
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from langchain_anthropic import ChatAnthropic
from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
import anthropic

load_dotenv()

app = Flask(__name__)
CORS(app)

# ── Upgraded to Opus 4.6 — smartest model ─────────────────
llm = ChatAnthropic(
    model="claude-opus-4-6",
    anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
    max_tokens=4096
)

direct_client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)

search_tool = TavilySearch(
    max_results=5,
    tavily_api_key=os.environ.get("TAVILY_API_KEY")
)

@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression like '2 + 2' or '15 * 8.5'"""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def get_current_date(query: str) -> str:
    """Get the current date and time"""
    return f"Current date and time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

@tool
def wikipedia_search(query: str) -> str:
    """Search Wikipedia for information about a topic"""
    try:
        summary = wikipedia.summary(query, sentences=5)
        return f"Wikipedia: {summary}"
    except wikipedia.DisambiguationError as e:
        return f"Multiple results: {e.options[:3]}"
    except wikipedia.PageError:
        return f"No Wikipedia page found for '{query}'"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def get_weather(city: str) -> str:
    """Get current weather for a city"""
    try:
        url = f"https://wttr.in/{city}?format=3"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return f"Weather in {city}: {response.text.strip()}"
        return f"Could not get weather for {city}"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def get_news(topic: str) -> str:
    """Get latest news headlines about a topic"""
    try:
        news_search = TavilySearch(
            max_results=5,
            tavily_api_key=os.environ.get("TAVILY_API_KEY")
        )
        results = news_search.invoke(f"latest news {topic} 2026")
        return str(results)
    except Exception as e:
        return f"Error: {str(e)}"

tools = [search_tool, calculator, get_current_date, wikipedia_search, get_weather, get_news]
agent = create_react_agent(llm, tools)

# ── Persistent memory stored in JSON file ─────────────────
MEMORY_FILE = "memory.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

# ── Conversation summary helper ────────────────────────────
def summarize_conversation(messages):
    if len(messages) < 10:
        return messages

    # Summarize older messages keeping last 6
    old_messages = messages[:-6]
    recent_messages = messages[-6:]

    history_text = ""
    for msg in old_messages:
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        history_text += f"{role}: {content[:200]}\n"

    summary_response = direct_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": f"Summarize this conversation in 3-4 sentences:\n{history_text}"
        }]
    )

    summary = summary_response.content[0].text
    summary_message = SystemMessage(
        content=f"Earlier conversation summary: {summary}"
    )

    return [summary_message] + recent_messages

# ── In-memory conversations ────────────────────────────────
conversations = {}

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    session_id = data.get("session_id", "default")
    message = data.get("message", "")
    stream = data.get("stream", False)

    if not message:
        return jsonify({"error": "No message provided"}), 400

    # Load persistent memory for this session
    memory = load_memory()
    user_memory = memory.get(session_id, {})

    if session_id not in conversations:
        conversations[session_id] = []
        # Inject memory context if exists
        if user_memory.get("summary"):
            conversations[session_id].append(
                SystemMessage(content=f"Memory about this user: {user_memory['summary']}")
            )

    conversations[session_id].append(HumanMessage(content=message))

    # Auto summarize if conversation gets long
    conversations[session_id] = summarize_conversation(conversations[session_id])

    result = agent.invoke({"messages": conversations[session_id]})
    conversations[session_id] = result["messages"]

    final = result["messages"][-1].content

    # Update persistent memory
    memory[session_id] = memory.get(session_id, {})
    memory[session_id]["last_seen"] = datetime.now().isoformat()
    memory[session_id]["message_count"] = memory[session_id].get("message_count", 0) + 1

    # Extract name if mentioned
    if "my name is" in message.lower() or "i am" in message.lower():
        memory[session_id]["context"] = message[:100]

    save_memory(memory)

    tools_used = []
    for msg in result["messages"]:
        if hasattr(msg, "name") and msg.name:
            tools_used.append(msg.name)

    # ── Streaming response ─────────────────────────────────
    if stream:
        def generate():
            words = final.split(' ')
            for i, word in enumerate(words):
                chunk = word + (' ' if i < len(words) - 1 else '')
                yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"
            yield f"data: {json.dumps({'chunk': '', 'done': True, 'tools_used': tools_used})}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
        )

    return jsonify({"reply": final, "tools_used": list(set(tools_used))})

@app.route("/image", methods=["POST"])
def analyze_image():
    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400

    file = request.files["image"]
    question = request.form.get("question", "Please describe this image in detail.")
    image_data = base64.standard_b64encode(file.read()).decode("utf-8")
    media_type = file.content_type or "image/jpeg"

    response = direct_client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    },
                },
                {"type": "text", "text": question}
            ],
        }]
    )

    return jsonify({"reply": response.content[0].text})

@app.route("/memory/<session_id>", methods=["GET"])
def get_memory(session_id):
    memory = load_memory()
    return jsonify(memory.get(session_id, {}))

@app.route("/clear", methods=["POST"])
def clear():
    data = request.json
    session_id = data.get("session_id", "default")
    if session_id in conversations:
        del conversations[session_id]
    return jsonify({"message": "Conversation cleared"})

port = int(os.environ.get("PORT", 5002))

if __name__ == "__main__":
    print(f"SHO.AI API running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)