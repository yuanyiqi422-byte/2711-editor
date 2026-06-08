import asyncio
import hashlib
import json
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field, ValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from static_cache import VERSIONED_EXTS, VersionedStaticFiles

from document_extract import (
    ALLOWED_EXTENSIONS,
    ExtractError,
    LLM_INPUT_CHARS,
    LLM_MODEL_SAFE_CHARS,
    MAX_CREATE_CHARS,
    MAX_EXTRACT_CHARS,
    MAX_PDF_PAGES,
    MAX_UPLOAD_BYTES,
    upload_max_mb,
    PDF_PAGE_HARD_CAP,
    effective_llm_limit,
    extract_from_bytes,
    prepare_llm_text,
)
from env_check import validate_env
from ingest_models import IngestFileResponse
from llm import LLMError
from models import CreateGameRequest, ExpandNodeRequest, GamePack, STYLE_LABELS
from history_models import HistoryDetail, HistoryItem, HistoryProgress, HistorySaveRequest
from history_service import (
    delete_entry,
    ensure_share_token,
    get_entry,
    get_entry_by_share_token,
    list_entries,
    load_progress,
    refresh_history_count,
    save_entry,
    save_progress,
    touch_entry,
)
from image_service import (
    cache_id_for,
    generate_scene_image,
    is_image_gen_configured,
    read_cached_image,
)
from narrative_service import analyze_story, estimate_play_minutes, expand_branch, generate_game_nodes

logger = logging.getLogger(__name__)

# 圣经分析缓存：同文本+风格重复提交时跳过 analyze（TTL 秒）
_BIBLE_CACHE_TTL = int(os.getenv("BIBLE_CACHE_TTL", "1800"))
_bible_cache: dict[str, tuple[float, object]] = {}


def _bible_cache_key(text: str, style: str) -> str:
    digest = hashlib.sha256((text + "|" + style).encode("utf-8")).hexdigest()
    return digest


async def _cached_analyze_story(text: str, style, source_char_count: int):
    key = _bible_cache_key(text, style)
    now = time.time()
    cached = _bible_cache.get(key)
    if cached and now - cached[0] < _BIBLE_CACHE_TTL:
        logger.info("bible cache hit (%s chars)", source_char_count)
        return cached[1]
    t0 = time.perf_counter()
    bible = await analyze_story(text, style, source_char_count=source_char_count)
    logger.info("analyze_story (no cache) %.1fs", time.perf_counter() - t0)
    _bible_cache[key] = (now, bible)
    if len(_bible_cache) > 32:
        oldest = min(_bible_cache, key=lambda k: _bible_cache[k][0])
        _bible_cache.pop(oldest, None)
    return bible

ENV_PATH = Path(__file__).resolve().parent / ".env"
APP_VERSION = "0.2.7"
_startup_issues: list[str] = []
_history_count_cache: int = 0


def load_env() -> None:
    load_dotenv(ENV_PATH, override=True, encoding="utf-8")


def refresh_env_status() -> list[str]:
    global _startup_issues
    load_env()
    _startup_issues = validate_env()
    return _startup_issues


load_env()

app = FastAPI(title="2711编辑器", version=APP_VERSION)


@app.on_event("startup")
async def on_startup() -> None:
    issues = refresh_env_status()
    if issues:
        print("[2711编辑器] 环境检查：")
        for msg in issues:
            print(f"  · {msg}")
    else:
        global _history_count_cache
        _history_count_cache = len(list_entries())
        print(f"[2711编辑器] v{APP_VERSION} 就绪 · 模型 {os.getenv('AI_MODEL', '—')}")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


