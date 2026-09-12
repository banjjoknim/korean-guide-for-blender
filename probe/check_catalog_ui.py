# 검색 결과 목록이 실제 창에서 도는지 본다.
#
#     /Applications/Blender.app/Contents/MacOS/Blender --factory-startup \
#         --python probe/check_catalog_ui.py
#
# ⚠️ 창이 있어야 한다. 창 없이 띄우면 팝업이 열리지 않는다.
# ⚠️ 시작 화면이 떠 있으면 팝업이 안 열리므로 먼저 치운다.
import bpy

lines = []
fail = {"n": 0}
drew = {"popup": 0}


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


def rows():
    return list(bpy.context.window_manager.blender_guide_results)


def ask(query):
    """검색어를 넣고 팝업을 연다. 목록은 검색어가 바뀔 때 채워진다."""
    bpy.context.window_manager.blender_guide_query = query
    with bpy.context.temp_override(**view3d()):
        bpy.ops.blender_guide.popup('INVOKE_DEFAULT')


def start():
    bpy.ops.preferences.addon_enable(module="blender_guide")
    import blender_guide.popup as popup

    draw = popup.BLENDERGUIDE_OT_popup.draw

    def watch(self, context):
        drew["popup"] += 1
        return draw(self, context)

    popup.BLENDERGUIDE_OT_popup.draw = watch

    ask("데이터 전송")
    bpy.app.timers.register(step_catalog, first_interval=1.0)
    return None


def step_catalog():
    check("팝업이 그려진다", drew["popup"] > 0, f"{drew['popup']}번")
    got = rows()
    check("카탈로그가 목록에 담긴다",
          any(r.kind == "catalog" for r in got),
          " · ".join(f"{r.ko}({r.kind})" for r in got[:3]))
    ask("그림자 끄기")
    bpy.app.timers.register(step_setting, first_interval=1.0)
    return None


def step_setting():
    got = rows()
    # '그림자 끄기' 는 정리된 항목의 설명문에 스쳐 걸린다. 그 약한 답에
    # 막히지 않고 설정값까지 내려와야 한다.
    check("약하게 걸렸을 때 설정값이 함께 담긴다",
          any(r.kind == "catalog" for r in got),
          " · ".join(f"{r.ko}({r.right})" for r in got[:3]))
    check("설정값에 어느 묶음인지 붙는다",
          any(r.right.startswith("설정값 · ") for r in got),
          " · ".join(r.right for r in got[:3]))
    ask("스네이크 훅")
    bpy.app.timers.register(step_translit, first_interval=1.0)
    return None


def step_translit():
    got = rows()
    check("음차로 친 것이 담긴다", any(r.en == "Snake Hook" for r in got),
          " · ".join(r.ko for r in got[:3]))
    check("사용 방법이 한 줄로 붙는다", any(r.how for r in got),
          " · ".join(f"{r.ko}: {r.how}" for r in got[:2]))
    ask("면 나누기")
    bpy.app.timers.register(step_clean, first_interval=1.0)
    return None


def step_clean():
    got = rows()
    check("정리된 항목을 찾으면 카탈로그가 안 끼어든다",
          all(r.kind == "entry" for r in got),
          " · ".join(f"{r.ko}({r.kind})" for r in got[:3]))
    check("단축키가 오른쪽에 붙는다", any(r.right for r in got),
          " · ".join(f"{r.ko} {r.right}" for r in got[:3]))
    ask("점")
    bpy.app.timers.register(step_long, first_interval=1.0)
    return None


def step_long():
    import blender_guide.results as results
    got = rows()
    # 목록이 길어도 보이는 줄은 정해진 만큼이다. 그래야 화면을 안 덮는다.
    check("결과가 많아도 목록에 담긴다", len(got) > 1, f"{len(got)}개")
    check("한 번에 보이는 줄은 정해져 있다", results.MAX_ROWS <= 8,
          f"{results.MAX_ROWS}줄까지 보이고 나머지는 스크롤")
    ask("")
    bpy.app.timers.register(step_empty, first_interval=1.0)
    return None


def step_empty():
    check("검색어를 지우면 목록도 빈다", not rows(), f"{len(rows())}개")
    print("\n── 검색 결과 목록 점검 ──")
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
