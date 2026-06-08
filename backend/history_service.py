import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from pydantic import ValidationError

from history_models import HistoryDetail, HistoryItem, HistoryProgress, HistorySaveRequest
from models import GamePack

HISTORY_ROOT = Path(__file__).resolve().parent / "data" / "history"
MAX_ENTRIES = 30


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _validate_entry_id(entry_id: str) -> str:
    if not entry_id or not re.fullmatch(r"[a-f0-9]{12}", entry_id):
        raise HTTPException(status_code=400, detail="无效的历史记录 ID")
    return entry_id


def _entry_dir(entry_id: str) -> Path:
    _validate_entry_id(entry_id)
    return HISTORY_ROOT / entry_id


def _meta_path(entry_id: str) -> Path:
    return _entry_dir(entry_id) / "meta.json"


def _text_path(entry_id: str) -> Path:
    return _entry_dir(entry_id) / "text.txt"


def _game_path(entry_id: str) -> Path:
    return _entry_dir(entry_id) / "game.json"


def _progress_path(entry_id: str) -> Path:
    return _entry_dir(entry_id) / "progress.json"


def _ensure_root() -> None:
    HISTORY_ROOT.mkdir(parents=True, exist_ok=True)


def _load_meta(entry_id: str) -> dict:
    path = _meta_path(entry_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="历史记录不存在")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_meta(entry_id: str, meta: dict) -> None:
    _entry_dir(entry_id).mkdir(parents=True, exist_ok=True)
    _meta_path(entry_id).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _find_by_filename(filename: str) -> str | None:
    if not filename or not HISTORY_ROOT.is_dir():
        return None
    name = filename.strip()
    for child in sorted(HISTORY_ROOT.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not child.is_dir():
            continue
        meta_file = child / "meta.json"
        if not meta_file.is_file():
            continue
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if meta.get("filename") == name:
            return child.name
    return None


def _prune_old_entries() -> None:
    if not HISTORY_ROOT.is_dir():
        return
    dirs = [p for p in HISTORY_ROOT.iterdir() if p.is_dir() and (p / "meta.json").is_file()]
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for old in dirs[MAX_ENTRIES:]:
        for f in old.iterdir():
            f.unlink(missing_ok=True)
        old.rmdir()


def _meta_to_item(meta: dict) -> HistoryItem:
    item = HistoryItem.model_validate(meta)
    if item.unlocked_endings == 0:
        progress = _load_progress_raw(meta.get("id", ""))
        if progress:
            item = item.model_copy(update={"unlocked_endings": len(progress.get("unlocked") or [])})
    return item


def _load_progress_raw(entry_id: str) -> dict | None:
    path = _progress_path(entry_id)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def load_progress(entry_id: str) -> HistoryProgress:
    raw = _load_progress_raw(entry_id)
    if not raw:
        return HistoryProgress(unlocked=[])
    return HistoryProgress.model_validate(raw)


def save_progress(entry_id: str, progress: HistoryProgress) -> HistoryItem:
    _load_meta(entry_id)
    _entry_dir(entry_id).mkdir(parents=True, exist_ok=True)
    unlocked = progress.unlocked or []
    _progress_path(entry_id).write_text(
        json.dumps({"unlocked": unlocked}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    meta = _load_meta(entry_id)
    meta["unlocked_endings"] = len(unlocked)
    meta["updated_at"] = _now_iso()
    _write_meta(entry_id, meta)
    return _meta_to_item(meta)


def refresh_history_count() -> int:
    if not HISTORY_ROOT.is_dir():
        return 0
    return sum(
        1
        for child in HISTORY_ROOT.iterdir()
        if child.is_dir() and (child / "meta.json").is_file()
    )


def list_entries() -> list[HistoryItem]:
    _ensure_root()
    items: list[HistoryItem] = []
    for child in HISTORY_ROOT.iterdir():
        if not child.is_dir():
            continue
        meta_file = child / "meta.json"
        if not meta_file.is_file():
            continue
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            items.append(_meta_to_item(meta))
        except (json.JSONDecodeError, ValidationError, OSError):
            continue
    items.sort(key=lambda x: x.updated_at, reverse=True)
    return items[:MAX_ENTRIES]


def get_entry(entry_id: str) -> HistoryDetail:
    meta = _load_meta(entry_id)
    text_file = _text_path(entry_id)
    if not text_file.is_file():
        raise HTTPException(status_code=404, detail="历史文本不存在")
    text = text_file.read_text(encoding="utf-8")
    game = None
    game_file = _game_path(entry_id)
    if game_file.is_file():
        try:
            game = GamePack.model_validate(json.loads(game_file.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, ValidationError):
            game = None
    return HistoryDetail(item=_meta_to_item(meta), text=text, game=game, progress=load_progress(entry_id))


def _default_title(req: HistorySaveRequest) -> str:
    if req.title and req.title.strip():
        return req.title.strip()
    if req.filename:
        stem = Path(req.filename).stem
        return stem or "未命名故事"
    snippet = req.text.strip().replace("\n", " ")[:32]
    return snippet or "未命名故事"


def save_entry(req: HistorySaveRequest) -> HistoryItem:
    _ensure_root()
    entry_id = req.entry_id
    if not entry_id and req.filename:
        entry_id = _find_by_filename(req.filename)
    if not entry_id:
        entry_id = uuid.uuid4().hex[:12]

    meta_file = _meta_path(entry_id)
    created_at = _now_iso()
    if meta_file.is_file():
        try:
            old = json.loads(meta_file.read_text(encoding="utf-8"))
            created_at = old.get("created_at") or created_at
        except (json.JSONDecodeError, OSError):
            pass

    game_data = req.game
    node_count = 0
    ending_count = 0
    branch_count = 0
    title = _default_title(req)
    share_token = None
    unlocked_endings = 0
    if meta_file.is_file():
        try:
            old_meta = json.loads(meta_file.read_text(encoding="utf-8"))
            share_token = old_meta.get("share_token")
            unlocked_endings = int(old_meta.get("unlocked_endings") or 0)
        except (json.JSONDecodeError, OSError):
            pass
        progress_raw = _load_progress_raw(entry_id)
        if progress_raw:
            unlocked_endings = len(progress_raw.get("unlocked") or [])
    if game_data:
        title = game_data.title or title
        node_count = len(game_data.nodes)
        ending_count = sum(1 for n in game_data.nodes.values() if n.is_ending)
        branch_count = sum(len(n.choices) for n in game_data.nodes.values())

    meta = {
        "id": entry_id,
        "title": title,
        "filename": req.filename,
        "style": req.style,
        "char_count": len(req.text),
        "created_at": created_at,
        "updated_at": _now_iso(),
        "has_game": game_data is not None,
        "node_count": node_count,
        "ending_count": ending_count,
        "branch_count": branch_count,
        "unlocked_endings": unlocked_endings,
        "share_token": share_token,
    }

    _entry_dir(entry_id).mkdir(parents=True, exist_ok=True)
    _text_path(entry_id).write_text(req.text, encoding="utf-8")
    if game_data:
        _game_path(entry_id).write_text(
            json.dumps(game_data.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        _game_path(entry_id).unlink(missing_ok=True)

    _write_meta(entry_id, meta)
    _prune_old_entries()
    return _meta_to_item(meta)


def ensure_share_token(entry_id: str) -> str:
    meta = _load_meta(entry_id)
    if not meta.get("has_game"):
        raise HTTPException(status_code=400, detail="该记录尚未生成可分享的游戏")
    token = meta.get("share_token")
    if not token:
        token = uuid.uuid4().hex[:10]
        meta["share_token"] = token
        meta["updated_at"] = _now_iso()
        _write_meta(entry_id, meta)
    return token


def get_entry_by_share_token(token: str) -> HistoryDetail:
    if not token or not re.fullmatch(r"[a-f0-9]{8,12}", token):
        raise HTTPException(status_code=400, detail="无效的分享链接")
    if not HISTORY_ROOT.is_dir():
        raise HTTPException(status_code=404, detail="分享内容不存在")
    for child in HISTORY_ROOT.iterdir():
        if not child.is_dir():
            continue
        meta_file = child / "meta.json"
        if not meta_file.is_file():
            continue
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if meta.get("share_token") == token and meta.get("has_game"):
            return get_entry(meta["id"])
    raise HTTPException(status_code=404, detail="分享内容不存在或已删除")


def touch_entry(entry_id: str) -> HistoryItem:
    meta = _load_meta(entry_id)
    meta["updated_at"] = _now_iso()
    _write_meta(entry_id, meta)
    return _meta_to_item(meta)


def delete_entry(entry_id: str) -> None:
    entry_dir = _entry_dir(entry_id)
    if not entry_dir.is_dir():
        raise HTTPException(status_code=404, detail="历史记录不存在")
    for f in entry_dir.iterdir():
        f.unlink(missing_ok=True)
    entry_dir.rmdir()
