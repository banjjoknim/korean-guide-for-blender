# ═══════════════════════════════════════════════════════════════════════
# 에이전트에게 물어보기 — 규칙으로 못 찾았을 때의 마지막 수단이다.
#
# 언제 쓰는가: nl.py 의 규칙 검색이 아무것도 못 찾았을 때만이다. 대부분의
# 검색은 규칙으로 즉시 끝나므로, 여기까지 오는 일은 드물다.
#
# 왜 뒤에서 돌리는가: 물어보고 답을 받는 데 3초쯤 걸린다. 그동안 블렌더가
# 멈춰 있으면 쓸 수 없다. 그래서 딴 갈래로 보내 두고, 타이머가 답을 받아 온다.
#
# 왜 기본으로 꺼 두는가: 바깥 프로그램을 실행하는 일이다. 사용자가 모르는
# 사이에 컴퓨터에서 무언가가 돌아가면 안 된다. 설정에서 직접 켜야 한다.
#
# 어느 도구를 쓰는가: 사용자 컴퓨터에 이미 깔린 것을 쓴다. claude 명령줄
# 도구는 알아서 찾고, 그 밖의 것은 설정에 명령을 적어 두면 그대로 부른다.
# 무엇을 쓰든 프로그램에 넘기는 것은 질문 글자 하나뿐이다.
# ═══════════════════════════════════════════════════════════════════════

from __future__ import annotations

import os
import queue
import re
import shlex
import shutil
import subprocess
import threading
import time

import bpy

# 이름을 알고 있는 도구이다. 명령에서 {prompt} 자리에 질문이 들어간다.
#
# ⚠️ 셸을 거치지 않고 인자로 곧장 넘긴다. 셸을 거치면 질문에 들어간 따옴표나
#    기호가 명령으로 해석될 수 있다. 사용자가 친 글자를 명령에 섞으면 안 된다.
PRESETS = {
    "claude": ["claude", "-p", "{prompt}"],
}

# 도구가 흔히 깔리는 자리이다.
#
# 왜 PATH 만으로는 안 되는가: 독이나 파인더로 켠 블렌더는 셸을 거치지 않아서
# PATH 가 /usr/bin:/bin:/usr/sbin:/sbin 뿐이다. 사용자가 도구를 어디에 깔든
# 거기에는 없다. 터미널에서 켜면 찾아지고 독으로 켜면 못 찾는 일이 실제로
# 벌어져서, 자주 쓰이는 자리를 직접 뒤진다.
EXTRA_DIRS = [
    "~/.local/bin",
    "~/bin",
    "/opt/homebrew/bin",
    "/usr/local/bin",
    "/opt/local/bin",
    "~/.bun/bin",
    "~/.npm-global/bin",
    "~/.volta/bin",
]

# 한 번에 몇 개까지 받아 올 것인가.
MAX_ANSWERS = 3

_state = {
    "status": "idle",     # idle · asking · done · failed
    "question": "",
    "ids": [],
    "error": "",
    "raw": "",
    "took": 0.0,
}
_answers: queue.Queue = queue.Queue()
_worker: threading.Thread | None = None


def get_state() -> dict:
    return dict(_state)


def reset() -> None:
    _state.update(status="idle", question="", ids=[], error="", raw="",
                  took=0.0)


