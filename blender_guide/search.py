# ═══════════════════════════════════════════════════════════════════════
# 검색 — 한국어로 친 말을 가이드 항목에 이어 준다.
#
# 책임: 검색어 하나를 받아서 항목 목록을 점수 순으로 돌려준다.
# 핵심 패턴: 블렌더 API 를 전혀 쓰지 않는다. 그래서 블렌더를 켜지 않고도
#            `python3 blender_guide/search.py` 로 검색 품질을 시험할 수 있다.
#
# 왜 이렇게 나눴는가: 검색이 잘 걸리는지는 눈으로 보기 전에 숫자로 확인해야
# 하는데, 블렌더를 띄워야만 확인할 수 있으면 한 번 고칠 때마다 수십 초가 든다.
# ═══════════════════════════════════════════════════════════════════════

from __future__ import annotations

# 한글 초성 목록. 유니코드에 정해진 순서 그대로이며 바꾸면 안 된다.
CHOSUNG = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"

HANGUL_BASE = 0xAC00   # '가'
HANGUL_LAST = 0xD7A3   # '힣'
JONGSUNG_COUNT = 28    # 받침의 가짓수(없음을 포함한다)
JUNGSUNG_COUNT = 21    # 가운뎃소리의 가짓수
# 초성 하나가 차지하는 칸 수. '가'부터 '깋'까지가 588자이다.
CHOSUNG_STRIDE = JUNGSUNG_COUNT * JONGSUNG_COUNT  # 588


def normalize(text: str) -> str:
    """검색어와 비교 대상을 같은 모양으로 맞춘다.

    공백을 지우는 이유: 초보자는 '면 나누기'와 '면나누기'를 섞어 친다.
    공백을 남겨 두면 둘 중 하나만 걸려서, 안 걸린 쪽에서는 검색이 고장 난 것처럼 보인다.
    """
    return "".join(text.split()).lower()


