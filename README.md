# Agents as remote LLMs

Two servers that expose an agent through the OpenAI API (`POST /v1/chat/completions`):
`claude_server.py` uses the Claude Agent SDK, `codex_server.py` uses the Codex SDK.

## Login

The servers reuse the login you already have for the two agents, so you only do it once:

```bash
claude auth login   # with your Claude account
codex login         # with your ChatGPT account
```

## Run

```bash
uv sync
uv run uvicorn claude_server:app --port 8001
uv run uvicorn codex_server:app --port 8002
uv run python client.py claude "What's in your working directory?"
uv run python client.py codex "Hi!" -m gpt-6.1-sol
```

Or with curl:

```bash
curl localhost:8001/v1/chat/completions -H 'content-type: application/json' \
  -d '{"model": "default", "messages": [{"role": "user", "content": "Hi!"}]}'
```

`model` can be `"default"` or a specific model (e.g. `"sonnet"`, `"opus"` for Claude).

## Notes

- The agents work read-only inside `./workspace` (change the folder with `AGENT_CWD`).
- The servers only listen on `127.0.0.1`. If you expose them on a network, set `AGENT_API_KEY`:
  clients must then send it as `Authorization: Bearer ...`.
- Streaming is not supported.
