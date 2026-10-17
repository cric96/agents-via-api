"""Example 1: Claude Agent SDK exposed as an OpenAI-compatible /v1/chat/completions.

Run:  uv run uvicorn claude_server:app --port 8001
Model: "default", or any Claude model name/alias ("sonnet", "opus", "claude-opus-5-5", ...).
"""

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKError, ResultMessage, query
from fastapi import Depends, FastAPI, HTTPException

from common import WORKSPACE, ChatRequest, check_auth, completion, split_messages

# Read-only tools: the agent can explore WORKSPACE and the web, but not edit files or run commands.
TOOLS = ["Read", "Glob", "Grep", "WebSearch", "WebFetch"]

app = FastAPI()


@app.post("/v1/chat/completions", dependencies=[Depends(check_auth)])
async def chat(req: ChatRequest):
    if req.stream:
        raise HTTPException(400, "stream=True not supported")
    system, prompt = split_messages(req.messages)
    options = ClaudeAgentOptions(
        cwd=WORKSPACE,
        model=None if req.model == "default" else req.model,
        # keep Claude Code's agent prompt (tool usage etc.), append the caller's system message
        system_prompt={"type": "preset", "preset": "claude_code", "append": system},
        tools=TOOLS,
        allowed_tools=TOOLS,
        permission_mode="dontAsk",  # anything not pre-approved is denied, never prompted
        max_turns=20,
    )
    result = None
    try:
        async for msg in query(prompt=prompt, options=options):
            if isinstance(msg, ResultMessage):
                result = msg
    except ClaudeSDKError as e:  # bad key, max_turns reached, CLI crash, ...
        raise HTTPException(502, str(e))
    if result is None or result.is_error:
        raise HTTPException(502, (result and (result.result or str(result.errors))) or "agent produced no result")
    usage = result.usage or {}
    prompt_tokens = sum(usage.get(k, 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    return completion(req.model, result.result, prompt_tokens, usage.get("output_tokens", 0))
