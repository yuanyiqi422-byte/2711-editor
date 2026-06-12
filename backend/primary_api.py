"""Primary API exhaustion detection and persistent disable."""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent
ENV_PATH = BACKEND_DIR / ".env"
DISABLED_FLAG = BACKEND_DIR / ".api-primary-disabled"

_PROVIDER_SWITCH_NOTICE: str | None = None
_LOGGED_PRIMARY_DISABLED = False

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def _truthy(value: str) -> bool:
    return value.strip().lower() in _TRUE_VALUES


def is_primary_disabled() -> bool:
    if _truthy(os.getenv("AI_PRIMARY_DISABLED", "")):
        return True
    return DISABLED_FLAG.is_file()


def _has_primary_key() -> bool:
    key = os.getenv("AI_API_KEY", "").strip()
    return bool(key and key != "your-secret-key-here")


def has_fallback_config() -> bool:
    base = (
        os.getenv("AI_API_BASE_FALLBACK", "").strip()
        or os.getenv("AI_BASE_URL_FALLBACK", "").strip()
    )
    key = os.getenv("AI_API_KEY_FALLBACK", "").strip()
    return bool(base and key and key != "your-secret-key-here")


def has_usable_api_key() -> bool:
    if is_primary_disabled():
        return has_fallback_config()
    return _has_primary_key() or has_fallback_config()


def primary_api_status() -> str:
    if is_primary_disabled():
        return "disabled"
    if not _has_primary_key() and has_fallback_config():
        return "fallback_only"
    return "active"


def is_primary_exhaustion_error(message: str) -> bool:
    msg = message.lower()
    if any(token in msg for token in ("http 401", "http 402")):
        return True
    quota_markers = (
        "insufficient balance",
        "quota",
        "余额不足",
        "余额",
        "invalid key",
        "invalid api key",
        "密钥无效",
    )
    return any(marker in msg for marker in quota_markers)


def provider_switch_message() -> str:
    return "赠送 API 已用尽，已自动切换至 DeepSeek"


def consume_provider_switch_notice() -> str | None:
    global _PROVIDER_SWITCH_NOTICE
    notice = _PROVIDER_SWITCH_NOTICE
    _PROVIDER_SWITCH_NOTICE = None
    return notice


def _set_provider_switch_notice(message: str) -> None:
    global _PROVIDER_SWITCH_NOTICE
    _PROVIDER_SWITCH_NOTICE = message


def log_primary_disabled_once() -> None:
    global _LOGGED_PRIMARY_DISABLED
    if _LOGGED_PRIMARY_DISABLED:
        return
    _LOGGED_PRIMARY_DISABLED = True
    logger.warning("Primary API disabled — using fallback provider only")


def _upsert_env_flag() -> None:
    if not ENV_PATH.is_file():
        ENV_PATH.write_text("AI_PRIMARY_DISABLED=1\n", encoding="utf-8")
        return

    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    found = False
    for line in lines:
        if re.match(r"^\s*AI_PRIMARY_DISABLED\s*=", line):
            out.append("AI_PRIMARY_DISABLED=1")
            found = True
        else:
            out.append(line)
    if not found:
        if out and out[-1].strip():
            out.append("")
        out.append("# Primary API exhausted — auto-disabled; remove flag or set 0 to re-enable")
        out.append("AI_PRIMARY_DISABLED=1")
    ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")


def disable_primary_api(reason: str = "") -> None:
    """Persist primary-disable state without touching fallback vars or logging secrets."""
    exhausted_at = datetime.now(timezone.utc).isoformat()
    os.environ["AI_PRIMARY_DISABLED"] = "1"
    flag_body = f"PRIMARY_API_EXHAUSTED at {exhausted_at}"
    if reason:
        flag_body += f"\n{reason[:400]}"
    try:
        DISABLED_FLAG.write_text(flag_body[:500], encoding="utf-8")
    except OSError as exc:
        logger.warning("could not write primary-disabled flag: %s", exc)
    logger.warning("PRIMARY_API_EXHAUSTED at %s", exhausted_at)
    try:
        _upsert_env_flag()
    except OSError as exc:
        logger.warning("could not update .env primary-disabled flag: %s", exc)
    _set_provider_switch_notice(provider_switch_message())
    log_primary_disabled_once()


def handle_primary_exhausted(reason: str) -> None:
    if is_primary_disabled():
        return
    disable_primary_api(reason)
