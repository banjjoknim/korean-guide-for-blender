# 안내(포커스) 기능이 실제 창에서 제대로 도는지 확인한다.
#
# 왜 창이 필요한가: 그리기 손잡이 · 강조 오버레이 · 모드 바꾸기는 모두 창이
# 있어야만 돈다. 창 없이 띄운 블렌더에는 gpu 문맥도 키맵도 없어서, 여기서
# 확인하는 것들은 test_headless.py 로는 하나도 확인할 수 없다.
#
# 돌리는 법:
#   /Applications/Blender.app/Contents/MacOS/Blender --factory-startup \
#       --python probe/check_focus.py
#
# GUIDE_FOCUS_SHOT 을 1 로 두면 강조 표시를 찍은 화면도 probe/ 밑에 남긴다.
import os
import sys
import traceback

import bpy

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
PROBE = os.path.join(HERE, "probe")
WANT_SHOT = os.environ.get("GUIDE_FOCUS_SHOT", "") == "1"

lines = []
failed = {"count": 0}


def ok(name, detail=""):
    lines.append(f"  [통과] {name}" + (f" — {detail}" if detail else ""))


def bad(name, detail=""):
    failed["count"] += 1
    lines.append(f"  [실패] {name}" + (f" — {detail}" if detail else ""))


def check(name, condition, detail=""):
    (ok if condition else bad)(name, detail)


def op_registered(name: str) -> bool:
    """blender_guide.<name> 오퍼레이터가 실제로 등록돼 있는지 본다.

    ⚠️ hasattr(bpy.ops.blender_guide, name) 으로는 알 수 없다. bpy.ops 는
    이름이 없어도 껍데기를 돌려주므로 언제나 참이다. bpy.types 로 찾는 것도
    안 된다. 블렌더가 bl_idname 에서 만드는 이름은 BLENDER_GUIDE_OT_focus
    처럼 밑줄이 더 붙어서, 클래스 이름과 다르다.
    poll 을 불러 보면 없는 오퍼레이터일 때만 AttributeError 가 난다.
    """
    try:
        getattr(bpy.ops.blender_guide, name).poll()
        return True
    except AttributeError:
        return False
    except Exception:
        # poll 이 거짓을 돌려주거나 문맥이 안 맞아 오류가 나도 등록은 돼 있다.
        return True


def view3d():
    """3D 화면을 쓰는 것처럼 문맥을 바꿔 줄 값을 찾는다."""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            for region in area.regions:
                if region.type == 'WINDOW':
                    return {"window": window, "area": area, "region": region}
    return None


def enable_addon():
    """설치돼 있으면 정식으로 켜고, 아니면 경로만 잡고 등록한다."""
    try:
        bpy.ops.preferences.addon_enable(module="blender_guide")
        return "설치된 애드온을 켰다"
    except Exception:
        import blender_guide
        blender_guide.register()
        return "설치 없이 등록했다 (설정은 기본값으로 읽힌다)"