def to_chosung(text: str) -> str:
    """글자를 초성만 남긴 문자열로 바꾼다. ('면 나누기' -> 'ㅁㄴㄴㄱ')

    한글이 아닌 글자는 그대로 둔다. 영어 이름이 섞인 항목에서도 쓸 수 있게 하기 위해서이다.
    """
    out = []
    for ch in text:
        code = ord(ch)
        if HANGUL_BASE <= code <= HANGUL_LAST:
            out.append(CHOSUNG[(code - HANGUL_BASE) // CHOSUNG_STRIDE])
        elif not ch.isspace():
            out.append(ch.lower())
    return "".join(out)


def is_chosung_query(query: str) -> bool:
    """검색어가 초성으로만 이루어졌는지 본다.

    초성 검색은 글자 수가 적어서 아무 항목에나 걸리기 쉽다. 그래서 검색어가
    전부 초성일 때만 초성 비교를 하고, 평범한 말이 섞이면 하지 않는다.
    """
    stripped = normalize(query)
    return bool(stripped) and all(ch in CHOSUNG for ch in stripped)


# ── 점수표 ────────────────────────────────────────────────────────────
# 높을수록 위에 뜬다. 값을 바꾸면 결과 순서가 바뀌므로, 바꾼 뒤에는
# `python3 blender_guide/search.py` 로 예시 검색어들을 다시 확인한다.
SCORE_KO_EXACT      = 1000   # 한국어 이름이 검색어와 똑같다
SCORE_ALIAS_EXACT   = 900    # 별칭이 검색어와 똑같다
SCORE_KO_PREFIX     = 800    # 한국어 이름이 검색어로 시작한다
SCORE_ALIAS_PREFIX  = 700    # 별칭이 검색어로 시작한다
SCORE_KO_CONTAINS   = 600    # 한국어 이름 안에 검색어가 들어 있다
SCORE_ALIAS_CONTAIN = 500    # 별칭 안에 검색어가 들어 있다
SCORE_EN_PREFIX     = 450    # 영어 이름이 검색어로 시작한다
SCORE_EN_CONTAINS   = 400    # 영어 이름 안에 검색어가 들어 있다
SCORE_TAG           = 300    # 분류 이름이 걸린다
SCORE_NOTE          = 200    # 설명문 안에 들어 있다
SCORE_CHOSUNG       = 150    # 초성이 맞는다
SCORE_TOKEN_ALL     = 350    # 띄어 쓴 낱말이 모두 어딘가에 들어 있다

# 검색 결과가 지금 상황에서 바로 쓸 수 있는 것이면 이만큼 더해서 위로 올린다.
# 왜: '지금 눌러도 되는 것'이 '모드를 바꿔야 하는 것'보다 먼저 보여야 덜 헤맨다.
BONUS_AVAILABLE_NOW = 120


def _entry_haystacks(entry: dict) -> dict:
    """항목 하나에서 비교에 쓸 문자열들을 미리 만들어 둔다.

    매번 만들면 글자가 바뀔 때마다 61개 항목을 전부 다시 다듬게 되므로,
    처음 한 번만 만들어 항목 안에 넣어 두고 다시 쓴다.
    """
    cache = entry.get("_search_cache")
    if cache is not None:
        return cache

    ko = normalize(entry.get("ko", ""))
    aliases = [normalize(a) for a in entry.get("aliases", [])]
    en = normalize(entry.get("en") or "")
    tags = [normalize(t) for t in entry.get("tags", [])]
    note = normalize(entry.get("note") or "")
    where = normalize(entry.get("where") or "")

    cache = {
        "ko": ko,
        "aliases": aliases,
        "en": en,
        "tags": tags,
        "note": note + where,
        "chosung": to_chosung(entry.get("ko", "")),
        "alias_chosung": [to_chosung(a) for a in entry.get("aliases", [])],
        # 낱말 단위 비교에 쓰는 한 덩어리. 한국어·영어·분류를 모두 붙여 둔다.
        "blob": " ".join([ko] + aliases + [en, note, where] + tags),
    }
    entry["_search_cache"] = cache
    return cache


def score_entry(entry: dict, query: str, available_now: bool = False) -> int:
    """항목 하나가 검색어에 얼마나 맞는지 점수로 매긴다. 0 이면 안 걸린 것이다."""
    q = normalize(query)
    if not q:
        return 0

    hay = _entry_haystacks(entry)
    best = 0

    # 초성만 친 경우에는 초성끼리만 비교한다.
    if is_chosung_query(query):
        if hay["chosung"].startswith(q):
            best = max(best, SCORE_CHOSUNG + 60)
        elif q in hay["chosung"]:
            best = max(best, SCORE_CHOSUNG + 30)
        else:
            for ac in hay["alias_chosung"]:
                if ac.startswith(q):
                    best = max(best, SCORE_CHOSUNG)
                    break
        return best + (BONUS_AVAILABLE_NOW if best and available_now else 0)

    # 한국어 이름
    if hay["ko"] == q:
        best = max(best, SCORE_KO_EXACT)
    elif hay["ko"].startswith(q):
        best = max(best, SCORE_KO_PREFIX)
    elif q in hay["ko"]:
        best = max(best, SCORE_KO_CONTAINS)

    # 별칭
    for a in hay["aliases"]:
        if a == q:
            best = max(best, SCORE_ALIAS_EXACT)
        elif a.startswith(q):
            best = max(best, SCORE_ALIAS_PREFIX)
        elif q in a:
            best = max(best, SCORE_ALIAS_CONTAIN)

    # 영어 이름. 영어 이름을 이미 아는 사람도 쓸 수 있어야 한다.
    if hay["en"]:
        if hay["en"].startswith(q):
            best = max(best, SCORE_EN_PREFIX)
        elif q in hay["en"]:
            best = max(best, SCORE_EN_CONTAINS)

    # 분류
    for t in hay["tags"]:
        if q in t:
            best = max(best, SCORE_TAG)

    # 설명문과 메뉴 경로. 여기까지 와야 걸리는 것은 관련이 약하므로 점수가 낮다.
    if q in hay["note"]:
        best = max(best, SCORE_NOTE)

    # 낱말을 띄어 쳤을 때: 모든 낱말이 어딘가에 들어 있으면 인정한다.
    # 예를 들어 '면 뽑기'는 '면 밀어내기'의 이름에는 없지만 별칭에 '뽑기'가 있다.
    tokens = [normalize(t) for t in query.split() if t.strip()]
    if len(tokens) > 1 and all(t in hay["blob"] for t in tokens):
        best = max(best, SCORE_TOKEN_ALL)

    if best and available_now:
        best += BONUS_AVAILABLE_NOW
    return best


def search(entries: list, query: str, availability: dict | None = None,
           limit: int = 12) -> list:
    """검색어에 맞는 항목을 점수가 높은 순으로 돌려준다.

    availability: 항목 id 를 키로, 지금 쓸 수 있는지를 참·거짓으로 담은 사전이다.
                  넘기지 않으면 상황을 따지지 않고 점수만으로 줄을 세운다.
    """
    availability = availability or {}
    scored = []
    for e in entries:
        now = bool(availability.get(e.get("id"), False))
        s = score_entry(e, query, available_now=now)
        if s > 0:
            scored.append((s, e))
    # 점수가 같으면 한국어 이름이 짧은 것을 앞에 둔다. 짧은 이름이 대개 더 기본적인 기능이다.
    scored.sort(key=lambda pair: (-pair[0], len(pair[1].get("ko", ""))))
    return [e for _, e in scored[:limit]]


# ── 블렌더 없이 검색 품질을 확인하는 자체 시험 ────────────────────────
if __name__ == "__main__":
    import json, os, sys

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "data", "guide_ko.json"), encoding="utf-8") as f:
        entries = json.load(f)["entries"]

    # 왼쪽이 검색어, 오른쪽이 첫 번째로 나와야 하는 항목의 id 이다.
    cases = [
        ("면 나누기", "subdivide"),
        ("면나누기", "subdivide"),
        ("세분화", "subdivide"),
        ("뽑기", "extrude"),
        ("돌출", "extrude"),
        ("루프컷", "loopcut"),
        ("가로줄", "loopcut"),
        ("둥글게", "bevel"),
        ("모따기", "bevel"),
        ("대칭", "modifier_mirror"),
        ("반만", "modifier_mirror"),
        ("게임엔진", "export_gltf"),
        ("내보내기", "export_gltf"),
        ("유니티", "export_gltf"),
        ("뒤집힘", "recalc_normals"),
        ("까맣게", "recalc_normals"),
        ("안 골라져", "toggle_xray"),
        ("날아갔어", "recover_last_session"),
        ("어디갔지", "view_selected"),
        ("bevel", "bevel"),
        ("subdiv", "subdivide"),
        ("ㅁㄴㄴ", "subdivide"),
        ("실수", "undo"),
        ("스냅", "snap_toggle"),
        ("F9", "adjust_last_operation"),
        ("폴리곤 수", "statistics_overlay"),
    ]

    ok = fail = 0
    for query, expect in cases:
        got = search(entries, query, limit=3)
        got_ids = [g["id"] for g in got]
        if got_ids and got_ids[0] == expect:
            ok += 1
            mark = "통과"
        elif expect in got_ids:
            ok += 1
            mark = f"통과(순위 {got_ids.index(expect) + 1})"
        else:
            fail += 1
            mark = "실패"
        if mark != "통과":
            print(f"  [{mark}] '{query}' -> {got_ids or '결과 없음'} (기대: {expect})")

    print(f"\n검색 시험: {ok}건 통과 / {fail}건 실패 (전체 {len(cases)}건)")
    sys.exit(1 if fail else 0)
