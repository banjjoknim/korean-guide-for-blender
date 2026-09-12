# 에이전트에게 실제로 물어보고 답이 돌아오는지 끝까지 확인한다.
#
# ⚠️ 이 점검은 **바깥 프로그램을 실제로 실행한다.** 사용자 컴퓨터에 깔린
#    에이전트를 부르므로 몇 초가 걸리고, 도구에 따라 비용이 들 수도 있다.
#    그래서 test_headless.py 에 넣지 않고 여기에 따로 둔다.
#    test_headless.py 는 '기본으로 꺼져 있는가' 와 '답을 걸러 내는가' 까지만 본다.
#
# 창이 필요한 까닭: 답을 받아 오는 일을 bpy.app.timers 가 맡는데, 창 없이
# 띄운 블렌더에서는 타이머가 돌 기회가 없다.
#
# 돌리는 법:
#   /Applications/Blender.app/Contents/MacOS/Blender --python probe/check_agent.py
import os
import sys
import time
import traceback

import bpy

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

# 규칙 검색으로는 절대 못 찾을 말을 일부러 고른다. 항목의 이름이나 별칭에
# 들어 있는 낱말을 하나도 쓰지 않았다.
QUESTION = "물건이 자꾸 두 개로 늘어나는데 그거 만드는 기능"

lines = []
failed = {"count": 0}
started = {"at": 0.0}


def ok(name, detail=""):
    lines.append(f"  [통과] {name}" + (f" — {detail}" if detail else ""))


def bad(name, detail=""):
    failed["count"] += 1
    lines.append(f"  [실패] {name}" + (f" — {detail}" if detail else ""))


def check(name, condition, detail=""):
    (ok if condition else bad)(name, detail)


def start():
    try:
        bpy.ops.preferences.addon_enable(module="blender_guide")
    except Exception:
        import blender_guide
        blender_guide.register()

    import blender_guide.agent as agent
    import blender_guide.guide_data as guide_data
    import blender_guide.nl as nl
    import blender_guide.prefs as prefs

    p = prefs.get_prefs(bpy.context)
    tool = agent.available(p)
    check("쓸 도구를 찾는다", bool(tool), tool or "없음")
    if not tool:
        lines.append("  (claude 명령줄 도구가 없으면 설정에 명령을 적어야 한다)")
        return finish()

    # 점검하는 동안만 켠다. 사용자 설정은 저장하지 않으므로 남지 않는다.
    p.use_agent = True
    p.agent_timeout = 60.0

    guessed, _ = nl.search(guide_data.load_entries(), QUESTION)
    lines.append(f"  (규칙만으로는 {[e.get('id') for e in guessed[:3]]} 를 내놓는다)")

    problem = agent.ask(bpy.context, QUESTION)
    check("물어보기 시작", not problem, problem or "시작함")
    check("바로 돌아온다 (블렌더가 안 멈춘다)",
          agent.get_state()["status"] == "asking",
          agent.get_state()["status"])

    started["at"] = time.time()
    bpy.app.timers.register(wait, first_interval=0.5)


def wait():
    import blender_guide.agent as agent

    state = agent.get_state()
    if state["status"] == "asking":
        if time.time() - started["at"] > 70:
            bad("답을 받는다", "70초를 넘겼다")
            return finish()
        return 0.5

    if state["status"] == "failed":
        bad("답을 받는다", state["error"])
        return finish()

    found = agent.found_entries()
    check("답을 받는다", bool(found),
          f"{state['took']}초 · {[e.get('id') for e in found]}")
    check("우리가 아는 항목만 돌려준다", all(e.get("ko") for e in found),
          " · ".join(e.get("ko", "") for e in found))
    return finish()


def finish():
    print("\n── 에이전트 점검 ──")
    print(f"블렌더 {bpy.app.version_string}")
    print(f"물어본 말: {QUESTION}\n")
    print("\n".join(lines))
    print("\n── 결과 ──")
    print("점검 통과" if failed["count"] == 0 else f"실패 {failed['count']}건")
    bpy.ops.wm.quit_blender()
    return None


def clear_splash():
    # ⚠️ read_homefile 은 예약해 둔 타이머까지 지운다. 다음 단계는 부른 뒤에 건다.
    try:
        bpy.ops.wm.read_homefile(use_empty=False)
    except Exception:
        pass
    bpy.app.timers.register(start, first_interval=1.0)
    return None


bpy.app.timers.register(clear_splash, first_interval=1.5)