def step_register():
    try:
        how = enable_addon()
        ok("애드온 켜기", how)
    except Exception:
        bad("애드온 켜기", traceback.format_exc(limit=3))
        return finish()

    import blender_guide.focus as focus
    import blender_guide.guide_data as guide_data
    import blender_guide.prefs as prefs

    check("안내 오퍼레이터 등록", op_registered("focus"))
    check("모드 바꾸기 오퍼레이터 등록", op_registered("set_mode"))
    check("그리기 손잡이 등록", len(focus._handles) == 3, f"{len(focus._handles)}개")

    p = prefs.get_prefs(bpy.context)
    for attr in ("learner_mode", "focus_open_menu", "focus_highlight",
                 "focus_show_path", "focus_duration"):
        check(f"설정 항목 {attr}", hasattr(p, attr), str(getattr(p, attr, "없음")))

    # 항목마다 안내가 무엇을 할 수 있는지 센다. '자리만 두른다' 가 많으면
    # 안내가 '저쪽 어딘가를 보세요' 로 흐려졌다는 뜻이다.
    import blender_guide.catalog as catalog

    def what_it_does(entry):
        if focus.resolve_menu(entry, bpy.context):
            return "메뉴를 펼친다"
        if focus.resolve_popover(entry):
            return "쪽창을 연다"
        if focus.resolve_properties_tab(entry):
            return "속성 탭을 연다"
        area, _, place = focus.resolve_region(entry, bpy.context)
        if area == 'NONE':
            return "다른 작업 공간이라 알림만"
        return "자리만 두른다"

    entries = guide_data.load_entries()
    for label, items in (("정리된 항목", entries),
                         ("카탈로그", catalog.as_entries())):
        tally = {}
        for entry in items:
            key = what_it_does(entry)
            tally[key] = tally.get(key, 0) + 1
        opens = sum(v for k, v in tally.items() if k.endswith(("펼친다", "연다")))
        ok(f"안내가 실제로 여는 것 · {label}",
           f"{len(items)}개 중 {opens}개를 연다 — "
           + " · ".join(f"{k} {v}" for k, v in sorted(tally.items())))

    # 속성 패널에 있는 것에는 빠짐없이 탭이 정해져야 한다. 탭이 스무 개라
    # '오른쪽 어딘가' 로는 못 찾는다.
    blind = [e["ko"] for e in catalog.as_entries()
             if focus.resolve_region(e, bpy.context)[0] == 'PROPERTIES'
             and not focus.resolve_properties_tab(e)]
    check("속성 패널 항목에는 탭이 정해진다", not blind,
          f"탭을 못 고른 것 {len(blind)}개" if blind else "모두 정해진다")

    # 어떤 항목이든 강조 자리를 예외 없이 정할 수 있어야 한다.
    try:
        places = {}
        for entry in entries:
            _, _, place = focus.resolve_region(entry, bpy.context)
            places[place] = places.get(place, 0) + 1
        ok("강조 자리 결정", str(places))
    except Exception:
        bad("강조 자리 결정", traceback.format_exc(limit=3))

    bpy.app.timers.register(step_mode, first_interval=0.5)


def step_mode():
    import blender_guide.focus as focus
    import blender_guide.guide_data as guide_data

    override = view3d()
    if override is None:
        bad("3D 화면 찾기", "창에 3D 화면이 없다")
        return finish()

    try:
        with bpy.context.temp_override(**override):
            bpy.ops.blender_guide.set_mode(mode='EDIT')
        check("모드 바꾸기 → 에디트", bpy.context.mode == 'EDIT_MESH', bpy.context.mode)

        # 모드에 따라 다른 메뉴를 골라야 한다. 우클릭 메뉴도 알아채야 한다.
        sub = guide_data.find_entry("subdivide")
        if sub:
            got = focus.resolve_menu(sub, bpy.context)
            check("에디트 모드에서 우클릭 메뉴 해석",
                  got == "VIEW3D_MT_edit_mesh_context_menu", got or "빈 값")

        with bpy.context.temp_override(**override):
            bpy.ops.blender_guide.set_mode(mode='OBJECT')
        check("모드 바꾸기 → 오브젝트", bpy.context.mode == 'OBJECT', bpy.context.mode)
    except Exception:
        bad("모드 바꾸기", traceback.format_exc(limit=4))

    # 고른 물체가 없으면 얌전히 거절해야 한다. Tab 이 안 듣는 것과 같은 상황이다.
    try:
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = None
        with bpy.context.temp_override(**override):
            result = bpy.ops.blender_guide.set_mode(mode='EDIT')
        check("고른 물체가 없으면 거절", result == {'CANCELLED'}, str(result))
    except Exception:
        bad("고른 물체가 없으면 거절", traceback.format_exc(limit=3))

    cube = bpy.data.objects.get("Cube")
    if cube:
        bpy.context.view_layer.objects.active = cube
        cube.select_set(True)

    bpy.app.timers.register(step_focus, first_interval=0.3)


