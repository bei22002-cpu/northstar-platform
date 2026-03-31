"""Configuration — loads settings from environment and detects hardware.

Supports both .env files and a config.toml for advanced users.
Hardware auto-detection recommends the best engine and model for the system.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

from agent_v5.types import HardwareInfo

# ── Load .env ────────────────────────────────────────────────────────────

_ENV_PATH = Path(__file__).parent / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)

# ── API keys ─────────────────────────────────────────────────────────────

ANTHROPIC_API_KEYS: list[str] = []
for i in range(1, 11):
    key = os.getenv(f"ANTHROPIC_API_KEY_{i}", "")
    if key:
        ANTHROPIC_API_KEYS.append(key)
# Fallback to single key
if not ANTHROPIC_API_KEYS:
    single = os.getenv("ANTHROPIC_API_KEY", "")
    if single:
        ANTHROPIC_API_KEYS.append(single)

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen3:8b")

# ── Workspace ────────────────────────────────────────────────────────────

WORKSPACE: str = os.getenv("WORKSPACE", "./backend")

# ── Engine preference ────────────────────────────────────────────────────

DEFAULT_ENGINE: str = os.getenv("DEFAULT_ENGINE", "auto")  # auto, ollama, anthropic, openai
DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "")  # Empty = auto-select

# ── Memory ───────────────────────────────────────────────────────────────

MEMORY_BACKEND: str = os.getenv("MEMORY_BACKEND", "sqlite")  # sqlite, vector, hybrid
MEMORY_DB_PATH: str = os.getenv("MEMORY_DB_PATH", str(Path(__file__).parent / "data" / "memory.db"))

# ── Server ───────────────────────────────────────────────────────────────

SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))

# ── Data directory ───────────────────────────────────────────────────────

DATA_DIR: Path = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

TRACES_PATH: Path = DATA_DIR / "traces.jsonl"
LOGS_DIR: Path = Path(__file__).parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


# ── Hardware detection ───────────────────────────────────────────────────

def detect_hardware() -> HardwareInfo:
    """Auto-detect hardware capabilities."""
    info = HardwareInfo()
    info.platform = platform.system()
    info.cpu = platform.processor() or platform.machine()
    info.cpu_cores = os.cpu_count() or 1

    # RAM
    try:
        if info.platform == "Linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal"):
                        kb = int(line.split()[1])
                        info.ram_gb = round(kb / 1024 / 1024, 1)
                        break
        elif info.platform == "Darwin":
            out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True)
            info.ram_gb = round(int(out.strip()) / 1024**3, 1)
        elif info.platform == "Windows":
            out = subprocess.check_output(
                ["wmic", "ComputerSystem", "get", "TotalPhysicalMemory"],
                text=True,
            )
            for line in out.strip().split("\n"):
                line = line.strip()
                if line.isdigit():
                    info.ram_gb = round(int(line) / 1024**3, 1)
                    break
    except Exception:
        pass

    # GPU detection
    try:
        # NVIDIA
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        if out.strip():
            parts = out.strip().split(",")
            info.gpu_vendor = "nvidia"
            info.gpu_name = parts[0].strip()
            mem_str = parts[1].strip().replace("MiB", "").strip()
            info.vram_gb = round(float(mem_str) / 1024, 1)
            info.has_gpu = True
            return info
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    # Apple Silicon
    if info.platform == "Darwin" and "arm" in platform.machine().lower():
        info.gpu_vendor = "apple"
        info.gpu_name = "Apple Silicon (unified memory)"
        info.vram_gb = info.ram_gb  # Unified memory
        info.has_gpu = True
        return info

    # AMD
    try:
        out = subprocess.check_output(
            ["rocm-smi", "--showproductname"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        if out.strip():
            info.gpu_vendor = "amd"
            info.gpu_name = "AMD GPU"
            info.has_gpu = True
            return info
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    info.gpu_vendor = "none"
    return info


def recommend_engine(hw: HardwareInfo) -> str:
    """Recommend the best engine based on hardware."""
    # If Ollama is installed and GPU available, prefer local
    if shutil.which("ollama") and (hw.has_gpu or hw.ram_gb >= 8):
        return "ollama"
    # Fall back to cloud
    if ANTHROPIC_API_KEYS:
        return "anthropic"
    if OPENAI_API_KEY:
        return "openai"
    # Last resort — try Ollama anyway
    if shutil.which("ollama"):
        return "ollama"
    return "anthropic"


def recommend_model(hw: HardwareInfo, engine: str) -> str:
    """Recommend the best model for the given engine and hardware."""
    if engine == "ollama":
        if hw.vram_gb >= 16 or hw.ram_gb >= 32:
            return "qwen3:14b"
        if hw.vram_gb >= 8 or hw.ram_gb >= 16:
            return "qwen3:8b"
        if hw.vram_gb >= 4 or hw.ram_gb >= 8:
            return "qwen3:4b"
        return "qwen3:1.7b"
    if engine == "anthropic":
        return "claude-sonnet-4-20250514"
    if engine == "openai":
        return "gpt-4o"
    return "claude-sonnet-4-20250514"
