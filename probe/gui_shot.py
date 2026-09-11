# 팝업 화면을 한 장 찍는다. 무엇을 찍을지는 환경변수 GUIDE_SHOT_MODE 로 정한다.
#   search = 검색 결과 화면 · edit = 에디트 모드의 상황별 추천 화면
import bpy, sys, os, json, subprocess

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
PROBE = os.path.join(HERE, "probe")
MODE = os.environ.get("GUIDE_SHOT_MODE", "search")

import blender_guide

state = {"step": 0}
result = {"mode": MODE}

def step():
    state["step"] += 1
    s = state["step"]

    if s == 1:
        blender_guide.register()
        return 0.5

    if s == 2:
        smap = blender_guide.guide_data.build_shortcut_map()
        result["keymap_item_count"] = len(smap)
        checks = {}
        for eid in ("view_selected", "view_orbit", "view_pan", "shading_wireframe",
                    "bevel", "loopcut", "undo", "apply_transform", "select_loop"):
            e = blender_guide.guide_data.find_entry(eid)
            key, auto = blender_guide.guide_data.get_shortcut(e)
            checks[eid] = {"표시": key, "자동": auto}
        result["shortcut_checks"] = checks
        result["popup_key"] = [k.to_string() for _, k in blender_guide.keymaps.addon_keymaps]
        result["conflicts"] = blender_guide.keymaps.find_conflicts(bpy.context)

        if MODE == "edit":
            try:
                obj = bpy.data.objects.get("Cube")
                if obj:
                    bpy.context.view_layer.objects.active = obj
                    obj.select_set(True)
                for window in bpy.context.window_manager.windows:
                    for area in window.screen.areas:
                        if area.type == 'VIEW_3D':
                            with bpy.context.temp_override(window=window, area=area):
                                bpy.ops.object.mode_set(mode='EDIT')
                            break
            except Exception as ex:
                result["mode_switch"] = f"실패: {ex}"
            bpy.context.window_manager.blender_guide_query = ""
        else:
            bpy.context.window_manager.blender_guide_query = "둥글게"
        return 0.8

    if s == 3:
        result["mode_now"] = bpy.context.mode
        avail = blender_guide.guide_data.get_availability(bpy.context)
        result["usable"] = sorted(e["ko"] for e in blender_guide.guide_data.load_entries()
                                  if avail.get(e["id"]))
        try:
            bpy.ops.blender_guide.popup('INVOKE_DEFAULT')
            result["popup"] = True
        except Exception as ex:
            result["popup"] = f"실패: {ex}"
        return 1.5

    if s == 4:
        path = os.path.join(PROBE, f"shot_{MODE}.png")
        subprocess.run(["screencapture", "-x", path], timeout=20, check=False)
        result["shot"] = os.path.exists(path)
        return 0.5

    with open(os.path.join(PROBE, f"gui_{MODE}.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    bpy.ops.wm.quit_blender()
    return None

bpy.app.timers.register(step, first_interval=3.0)
