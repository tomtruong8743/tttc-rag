"""
LLM client abstraction — supports both Anthropic (Claude) and Ollama (local, free).

Set LLM_BACKEND environment variable:
  - "anthropic" (default) — requires ANTHROPIC_API_KEY
  - "ollama"              — free, runs locally, requires Ollama installed

Set OLLAMA_MODEL to choose the model (default: llama3.2)
Recommended models for Vietnamese legal documents:
  - llama3.2        (fast, good quality)
  - qwen2.5         (best Vietnamese support)
  - mistral         (good multilingual)

Usage:
    # Use Anthropic (default)
    export ANTHROPIC_API_KEY=sk-ant-...

    # Use Ollama (free)
    export LLM_BACKEND=ollama
    export OLLAMA_MODEL=qwen2.5
"""

import os
from typing import Optional


LLM_BACKEND   = os.environ.get("LLM_BACKEND", "anthropic").lower()
ANTHROPIC_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
OLLAMA_MODEL  = os.environ.get("OLLAMA_MODEL", "llama3.2")
OLLAMA_URL    = os.environ.get("OLLAMA_URL", "http://localhost:11434")


def chat(system: str, user: str, max_tokens: int = 4096) -> str:
    """Send a chat message and return the response text."""
    if LLM_BACKEND == "ollama":
        return _ollama_chat(system, user, max_tokens)
    else:
        return _anthropic_chat(system, user, max_tokens)


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
            "Could not connect to Ollama. Make sure Ollama is running: "
            "open a terminal and run 'ollama serve'"
        )


def backend_info() -> str:
    if LLM_BACKEND == "ollama":
        return f"Ollama ({OLLAMA_MODEL})"
    return f"Anthropic ({ANTHROPIC_MODEL})"
