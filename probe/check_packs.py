# ═══════════════════════════════════════════════════════════════════════
# 팩 점검 — 기본 항목에 추가 폴더의 항목이 제대로 합쳐지는지 본다.
#
# 쓰는 법:
#   GUIDE_PACK_DIR=<팩 폴더> /Applications/Blender.app/Contents/MacOS/Blender \
#       --background --python probe/check_packs.py
#
# ⚠️ 설정(Preferences)에 손을 대므로, 설치해서 켜 둔 상태에서만 돌아간다.
#    바꾼 값은 끝나면 되돌리고 저장하지 않으므로 실제 설정은 그대로 남는다.
# ═══════════════════════════════════════════════════════════════════════
import bpy, sys, os, json

PACK_DIR = os.environ.get("GUIDE_PACK_DIR", "")
MODULE = "blender_guide"
ok = True

# 설치해서 켜 두지 않았으면 설정에 접근할 수 없다.
# 직접 register() 를 불러서는 안 된다. 그렇게 하면 클래스는 등록되지만
# preferences.addons 목록에는 들어가지 않아서 설정을 읽을 수 없다.
if MODULE not in bpy.context.preferences.addons:
    try:
        bpy.ops.preferences.addon_enable(module=MODULE)
    except Exception as exc:
        print(f"애드온을 켤 수 없습니다: {exc}")
        print("먼저 ./install.sh 를 돌려 연결하세요.")
        sys.exit(1)

import blender_guide

prefs = bpy.context.preferences.addons[MODULE].preferences
original = prefs.pack_dir

base = len(blender_guide.guide_data.load_entries())
print(f"기본 항목: {base}개")

if not PACK_DIR:
    print("GUIDE_PACK_DIR 이 없어서 기본 항목만 확인했습니다.")
    sys.exit(0)

try:
    prefs.pack_dir = PACK_DIR       # 값을 바꾸면 스스로 다시 읽는다
    merged = blender_guide.guide_data.load_entries()
    counts = blender_guide.guide_data.get_source_counts()
    errors = blender_guide.guide_data.get_load_errors()

    print(f"팩 폴더를 잡은 뒤: {len(merged)}개")
    print("출처별:", json.dumps(counts, ensure_ascii=False))

    if errors:
        print("읽기 실패:", errors)
        ok = False
    if len(merged) <= base:
        print("팩 항목이 더해지지 않았습니다.")
        ok = False

    # 팩에서 온 항목이 검색으로 걸리는지 본다.
    avail = blender_guide.guide_data.get_availability(bpy.context)
    for query, expect in (("쿼터뷰", "proj_quarter_view"),
                          ("해상도", "proj_pixel_scale"),
                          ("고닷", "proj_godot_export")):
        hits = blender_guide.search.search(merged, query, avail, limit=3)
        ids = [h["id"] for h in hits]
        mark = "찾음" if expect in ids else "못 찾음"
        print(f"  '{query}' -> {ids[:2]} [{mark}]")
        if expect not in ids:
            ok = False

    sources = sorted({e.get("_source") for e in merged if e.get("_source")})
    print("출처 표시:", sources)

    # 팩 폴더를 지우면 다시 기본만 남는지 본다.
    prefs.pack_dir = ""
    back = len(blender_guide.guide_data.load_entries())
    print(f"팩 폴더를 비운 뒤: {back}개")
    if back != base:
        print("팩을 빼도 개수가 돌아오지 않습니다.")
        ok = False
finally:
    # 점검하려고 바꾼 값을 되돌린다. 저장하지 않으므로 실제 설정은 그대로다.
    prefs.pack_dir = original

print("\n팩 점검", "통과" if ok else "실패")
sys.exit(0 if ok else 1)
