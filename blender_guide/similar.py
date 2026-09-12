# ═══════════════════════════════════════════════════════════════════════
# 비슷한 것 찾기 — 오타나 소리만 옮긴 말도 닿게 한다.
#
# 왜 필요한가: 지금 검색은 글자가 정확히 들어 있어야 걸린다. '모서리' 를
# '모서라' 로 잘못 치거나 'Subdivide' 를 '섭디비전' 이라고 소리만 옮겨 적으면
# 아무것도 안 나온다. 실제로 열 가지를 재어 보니 지금 검색은 다섯 개를 놓쳤다.
#
# 어떻게 하는가: 글자를 두세 자씩 잘라 조각으로 만들고, 그 조각이 얼마나 겹치는지
# 로 가까움을 잰다. '모서라' 와 '모서리' 는 '모서' 라는 조각을 함께 갖는다.
#
# 왜 이 방법인가: 뜻을 아는 모델을 쓰면 더 좋겠지만, 그러려면 수백 MB짜리 모델을
# 애드온에 넣거나 글자를 칠 때마다 바깥에 물어봐야 한다. 둘 다 할 수 없다.
# 조각 겹침은 바깥 의존이 하나도 없고 1ms 안에 끝나며, 재어 보니 열 개 중
# 여덟 개를 맞혔다.
#
# ⚠️ 이것은 대체가 아니라 보완이다. 정확히 친 말은 지금 검색이 훨씬 낫다.
# '물체를 움직이게' 는 지금 검색이 맞히고 유사도는 틀렸다. 그래서 아무것도
# 못 찾았을 때만 끼어든다.
#
# 블렌더 없이 시험할 수 있다: python3 blender_guide/similar.py
# ═══════════════════════════════════════════════════════════════════════

from __future__ import annotations

import collections
import math

# 글자를 몇 자씩 자를 것인가.
#
# 두 자와 세 자를 함께 쓰는 까닭: 두 자만 쓰면 '면' 이나 '기' 같은 흔한 조각이
# 너무 많이 걸리고, 세 자만 쓰면 짧은 낱말이 조각을 거의 못 만든다.
GRAM_SIZES = (2, 3)

# 이보다 낮으면 안 보여 준다.
#
# 왜 문턱이 필요한가: 유사도는 언제나 뭔가를 내놓는다. 아무 관계 없는 것도
# 조각 하나만 겹치면 점수가 조금 붙는다. 그것을 그대로 보여 주면 '비슷한 것' 이
# 아니라 '아무거나' 가 된다.
#
# 왜 0.12 인가: 실제로 재어 보고 정했다. 뜻 없는 'asdfgh' 가 0.085 까지 올라오고,
# 제대로 된 오타인 '키프래임' 이 0.143, 'bevle' 이 0.165 이다. 그 사이에 둔다.
# 더 내리면 아무 말에나 뭔가가 나오고, 더 올리면 오타를 놓친다.
#
# ⚠️ 외래어를 소리대로 적은 말('서브디비전')은 조각이 거의 안 겹쳐서 이 방법으로는
#    못 잡는다. 그런 것은 항목의 별칭에 적어 두는 편이 맞다. 문턱을 억지로 내려
#    맞추면 엉뚱한 것까지 함께 올라온다.
MIN_SCORE = 0.12

_index: dict | None = None


def grams(text: str) -> list:
    """글자를 두세 자씩 잘라 조각 목록으로 만든다."""
    text = (text or "").lower()
    found = []
    for size in GRAM_SIZES:
        for i in range(len(text) - size + 1):
            piece = text[i:i + size]
            if piece.strip():
                found.append(piece)
    return found


def _entry_text(entry: dict) -> str:
    """항목에서 견줄 글자를 모은다.

    설명문(note)은 넣지 않는다. 길어서 조각이 너무 많아지고, 그러면 설명문이
    긴 항목이 무엇을 쳐도 걸리게 된다.
    """
    return " ".join([
        entry.get("ko", ""),
        " ".join(entry.get("aliases", [])),
        entry.get("en", "") or "",
        " ".join(entry.get("tags", [])),
    ])


