import os
from typing import List, Dict, Any
from dotenv import load_dotenv
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except Exception:
    genai = None
    types = None
    HAS_GENAI = False

load_dotenv()

SYSTEM_INSTRUCTION = """
You are the SmartMonitor AI Assistant, an enterprise copilot for site monitoring, occupancy, attendance, and project safety analytics.

CRITICAL RULES:
1. Answer ONLY using the facts provided in the Database Context and Chat History below.
2. If the user asks a question about data NOT present in the Database Context, clearly state: "I do not have access to that information in the system records."
3. Never make up dates, attendance status, camera locations, or safety metrics.
4. Keep answers concise, professional, and directly actionable.
"""

class LLMService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not HAS_GENAI or not api_key or api_key == "your_gemini_api_key_here":
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)
            
        # Memory storage per user session
        self.sessions: Dict[str, List[Dict[str, str]]] = {}

    def get_session_history(self, user_id: str) -> List[Dict[str, str]]:
        return self.sessions.get(user_id, [])

    def update_session_history(self, user_id: str, role: str, content: str):
        if user_id not in self.sessions:
            self.sessions[user_id] = []
        self.sessions[user_id].append({"role": role, "content": content})
        if len(self.sessions[user_id]) > 10:
            self.sessions[user_id] = self.sessions[user_id][-10:]

    def generate_response(self, query: str, intent: str, context_data: dict, user_id: str = "default_user") -> str:
        history = self.get_session_history(user_id)
        
        history_str = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history])
        
        prompt = f"""
Chat History:
{history_str if history_str else "No previous history."}

Database Context (Retrieved for current turn):
{context_data}

Current User Query:
{query}
"""

        if not self.client:
            reply = f"[System Mode - No Gemini API Key set]\nIntent: {intent}\nRetrieved Data: {context_data}"
            self.update_session_history(user_id, "user", query)
            self.update_session_history(user_id, "assistant", reply)
            return reply

        try:
            response = self.client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.2,
                ),
            )
            reply = response.text
            
            self.update_session_history(user_id, "user", query)
            self.update_session_history(user_id, "assistant", reply)
            
            return reply
        except Exception as e:
            return f"Error communicating with Gemini LLM API: {str(e)}"

llm_service = LLMService()