class StaticCacheMiddleware(BaseHTTPMiddleware):
    """PERF-001: HTML no-cache; ?v= static assets long-lived immutable."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            return response
        path = request.url.path
        query = request.url.query
        ext = Path(path).suffix.lower()
        ctype = response.headers.get("content-type", "")

        if path.endswith(".html") or path.rstrip("/") == "" or "text/html" in ctype:
            response.headers["Cache-Control"] = "no-cache"
        elif "v=" in query and ext in VERSIONED_EXTS:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif ext in VERSIONED_EXTS:
            response.headers["Cache-Control"] = "public, max-age=3600"
        return response


app.add_middleware(StaticCacheMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
def _cors_origins() -> list[str]:
    origins = [
        "http://127.0.0.1:8010",
        "http://localhost:8010",
        "https://2711editor.netlify.app",
    ]
    extra = os.getenv("CORS_ORIGINS", "").strip()
    if extra:
        for part in extra.split(","):
            o = part.strip().rstrip("/")
            if o and o not in origins:
                origins.append(o)
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_origin_regex=r"https://([a-zA-Z0-9-]+--)?2711editor\.netlify\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception(_request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        raise exc
    print(f"[2711编辑器] 未处理异常: {exc}")
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误，请稍后重试"})


@app.get("/api/health")
async def health():
    return {
        "ok": len(_startup_issues) == 0,
        "model": os.getenv("AI_MODEL", "deepseek-chat"),
        "has_key": bool(os.getenv("AI_API_KEY", "").strip())
        and os.getenv("AI_API_KEY", "").strip() != "your-secret-key-here",
        "version": APP_VERSION,
        "styles": STYLE_LABELS,
        "env_issues": _startup_issues,
        "upload": {
            "max_mb": upload_max_mb(),
            "formats": sorted(ALLOWED_EXTENSIONS),
        },
        "extract": {
            "max_extract_chars": MAX_EXTRACT_CHARS,
            "max_create_chars": MAX_CREATE_CHARS,
            "llm_input_chars": LLM_INPUT_CHARS,
            "llm_model_safe_chars": LLM_MODEL_SAFE_CHARS,
            "llm_effective_chars": effective_llm_limit(),
            "max_pdf_pages": MAX_PDF_PAGES,
            "pdf_page_hard_cap": PDF_PAGE_HARD_CAP,
        },
        "image_gen": is_image_gen_configured(),
        "history_count": _history_count_cache,
    }


@app.post("/api/ingest/file", response_model=IngestFileResponse)
async def ingest_file(file: UploadFile = File(...)):
    filename = file.filename or "upload.txt"
    try:
        if MAX_UPLOAD_BYTES > 0:
            if file.size is not None and file.size > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"文件过大，最大 {upload_max_mb()}MB",
                )
        data = await file.read()
        if MAX_UPLOAD_BYTES > 0 and len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"文件过大，最大 {upload_max_mb()}MB",
            )
        result = extract_from_bytes(data, filename)
        return IngestFileResponse(
            text=result.text,
            char_count=result.char_count,
            truncated=result.truncated,
            truncate_note=result.truncate_note,
            format=result.format,
            filename=result.filename,
            pages_processed=result.pages_processed,
            total_pages=result.total_pages,
            used_ocr=result.used_ocr,
            warnings=result.warnings or [],
            llm_char_count=result.llm_char_count,
        )
    except ExtractError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        print(f"[2711编辑器] 文件解析失败: {exc}")
        raise HTTPException(status_code=500, detail="文件解析失败，请检查格式后重试") from exc


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


_SSE_KEEPALIVE = ": keepalive\n\n"
_SSE_HEARTBEAT_SEC = float(os.getenv("SSE_HEARTBEAT_SEC", "12"))


async def _await_with_sse_heartbeats(coro):
    """Yield SSE comment keepalives while waiting on a long LLM call."""
    task = asyncio.create_task(coro)
    while not task.done():
        _done, _ = await asyncio.wait({task}, timeout=_SSE_HEARTBEAT_SEC)
        if not task.done():
            yield _SSE_KEEPALIVE
    yield await task


PIPELINE_STEPS = [
    (5, "正在构筑世界……"),
    (15, "✓ 阅读原著"),
    (35, "✓ 编织剧情"),
    (55, "✓ 生成命运分支"),
    (75, "✓ 准备场景"),
    (90, "故事正在成形…"),
]


@app.post("/api/create/stream")
async def create_game_stream(body: CreateGameRequest):
    async def events():
        try:
            yield _sse("status", {"progress": 5, "msg": "正在构筑世界……", "step": "read"})
            yield _sse("status", {"progress": 15, "msg": "✓ 阅读原著", "step": "read"})

            source_char_count = len(body.text)
            llm_text, truncated, trunc_note = prepare_llm_text(body.text)
            if truncated and trunc_note:
                yield _sse(
                    "status",
                    {
                        "progress": 12,
                        "msg": "✓ 阅读原著 · " + trunc_note[:200] + ("…" if len(trunc_note) > 200 else ""),
                        "step": "read",
                    },
                )

            bible = None
            async for chunk in _await_with_sse_heartbeats(
                _cached_analyze_story(llm_text, body.style, source_char_count=source_char_count)
            ):
                if isinstance(chunk, str):
                    yield chunk
                else:
                    bible = chunk
            yield _sse(
                "status",
                {
                    "progress": 40,
                    "msg": "✓ 编织剧情 · " + (bible.title or "未命名"),
                    "step": "weave",
                },
            )

            progress_queue: asyncio.Queue = asyncio.Queue()

            async def on_progress(pct: int, msg: str) -> None:
                await progress_queue.put({"progress": pct, "msg": msg})

            gen_task = asyncio.create_task(
                generate_game_nodes(
                    bible,
                    body.style,
                    source_char_count=source_char_count,
                    on_progress=on_progress,
                )
            )

            idle_ticks = 0
            while not gen_task.done():
                try:
                    upd = progress_queue.get_nowait()
                    idle_ticks = 0
                    yield _sse("status", upd)
                except asyncio.QueueEmpty:
                    idle_ticks += 1
                    if idle_ticks * 0.2 >= _SSE_HEARTBEAT_SEC:
                        yield _SSE_KEEPALIVE
                        idle_ticks = 0
                    await asyncio.sleep(0.2)

            while not progress_queue.empty():
                yield _sse("status", progress_queue.get_nowait())

            game = await gen_task

            node_count = len(game.nodes)
            ending_count = sum(1 for n in game.nodes.values() if n.is_ending)
            branch_count = sum(len(n.choices) for n in game.nodes.values())
            yield _sse(
                "status",
                {
                    "progress": 88,
                    "msg": "✓ 准备场景 · 已规划 " + str(branch_count) + " 条命运分支",
                    "step": "scene",
                    "branch_count": branch_count,
                    "ending_count": ending_count,
                },
            )
            play_minutes = estimate_play_minutes(game)

            yield _sse(
                "status",
                {
                    "progress": 100,
                    "msg": (
                        f"故事成形 · {branch_count} 条命运分支 · {ending_count} 种结局 · "
                        f"约 {play_minutes} 分钟"
                    ),
                    "step": "done",
                    "branch_count": branch_count,
                    "ending_count": ending_count,
                },
            )
            done_payload = game.model_dump()
            done_payload["meta"] = {
                "node_count": node_count,
                "ending_count": ending_count,
                "branch_count": branch_count,
                "play_minutes": play_minutes,
                "source_char_count": source_char_count,
                "llm_char_count": len(llm_text),
            }
            yield _sse("done", done_payload)
        except LLMError as exc:
            yield _sse("error", {"detail": str(exc)})
        except ValidationError as exc:
            logger.warning("game generation validation failed: %s", exc)
            yield _sse(
                "error",
                {
                    "detail": "故事结构数据格式异常，请重试生成。",
                    "debug": str(exc),
                },
            )
        except Exception as exc:
            logger.exception("game generation failed")
            yield _sse("error", {"detail": f"生成过程出错：{exc}"})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/history", response_model=list[HistoryItem])
async def history_list():
    return list_entries()


@app.get("/api/history/{entry_id}", response_model=HistoryDetail)
async def history_get(entry_id: str):
    return get_entry(entry_id)


@app.post("/api/history", response_model=HistoryItem)
async def history_save(body: HistorySaveRequest):
    try:
        global _history_count_cache
        item = save_entry(body)
        _history_count_cache = refresh_history_count()
        return item
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/history/{entry_id}")
async def history_delete(entry_id: str):
    global _history_count_cache
    delete_entry(entry_id)
    _history_count_cache = refresh_history_count()
    return {"ok": True}


@app.put("/api/history/{entry_id}/progress", response_model=HistoryItem)
async def history_save_progress(entry_id: str, body: HistoryProgress):
    try:
        return save_progress(entry_id, body)
    except HTTPException:
        raise
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/history/{entry_id}/touch", response_model=HistoryItem)
async def history_touch(entry_id: str):
    return touch_entry(entry_id)


class CharacterPreviewRequest(BaseModel):
    text: str = Field(..., min_length=20)


@app.post("/api/characters/preview")
async def characters_preview(body: CharacterPreviewRequest):
    from character_extract import extract_protagonist_candidates_enhanced

    result = await extract_protagonist_candidates_enhanced(body.text)
    return result


@app.post("/api/history/{entry_id}/share")
async def history_share(entry_id: str):
    token = ensure_share_token(entry_id)
    return {"share_token": token, "url": f"/?play={token}"}


@app.get("/api/share/{token}")
async def share_get(token: str):
    detail = get_entry_by_share_token(token)
    return {
        "item": detail.item.model_dump(),
        "game": detail.game.model_dump() if detail.game else None,
        "text": detail.text[:8000] if detail.text else "",
    }


class GameAssetsRequest(BaseModel):
    title: str = ""
    synopsis: str = ""
    style: str = "urban_romance"


@app.post("/api/game-assets/cover")
async def game_cover(body: GameAssetsRequest):
    """生成游戏封面；未配置生图 API 时返回风格预设图路径。"""
    style = body.style or "urban_romance"
    # Source art: 古风仙侠→xianxia, 都市言情→urban_romance, 悬疑推理→mystery, 校园青春→campus
    preset_paths = {
        "xianxia": "/images/workbench/world-xianxia.png",
        "urban_romance": "/images/workbench/world-urban-romance.png",
        "mystery": "/images/workbench/world-mystery.png",
        "campus": "/images/workbench/world-campus.png",
    }
    fallback = preset_paths.get(style, preset_paths["urban_romance"])
    prompt = (
        f"Visual novel game cover, title mood: {body.title or 'story'}. "
        f"{body.synopsis[:120] if body.synopsis else 'interactive fiction'}. "
        "2D anime art style, watercolor, pastel, no text, no watermark."
    )
    if not is_image_gen_configured():
        return {"url": fallback, "generated": False}
    raw = await generate_scene_image(prompt, style)
    if not raw:
        return {"url": fallback, "generated": False}
    cache_id = cache_id_for(prompt, style)
    return {"url": f"/api/scene-image/{cache_id}.png", "generated": True}


class SceneImageRequest(BaseModel):
    prompt: str = ""
    mood: str = "neutral"


@app.post("/api/scene-image")
async def create_scene_image(body: SceneImageRequest):
    if not is_image_gen_configured():
        raise HTTPException(status_code=503, detail="场景生图未配置")
    if not body.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt 不能为空")
    raw = await generate_scene_image(body.prompt, body.mood)
    if not raw:
        raise HTTPException(status_code=502, detail="场景生图失败，请使用图库背景")
    cache_id = cache_id_for(body.prompt, body.mood)
    return {"url": f"/api/scene-image/{cache_id}.png", "cached": True}


@app.get("/api/scene-image/{image_id}.png")
async def get_scene_image(image_id: str):
    safe = image_id.replace(".png", "")
    raw = read_cached_image(safe)
    if not raw:
        raise HTTPException(status_code=404, detail="场景图不存在")
    return StreamingResponse(iter([raw]), media_type="image/png")


@app.post("/api/expand", response_model=GamePack)
async def expand_node(body: ExpandNodeRequest):
    if body.current_node_id not in body.game.nodes:
        raise HTTPException(status_code=400, detail="当前节点不存在于游戏包中")
    node = body.game.nodes[body.current_node_id]
    if not any(c.id == body.choice_id for c in node.choices):
        raise HTTPException(status_code=400, detail="所选分支不存在")
    try:
        expand_text, _, _ = prepare_llm_text(body.text)
        return await expand_branch(
            expand_text,
            body.style,
            body.game,
            body.current_node_id,
            body.choice_id,
        )
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


frontend_dir = Path(__file__).resolve().parent.parent / "frontend"


if not frontend_dir.is_dir():
    raise RuntimeError(f"frontend 目录不存在: {frontend_dir}")

app.mount(
    "/",
    VersionedStaticFiles(directory=str(frontend_dir), html=True),
    name="frontend",
)
