import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from pydantic import ValidationError

from history_models import HistoryDetail, HistoryItem, HistorySaveRequest
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
    return HistoryItem.model_validate(meta)


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
    return HistoryDetail(item=_meta_to_item(meta), text=text, game=game)


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
    title = _default_title(req)
    if game_data:
        title = game_data.title or title
        node_count = len(game_data.nodes)
        ending_count = sum(1 for n in game_data.nodes.values() if n.is_ending)

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


def delete_entry(entry_id: str) -> None:
    entry_dir = _entry_dir(entry_id)
    if not entry_dir.is_dir():
        raise HTTPException(status_code=404, detail="历史记录不存在")
    for f in entry_dir.iterdir():
        f.unlink(missing_ok=True)
    entry_dir.rmdir()
