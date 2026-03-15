import os
import math
import hashlib
import requests
import wikipedia
from datetime import datetime
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

load_dotenv()

llm = ChatAnthropic(
    model="claude-sonnet-4-6",
    anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
    max_tokens=2048
)

# ── Tools ─────────────────────────────────────────────────

search_tool = TavilySearch(
    max_results=3,
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
        summary = wikipedia.summary(query, sentences=4)
        return f"Wikipedia: {summary}"
    except wikipedia.DisambiguationError as e:
        return f"Multiple results found: {e.options[:3]}"
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
    """Get latest news headlines about a topic using web search"""
    try:
        from langchain_tavily import TavilySearch
        news_search = TavilySearch(
            max_results=3,
            tavily_api_key=os.environ.get("TAVILY_API_KEY")
        )
        results = news_search.invoke(f"latest news {topic} 2026")
        return str(results)
    except Exception as e:
        return f"Error fetching news: {str(e)}"

tools = [search_tool, calculator, get_current_date, wikipedia_search, get_weather, get_news]

# ── Agent ─────────────────────────────────────────────────
from langgraph.prebuilt import create_react_agent as create_langgraph_agent

agent = create_langgraph_agent(llm, tools)

if __name__ == "__main__":
    print("=" * 50)
    print("  SHO.AI — Your Personal AI Agent")
    print("  Type 'quit' to exit")
    print("=" * 50)

    # Memory — keeps full conversation history
    conversation_history = []

    while True:
        question = input("\nYou: ").strip()
        if question.lower() == "quit":
            break

        # Add user message to history
        conversation_history.append(HumanMessage(content=question))

        result = agent.invoke({
            "messages": conversation_history
        })

        # Get the final response
        final_message = result["messages"][-1]
        final = final_message.content
        
        # Add assistant response to history
        conversation_history = result["messages"]

        print(f"\nSHO.AI: {final}\n")