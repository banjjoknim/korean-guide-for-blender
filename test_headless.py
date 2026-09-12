# ═══════════════════════════════════════════════════════════════════════
# 헤드리스 점검 — 블렌더 창을 띄우지 않고 애드온이 제대로 붙는지 본다.
#
# 쓰는 법:
#   GODOT 과 무관하다. 아래처럼 부른다.
#   /Applications/Blender.app/Contents/MacOS/Blender --background \
#       --python tools/blender_guide/test_headless.py
#
# 종료 코드 0 이면 깨끗하고, 1 이면 어딘가 깨졌다.
#
# 무엇을 잡아 주는가: 등록이 실패하는 오류, 없는 속성을 쓴 오류, 검색이
# 아무것도 못 찾는 상태. 화면이 예쁜지는 이것으로 알 수 없다.
# ═══════════════════════════════════════════════════════════════════════

import os
import sys
import traceback

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

failures = []
notes = []


def check(label, fn):
    """점검 하나를 돌리고 결과를 적어 둔다."""
    try:
        result = fn()
    except Exception:
        failures.append(f"{label}\n{traceback.format_exc()}")
        print(f"  [실패] {label}")
        return None
    if result is False:
        failures.append(label)
        print(f"  [실패] {label}")
    else:
        print(f"  [통과] {label}" + (f" — {result}" if isinstance(result, str) else ""))
    return result


print("\n── 블렌더 가이드 애드온 점검 ──")
print(f"블렌더 {bpy.app.version_string}\n")

# 애드온이 이미 설치되어 켜져 있으면, 블렌더가 시작하면서 벌써 등록해 두었다.
# 그 상태에서 또 등록하면 '이미 등록됨' 오류가 나므로, 먼저 끄고 점검한 뒤
# 원래대로 되돌린다. 사용자 설정을 저장하지 않으므로 실제 설정은 그대로 남는다.
INSTALLED = "blender_guide" in bpy.context.preferences.addons
print(f"설치 상태: {'켜져 있음' if INSTALLED else '설치 안 됨(경로만 잡고 점검한다)'}\n")

if INSTALLED:
    try:
        bpy.ops.preferences.addon_disable(module="blender_guide")
    except Exception:
        traceback.print_exc()

import blender_guide

check("모듈을 읽어 들인다", lambda: f"{len(blender_guide.guide_data.load_entries())}개 항목")


def check_no_load_errors():
    """항목 파일을 하나라도 못 읽었으면 그 사유를 남긴다."""
    errors = blender_guide.guide_data.get_load_errors()
    if not errors:
        counts = blender_guide.guide_data.get_source_counts()
        return " · ".join(f"{label} {n}개" for label, n in counts.items())
    for label, reason in errors:
        notes.append(f"{label} 을(를) 읽지 못했습니다 — {reason}")
    return False


check("항목 파일을 모두 읽었다", check_no_load_errors)

check("애드온을 등록한다", lambda: blender_guide.register() or "완료")

wm = bpy.context.window_manager
check("검색어 속성이 붙었다", lambda: hasattr(wm, "blender_guide_query"))
check("분류 속성이 붙었다", lambda: hasattr(wm, "blender_guide_tag"))
check("항목 상태 묶음이 붙었다", lambda: hasattr(wm, "blender_guide_states"))
check("팝업 기능이 등록됐다", lambda: hasattr(bpy.ops.blender_guide, "popup"))
check("항목 다시 읽기 기능이 등록됐다",
      lambda: hasattr(bpy.ops.blender_guide, "reload_data"))

check("항목마다 상태가 하나씩 생긴다",
      lambda: (blender_guide.popup.sync_states(bpy.context),
               f"{len(wm.blender_guide_states)}개")[1])

check("항목 수와 상태 수가 같다",
      lambda: len(wm.blender_guide_states) == len(blender_guide.guide_data.load_entries()))

# ── 지금 쓸 수 있는지 판단이 실제로 갈리는지 본다 ──
def check_availability():
    avail = blender_guide.guide_data.get_availability(bpy.context)
    usable = sum(1 for v in avail.values() if v)
    blocked = len(avail) - usable
    if blocked == 0:
        # 오브젝트 모드인데 에디트 모드 전용 기능까지 전부 쓸 수 있다고 나오면
        # 판단이 작동하지 않는 것이다.
        notes.append("모든 항목이 '쓸 수 있음'으로 나왔다. 상황 판단이 안 되고 있을 수 있다.")
        return False
    return f"쓸 수 있음 {usable}개 / 못 씀 {blocked}개 (현재 {bpy.context.mode})"

