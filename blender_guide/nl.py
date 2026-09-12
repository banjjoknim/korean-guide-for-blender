# ═══════════════════════════════════════════════════════════════════════
# 자연어 검색 — 문장으로 쳐도 찾게 한다.
#
# 왜 필요한가: 초보자는 '면 나누기' 처럼 낱말로 치지 못한다. '면을 둘로
# 나누고 싶어' 처럼 문장으로 친다. 지금 검색기는 짧은 낱말을 받도록 만들어져
# 있어서 문장을 통째로 넘기면 아무것도 안 걸린다.
#
# 하는 일은 단순하다. 문장에서 군더더기를 걷어내고 핵심 낱말만 남긴 뒤,
# 원래 검색기에 넘긴다. 검색 규칙을 두 벌로 만들면 한쪽만 고쳐지는 일이
# 생기므로, 새 규칙을 만들지 않고 기존 검색기를 그대로 쓴다.
#
# 여기까지는 바깥에 아무것도 묻지 않는다. 이것으로 안 되는 것만 agent.py 가
# 에이전트에게 넘긴다.
#
# 블렌더 없이 시험할 수 있다: python3 blender_guide/nl.py
# ═══════════════════════════════════════════════════════════════════════

from __future__ import annotations

import re

# 문장 끝에 붙는 요청 표현이다. 긴 것부터 지워야 짧은 것이 먼저 먹지 않는다.
_ASK_PATTERNS = [
    "하고 싶은데", "하고싶은데", "하고 싶어요", "하고싶어요", "하고 싶어", "하고싶어",
    "하고 싶다", "하고싶다", "싶은데", "싶어요", "싶어", "싶다",
    "하려면 어떻게", "하려면", "하는 방법", "하는방법", "하는 법", "하는법",
    "어떻게 해요", "어떻게 해", "어떻게해", "어떻게",
    "알려 주세요", "알려주세요", "알려 줘", "알려줘", "가르쳐 줘", "가르쳐줘",
    "보여 줘", "보여줘", "해 주세요", "해주세요", "해 줘", "해줘",
    "할 수 있어", "할수있어", "하고 싶은", "가능해", "되나요", "되나", "될까",
    "있나요", "있어요", "인가요", "인가", "일까", "뭐야", "뭐죠", "뭔가요",
    "무엇", "방법", "좀", "제발", "please",
]

# 혼자서는 뜻이 없는 낱말이다. 남겨 두면 엉뚱한 항목이 걸린다.
_STOPWORDS = {
    "이거", "그거", "저거", "이것", "그것", "저것", "여기", "거기", "저기",
    "지금", "다시", "계속", "전부", "모두", "각각", "너무", "조금", "많이",
    "그냥", "혹시", "아까", "방금", "나는", "내가", "제가", "저는",
    "블렌더", "블랜더", "에서", "으로", "라고", "하는", "하고", "해서",
}

# 낱말 끝에 붙는 조사이다. 긴 것부터 떼어야 한다.
_PARTICLES = [
    "에서부터", "에서는", "으로는", "에게서", "한테서",
    "에서", "으로", "에게", "한테", "부터", "까지", "이나", "이랑", "라도",
    "처럼", "보다", "마다", "조차", "밖에", "만큼",
    "를", "을", "이", "가", "은", "는", "의", "에", "로", "와", "과", "랑",
    "도", "만", "요",
]

# 용언 끝에 붙는 어미이다. '나누고' 에서 '고' 를 떼면 '나누' 가 남아서
# 항목의 '나누기' 와 앞이 맞는다. 이것을 안 하면 활용형이 전부 빗나간다.
_ENDINGS = ["습니다", "합니다", "하려고", "하려", "시켜", "시키",
            "으려고", "려고", "으면", "면서", "면", "니까", "니",
            "아서", "어서", "여서", "서", "고", "게", "자", "지", "기"]

# 조사를 떼고 나서 이만큼은 남아야 낱말로 인정한다.
# 왜: '면을' 에서 '을' 을 떼면 '면' 한 글자가 남는데 이것은 뜻이 있다.
#     반면 '이' 같은 한 글자를 떼어 아무것도 안 남으면 버려야 한다.
_MIN_TOKEN = 1


def strip_asking(text: str) -> str:
    """문장에서 요청하는 말투를 걷어낸다."""
    cleaned = text
    for pattern in _ASK_PATTERNS:
        cleaned = cleaned.replace(pattern, " ")
    return re.sub(r"\s+", " ", cleaned).strip()


def strip_particle(token: str) -> str:
    """낱말 끝의 조사를 뗀다. 떼고 나면 너무 짧아지는 경우에는 그대로 둔다."""
    for particle in _PARTICLES:
        if token.endswith(particle) and len(token) - len(particle) >= _MIN_TOKEN:
            return token[: -len(particle)]
    return token


def stems(token: str) -> list:
    """낱말과, 어미를 뗀 줄기를 함께 돌려준다.

    둘 다 쓰는 까닭: '나누고' 는 '나누기' 와 앞이 안 맞지만 줄기 '나누' 는 맞는다.
    반대로 '모서리' 처럼 어미가 아닌데 어미처럼 끝나는 낱말도 있으므로,
    줄기만 쓰면 안 되고 원래 낱말도 남겨야 한다.
    """
    found = [token]
    for ending in _ENDINGS:
        if token.endswith(ending) and len(token) - len(ending) >= 2:
            stem = token[: -len(ending)]
            if stem not in found:
                found.append(stem)
            break
    return found


