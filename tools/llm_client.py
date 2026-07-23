import os
from dotenv import load_dotenv

# Load .env here, at import time, so this works no matter which script
# imports it first.
load_dotenv()

from groq import Groq

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# llama-3.3-70b-versatile is on Groq's free tier and strong enough for
# planning/analysis/report generation. If you hit rate limits, drop to
# "llama-3.1-8b-instant" — much higher free-tier throughput, lower quality.
_MODEL = "llama-3.3-70b-versatile"


def call_llm(prompt: str, max_tokens: int = 1000) -> str:
    """Single entry point for every agent's LLM call. Centralizing this
    means switching providers later only touches this one file."""
    response = _client.chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()