check("현재 모드에 따라 쓸 수 있는 기능이 갈린다", check_availability)

# ── 검색 ──
def check_search():
    entries = blender_guide.guide_data.load_entries()
    avail = blender_guide.guide_data.get_availability(bpy.context)
    cases = ["면 나누기", "대칭", "뒤집힘", "ㅁㄴㄴ", "bevel"]
    lines = []
    for q in cases:
        got = blender_guide.search.search(entries, q, avail, limit=3)
        if not got:
            return False
        lines.append(f"'{q}' -> {got[0]['ko']}")
    return " · ".join(lines)

check("검색이 결과를 낸다", check_search)

# ── 단축키 조회 ──
def check_shortcuts():
    smap = blender_guide.guide_data.build_shortcut_map()
    entries = blender_guide.guide_data.load_entries()
    auto = sum(1 for e in entries if blender_guide.guide_data.get_shortcut(e)[1])
    manual = sum(1 for e in entries
                 if blender_guide.guide_data.get_shortcut(e)[0]
                 and not blender_guide.guide_data.get_shortcut(e)[1])
    if not smap:
        notes.append(
            "블렌더에서 단축키를 하나도 못 읽었다. 창 없이 띄운 탓일 수 있으므로, "
            "실제 블렌더 창에서 다시 확인해야 한다. 지금은 손으로 적어 둔 값이 쓰인다.")
    return f"블렌더에서 읽음 {auto}개 · 손으로 적은 값 {manual}개 (키맵 항목 {len(smap)}개)"

check("단축키를 조회한다", check_shortcuts)

# ── 보조 색인 ──
def check_op_index():
    idx = blender_guide.guide_data.build_op_index()
    hits = blender_guide.guide_data.search_op_index("bevel", limit=3)
    if not idx:
        return False
    return f"색인 {len(idx)}개 · 'bevel' 검색 {len(hits)}건"

check("블렌더 전체 색인을 만든다", check_op_index)

# ── 항목 데이터 자체의 흠 ──
def check_entry_quality():
    entries = blender_guide.guide_data.load_entries()
    problems = []
    seen_ids = set()
    for e in entries:
        eid = e.get("id", "")
        if not eid:
            problems.append("id 가 없는 항목이 있다")
        if eid in seen_ids:
            problems.append(f"id 가 겹친다: {eid}")
        seen_ids.add(eid)
        if not e.get("ko"):
            problems.append(f"{eid}: 한국어 이름이 없다")
        if not e.get("aliases"):
            problems.append(f"{eid}: 별칭이 없다 (검색이 잘 안 걸린다)")
        op = e.get("op")
        if op and not blender_guide.guide_data.op_exists(op):
            problems.append(f"{eid}: 이 블렌더에 없는 기능이다 — {op}")
    if problems:
        for p in problems:
            notes.append(p)
        return False
    return f"{len(entries)}개 항목 모두 이상 없음"

check("항목 데이터에 흠이 없다", check_entry_quality)

# ── 단축키 ───────────────────────────────────────────────────────────

def check_default_shortcut():
    """기본 단축키가 운영체제에 맞게 정해지는지 본다.

    맥에서 Control 조합을 쓰면 한글 입력 상태에서 글쇠가 자모로 바뀌어
    단축키가 아예 안 듣는다. Command 조합은 운영체제가 먼저 가로채므로
    입력기를 거치지 않는다. 그래서 맥에서만 Command 를 쓴다.
    """
    km = blender_guide.keymaps
    if sys.platform == "darwin":
        if not km.DEFAULT_OSKEY or km.DEFAULT_CTRL:
            raise AssertionError(
                f"맥인데 Command 가 아니다 (oskey={km.DEFAULT_OSKEY}, "
                f"ctrl={km.DEFAULT_CTRL})")
    else:
        if km.DEFAULT_OSKEY or not km.DEFAULT_CTRL:
            raise AssertionError(
                f"맥이 아닌데 Control 이 아니다 (oskey={km.DEFAULT_OSKEY}, "
                f"ctrl={km.DEFAULT_CTRL})")
    return f"{sys.platform} → {km.default_shortcut_text()}"


check("기본 단축키가 운영체제에 맞는다", check_default_shortcut)


# ── 검색 기록 ────────────────────────────────────────────────────────