def find_tool(name: str) -> str:
    """도구의 실제 자리를 찾는다. 못 찾으면 빈 글자이다."""
    found = shutil.which(name)
    if found:
        return found
    for folder in EXTRA_DIRS:
        candidate = os.path.join(os.path.expanduser(folder), name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return ""


def command_for(prefs_obj) -> list:
    """무엇으로 물어볼지 정한다. 못 찾으면 빈 목록을 돌려준다."""
    custom = (getattr(prefs_obj, "agent_command", "") or "").strip()
    if custom:
        try:
            parts = shlex.split(custom)
        except ValueError:
            return []
        if "{prompt}" not in custom:
            # 질문을 넣을 자리가 없으면 맨 뒤에 붙인다.
            parts.append("{prompt}")
        # 이름만 적었으면 실제 자리를 찾아 바꿔 준다. 그래야 독으로 켠
        # 블렌더에서도 돈다.
        if parts and not os.path.sep in parts[0]:
            found = find_tool(parts[0])
            if found:
                parts[0] = found
        return parts

    for parts in PRESETS.values():
        found = find_tool(parts[0])
        if found:
            return [found] + list(parts[1:])
    return []


def available(prefs_obj) -> str:
    """쓸 수 있는 도구의 실제 자리를 돌려준다. 없으면 빈 글자이다."""
    parts = command_for(prefs_obj)
    if not parts:
        return ""
    path = parts[0]
    if os.path.sep in path:
        return path if os.path.isfile(path) else ""
    return path if shutil.which(path) else ""


def build_prompt(entries: list, question: str) -> str:
    """에이전트에게 보낼 질문을 만든다.

    항목 목록을 함께 보내는 까닭: 아무 답이나 받으면 쓸 수 없다. 우리가 가진
    것 중에서 고르게 해야 그 답을 그대로 화면에 띄울 수 있다.
    """
    lines = [f"{e.get('id')}={e.get('ko')}" for e in entries if e.get("id")]
    return (
        "아래 목록에서 사용자의 말에 가장 맞는 것을 최대 "
        f"{MAX_ANSWERS}개 고르고, id 만 쉼표로 이어서 답하십시오.\n"
        "설명이나 인사말 없이 id 만 적으십시오.\n"
        "맞는 것이 하나도 없으면 NONE 이라고만 적으십시오.\n\n"
        f"사용자의 말: {question}\n\n"
        "목록:\n" + "\n".join(lines)
    )


def parse_answer(text: str, entries: list) -> list:
    """답에서 우리가 아는 항목 id 만 골라낸다.

    에이전트가 설명을 덧붙이거나 없는 id 를 지어내도 걸러진다.
    """
    known = {e.get("id") for e in entries if e.get("id")}
    found = []
    # 쉼표·줄바꿈·띄어쓰기를 모두 경계로 본다. 항목 id 에는 띄어쓰기가 없으므로
    # 이렇게 해야 '답은 subdivide 입니다' 같은 문장에서도 골라낼 수 있다.
    for chunk in re.split(r"[\s,;]+", text or ""):
        token = chunk.strip().strip(".`'\"()[]")
        if token in known and token not in found:
            found.append(token)
    return found[:MAX_ANSWERS]


def _environment() -> dict:
    """부를 프로그램에게 넘길 환경을 만든다.

    왜 PATH 를 채워 주는가: 도구를 찾아내도 그 도구가 기대는 것들이 또 있다.
    claude 는 node 를 찾아 쓰는데, 독으로 켠 블렌더의 PATH 에는 그것이 없어서
    도구가 코드 1 로 끝났다. 도구를 찾는 것과 도구를 돌리는 것은 다른 문제이다.
    """
    env = dict(os.environ)
    parts = [os.path.expanduser(folder) for folder in EXTRA_DIRS]
    parts = [folder for folder in parts if os.path.isdir(folder)]
    parts.append(env.get("PATH", ""))
    env["PATH"] = os.pathsep.join(p for p in parts if p)
    return env


def _run(parts: list, prompt: str, timeout: float) -> None:
    """딴 갈래에서 도는 부분이다. 여기서는 블렌더를 절대 건드리지 않는다."""
    started = time.time()
    command = [p.replace("{prompt}", prompt) for p in parts]
    try:
        # ⚠️ stdin 을 반드시 막아야 한다. 막지 않으면 부른 프로그램이 블렌더의
        #    입력을 물려받아 무언가 들어오기를 기다린다. claude 는 3초를 기다린
        #    뒤 경고를 내고 진행하는데, 그 사이에 답이 어긋나는 것을 겪었다.
        done = subprocess.run(command, capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, timeout=timeout,
                              env=_environment())
    except FileNotFoundError:
        _answers.put(("failed", f"'{parts[0]}' 을(를) 찾지 못했습니다.", 0.0))
        return
    except subprocess.TimeoutExpired:
        _answers.put(("failed", f"{timeout:.0f}초 안에 답하지 않았습니다.", timeout))
        return
    except Exception as exc:
        _answers.put(("failed", str(exc), time.time() - started))
        return

    took = time.time() - started
    if done.returncode != 0:
        # 까닭을 최대한 남긴다. 표준 오류가 비면 표준 출력이라도 본다.
        detail = ((done.stderr or "").strip() or (done.stdout or "").strip())
        lines = detail.splitlines()
        _answers.put(("failed", lines[-1] if lines else
                      f"오류로 끝났습니다 (코드 {done.returncode})", took))
        return
    _answers.put(("done", done.stdout or "", took))


def _tick():
    """타이머가 부르는 부분이다. 답이 왔는지 보고 화면을 다시 그리게 한다."""
    from . import guide_data

    if _answers.empty():
        return 0.2 if _state["status"] == "asking" else None

    status, payload, took = _answers.get()
    _state["took"] = round(took, 1)
    if status == "done":
        ids = parse_answer(payload, guide_data.load_entries())
        _state["status"] = "done"
        _state["ids"] = ids
        _state["raw"] = (payload or "").strip()[:200]
        # 못 알아들었을 때 무엇을 받았는지 남긴다. 이것이 없으면 왜 비었는지
        # 알 길이 없다. 실제로 빈 답을 받고 한참 헤맸다.
        _state["error"] = "" if ids else (
            f"맞는 항목을 찾지 못했습니다. 받은 답: {_state['raw'] or '(비어 있음)'}")
    else:
        _state["status"] = "failed"
        _state["ids"] = []
        _state["error"] = payload

    _redraw()
    return None


def _redraw() -> None:
    wm = getattr(bpy.context, "window_manager", None)
    if wm is None:
        return
    for window in wm.windows:
        screen = getattr(window, "screen", None)
        if screen is None:
            continue
        for area in screen.areas:
            area.tag_redraw()


def ask(context, question: str) -> str:
    """에이전트에게 물어본다. 바로 돌아온다. 문제가 있으면 까닭을 돌려준다."""
    global _worker

    from . import guide_data, prefs

    question = (question or "").strip()
    if not question:
        return "물어볼 말이 없습니다."
    if _state["status"] == "asking":
        return "이미 물어보는 중입니다."

    p = prefs.get_prefs(context)
    if not getattr(p, "use_agent", False):
        return "설정에서 '못 찾으면 에이전트에게 물어본다' 를 먼저 켜 주세요."

    parts = command_for(p)
    if not parts:
        return ("물어볼 도구를 찾지 못했습니다. 설정에 명령을 직접 적어 주세요. "
                "예: claude -p {prompt}")

    prompt = build_prompt(guide_data.load_entries(), question)
    timeout = float(getattr(p, "agent_timeout", 30.0))

    _state.update(status="asking", question=question, ids=[], error="",
                  raw="", took=0.0)
    _worker = threading.Thread(target=_run, args=(parts, prompt, timeout),
                               daemon=True)
    _worker.start()

    if not bpy.app.timers.is_registered(_tick):
        bpy.app.timers.register(_tick, first_interval=0.2)
    return ""


def found_entries() -> list:
    """에이전트가 찾아 준 항목을 돌려준다."""
    from . import guide_data

    if _state["status"] != "done":
        return []
    found = []
    for entry_id in _state["ids"]:
        entry = guide_data.find_entry(entry_id)
        if entry is not None:
            found.append(entry)
    return found


def stop() -> None:
    """애드온을 끌 때 타이머를 걷는다. 도는 갈래는 알아서 끝난다."""
    if bpy.app.timers.is_registered(_tick):
        try:
            bpy.app.timers.unregister(_tick)
        except Exception:
            pass
    reset()


class BLENDERGUIDE_OT_ask_agent(bpy.types.Operator):
    """규칙으로 못 찾은 말을 에이전트에게 물어본다"""

    bl_idname = "blender_guide.ask_agent"
    bl_label = "에이전트에게 물어보기"
    bl_description = ("컴퓨터에 깔린 에이전트에게 물어봅니다. "
                      "답이 오는 데 몇 초 걸리며, 그동안 블렌더는 멈추지 않습니다")
    bl_options = {'REGISTER'}

    question: bpy.props.StringProperty(name="물어볼 말", default="")

    def execute(self, context):
        problem = ask(context, self.question)
        if problem:
            self.report({'WARNING'}, problem)
            return {'CANCELLED'}
        self.report({'INFO'},
                    f"'{self.question}' 을(를) 물어보는 중입니다. "
                    f"답이 오면 가이드에 나타납니다.")
        return {'FINISHED'}


classes = (
    BLENDERGUIDE_OT_ask_agent,
)
