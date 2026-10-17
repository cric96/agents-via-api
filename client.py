"""Call an agent with the plain OpenAI client, as if it were a remote LLM.

Start the servers first (see README), then: uv run python client.py claude "your question" -m sonnet
"""

import argparse
import os

from openai import OpenAI

PORTS = {"claude": 8001, "codex": 8002}

parser = argparse.ArgumentParser()
parser.add_argument("agent", choices=PORTS)
parser.add_argument("prompt")
parser.add_argument("-m", "--model", default="default", help='e.g. "sonnet", "opus", "gpt-6.1-sol"')
args = parser.parse_args()

client = OpenAI(base_url=f"http://127.0.0.1:{PORTS[args.agent]}/v1", api_key=os.environ.get("AGENT_API_KEY", "none"))
resp = client.chat.completions.create(model=args.model, messages=[{"role": "user", "content": args.prompt}])
print(resp.choices[0].message.content)