def check_history_record():
    history = blender_guide.history
    history.clear(bpy.context)
    for entry_id in ("bevel", "subdivide", "bevel"):
        history.record(bpy.context, entry_id)
    got = history.recent(bpy.context)
    if got[0] != "bevel":
        raise AssertionError(f"가장 최근에 고른 것이 앞에 와야 하는데 {got} 이다")
    if len(got) != 2:
        raise AssertionError(f"같은 것을 두 번 골랐으면 한 칸이어야 하는데 {got} 이다")
    times = history.pick_count(bpy.context, "bevel")
    if times != 2:
        raise AssertionError(f"두 번 골랐는데 {times}번으로 세어졌다")
    return f"기록 {got} · bevel {times}번"


check("골라 본 것을 기억한다", check_history_record)


def check_history_limit():
    """개수 제한을 넘으면 오래된 것부터 잊는지 본다."""
    history = blender_guide.history
    prefs_obj = blender_guide.prefs.get_prefs(bpy.context)
    history.clear(bpy.context)
    prefs_obj.max_history = 3
    for entry_id in ("a", "b", "c", "d", "e"):
        history.record(bpy.context, entry_id)
    got = history.recent(bpy.context)
    prefs_obj.max_history = 10
    if got != ["e", "d", "c"]:
        raise AssertionError(f"최근 3개만 남아야 하는데 {got} 이다")
    return f"3개로 묶으니 {got}"


check("기억할 개수를 넘으면 오래된 것부터 잊는다", check_history_limit)


def check_history_boost():
    """기록이 검색 순위를 바꾸되, 안 걸린 항목까지 끌어올리지는 않는지 본다.

    이것이 핵심이다. 기록만으로 상관없는 항목이 결과에 끼어들면 검색이
    못 미더워진다.
    """
    history = blender_guide.history
    entries = blender_guide.guide_data.load_entries()
    history.clear(bpy.context)

    plain = blender_guide.search.search(entries, "면", limit=5)
    if len(plain) < 2:
        return "견줄 결과가 모자라 건너뛴다"

    # 두 번째 것을 여러 번 고른 것으로 만들어 둔다.
    second = plain[1].get("id")
    for _ in range(5):
        history.record(bpy.context, second)

    boosted = blender_guide.search.search(
        entries, "면", limit=5, boosts=history.boosts(bpy.context))
    if boosted[0].get("id") != second:
        raise AssertionError(
            f"여러 번 고른 {second} 가 위로 와야 하는데 "
            f"{[e.get('id') for e in boosted]} 이다")

    # 검색어에 안 걸리는 것을 아무리 골라도 결과에 끼면 안 된다.
    history.clear(bpy.context)
    stranger = next(e.get("id") for e in entries
                    if e not in plain and e.get("id") != second)
    for _ in range(20):
        history.record(bpy.context, stranger)
    guarded = blender_guide.search.search(
        entries, "면", limit=5, boosts=history.boosts(bpy.context))
    if stranger in [e.get("id") for e in guarded]:
        raise AssertionError(f"안 걸리는 {stranger} 가 기록 때문에 끼어들었다")

    history.clear(bpy.context)
    return f"{second} 가 1등으로 올라가고, 안 걸리는 것은 끼지 않는다"


check("기록이 순위를 바꾸되 검색을 흐리지 않는다", check_history_boost)

check("기록 지우기 기능이 등록됐다",
      lambda: "BLENDERGUIDE_OT_clear_history" in
              [c.__name__ for c in bpy.types.Operator.__subclasses__()])

check("애드온을 끈다", lambda: blender_guide.unregister() or "완료")
check("끄고 나면 속성이 사라진다",
      lambda: not hasattr(bpy.types.WindowManager, "blender_guide_query"))

# 점검하려고 껐던 것을 원래대로 되돌린다. 이것을 안 하면 블렌더가 끝날 때
# 한 번 더 끄려다 오류를 낸다.
if INSTALLED:
    check("점검 전 상태로 되돌린다",
          lambda: bpy.ops.preferences.addon_enable(module="blender_guide") and "완료")

# ── 결과 ──
print("\n── 결과 ──")
if notes:
    print("살펴볼 것:")
    for n in notes:
        print(f"  · {n}")
if failures:
    print(f"\n실패 {len(failures)}건:")
    for f in failures:
        print(f"\n{f}")
    print("\n점검 실패")
    sys.exit(1)

print("점검 통과")
sys.exit(0)
