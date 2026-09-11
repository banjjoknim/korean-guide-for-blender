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