def keywords(text: str) -> list:
    """문장에서 찾을 만한 낱말만 남긴다."""
    cleaned = strip_asking(text or "")
    # 물음표·마침표 같은 것은 낱말 경계로 본다.
    cleaned = re.sub(r"[?!.,~…·\"'()\[\]{}]", " ", cleaned)

    found = []
    for raw in cleaned.split():
        token = strip_particle(raw.strip())
        if not token or token in _STOPWORDS:
            continue
        if len(token) < _MIN_TOKEN:
            continue
        if token not in found:
            found.append(token)
    return found


def looks_like_sentence(text: str) -> bool:
    """문장으로 친 것인지 낱말로 친 것인지 가늠한다.

    낱말로 친 것까지 손대면 멀쩡하던 검색이 틀어진다. 그래서 띄어쓰기가 있거나
    요청하는 말투가 섞였을 때만 자연어로 다룬다.
    """
    text = (text or "").strip()
    if not text:
        return False
    if " " in text:
        return True
    return any(p in text for p in _ASK_PATTERNS)


def search(entries: list, text: str, availability: dict | None = None,
           limit: int = 8, boosts: dict | None = None) -> tuple:
    """문장으로 찾는다. (결과 목록, 실제로 쓴 낱말) 을 돌려준다.

    쓴 낱말을 함께 돌려주는 까닭: 무엇으로 찾았는지 화면에 보여 주어야
    사용자가 '아, 이렇게 치면 되는구나' 를 배운다. 못 찾았을 때도 무엇이
    빠졌는지 알 수 있다.
    """
    # 블렌더 안에서는 꾸러미로, 자체 시험에서는 홀로 읽힌다. 둘 다 되게 한다.
    try:
        from . import search as engine
    except ImportError:
        import search as engine

    words = keywords(text)
    if not words:
        return [], []

    availability = availability or {}
    boosts = boosts or {}

    # 낱말마다 쓸 만한 꼴을 모아 둔다. 어미를 뗀 줄기까지 함께 본다.
    forms = {word: stems(word) for word in words}

    # 항목마다 (가장 높은 점수, 걸린 낱말 수) 를 모은다.
    best_score: dict = {}
    covered: dict = {}
    entry_by_id: dict = {}

    def take(query, word=None):
        for entry in entries:
            eid = entry.get("id")
            now = bool(availability.get(eid, False))
            score = engine.score_entry(entry, query, available_now=now)
            if score <= 0:
                continue
            entry_by_id[eid] = entry
            if score > best_score.get(eid, 0):
                best_score[eid] = score
            if word is not None:
                covered.setdefault(eid, set()).add(word)

    # 낱말을 붙여서 한 번 본다. 붙여야만 걸리는 항목이 있다.
    take(" ".join(words))
    for word, shapes in forms.items():
        for shape in shapes:
            take(shape, word)

    # ⚠️ 점수만으로 줄을 세우면 안 된다. '면' 처럼 흔한 낱말 하나만 걸린 항목이
    #    '면' 과 '나누' 를 둘 다 맞힌 항목을 이긴다. 실제로 '면을 둘로 나누고
    #    싶어' 가 '면 밀어내기' 로 갔다. 그래서 걸린 낱말이 많을수록 올려 준다.
    #    검색 점수는 단계마다 100씩 벌어져 있으므로 낱말 하나당 100이면
    #    한 단계를 넘어설 수 있고, 세 낱말 넘게는 쳐 주지 않는다.
    best: dict = {}
    for eid, score in best_score.items():
        extra = min(3, len(covered.get(eid, ())) - 1) if eid in covered else 0
        total = score + boosts.get(eid, 0) + 100 * max(0, extra)
        best[eid] = (total, entry_by_id[eid])

    ranked = sorted(best.values(),
                    key=lambda pair: (-pair[0], len(pair[1].get("ko", ""))))
    return [entry for _, entry in ranked[:limit]], words


# ── 블렌더 없이 확인하는 자체 시험 ────────────────────────────────────
if __name__ == "__main__":
    import json
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "data", "guide_ko.json"), encoding="utf-8") as f:
        entries = json.load(f)["entries"]

    # 왼쪽이 사용자가 칠 법한 문장, 오른쪽이 첫 번째로 나와야 하는 항목이다.
    cases = [
        ("면을 둘로 나누고 싶어", "subdivide"),
        ("모서리를 둥글게 하려면 어떻게 해?", "bevel"),
        ("물체를 복제하는 방법 알려줘", "duplicate"),
        ("가로줄 넣고 싶은데", "loopcut"),
        ("면을 밀어내고 싶어요", "extrude"),
        ("좌우 대칭으로 만들고 싶어", "modifier_mirror"),
        ("뒷면까지 비쳐 보이게 해줘", "toggle_xray"),
        ("에디트 모드 들어가는 법", "toggle_editmode"),
        ("구멍을 막고 싶어", "fill_face"),
        ("점을 합치고 싶은데 어떻게 해", "merge"),
        ("전체가 보이게 해줘", "view_all"),
        ("물체를 지우고 싶어", "delete_object"),
    ]

    passed = failed = 0
    for text, want in cases:
        got, words = search(entries, text)
        head = got[0].get("id") if got else None
        if head == want:
            passed += 1
            print(f"  [통과] {text!r} → {want} · 쓴 낱말 {words}")
        else:
            failed += 1
            names = [e.get("id") for e in got[:3]]
            print(f"  [실패] {text!r} → {want} 이어야 하는데 {names} · 쓴 낱말 {words}")

    print(f"\n자연어 시험: {passed}건 통과 / {failed}건 실패 (전체 {passed + failed}건)")
    sys.exit(1 if failed else 0)