def _properties_tab() -> str:
    """지금 속성 패널이 어느 탭을 보고 있는지 돌려준다."""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'PROPERTIES':
                return area.spaces.active.context
    return ""


def step_focus():
    import blender_guide.focus as focus
    import blender_guide.guide_data as guide_data
    import blender_guide.prefs as prefs

    override = view3d()
    p = prefs.get_prefs(bpy.context)
    # 메뉴를 실제로 펼치면 창이 떠서 다음 단계가 막힌다. 여기서는 끄고 부른다.
    if hasattr(p, "focus_open_menu"):
        p.focus_open_menu = False

    try:
        with bpy.context.temp_override(**override):
            result = bpy.ops.blender_guide.focus(entry_id="subdivide")
        check("안내 오퍼레이터", result == {'FINISHED'}, str(result))
        with bpy.context.temp_override(**override):
            result = bpy.ops.blender_guide.focus(entry_id="없는항목")
        check("없는 항목은 거절", result == {'CANCELLED'}, str(result))
    except Exception:
        bad("안내 오퍼레이터", traceback.format_exc(limit=4))

    # 속성 패널에 있는 것은 탭을 실제로 열어 주어야 한다. '오른쪽 속성 패널을
    # 보세요' 라고만 하면 탭이 스무 개라 여전히 헤맨다.
    if hasattr(p, "focus_open_menu"):
        p.focus_open_menu = True
    try:
        for name, entry_id, want in (
                ("모디파이어", "modifier_add", 'MODIFIER'),
                ("머티리얼", "material_new", 'MATERIAL'),
                ("씬 단위", "scene_scale", 'SCENE')):
            with bpy.context.temp_override(**override):
                bpy.ops.blender_guide.focus(entry_id=entry_id)
            now = _properties_tab()
            check(f"속성 탭을 연다 · {name}", now == want, f"{now} (바라던 것 {want})")
    except Exception:
        bad("속성 탭을 연다", traceback.format_exc(limit=4))

    # 카탈로그(모디파이어 종류·설정값)도 안내를 받을 수 있어야 한다.
    try:
        import blender_guide.catalog as catalog
        found = catalog.search("그림자 끄기", limit=1)
        if not found:
            bad("카탈로그 안내", "설정값을 못 찾았다")
        else:
            with bpy.context.temp_override(**override):
                result = bpy.ops.blender_guide.focus(entry_id=found[0]["id"])
            check("카탈로그 항목도 안내한다", result == {'FINISHED'},
                  f"{found[0]['ko']} → {result}")
            check("설정값에도 자리를 짚는다",
                  bool(focus._state.get("place")), focus._state.get("place", ""))
    except Exception:
        bad("카탈로그 안내", traceback.format_exc(limit=4))

    if hasattr(p, "focus_open_menu"):
        p.focus_open_menu = False

    # 강조를 켜 둔 채로 화면을 다시 그리게 해서, 오버레이가 예외 없이 도는지 본다.
    try:
        entry = guide_data.find_entry("bevel") or guide_data.load_entries()[0]
        focus.start(bpy.context, entry, duration=60.0)
        ok("강조 켜기", f"{entry['ko']} · 자리={focus._state['place']}")
    except Exception:
        bad("강조 켜기", traceback.format_exc(limit=3))

    bpy.app.timers.register(step_popup, first_interval=0.5)


def step_popup():
    ok("오버레이 그리기", "강조가 켜진 채로 화면을 다시 그렸다")
    bpy.app.timers.register(lambda: step_draw(True), first_interval=0.2)


_seen_context = {}


