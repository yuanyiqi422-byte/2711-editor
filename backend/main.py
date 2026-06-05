import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, ValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles

from document_extract import (
    ALLOWED_EXTENSIONS,
    ExtractError,
    LLM_INPUT_CHARS,
    LLM_MODEL_SAFE_CHARS,
    MAX_CREATE_CHARS,
    MAX_EXTRACT_CHARS,
    MAX_PDF_PAGES,
    MAX_UPLOAD_BYTES,
    PDF_PAGE_HARD_CAP,
    effective_llm_limit,
    extract_from_bytes,
    prepare_llm_text,
)
from env_check import validate_env
from ingest_models import IngestFileResponse
from llm import LLMError
from models import CreateGameRequest, ExpandNodeRequest, GamePack, STYLE_LABELS
from history_models import HistoryDetail, HistoryItem, HistorySaveRequest
from history_service import delete_entry, get_entry, list_entries, refresh_history_count, save_entry
from image_service import (
    cache_id_for,
    generate_scene_image,
    is_image_gen_configured,
    read_cached_image,
)
from narrative_service import analyze_story, estimate_play_minutes, expand_branch, generate_game_nodes

ENV_PATH = Path(__file__).resolve().parent / ".env"
APP_VERSION = "0.2.5"
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


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8010", "http://localhost:8010"],
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
            "max_mb": MAX_UPLOAD_BYTES // (1024 * 1024),
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
        if file.size is not None and file.size > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"文件过大，最大 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB",
            )
        data = await file.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"文件过大，最大 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB",
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


PIPELINE_STEPS = [
    (5, "正在读取输入文本…"),
    (15, "正在分析人物与冲突…"),
    (35, "正在构思剧情大纲…"),
    (55, "正在生成分支节点…"),
    (75, "正在校验叙事图谱…"),
    (90, "正在打包可玩内容…"),
]


@app.post("/api/create/stream")
async def create_game_stream(body: CreateGameRequest):
    async def events():
        try:
            for progress, msg in PIPELINE_STEPS[:2]:
                yield _sse("status", {"progress": progress, "msg": msg})

            source_char_count = len(body.text)
            llm_text, truncated, trunc_note = prepare_llm_text(body.text)
            if truncated and trunc_note:
                yield _sse(
                    "status",
                    {
                        "progress": 12,
                        "msg": trunc_note[:240] + ("…" if len(trunc_note) > 240 else ""),
                    },
                )

            bible = await analyze_story(llm_text, body.style, source_char_count=source_char_count)
            yield _sse("bible", bible.model_dump())
            yield _sse(
                "status",
                {
                    "progress": 40,
                    "msg": "故事圣经完成 · 正在铺陈分支场景（目标 15～25 节点）…",
                },
            )

            yield _sse("status", {"progress": 55, "msg": "正在生成分支节点与选项…"})
            game = await generate_game_nodes(bible, body.style, source_char_count=source_char_count)

            node_count = len(game.nodes)
            yield _sse(
                "status",
                {
                    "progress": 72,
                    "msg": "已生成 " + str(node_count) + " 个场景节点 · 正在校验叙事图谱…",
                    "node_count": node_count,
                },
            )
            ending_count = sum(1 for n in game.nodes.values() if n.is_ending)
            play_minutes = estimate_play_minutes(game)

            yield _sse(
                "status",
                {
                    "progress": 85,
                    "msg": "正在校验叙事图谱…",
                    "node_count": node_count,
                },
            )

            yield _sse(
                "status",
                {
                    "progress": 100,
                    "msg": (
                        f"完成 · 共 {node_count} 场景 · 预计游玩 {play_minutes} 分钟 · "
                        f"{ending_count} 个结局"
                    ),
                },
            )
            done_payload = game.model_dump()
            done_payload["meta"] = {
                "node_count": node_count,
                "ending_count": ending_count,
                "play_minutes": play_minutes,
                "source_char_count": source_char_count,
                "llm_char_count": len(llm_text),
            }
            yield _sse("done", done_payload)
        except LLMError as exc:
            yield _sse("error", {"detail": str(exc)})
        except Exception as exc:
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
    StaticFiles(directory=str(frontend_dir), html=True),
    name="frontend",
)
