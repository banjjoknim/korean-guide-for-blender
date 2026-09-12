# ═══════════════════════════════════════════════════════════════════════
# 검색 기록 — 골라 본 항목을 기억해서 다음에 더 빨리 찾게 한다.
#
# 왜 필요한가: 초보자가 쓰는 기능은 몇 가지로 좁혀진다. 그런데 검색어를 칠
# 때마다 매번 같은 자리에서 같은 것을 찾아야 한다. 한 번 고른 것을 기억해 두면
# 두 번째부터는 훨씬 빨리 닿는다.
#
# 즐겨찾기와 무엇이 다른가: 즐겨찾기는 사용자가 별표를 눌러 '일부러' 남기는
# 것이고, 기록은 쓰다 보면 '저절로' 쌓이는 것이다. 초보자는 무엇을 즐겨찾기할지
# 판단할 만큼 알지 못하므로, 저절로 쌓이는 쪽이 먼저 도움이 된다.
#
# 어떻게 담는가: 즐겨찾기와 같은 방식으로 글자 하나(JSON)에 눌러 담는다.
# 블렌더 설정에는 목록을 그대로 저장하는 자리가 없기 때문이다.
# ═══════════════════════════════════════════════════════════════════════

from __future__ import annotations

import json
import time

# 검색 순위에 얹어 주는 점수의 최댓값이다.
#
# 왜 80 인가: 검색 점수는 단계마다 100씩 벌어져 있다(이름이 똑같으면 1000,
# 이름으로 시작하면 800 하는 식이다). 기록 점수가 100을 넘으면 덜 맞는 항목이
# 더 맞는 항목을 제칠 수 있다. 80으로 묶어 두면 같은 단계 안에서만 순서가
# 바뀌므로, 기록이 검색의 정확도를 해치지 않는다.
MAX_BOOST = 80
_BOOST_BASE = 30          # 기록에 있기만 해도 주는 점수
_BOOST_PER_PICK = 12      # 고른 횟수마다 더해 주는 점수


def load(prefs_obj) -> list:
    """저장해 둔 글자를 기록 목록으로 되돌린다.

    한 칸은 {"id": 항목 id, "count": 고른 횟수, "at": 마지막으로 고른 때} 이다.
    최근에 고른 것이 앞에 온다.
    """
    try:
        value = json.loads(getattr(prefs_obj, "history_json", "[]"))
    except Exception:
        return []
    if not isinstance(value, list):
        return []

    cleaned = []
    for item in value:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        cleaned.append({"id": str(item["id"]),
                        "count": int(item.get("count", 1)),
                        "at": float(item.get("at", 0.0))})
    return cleaned


def save(prefs_obj, items: list) -> None:
    try:
        prefs_obj.history_json = json.dumps(items, ensure_ascii=False)
    except Exception:
        # 설정을 못 쓰는 상태여도 애드온이 멈추면 안 된다. 기록만 안 남는다.
        pass


def record(context, entry_id: str) -> None:
    """항목 하나를 골랐다고 적어 둔다.

    같은 것을 또 고르면 횟수만 올리고 맨 앞으로 옮긴다.
    """
    if not entry_id:
        return

    from . import prefs
    p = prefs.get_prefs(context)
    if not hasattr(p, "history_json"):
        # 설정을 못 읽는 상태이다. 기록은 건너뛰고 나머지는 그대로 돌아간다.
        return
    if not getattr(p, "use_history", True):
        return

    items = load(p)
    found = None
    for item in items:
        if item["id"] == entry_id:
            found = item
            break

    if found is None:
        found = {"id": entry_id, "count": 0, "at": 0.0}
    else:
        items.remove(found)

    found["count"] += 1
    found["at"] = time.time()
    items.insert(0, found)

    limit = max(1, int(getattr(p, "max_history", 10)))
    save(p, items[:limit])


def recent(context, limit: int = 0) -> list:
    """최근에 고른 항목 id 를 앞에서부터 돌려준다."""
    from . import prefs
    p = prefs.get_prefs(context)
    if not getattr(p, "use_history", True):
        return []
    items = load(p)
    ids = [item["id"] for item in items]
    return ids[:limit] if limit else ids


def boosts(context) -> dict:
    """검색 순위에 얹을 점수를 항목 id 별로 돌려준다."""
    from . import prefs
    p = prefs.get_prefs(context)
    if not getattr(p, "use_history", True):
        return {}

    table = {}
    for item in load(p):
        score = _BOOST_BASE + _BOOST_PER_PICK * (item["count"] - 1)
        table[item["id"]] = min(MAX_BOOST, score)
    return table


def pick_count(context, entry_id: str) -> int:
    """그 항목을 몇 번 골랐는지 돌려준다. 0 이면 기록에 없다."""
    from . import prefs
    for item in load(prefs.get_prefs(context)):
        if item["id"] == entry_id:
            return item["count"]
    return 0


def clear(context) -> None:
    from . import prefs
    p = prefs.get_prefs(context)
    if hasattr(p, "history_json"):
        save(p, [])