def _spy_on_draw():
    """팝업이 그려질 때의 기본 실행 문맥을 엿본다.

    왜 이것을 재는가: 돌리기처럼 마우스를 끄는 기능은 어느 구역에서 불리느냐에
    따라 눈에 보이게 다르게 동작한다. 실행 단추의 문맥을 INVOKE_DEFAULT 로
    되돌려 놓으면 R 을 누른 것과 결과가 달라지는데, 화면만 봐서는 등록이나 그리기가
    멀쩡해 보여서 알아채기 어렵다. 그래서 값으로 재어 둔다.
    """
    import blender_guide.popup as popup

    if _seen_context.get("patched"):
        return
    _seen_context["patched"] = True
    original = popup.BLENDERGUIDE_OT_popup.draw

    def spy(self, context):
        _seen_context.setdefault("default", self.layout.operator_context)
        return original(self, context)

    popup.BLENDERGUIDE_OT_popup.draw = spy


def step_draw(learner):
    """팝업을 실제로 그려 본다. 그리다가 터지면 콘솔에 자취가 남는다."""
    import blender_guide.prefs as prefs

    _spy_on_draw()
    p = prefs.get_prefs(bpy.context)
    if hasattr(p, "learner_mode"):
        p.learner_mode = learner

    label = "켬" if learner else "끔"
    try:
        bpy.context.window_manager.blender_guide_query = "면 나누기" if learner else ""
        with bpy.context.temp_override(**view3d()):
            bpy.ops.blender_guide.popup('INVOKE_DEFAULT')
        ok(f"팝업 그리기 (안내 모드 {label})")
    except Exception:
        bad(f"팝업 그리기 (안내 모드 {label})", traceback.format_exc(limit=4))

    if not learner:
        default = _seen_context.get("default")
        check("팝업의 기본 실행 문맥", default == 'INVOKE_REGION_WIN', str(default))

    if learner:
        bpy.app.timers.register(lambda: step_draw(False), first_interval=1.0)
    elif WANT_SHOT:
        bpy.app.timers.register(step_shot, first_interval=1.0)
    else:
        bpy.app.timers.register(finish, first_interval=1.0)


# 이름을 shot_ 으로 시작하게 둔다. .gitignore 가 그 규칙으로 걸러 내기 때문이다.
_SHOTS = (
    ("shot_focus_header.png", "bevel", 'EDIT'),
    ("shot_focus_props.png", "modifier_mirror", 'OBJECT'),
    ("shot_focus_topbar.png", "recover_last_session", 'OBJECT'),
)


def step_shot(index=0):
    import blender_guide.focus as focus
    import blender_guide.guide_data as guide_data

    if index >= len(_SHOTS):
        return finish()

    name, entry_id, mode = _SHOTS[index]
    override = view3d()
    try:
        with bpy.context.temp_override(**override):
            bpy.ops.blender_guide.set_mode(mode=mode)
        entry = guide_data.find_entry(entry_id)
        focus.start(bpy.context, entry, duration=60.0)
    except Exception:
        bad(f"화면 찍기 준비 {name}", traceback.format_exc(limit=3))
        return bpy.app.timers.register(lambda: step_shot(index + 1), first_interval=0.3)

    def take():
        try:
            with bpy.context.temp_override(**view3d()):
                bpy.ops.screen.screenshot(filepath=os.path.join(PROBE, name))
            ok(f"화면 찍기 {name}")
        except Exception:
            bad(f"화면 찍기 {name}", traceback.format_exc(limit=2))
        bpy.app.timers.register(lambda: step_shot(index + 1), first_interval=0.3)
        return None

    bpy.app.timers.register(take, first_interval=1.0)


def finish():
    print("\n── 안내 기능 점검 ──")
    print(f"블렌더 {bpy.app.version_string}\n")
    print("\n".join(lines))
    print("\n── 결과 ──")
    print("점검 통과" if failed["count"] == 0 else f"실패 {failed['count']}건")
    bpy.ops.wm.quit_blender()
    return None


# 창이 다 뜬 뒤에 시작해야 키맵과 그리기 문맥이 갖춰진다.
bpy.app.timers.register(step_register, first_interval=2.0)
