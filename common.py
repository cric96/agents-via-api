"""Minimal OpenAI Chat Completions shim shared by the two agent servers."""

import os
import time
import uuid

from fastapi import Header, HTTPException
from pydantic import BaseModel

# The agent's working directory: the only folder it can read (and nothing it can write).
WORKSPACE = os.path.abspath(os.environ.get("AGENT_CWD", "workspace"))
os.makedirs(WORKSPACE, exist_ok=True)


class ChatRequest(BaseModel):
    model: str
    messages: list[dict]
    stream: bool = False


def check_auth(authorization: str | None = Header(None)):
    # These servers run an agent on this machine: set AGENT_API_KEY before exposing them.
    key = os.environ.get("AGENT_API_KEY")
    if key and authorization != f"Bearer {key}":
        raise HTTPException(401, "invalid api key")


def _text(content) -> str:
    # content is a string, a list of {"type": "text", "text": ...} parts, or None
    if not content or isinstance(content, str):
        return content or ""
    return "\n".join(p.get("text", "") for p in content if p.get("type") == "text")


def split_messages(messages: list[dict]) -> tuple[str, str]:
    """Return (system prompt, user prompt). Multi-turn history is flattened into a transcript."""
    system = "\n".join(_text(m["content"]) for m in messages if m["role"] in ("system", "developer"))
    turns = [m for m in messages if m["role"] in ("user", "assistant")]
    if not turns:
        raise HTTPException(400, "no user message")
    if len(turns) == 1:
        return system, _text(turns[0]["content"])
    # ponytail: history is replayed on every call; reuse the agent session (resume / thread_resume) if it gets long
    transcript = "\n\n".join(f"{m['role'].upper()}: {_text(m['content'])}" for m in turns)
    return system, f"Conversation so far:\n\n{transcript}\n\nReply to the last USER message."


def completion(model: str, text: str, prompt_tokens: int = 0, completion_tokens: int = 0) -> dict:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }
