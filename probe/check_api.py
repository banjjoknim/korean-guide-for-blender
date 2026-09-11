# ═══════════════════════════════════════════════════════════════════════
# 블렌더 API 탐침 — 판이 올라갔을 때 애드온이 기대는 것들이 그대로 있는지 본다.
#
# 쓰는 법:
#   /Applications/Blender.app/Contents/MacOS/Blender --background \
#       --python probe/check_api.py
#
# 왜 필요한가: 이 애드온은 블렌더의 몇 가지 성질에 기대고 있다. 팝업이
# 프로퍼티로는 안 닫히는 것, UILayout.activate_init 이 있는 것, poll() 이
# 상황을 제대로 답하는 것. 판이 올라가서 이것들이 바뀌면 팝업이 조용히
# 이상해지므로, 그때 무엇이 바뀌었는지 빨리 짚으려고 남겨 둔다.
# ═══════════════════════════════════════════════════════════════════════
import bpy, json, sys

out = {"version": bpy.app.version_string}
problems = []

# ① 레거시 bl_info 애드온이 아직 지원되는가
import addon_utils
out["addon_module_count"] = len(list(addon_utils.modules()))

# ② 팝업 API
wm = bpy.types.WindowManager
out["wm_popup_api"] = {n: hasattr(wm, n) for n in
    ("invoke_popup", "invoke_props_dialog", "invoke_search_popup", "popup_menu")}
if not out["wm_popup_api"]["invoke_popup"]:
    problems.append("invoke_popup 이 없다. 팝업을 띄울 수 없다.")

# ③ UILayout 의 함수와 속성 (RNA 라서 hasattr 로는 안 잡히므로 bl_rna 를 본다)
fns = set(bpy.types.UILayout.bl_rna.functions.keys())
props = set(bpy.types.UILayout.bl_rna.properties.keys())
need_fns = {"prop", "operator", "label", "box", "column", "row", "separator"}
need_props = {"activate_init", "alert", "active", "enabled", "alignment", "emboss"}
out["uilayout_missing_functions"] = sorted(need_fns - fns)
out["uilayout_missing_properties"] = sorted(need_props - props)
if out["uilayout_missing_functions"]:
    problems.append(f"UILayout 함수가 없다: {out['uilayout_missing_functions']}")
if "activate_init" not in props:
    problems.append("activate_init 이 없다. 팝업이 떠도 검색창에 커서가 안 들어간다.")
if "alert" not in props:
    problems.append("alert 가 없다. 모드 경고를 빨갛게 표시할 수 없다.")

# ④ poll() 이 상황을 제대로 답하는가
try:
    out["poll_object_mode_op"] = bpy.ops.object.duplicate_move.poll()
    out["poll_edit_mode_op"] = bpy.ops.mesh.subdivide.poll()
    if out["poll_edit_mode_op"] is not False:
        problems.append(
            "오브젝트 모드인데 mesh.subdivide.poll() 이 거짓이 아니다. "
            "상황별 추천이 부정확해질 수 있다.")
except Exception as e:
    problems.append(f"poll() 호출이 실패한다: {e}")

# ⑤ 기능 색인의 재료
count = 0
for m in dir(bpy.ops):
    if m.startswith("_"):
        continue
    count += sum(1 for n in dir(getattr(bpy.ops, m)) if not n.startswith("_"))
out["registered_operator_count"] = count

# ⑥ 아이콘
try:
    icons = {e.identifier for e in
             bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items}
    used = {"VIEWZOOM", "QUESTION", "INFO", "SOLO_ON", "SOLO_OFF", "ERROR", "PLAY",
            "KEYINGSET", "BOOKMARKS", "FILE_REFRESH", "X", "EVENT_TAB", "BLANK1",
            "DISCLOSURE_TRI_RIGHT", "DISCLOSURE_TRI_DOWN"}
    out["missing_icons"] = sorted(used - icons)
    if out["missing_icons"]:
        problems.append(f"쓰고 있는 아이콘이 없다: {out['missing_icons']} "
                        "(안전장치가 있어 터지지는 않고 아이콘만 빠진다)")
except Exception as e:
    problems.append(f"아이콘 목록을 못 읽는다: {e}")

print(json.dumps(out, ensure_ascii=False, indent=1))
print()
if problems:
    print("살펴볼 것:")
    for p in problems:
        print(f"  · {p}")
    sys.exit(1)
print("애드온이 기대는 것들이 모두 그대로 있습니다.")
sys.exit(0)
