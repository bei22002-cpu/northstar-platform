"""Token rotation manager — automatically switches API keys on errors."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import anthropic
from rich.console import Console

console = Console()


@dataclass
class _KeyState:
    """Tracks per-key health metrics."""

    key: str
    calls: int = 0
    errors: int = 0
    rate_limited: bool = False
    cooldown_until: float = 0.0  # epoch timestamp


class TokenManager:
    """Round-robin key pool with automatic failover.

    Usage::

        tm = TokenManager(["sk-ant-1", "sk-ant-2", "sk-ant-3"])
        response = tm.create_message(model=..., max_tokens=..., ...)

    When a key hits a rate-limit (429) or an auth/overload error the manager
    marks it as cooling down and retries the same request with the next key.
    It cycles through all available keys before giving up.
    """

    # Seconds to wait before retrying a rate-limited key
    COOLDOWN_SECONDS = 60

    def __init__(self, api_keys: list[str]) -> None:
        if not api_keys:
            raise ValueError("At least one API key is required.")
        self._keys: list[_KeyState] = [_KeyState(key=k) for k in api_keys]
        self._current_index: int = 0
        self._total_keys = len(api_keys)
        console.print(
            f"[dim]TokenManager initialised with {self._total_keys} API key(s).[/dim]"
        )

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @property
    def active_key_index(self) -> int:
        return self._current_index + 1  # 1-based for display

    @property
    def total_keys(self) -> int:
        return self._total_keys

    def get_stats(self) -> list[dict[str, Any]]:
        """Return per-key statistics (keys are masked)."""
        stats: list[dict[str, Any]] = []
        for i, ks in enumerate(self._keys, start=1):
            masked = ks.key[:10] + "..." + ks.key[-4:]
            stats.append(
                {
                    "key_number": i,
                    "masked_key": masked,
                    "calls": ks.calls,
                    "errors": ks.errors,
                    "rate_limited": ks.rate_limited,
                    "cooldown_remaining": max(
                        0, round(ks.cooldown_until - time.time(), 1)
                    ),
                }
            )
        return stats

    # ------------------------------------------------------------------
    # Core API call with rotation
    # ------------------------------------------------------------------

    def create_message(self, **kwargs: Any) -> anthropic.types.Message:
        """Call ``client.messages.create`` with automatic key rotation.

        Accepts all keyword arguments that
        ``anthropic.Anthropic().messages.create`` accepts.

        Raises the last encountered exception if **all** keys fail.
        """
        last_exc: Exception | None = None
        attempts = 0

        while attempts < self._total_keys:
            ks = self._pick_key()
            if ks is None:
                # All keys are on cooldown — wait for the shortest one
                self._wait_for_cooldown()
                ks = self._pick_key()
                if ks is None:
                    break  # truly exhausted

            client = anthropic.Anthropic(api_key=ks.key)
            try:
                response = client.messages.create(**kwargs)
                ks.calls += 1
                ks.rate_limited = False
                return response

            except anthropic.RateLimitError as exc:
                ks.errors += 1
                ks.rate_limited = True
                ks.cooldown_until = time.time() + self.COOLDOWN_SECONDS
                last_exc = exc
                console.print(
                    f"[yellow]Key #{self._current_index + 1} rate-limited. "
                    f"Rotating to next key...[/yellow]"
                )
                self._advance()
                attempts += 1

            except anthropic.APIStatusError as exc:
                # 529 (overloaded), 500, 401 etc.
                ks.errors += 1
                if exc.status_code in (529, 500, 503):
                    ks.cooldown_until = time.time() + 10  # short cooldown
                    console.print(
                        f"[yellow]Key #{self._current_index + 1} got "
                        f"{exc.status_code}. Rotating...[/yellow]"
                    )
                    self._advance()
                    attempts += 1
                    last_exc = exc
                elif exc.status_code == 401:
                    # Bad key — permanently skip
                    ks.cooldown_until = float("inf")
                    console.print(
                        f"[red]Key #{self._current_index + 1} is invalid (401). "
                        f"Skipping permanently.[/red]"
                    )
                    self._advance()
                    attempts += 1
                    last_exc = exc
                else:
                    raise

            except anthropic.APIConnectionError as exc:
                ks.errors += 1
                ks.cooldown_until = time.time() + 5
                last_exc = exc
                console.print(
                    f"[yellow]Connection error on key #{self._current_index + 1}. "
                    f"Rotating...[/yellow]"
                )
                self._advance()
                attempts += 1

        # All keys exhausted
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("All API keys are exhausted or invalid.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _pick_key(self) -> _KeyState | None:
        """Return the current key if it isn't on cooldown, else try others."""
        now = time.time()
        for _ in range(self._total_keys):
            ks = self._keys[self._current_index]
            if now >= ks.cooldown_until:
                return ks
            self._advance()
        return None  # all on cooldown

    def _advance(self) -> None:
        self._current_index = (self._current_index + 1) % self._total_keys

    def _wait_for_cooldown(self) -> None:
        """Sleep until the earliest cooldown expires."""
        now = time.time()
        earliest = min(
            ks.cooldown_until for ks in self._keys if ks.cooldown_until > now
        )
        wait = earliest - now
        if wait > 0 and wait < float("inf"):
            console.print(
                f"[dim]All keys on cooldown. Waiting {wait:.0f}s...[/dim]"
            )
            time.sleep(wait)
