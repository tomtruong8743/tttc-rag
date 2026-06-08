"""
LLM client abstraction — supports Anthropic, Gemini (free), and Ollama (local).

Set LLM_BACKEND environment variable:
  - "gemini"    — FREE, requires GEMINI_API_KEY from aistudio.google.com
  - "anthropic" — requires ANTHROPIC_API_KEY
  - "ollama"    — free, runs locally, requires Ollama installed

Gemini free tier:
  - 15 requests/minute, 1 million tokens/day
  - Get a free key at: https://aistudio.google.com/app/apikey

Usage:
    # Gemini (free)
    export LLM_BACKEND=gemini
    export GEMINI_API_KEY=your-free-key

    # Anthropic
    export ANTHROPIC_API_KEY=sk-ant-...

    # Ollama (local)
    export LLM_BACKEND=ollama
    export OLLAMA_MODEL=qwen2.5
"""

import os

LLM_BACKEND     = os.environ.get("LLM_BACKEND", "gemini").lower()
GEMINI_MODEL    = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
ANTHROPIC_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
OLLAMA_MODEL    = os.environ.get("OLLAMA_MODEL", "llama3.2")
OLLAMA_URL      = os.environ.get("OLLAMA_URL", "http://localhost:11434")


def chat(system: str, user: str, max_tokens: int = 4096) -> str:
    """Send a chat message and return the response text."""
    if LLM_BACKEND == "gemini":
        return _gemini_chat(system, user, max_tokens)
    elif LLM_BACKEND == "ollama":
        return _ollama_chat(system, user, max_tokens)
    else:
        return _anthropic_chat(system, user, max_tokens)


def _gemini_chat(system: str, user: str, max_tokens: int) -> str:
    import requests
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Get a free key at https://aistudio.google.com/app/apikey")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={api_key}"
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }
    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected Gemini response: {data}") from e


def _anthropic_chat(system: str, user: str, max_tokens: int) -> str:
    import anthropic
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text.strip()


def _ollama_chat(system: str, user: str, max_tokens: int) -> str:
    import requests
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "stream": False,
        "options": {"num_predict": max_tokens},
    }
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=300)
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Could not connect to Ollama. Make sure it is running: ollama serve"
        )


def backend_info() -> str:
    if LLM_BACKEND == "gemini":
        return f"Gemini ({GEMINI_MODEL})"
    if LLM_BACKEND == "ollama":
        return f"Ollama ({OLLAMA_MODEL})"
    return f"Anthropic ({ANTHROPIC_MODEL})"
