# ═══════════════════════════════════════════════════════════════════════
# 카탈로그 — 기능이 아니라서 색인에 안 들어가던 것들을 찾게 한다.
#
# 무엇이 빠져 있었나: 색인은 bpy.ops 에 등록된 기능만 훑는다. 그런데 블렌더에는
# 기능이 아닌 것이 많다. 모디파이어는 '모디파이어 붙이기' 라는 기능 하나의
# 선택지일 뿐이라, 74가지 종류가 이름조차 없었다. 노드는 469가지가 '노드 추가'
# 하나 뒤에 숨어 있었다. 설정값은 아예 기능이 아니라서, '그림자 끄기' 를 쳐도
# 나오는 것이 없었다. 다 합쳐 1,567가지를 못 찾았다.
#
#     모디파이어 74 · 제약 29 · 노드 469 · 브러시 31 · 도구 64 · 설정값 900
#
# 한국어 이름은 어디서 오나: 블렌더에 딸려 오는 번역을 그대로 쓴다. 1,567개 중
# 1,472개에 번역이 있었다. 블렌더를 한국어로 쓰는 사람이 화면에서 보는 말과
# 같아야 헷갈리지 않기 때문이다. 번역이 없는 95개는 손으로 적었고, 그 가운데
# 뜻으로 옮긴 74개에는 음차도 별칭으로 함께 넣었다. '길게 뽑아내기' 만 적어
# 두면 '스네이크 훅' 이라고 부르는 사람이 못 찾기 때문이다.
# 영어 이름은 언제나 함께 보여 준다. 자료가 대부분 영어이기 때문이다.
#
# 카탈로그는 probe/build_catalog.py 가 블렌더에서 뽑아 만든다. 블렌더 판이
# 올라가면 그 스크립트를 다시 돌려 새 판의 것을 받아 온다.
#
# 어디에 두나: 정리된 항목(guide_ko.json)과 섞지 않는다. 1,567개가 같은 자격으로
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
_entries: list | None = None
# 팝업은 마우스가 움직일 때마다 다시 그린다. 1,567개를 그때마다 훑으면
# 손이 무겁게 느껴진다. 바로 앞에 찾은 것 한 벌만 들고 있는다.
_last: tuple | None = None


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
                                item.get("gloss", ""),
                                " ".join(item.get("aliases") or []),
                                item.get("kind_ko", ""),
                                item.get("note", ""))).lower()
    _items = found
    return _items


def get_error() -> str:
    return _error


def invalidate() -> None:
    global _items, _entries, _last
    _items = None
    _entries = None
    _last = None


def as_entries() -> list:
    """검색기가 먹을 수 있는 꼴로 바꾼다.

    정리된 항목과 같은 필드 이름을 쓰므로 같은 검색기와 같은 화면을 쓸 수 있다.
    다만 op 는 넣지 않는다. 모디파이어나 노드나 설정값은 눌러서 바로 실행할
    수 있는 것이 아니라 어디에 가서 고치는 것이기 때문이다.
    """
    global _entries
    if _entries is not None:
        return _entries
    made = []
    for item in load():
        made.append({
            "id": f"catalog:{item.get('kind')}:{item.get('key')}",
            "ko": item.get("ko", ""),
            "en": item.get("en", ""),
            "aliases": list(item.get("aliases") or []),
            "tags": [item.get("kind_ko", "")],
            "note": item.get("note", ""),
            "where": item.get("where", ""),
            # 블렌더에 번역이 없어 음차를 이름으로 삼은 것에만 있다.
            # 이름만으로는 무엇인지 알 수 없으므로 뜻을 한 줄 덧붙인다.
            "_gloss": item.get("gloss", ""),
            "modes": [],
            "shortcut": None,
            # 설정값은 같은 이름이 여러 자리에 있다. '해상도' 만 세 군데다.
            # 어느 묶음의 것인지 이름 옆에 함께 보여 주어야 고를 수 있다.
            "_kind_ko": (f"{item.get('kind_ko', '')} · {item['group']}"
                         if item.get("group") else item.get("kind_ko", "")),
        })
    _entries = made
    return _entries


def search(query: str, limit: int = 6) -> list:
    """카탈로그에서 찾는다. 정리된 항목과 같은 검색기를 쓴다."""
    global _last
    query = (query or "").strip()
    if not query:
        return []
    if _last is not None and _last[0] == query and _last[1] == limit:
        return _last[2]

    from . import search as engine
    from . import nl
    entries = as_entries()
    if not entries:
        return []
    # 카탈로그는 지금 모드와 상관없이 언제나 볼 수 있다.
    always = {e["id"]: True for e in entries}
    found = engine.search(entries, query, always, limit=limit)

    # 문장으로 친 것도 받아 준다. '샘플 수 올리기' 는 통째로는 아무 데도
    # 안 걸리지만 '샘플' 로는 렌더 샘플에 닿는다.
    if not found and nl.looks_like_sentence(query):
        words = nl.keywords(query)
        got, _ = nl.search(entries, query, always, limit=limit * 2)
        # 설명문에만 스쳐 걸린 것은 버린다. 카탈로그는 1,567개나 되어서
        # 그냥 두면 아무거나 그럴듯하게 올라온다.
        found = [entry for entry in got
                 if max((engine.score_entry(entry, word) for word in words),
                        default=0) >= engine.SCORE_TAG][:limit]

    _last = (query, limit, found)
    return found


def counts() -> dict:
    """종류별 개수를 돌려준다. 설정 화면에서 쓴다."""
    found = {}
    for item in load():
        name = item.get("kind_ko", "?")
        found[name] = found.get(name, 0) + 1
    return found
