"""Example 2: Codex Python SDK exposed as an OpenAI-compatible /v1/chat/completions.

Run:  uv run uvicorn codex_server:app --port 8002
Model: "default", or a Codex model id (list them with `Codex().models()`).
"""

import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from openai_codex import ApprovalMode, AsyncCodex, CodexConfig, Sandbox

from common import WORKSPACE, ChatRequest, check_auth, completion, split_messages

codex: AsyncCodex


@asynccontextmanager
async def lifespan(_app):
    global codex
    key = os.environ.get("CODEX_API_KEY")
    config = None
    if key:
        # API-key login goes to a server-only CODEX_HOME, so the ChatGPT login in ~/.codex stays untouched
        home = os.environ.get("CODEX_HOME") or os.path.abspath(".codex-server")
        os.makedirs(home, exist_ok=True)
        config = CodexConfig(env={"CODEX_HOME": home})
    async with AsyncCodex(config) as codex:  # one `codex app-server` subprocess for the whole server
        if key:
            await codex.login_api_key(key)  # the SDK ignores *_API_KEY env vars, it needs an explicit login
        yield


app = FastAPI(lifespan=lifespan)


@app.post("/v1/chat/completions", dependencies=[Depends(check_auth)])
async def chat(req: ChatRequest):
    if req.stream:
        raise HTTPException(400, "stream=True not supported")
    system, prompt = split_messages(req.messages)
    thread = await codex.thread_start(
        cwd=WORKSPACE,
        model=None if req.model == "default" else req.model,
        developer_instructions=system or None,
        sandbox=Sandbox.read_only,  # OS-level sandbox: commands run, but can't write anywhere
        approval_mode=ApprovalMode.deny_all,  # never escalate out of the sandbox
        ephemeral=True,  # don't persist the thread in ~/.codex
    )
    try:
        result = await thread.run(prompt)
    except RuntimeError as e:  # failed turn: bad key, rate limit, ...
        raise HTTPException(502, str(e))
    usage = result.usage.total if result.usage else None
    return completion(
        req.model,
        result.final_response or "",
        usage.input_tokens if usage else 0,
        usage.output_tokens if usage else 0,
    )
