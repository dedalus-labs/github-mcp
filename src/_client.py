# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Sample MCP client demonstrating Dedalus Auth (DAuth) with interactive loop.

DAuth (Dedalus Auth):
    Multi-tenant MCP authentication requires the Dedalus SDK. Generic MCP clients
    are spec-compliant but don't support credential injection.

    This file demonstrates DAuth: credentials encrypted client-side, decrypted
    in a secure enclave at dispatch time. The server NEVER sees the actual API key.

    For custom runners or lower-level SDK usage, see https://docs.dedaluslabs.ai

Environment variables:
    DEDALUS_API_KEY:  Your Dedalus API key (dsk_*)
    DEDALUS_API_URL:  API base URL
    DEDALUS_AS_URL:   Authorization server URL
    GITHUB_TOKEN:     GitHub personal access token
"""

import asyncio
import os
import webbrowser

from dotenv import load_dotenv


load_dotenv()

from dedalus_labs import AsyncDedalus, AuthenticationError, DedalusRunner
from dedalus_labs.utils.stream import stream_async
from dedalus_mcp.auth import Connection, SecretKeys, SecretValues


class MissingEnvError(ValueError):
    """Required environment variable not set."""


def get_env(key: str) -> str:
    """Get required env var or raise."""
    val = os.getenv(key)
    if not val:
        raise MissingEnvError(key)
    return val


API_URL = get_env("DEDALUS_API_URL")
AS_URL = get_env("DEDALUS_AS_URL")
DEDALUS_API_KEY = os.getenv("DEDALUS_API_KEY")

# Debug: print env vars
print("=== Environment ===")
print(f"  DEDALUS_API_URL: {API_URL}")
print(f"  DEDALUS_AS_URL: {AS_URL}")
print(
    f"  DEDALUS_API_KEY: {DEDALUS_API_KEY[:20]}..."
    if DEDALUS_API_KEY
    else "  DEDALUS_API_KEY: None"
)

# Connection: schema for GitHub API (must match server's Connection definition)
github = Connection(
    name="github-mcp",
    secrets=SecretKeys(token="GITHUB_TOKEN"),  # noqa: S106
    base_url=os.getenv("GITHUB_BASE_URL", "https://api.github.com"),
    auth_header_format="token {api_key}",
)

# SecretValues: binds actual credentials to a Connection schema.
# Encrypted client-side, decrypted in secure enclave at dispatch time.
github_credentials = SecretValues(github, token=os.getenv("GITHUB_TOKEN", ""))


def _extract_connect_url(err: AuthenticationError) -> str | None:
    """Pull the OAuth connect URL from an AuthenticationError, if present."""
    body = err.body if isinstance(err.body, dict) else {}
    return body.get("connect_url") or body.get("detail", {}).get("connect_url")


def _prompt_oauth(url: str) -> None:
    """Open OAuth URL in browser and block until user confirms."""
    print("\nAttempting to open your default browser.")
    print("If the browser does not open, open the following URL:\n")
    print(url)
    webbrowser.open(url)
    input("\nPress Enter after completing OAuth...")


async def run_agent_loop() -> None:
    """Interactive agent loop with streaming."""
    client = AsyncDedalus(api_key=DEDALUS_API_KEY, base_url=API_URL, as_base_url=AS_URL)
    runner = DedalusRunner(client)
    messages: list[dict] = []

    async def run_turn() -> None:
        stream = runner.run(
            input=messages,
            model="anthropic/claude-opus-4-5",
            mcp_servers=["windsor/github-mcp"],
            credentials=[github_credentials],
            stream=True,
        )
        print("\nAssistant: ", end="", flush=True)
        await stream_async(stream)

    print("\n=== GitHub MCP Agent ===")
    print("Type 'quit' or 'exit' to end the session.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            print("Goodbye!")
            break

        messages.append({"role": "user", "content": user_input})

        try:
            await run_turn()
        except AuthenticationError as err:
            url = _extract_connect_url(err)
            if not url:
                raise
            _prompt_oauth(url)
            await run_turn()

        print()


async def main() -> None:
    """Run interactive agent loop."""
    await run_agent_loop()


if __name__ == "__main__":
    asyncio.run(main())