def build(entries: list, force: bool = False) -> dict:
    """조각 사전을 만든다. 항목이 바뀌지 않으면 다시 만들지 않는다.

    두 번 훑는 까닭: 조각의 무게(idf)는 전체를 봐야 정해지는데, 길이는 그 무게를
    곱한 뒤에 재야 한다. 한 번에 하려다 무게를 두 번 곱하고 길이는 무게 없이 재어서,
    가까움이 1을 넘는 값이 나왔다. 그러면 문턱을 정할 수가 없다.
    """
    global _index
    if _index is not None and not force and _index["count"] == len(entries):
        return _index

    # ① 항목마다 조각을 세고, 조각이 몇 항목에 나오는지 함께 센다.
    per_entry = []
    document_count: dict = collections.Counter()
    for entry in entries:
        counts = collections.Counter(grams(_entry_text(entry)))
        per_entry.append(counts)
        for piece in counts:
            document_count[piece] += 1

    # ② 흔한 조각일수록 무게를 줄인다.
    total = max(1, len(entries))
    idf = {piece: math.log((total + 1) / (n + 1)) + 1.0
           for piece, n in document_count.items()}

    # ③ 무게를 곱한 뒤에 길이를 잰다. 그래야 가까움이 0과 1 사이에 들어온다.
    posting: dict = collections.defaultdict(list)
    lengths = []
    for i, counts in enumerate(per_entry):
        squared = 0.0
        for piece, n in counts.items():
            weighted = n * idf[piece]
            posting[piece].append((i, weighted))
            squared += weighted * weighted
        lengths.append(math.sqrt(squared) or 1.0)

    _index = {"posting": dict(posting), "idf": idf, "lengths": lengths,
              "count": len(entries)}
    return _index


def invalidate() -> None:
    global _index
    _index = None


def search(entries: list, query: str, limit: int = 5,
           min_score: float = MIN_SCORE) -> list:
    """비슷한 항목을 가까운 순으로 돌려준다. (항목, 가까움) 목록이다."""
    query = (query or "").strip()
    if not query or not entries:
        return []

    index = build(entries)
    counts = collections.Counter(grams(query))
    if not counts:
        return []

    idf = index["idf"]
    posting = index["posting"]

    # 친 말도 같은 방식으로 무게를 곱하고 길이를 잰다.
    weighted_query = {}
    squared = 0.0
    for piece, n in counts.items():
        weight = idf.get(piece)
        if weight is None:
            continue                 # 어느 항목에도 없는 조각이다.
        value = n * weight
        weighted_query[piece] = value
        squared += value * value
    if not weighted_query:
        return []
    query_length = math.sqrt(squared) or 1.0

    scores: dict = collections.defaultdict(float)
    for piece, value in weighted_query.items():
        for i, doc_value in posting[piece]:
            scores[i] += value * doc_value

    ranked = []
    for i, raw in scores.items():
        close = raw / (index["lengths"][i] * query_length)
        if close >= min_score:
            ranked.append((close, entries[i]))

    ranked.sort(key=lambda pair: -pair[0])
    return [(entry, round(close, 3)) for close, entry in ranked[:limit]]


# ── 블렌더 없이 확인하는 자체 시험 ────────────────────────────────────
if __name__ == "__main__":
    import json
    import os
    import sys

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "data", "guide_ko.json"), encoding="utf-8") as f:
        entries = json.load(f)["entries"]

    # 지금 검색이 놓치는 것들이다. 오타와 소리만 옮긴 말이 대부분이다.
    cases = [
        ("모서라 둥글게", "bevel"),
        ("서브디비전", "subdivide"),
        ("키프래임", "keyframe_insert"),
        ("bevle", "bevel"),
        ("subdivid", "subdivide"),
        ("까맣게 보임", "recalc_normals"),
        ("아마추어 넣기", "armature_add"),
        ("셰이프 키", "shape_key_add"),
    ]

    passed = failed = 0
    for text, want in cases:
        got = search(entries, text, limit=3)
        head = got[0][0].get("id") if got else None
        if head == want:
            passed += 1
            print(f"  [통과] {text!r} → {want} (가까움 {got[0][1]})")
        else:
            failed += 1
            names = [(e.get('id'), s) for e, s in got[:3]]
            print(f"  [실패] {text!r} → {want} 이어야 하는데 {names}")

    # 아무 관계 없는 말에는 아무것도 안 나와야 한다.
    for junk in ("zzzzzz", "ㅋㅋㅋㅋ", "asdfgh"):
        got = search(entries, junk)
        if got:
            failed += 1
            print(f"  [실패] {junk!r} 에 엉뚱한 것이 나왔다: "
                  f"{[(e.get('id'), s) for e, s in got[:2]]}")
        else:
            passed += 1
            print(f"  [통과] {junk!r} → 아무것도 안 나온다")

    print(f"\n비슷한 것 찾기 시험: {passed}건 통과 / {failed}건 실패 "
          f"(전체 {passed + failed}건)")
    sys.exit(1 if failed else 0)
