# 팝업 안의 단추가 첫 클릭에 눌리는지 확인한다.
#
# 무엇을 재는가: 검색창에 커서가 들어가 있으면(설정의 '팝업을 열면 바로 칠 수
# 있게 한다') 팝업 안의 첫 클릭이 글자 입력 상태를 빠져나오는 데 쓰여서,
# 단추까지 닿지 않는다. 사용자는 눌렀는데 아무 일도 안 일어난 것처럼 느낀다.
#
# 어떻게 재는가: 팝업을 '검색창 + 큰 단추 하나'로 바꿔치기해서 어디를 눌러도
# 그 단추가 눌리게 만든 뒤, 이벤트를 흉내 내어 실제로 클릭한다. 단추가 불렸는지는
# 오퍼레이터를 가로채어 센다. 실제로 부르지는 않으므로 장면은 그대로 남는다.
#
# 왜 이렇게까지 하는가: 이 증상은 화면으로 확인할 수 없다. screen.screenshot 은
# 팝업과 모달 오버레이를 담지 못하기 때문이다. 값으로 재는 수밖에 없다.
#
# 한 조건씩 따로 띄워야 한다. 한 프로세스에서 세 조건을 이어 돌리면, 앞 조건이
# 남긴 팝업과 변형 상태 때문에 다음 조건에서 팝업이 안 열린다. 실제로 겪었다.
#
# 돌리는 법 (이벤트 흉내를 켜야 한다):
#   BL=/Applications/Blender.app/Contents/MacOS/Blender
#   for c in none plain focus; do
#     GUIDE_CLICK_CASE=$c $BL --factory-startup --enable-event-simulate \
#         --python probe/check_click.py
#   done
import os
import sys
import traceback

import bpy

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

MX, MY = 1000, 1200      # 팝업을 여는 자리
CX, CY = 1242, 979       # 그 팝업 안쪽. 큰 단추가 이 자리를 덮는다.

lines = []
failed = {"count": 0}
st = {"draws": 0, "invoked": 0, "first": True}


def ok(name, detail=""):
    lines.append(f"  [통과] {name}" + (f" — {detail}" if detail else ""))


def bad(name, detail=""):
    failed["count"] += 1
    lines.append(f"  [실패] {name}" + (f" — {detail}" if detail else ""))


def sim(**kw):
    kw.setdefault("x", MX)
    kw.setdefault("y", MY)
    bpy.context.window.event_simulate(**kw)


def enable_addon():
    try:
        bpy.ops.preferences.addon_enable(module="blender_guide")
    except Exception:
        import blender_guide
        blender_guide.register()


# 검사할 조건이다. (이름, 검색창을 두는가, 커서를 넣는가, 첫 클릭에 눌려야 하는가)
#
# '검색창에 커서가 들어가 있으면 첫 클릭이 삼켜진다'는 블렌더의 원래 동작을
# 지켜보는 것이지, 고쳐야 할 흠을 잡는 것이 아니다.
CASES = {
    "none":  ("검색창 없음", False, False, True),
    "plain": ("검색창 있고 커서 없음", True, False, True),
    "focus": ("검색창에 커서가 들어감", True, True, False),
}

CASE = os.environ.get("GUIDE_CLICK_CASE", "focus")
steps = []


class BLENDERGUIDE_OT_probe_click(bpy.types.Operator):
    """점검 전용 단추이다. 눌린 횟수만 센다."""

    bl_idname = "blender_guide.probe_click"
    bl_label = "점검용"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        st["invoked"] += 1
        return {'FINISHED'}


def patch(has_field, focus_field):
    """팝업을 '검색창 + 큰 단추 하나'로 바꿔치기한다.

    ⚠️ 애드온의 오퍼레이터에 손대면 안 된다. 이미 등록된 오퍼레이터의 메서드를
    파이썬에서 갈아 끼우면 블렌더가 죽는다. 실제로 겪었다. 그래서 점검 전용
    오퍼레이터를 따로 등록해서 쓴다.
    """
    import blender_guide.popup as popup

    # ⚠️ hasattr(bpy.ops.…) 로 등록 여부를 볼 수 없다. bpy.ops 는 이름이 없어도
    #    껍데기를 돌려주므로 언제나 참이다. 그래서 그냥 등록하고, 이미 있으면
    #    나는 오류만 넘긴다.
    try:
        bpy.utils.register_class(BLENDERGUIDE_OT_probe_click)
    except Exception:
        pass

    def draw(self, context):
        st["draws"] += 1
        layout = self.layout
        if has_field:
            row = layout.row()
            if focus_field and st["first"]:
                row.activate_init = True
                st["first"] = False
            row.prop(context.window_manager, "blender_guide_query", text="")
        # 단추를 여러 개 쌓아서 팝업 안 어디를 눌러도 맞게 한다.
        # 클릭 자리를 정확히 맞히는 것은 이 점검의 목적이 아니다.
        col = layout.column(align=True)
        col.scale_y = 3.0
        for _ in range(12):
            col.operator("blender_guide.probe_click", text="점검용 단추")

    popup.BLENDERGUIDE_OT_popup.draw = draw


