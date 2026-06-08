"""Static file serving with HTTP Cache-Control headers (PERF-001)."""

from __future__ import annotations

import os
from pathlib import Path

from starlette.staticfiles import StaticFiles
from starlette.types import Scope

_LONG_CACHE = "public, max-age=31536000, immutable"
_HTML_CACHE = "no-cache"
_DEFAULT_CACHE = "public, max-age=3600"

_VERSIONED_EXTS = frozenset({".js", ".css", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".woff2", ".ico"})
VERSIONED_EXTS = _VERSIONED_EXTS


class VersionedStaticFiles(StaticFiles):
    """Apply cache headers: HTML revalidates; ?v= assets cache long-term."""

    def _apply_cache_headers(self, response, full_path: str | os.PathLike, scope: Scope) -> None:
        query = scope.get("query_string", b"").decode()
        ext = Path(str(full_path)).suffix.lower()
        is_html = ext == ".html" or str(full_path).replace("\\", "/").endswith("index.html")

        if is_html:
            response.headers["Cache-Control"] = _HTML_CACHE
        elif "v=" in query and ext in _VERSIONED_EXTS:
            response.headers["Cache-Control"] = _LONG_CACHE
        elif ext in _VERSIONED_EXTS:
            response.headers["Cache-Control"] = _DEFAULT_CACHE

    def file_response(self, full_path, stat_result, scope, status_code: int = 200):
        response = super().file_response(full_path, stat_result, scope, status_code)
        if hasattr(response, "headers"):
            self._apply_cache_headers(response, full_path, scope)
        return response
