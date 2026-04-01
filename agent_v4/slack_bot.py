"""Slack bot integration (#9).

Runs the agent as a Slack bot that responds to messages in channels.
Uses the Slack Bolt framework with Socket Mode for real-time events.

Requires:
  pip install slack-bolt
  SLACK_BOT_TOKEN and SLACK_APP_TOKEN in .env
"""

from __future__ import annotations

import os
import sys
import threading
from typing import Any

from agent_v4.config import (
    API_KEYS,
    AVAILABLE_MODELS,
    MAX_TOKENS,
    SLACK_APP_TOKEN,
    SLACK_BOT_TOKEN,
    get_system_prompt,
)
from agent_v4.cost_tracker import CostTracker
from agent_v4.history import SessionHistory
from agent_v4.safety import check_safety
from agent_v4.token_manager import TokenManager
from agent_v4.tools import TOOL_DEFINITIONS, execute_tool


def _check_slack_deps() -> bool:
    """Check if slack-bolt is installed."""
    try:
        import slack_bolt  # noqa: F401
        return True
    except ImportError:
        return False


def start_slack_bot() -> None:
    """Launch the Slack bot in Socket Mode.

    This is a blocking call that runs the bot event loop.
    """
    if not SLACK_BOT_TOKEN:
        print("[ERROR] SLACK_BOT_TOKEN not configured. Set it in agent_v4/.env")
        return
    if not SLACK_APP_TOKEN:
        print("[ERROR] SLACK_APP_TOKEN not configured. Set it in agent_v4/.env")
        return

    if not _check_slack_deps():
        print("[ERROR] slack-bolt not installed. Run: pip install slack-bolt")
        return

    from slack_bolt import App
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    app = App(token=SLACK_BOT_TOKEN)

    # Per-channel session state
    _sessions: dict[str, dict[str, Any]] = {}
    _lock = threading.Lock()

    def _get_session(channel: str) -> dict[str, Any]:
        with _lock:
            if channel not in _sessions:
                _sessions[channel] = {
                    "history": SessionHistory(),
                    "cost": CostTracker(),
                    "model": AVAILABLE_MODELS.get("sonnet", "claude-sonnet-4-5-20250514"),
                }
            return _sessions[channel]

    token_manager = TokenManager(API_KEYS)

    @app.event("app_mention")
    def handle_mention(event: dict[str, Any], say: Any) -> None:
        """Respond when the bot is @mentioned."""
        text = event.get("text", "")
        channel = event.get("channel", "unknown")
        # Strip the bot mention from the text
        # Format is usually "<@BOT_ID> actual message"
        parts = text.split(">", 1)
        user_message = parts[1].strip() if len(parts) > 1 else text.strip()

        if not user_message:
            say("Please provide a message after mentioning me!")
            return

        _handle_message(user_message, channel, say, token_manager)

    @app.event("message")
    def handle_dm(event: dict[str, Any], say: Any) -> None:
        """Respond to direct messages."""
        # Only respond to DMs (channel_type == 'im')
        if event.get("channel_type") != "im":
            return
        # Ignore bot's own messages
        if event.get("bot_id"):
            return

        text = event.get("text", "").strip()
        channel = event.get("channel", "unknown")

        if not text:
            return

        # Handle special commands
        lower = text.lower()
        if lower == "cost":
            session = _get_session(channel)
            say(f"```\n{session['cost'].summary()}\n```")
            return
        if lower == "clear":
            session = _get_session(channel)
            session["history"].clear()
            say("History cleared.")
            return
        if lower.startswith("model "):
            model_key = lower.split(" ", 1)[1].strip()
            session = _get_session(channel)
            if model_key in AVAILABLE_MODELS:
                session["model"] = AVAILABLE_MODELS[model_key]
                say(f"Switched to {model_key} ({session['model']})")
            else:
                say(f"Unknown model. Available: {', '.join(AVAILABLE_MODELS.keys())}")
            return

        _handle_message(text, channel, say, token_manager)

    def _handle_message(
        user_message: str,
        channel: str,
        say: Any,
        tm: TokenManager,
    ) -> None:
        """Process a message through the agent and respond."""
        session = _get_session(channel)
        history = session["history"]
        cost = session["cost"]
        model = session["model"]

        history.add_user(user_message)
        messages = history.get_messages()

        max_turns = 10
        for _ in range(max_turns):
            try:
                response = tm.create_message(
                    model=model,
                    max_tokens=MAX_TOKENS,
                    system=get_system_prompt(),
                    tools=TOOL_DEFINITIONS,
                    messages=messages,
                )
            except Exception as exc:
                say(f"Error: {exc}")
                return

            if hasattr(response, "usage"):
                cost.record(model, response.usage.input_tokens, response.usage.output_tokens)

            history.add_assistant(response.content)
            messages = history.get_messages()

            # Send text blocks
            for block in response.content:
                if hasattr(block, "text") and block.text.strip():
                    # Slack has a 4000 char limit per message
                    text = block.text
                    while text:
                        chunk = text[:3900]
                        text = text[3900:]
                        say(chunk)

            if response.stop_reason == "end_turn":
                break

            if response.stop_reason == "tool_use":
                tool_results: list[dict[str, Any]] = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    block_reason = check_safety(block.name, block.input)
                    if block_reason:
                        result = block_reason
                        say(f":warning: {block_reason}")
                    else:
                        say(f":gear: Executing `{block.name}`...")
                        result = execute_tool(block.name, block.input)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

                history.add_tool_results(tool_results)
                messages = history.get_messages()
            else:
                break

    print("[Slack Bot] Starting in Socket Mode...")
    print("[Slack Bot] Mention @bot in channels or DM directly.")
    print("[Slack Bot] Commands in DM: cost, clear, model <opus/sonnet/haiku>")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()


if __name__ == "__main__":
    start_slack_bot()