def begin_case():
    name, has_field, focus_field, expect_hit = CASES[CASE]
    cube = bpy.data.objects.get("Cube")
    if cube is None:
        bad("준비", "장면에 Cube 가 없다")
        return
    bpy.context.view_layer.objects.active = cube
    cube.select_set(True)
    cube.rotation_euler = (0, 0, 0)
    st.update(first=True)
    bpy.context.window_manager.blender_guide_query = "돌리기"
    patch(has_field, focus_field)
    sim(type='MOUSEMOVE', value='NOTHING')


def open_popup():
    st["draws"] = 0
    sim(type='H', value='PRESS', ctrl=True, shift=True)
    sim(type='H', value='RELEASE')


def check_opened():
    name = CASES[CASE][0]
    if st["draws"] == 0:
        bad(f"{name} · 팝업 열기", "팝업이 안 열렸다")
    else:
        ok(f"{name} · 팝업 열기")


def click():
    st["before"] = st["invoked"]
    sim(type='MOUSEMOVE', value='NOTHING', x=CX, y=CY)
    sim(type='LEFTMOUSE', value='PRESS', x=CX, y=CY)
    sim(type='LEFTMOUSE', value='RELEASE', x=CX, y=CY)


def judge():
    name, _, _, expect_hit = CASES[CASE]
    hit = st["invoked"] > st["before"]
    got = "눌림" if hit else "안 눌림"
    want = "눌려야 한다" if expect_hit else "삼켜져야 한다"
    if hit == expect_hit:
        ok(f"{name} · 첫 클릭", f"{got} ({want})")
    else:
        bad(f"{name} · 첫 클릭", f"{got} ({want})")


def cleanup_case():
    # 시작한 변형을 물린다. 남겨 두면 블렌더가 안 닫힌다.
    try:
        sim(type='ESC', value='PRESS', x=CX, y=CY)
        sim(type='ESC', value='RELEASE', x=CX, y=CY)
    except Exception:
        pass


def drive():
    if not steps:
        return finish()
    fn, wait = steps.pop(0)
    try:
        fn()
    except Exception:
        bad("점검 중 예외", traceback.format_exc(limit=2).strip().splitlines()[-1])
    bpy.app.timers.register(drive, first_interval=wait)
    return None


def finish():
    print(f"\n── 팝업 첫 클릭 점검 · 조건 '{CASE}' ──")
    print(f"블렌더 {bpy.app.version_string}\n")
    print("\n".join(lines))
    print("\n메모: 검색창에 커서가 들어가 있으면 첫 클릭이 삼켜지는 것이 블렌더의")
    print("      원래 동작이다. 이 점검은 그 사실이 그대로인지 지켜보는 것이지,")
    print("      고쳐야 할 흠을 잡는 것이 아니다.")
    print("\n── 결과 ──")
    print("점검 통과" if failed["count"] == 0 else f"실패 {failed['count']}건")
    bpy.ops.wm.quit_blender()
    return None


def build():
    # 이벤트 흉내는 창이 다 뜬 뒤에야 쓸 수 있다. 스크립트를 읽는 시점에
    # 확인하면 아직 붙어 있지 않아서 잘못 판단한다.
    if not hasattr(bpy.context.window, "event_simulate"):
        print("\n이 점검은 --enable-event-simulate 를 켜야 돌아갑니다.")
        print("  Blender --factory-startup --enable-event-simulate "
              "--python probe/check_click.py\n")
        bpy.ops.wm.quit_blender()
        return None

    if CASE not in CASES:
        print(f"\n모르는 조건입니다: {CASE}. 쓸 수 있는 값: {', '.join(CASES)}\n")
        bpy.ops.wm.quit_blender()
        return None

    enable_addon()

    steps.extend([(begin_case, 0.35), (open_popup, 0.45), (check_opened, 0.1),
                  (click, 0.4), (judge, 0.1), (cleanup_case, 0.35)])

    bpy.app.timers.register(drive, first_interval=0.3)
    return None


def clear_splash():
    """시작 화면을 치운다. 떠 있으면 팝업이 아예 안 열린다.

    ⚠️ read_homefile 은 예약해 둔 타이머까지 같이 지운다. 그래서 다음 단계는
    반드시 이 함수를 부른 뒤에 등록해야 한다. 미리 등록해 두면 사라진다.
    """
    try:
        bpy.ops.wm.read_homefile(use_empty=False)
    except Exception:
        pass
    bpy.app.timers.register(build, first_interval=1.0)
    return None


bpy.app.timers.register(clear_splash, first_interval=1.5)
