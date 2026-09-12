# 카탈로그와 설정값이 실제 창에서 그려지는지 본다.
#
#     /Applications/Blender.app/Contents/MacOS/Blender --factory-startup \
#         --python probe/check_catalog_ui.py
#
# ⚠️ 창이 있어야 한다. 창 없이 띄우면 팝업이 열리지 않는다.
# ⚠️ 시작 화면이 떠 있으면 팝업이 안 열리므로 먼저 치운다.
import bpy

lines = []
fail = {"n": 0}
draws = {"popup": 0, "catalog": 0, "rows": []}


def ok(name, detail=""):
    lines.append(f"  [통과] {name}" + (f" — {detail}" if detail else ""))


def bad(name, detail=""):
    fail["n"] += 1
    lines.append(f"  [실패] {name}" + (f" — {detail}" if detail else ""))


def check(name, cond, detail=""):
    (ok if cond else bad)(name, detail)


def view3d():
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        return dict(window=win, area=area, region=region)
    return None


def ask(query):
    """팝업에 글을 넣고 연다."""
    draws["catalog"] = 0
    draws["rows"] = []
    bpy.context.window_manager.blender_guide_query = query
    with bpy.context.temp_override(**view3d()):
        bpy.ops.blender_guide.popup('INVOKE_DEFAULT')


def start():
    bpy.ops.preferences.addon_enable(module="blender_guide")
    import blender_guide.popup as popup
    from blender_guide import catalog

    original = popup._draw_catalog

    def spy(layout, context, query, prefs, probes=None):
        drew = original(layout, context, query, prefs, probes=probes)
        if drew:
            draws["catalog"] += 1
            draws["rows"] = catalog.search(query, limit=prefs.max_results)
        return drew

    popup._draw_catalog = spy

    draw = popup.BLENDERGUIDE_OT_popup.draw

    def watch(self, context):
        draws["popup"] += 1
        return draw(self, context)

    popup.BLENDERGUIDE_OT_popup.draw = watch

    ask("데이터 전송")
    bpy.app.timers.register(step_catalog, first_interval=1.0)
    return None


def step_catalog():
    check("카탈로그를 친 팝업이 그려진다", draws["popup"] > 0,
          f"{draws['popup']}번")
    check("'다른 도구' 자리가 그려진다", draws["catalog"] > 0)
    ask("그림자 끄기")
    bpy.app.timers.register(step_setting, first_interval=1.0)
    return None


def step_setting():
    # '그림자 끄기' 는 정리된 항목의 설명문에 스쳐 걸린다. 그 약한 답에
    # 막히지 않고 설정값까지 내려와야 한다.
    check("약하게 걸렸을 때 설정값이 함께 그려진다", draws["catalog"] > 0)
    kinds = [r.get("_kind_ko", "") for r in draws["rows"]]
    check("설정값에 어느 묶음인지 붙는다",
          any(k.startswith("설정값 · ") for k in kinds), " · ".join(kinds[:3]))
    ask("스네이크 훅")
    bpy.app.timers.register(step_translit, first_interval=1.0)
    return None


def step_translit():
    names = [r.get("en") for r in draws["rows"]]
    check("음차로 친 것이 그려진다", "Snake Hook" in names, " · ".join(names[:3]))
    ask("면 나누기")
    bpy.app.timers.register(step_clean, first_interval=1.0)
    return None


def step_clean():
    check("정리된 항목을 찾으면 카탈로그가 안 끼어든다", draws["catalog"] == 0,
          f"{draws['catalog']}번")
    print("\n── 카탈로그·설정값 화면 점검 ──")
    print("\n".join(lines))
    print("점검 통과" if fail["n"] == 0 else f"실패 {fail['n']}건")
    bpy.ops.wm.quit_blender()
    return None


def clear_splash():
    # ⚠️ read_homefile 은 예약해 둔 타이머까지 지운다. 부른 뒤에 등록한다.
    try:
        bpy.ops.wm.read_homefile(use_empty=False)
    except Exception:
        pass
    bpy.app.timers.register(start, first_interval=1.0)
    return None


bpy.app.timers.register(clear_splash, first_interval=1.5)
