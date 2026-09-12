# ═══════════════════════════════════════════════════════════════════════
# 카탈로그 — 기능이 아니라서 색인에 안 들어가던 것들을 찾게 한다.
#
# 무엇이 빠져 있었나: 색인은 bpy.ops 에 등록된 기능만 훑는다. 그런데 블렌더에는
# 기능이 아닌 것이 많다. 모디파이어는 '모디파이어 붙이기' 라는 기능 하나의
# 선택지일 뿐이라, 83가지 종류가 이름조차 없었다. 노드는 469가지가 '노드 추가'
# 하나 뒤에 숨어 있었다. 다 합쳐 667가지를 못 찾았다.
#
#     모디파이어 74 · 제약 29 · 노드 469 · 브러시 31 · 도구 64
#
# 한국어 이름은 어디서 오나: 블렌더에 딸려 오는 번역을 그대로 쓴다. 667개 중
# 601개에 번역이 있었다. 블렌더를 한국어로 쓰는 사람이 화면에서 보는 말과 같아야
# 헷갈리지 않기 때문이다. 번역이 없는 75개는 손으로 적었다.
# 영어 이름은 언제나 함께 보여 준다. 자료가 대부분 영어이기 때문이다.
#
# 어디에 두나: 정리된 항목(guide_ko.json)과 섞지 않는다. 667개가 같은 자격으로
# 끼어들면, 하나의 답을 주던 검색이 수십 개를 쏟아내게 된다. 그래서 정리된
# 항목에서 못 찾았을 때만 따로 보여 준다.
# ═══════════════════════════════════════════════════════════════════════

from __future__ import annotations

import json
import os

_CATALOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "data", "catalog_ko.json")

_items: list | None = None
_error: str = ""


def load(force: bool = False) -> list:
    """카탈로그를 읽는다. 못 읽으면 빈 목록을 돌려주고 까닭을 적어 둔다."""
    global _items, _error
    if _items is not None and not force:
        return _items

    _error = ""
    try:
        with open(_CATALOG_PATH, encoding="utf-8") as handle:
            data = json.load(handle)
        found = data.get("catalog")
        if not isinstance(found, list):
            raise ValueError("catalog 목록이 들어 있지 않습니다")
    except Exception as exc:
        _error = f"{type(exc).__name__}: {exc}"
        _items = []
        return _items

    # 검색에 쓸 비교용 한 덩어리를 미리 만들어 둔다.
    for item in found:
        item["hay"] = " ".join((item.get("ko", ""), item.get("en", ""),
                                item.get("kind_ko", ""),
                                item.get("note", ""))).lower()
    _items = found
    return _items


def get_error() -> str:
    return _error


def invalidate() -> None:
    global _items
    _items = None


def as_entries() -> list:
    """검색기가 먹을 수 있는 꼴로 바꾼다.

    정리된 항목과 같은 필드 이름을 쓰므로 같은 검색기와 같은 화면을 쓸 수 있다.
    다만 op 는 넣지 않는다. 모디파이어나 노드는 눌러서 바로 실행할 수 있는
    것이 아니라 어디에 가서 골라야 하는 것이기 때문이다.
    """
    made = []
    for item in load():
        made.append({
            "id": f"catalog:{item.get('kind')}:{item.get('key')}",
            "ko": item.get("ko", ""),
            "en": item.get("en", ""),
            "aliases": [],
            "tags": [item.get("kind_ko", "")],
            "note": item.get("note", ""),
            "where": item.get("where", ""),
            "modes": [],
            "shortcut": None,
            "_kind_ko": item.get("kind_ko", ""),
        })
    return made


def search(query: str, limit: int = 6) -> list:
    """카탈로그에서 찾는다. 정리된 항목과 같은 검색기를 쓴다."""
    query = (query or "").strip()
    if not query:
        return []
    from . import search as engine
    entries = as_entries()
    if not entries:
        return []
    # 카탈로그는 지금 모드와 상관없이 언제나 볼 수 있다.
    always = {e["id"]: True for e in entries}
    return engine.search(entries, query, always, limit=limit)


def counts() -> dict:
    """종류별 개수를 돌려준다. 설정 화면에서 쓴다."""
    found = {}
    for item in load():
        name = item.get("kind_ko", "?")
        found[name] = found.get(name, 0) + 1
    return found
