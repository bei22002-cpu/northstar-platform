"""Automatic API-key rotation with exponential backoff.

Manages a pool of Anthropic API keys, rotating through them when one
hits a rate limit or server error. Includes streaming support.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

import anthropic


@dataclass
class _KeyState:
    key: str
    calls: int = 0
    errors: int = 0
    rate_limited: bool = False
    cooldown_until: float = 0.0
    consecutive_failures: int = 0


class TokenManager:
    """Round-robin key pool with automatic failover + exponential backoff."""

    BASE_COOLDOWN: float = 60.0
    SERVER_COOLDOWN: float = 10.0
    CONNECT_COOLDOWN: float = 5.0
    MAX_BACKOFF: float = 300.0

    def __init__(self, api_keys: list[str]) -> None:
        if not api_keys:
            raise ValueError("At least one API key is required.")
        self._keys: list[_KeyState] = [_KeyState(key=k) for k in api_keys]
        self._current_index: int = 0
        self._total_keys = len(api_keys)

    @property
    def active_key_index(self) -> int:
        return self._current_index + 1

    @property
    def total_keys(self) -> int:
        return self._total_keys

    def get_stats(self) -> list[dict[str, Any]]:
        now = time.time()
        stats: list[dict[str, Any]] = []
        for i, ks in enumerate(self._keys):
            cd = max(0, int(ks.cooldown_until - now))
            masked = ks.key[:10] + "..." + ks.key[-4:] if len(ks.key) > 14 else ks.key
            stats.append({
                "key_number": i + 1,
                "masked_key": masked,
                "calls": ks.calls,
                "errors": ks.errors,
                "rate_limited": ks.rate_limited,
                "cooldown_remaining": cd,
                "consecutive_failures": ks.consecutive_failures,
            })
        return stats

    def get_total_calls(self) -> int:
        return sum(ks.calls for ks in self._keys)

    def create_message(self, **kwargs: Any) -> anthropic.types.Message:
        """Call messages.create with automatic key rotation + backoff."""
        return self._call_with_rotation("create", **kwargs)

    def create_message_stream(self, **kwargs: Any) -> Any:
        """Return a streaming context manager with key rotation."""
        return self._call_with_rotation("stream", **kwargs)

    def _call_with_rotation(self, mode: str, **kwargs: Any) -> Any:
        last_exc: Exception | None = None
        attempts = 0

        while attempts < self._total_keys:
            ks = self._pick_key()
            if ks is None:
                self._wait_for_cooldown()
                ks = self._pick_key()
                if ks is None:
                    break

            client = anthropic.Anthropic(api_key=ks.key)
            try:
                if mode == "stream":
                    result = client.messages.stream(**kwargs)
                else:
                    result = client.messages.create(**kwargs)
                ks.calls += 1
                ks.rate_limited = False
                ks.consecutive_failures = 0
                return result

            except anthropic.RateLimitError as exc:
                last_exc = exc
                ks.errors += 1
                ks.rate_limited = True
                ks.consecutive_failures += 1
                backoff = self._backoff(ks.consecutive_failures, self.BASE_COOLDOWN)
                ks.cooldown_until = time.time() + backoff
                print(f"Key #{self._current_index + 1} rate-limited. "
                      f"Cooldown {backoff:.0f}s. Rotating...")
                self._advance()
                attempts += 1

            except anthropic.APIStatusError as exc:
                last_exc = exc
                ks.errors += 1
                if exc.status_code in (529, 500, 503):
                    ks.consecutive_failures += 1
                    backoff = self._backoff(ks.consecutive_failures,
                                            self.SERVER_COOLDOWN)
                    ks.cooldown_until = time.time() + backoff
                    print(f"Key #{self._current_index + 1} server error "
                          f"({exc.status_code}). Rotating...")
                    self._advance()
                    attempts += 1
                elif exc.status_code == 401:
                    ks.cooldown_until = float("inf")
                    print(f"Key #{self._current_index + 1} is invalid (401). "
                          "Skipping permanently.")
                    self._advance()
                    attempts += 1
                else:
                    raise

            except anthropic.APIConnectionError as exc:
                last_exc = exc
                ks.errors += 1
                ks.consecutive_failures += 1
                backoff = self._backoff(ks.consecutive_failures,
                                        self.CONNECT_COOLDOWN)
                ks.cooldown_until = time.time() + backoff
                self._advance()
                attempts += 1

        if last_exc is not None:
            raise last_exc
        raise RuntimeError("All API keys are exhausted or invalid.")

    def _pick_key(self) -> _KeyState | None:
        now = time.time()
        for _ in range(self._total_keys):
            ks = self._keys[self._current_index]
            if ks.cooldown_until <= now:
                return ks
            self._advance()
        return None

    def _advance(self) -> None:
        self._current_index = (self._current_index + 1) % self._total_keys

    def _wait_for_cooldown(self) -> None:
        now = time.time()
        finite = [ks.cooldown_until for ks in self._keys
                  if ks.cooldown_until < float("inf")]
        if not finite:
            return
        wait = max(0.0, min(finite) - now)
        if wait > 0:
            print(f"All keys on cooldown. Waiting {wait:.1f}s...")
            time.sleep(wait)

    @staticmethod
    def _backoff(failures: int, base: float) -> float:
        delay = base * math.pow(2, failures - 1)
        return min(delay, TokenManager.MAX_BACKOFF)
