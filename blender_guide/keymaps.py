# ═══════════════════════════════════════════════════════════════════════
# 단축키 — 팝업을 여는 키를 블렌더에 등록하고, 겹치는 키가 있는지 살핀다.
#
# 핵심 패턴: 애드온 단축키는 'addon' 이라는 별도 설정에 등록한다.
# 왜: 사용자의 원래 설정을 건드리지 않기 때문에, 애드온을 끄면 단축키도
#     깨끗이 사라진다. 사용자 설정에 직접 쓰면 애드온을 지운 뒤에도 찌꺼기가 남는다.
# ═══════════════════════════════════════════════════════════════════════

from __future__ import annotations

import sys

import bpy

# 맥에서는 Command 를, 그 밖에서는 Control 을 쓴다.
#
# 왜 갈라 두는가: 맥에서 한글 입력 상태일 때 Control 조합은 글자 입력 단계를
# 먼저 거치면서 글쇠가 한글 자모로 바뀌어 버린다. 그래서 단축키가 아예 안 듣는다.
# Command 조합은 운영체제가 명령으로 먼저 가로채므로 입력기를 거치지 않는다.
# 맥에서 Command+S 가 어떤 입력기에서도 저장으로 도는 것과 같은 까닭이다.
#
# 덤으로 맥 사용자에게는 Command 쪽이 손에 익은 자리이기도 하다.
IS_MAC = sys.platform == "darwin"

# 팝업을 여는 기본 단축키이다. 설정 화면에서 바꿀 수 있다.
#
# 왜 H 인가: 블렌더 5.1 의 키맵 7,726개를 훑어서 비어 있는 조합을 찾았다.
# 처음에 고른 Ctrl+Shift+G 는 이미 collection.objects_add_active 가 쓰고 있었다.
# H 는 Help 를 떠올리게 해서 기억하기도 낫다.
# Cmd+Shift+H 와 Ctrl+Shift+H 모두 쓰는 기능이 없는 것을 확인했다.
# 다시 확인하려면: probe/find_free_key.py
DEFAULT_KEY = 'H'
DEFAULT_SHIFT = True
DEFAULT_ALT = False
DEFAULT_CTRL = not IS_MAC
DEFAULT_OSKEY = IS_MAC

# 어느 키맵에 등록할지 정한다. 'Window' 는 블렌더 어디에서나 듣는다.
# 왜 'Window' 인가: 초보자는 3D 화면이 아닌 곳에서 막히는 일도 잦다.
# 어디서 눌러도 떠야 '일단 이 키를 누르면 된다'가 하나의 규칙으로 남는다.
KEYMAP_NAME = 'Window'
KEYMAP_SPACE = 'EMPTY'

# 등록한 (키맵, 키항목) 짝을 기억해 둔다. 애드온을 끌 때 정확히 이것만 지운다.
addon_keymaps: list = []


def register_keymaps() -> None:
    """팝업 단축키를 등록한다."""
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc is None:
        # 블렌더를 창 없이 띄운 경우에는 애드온 키 설정이 없다. 조용히 넘어간다.
        return

    km = kc.keymaps.new(name=KEYMAP_NAME, space_type=KEYMAP_SPACE)
    kmi = km.keymap_items.new(
        "blender_guide.popup", DEFAULT_KEY, 'PRESS',
        ctrl=DEFAULT_CTRL, shift=DEFAULT_SHIFT, alt=DEFAULT_ALT,
        oskey=DEFAULT_OSKEY,
    )
    addon_keymaps.append((km, kmi))


def default_shortcut_text() -> str:
    """기본 단축키를 사람이 읽는 글자로 만든다. 설명에 쓴다."""
    parts = []
    if DEFAULT_OSKEY:
        parts.append("Cmd")
    if DEFAULT_CTRL:
        parts.append("Ctrl")
    if DEFAULT_SHIFT:
        parts.append("Shift")
    if DEFAULT_ALT:
        parts.append("Alt")
    parts.append(DEFAULT_KEY)
    return "+".join(parts)


def unregister_keymaps() -> None:
    """등록했던 단축키만 골라 지운다."""
    for km, kmi in addon_keymaps:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            # 블렌더가 먼저 정리한 경우이다. 지우려던 것이 이미 없으니 넘어간다.
            pass
    addon_keymaps.clear()


def iter_registered_keymap_names():
    """단축키를 등록한 키맵 이름을 하나씩 돌려준다. 설정 화면에서 쓴다."""
    for km, _ in addon_keymaps:
        yield km.name


def find_conflicts(context) -> list:
    """이 단축키를 이미 쓰고 있는 다른 기능이 있는지 찾는다.

    돌려주는 값은 (키맵 이름, 기능 이름, 단축키 글자) 목록이다.
    겹치면 두 기능이 함께 실행되거나 한쪽이 먹히지 않아 혼란스럽기 때문에,
    설정 화면에 알려 준다.
    """
    conflicts = []
    if not addon_keymaps:
        return conflicts

    # 우리가 실제로 쓰고 있는 키 조합을 모은다. 사용자가 바꿨을 수도 있으므로
    # 기본값이 아니라 지금 등록된 값을 본다.
    ours = set()
    for _, kmi in addon_keymaps:
        try:
            ours.add((kmi.type, kmi.ctrl, kmi.shift, kmi.alt, kmi.oskey))
        except Exception:
            continue
    if not ours:
        return conflicts

    kc = context.window_manager.keyconfigs.user
    if kc is None:
        return conflicts

    # 어디서나 듣는 키맵만 본다. 특정 편집기 안에서만 도는 키맵까지 따지면
    # 실제로는 겹치지 않는 것까지 경고로 나와서 오히려 헷갈린다.
    watched = {'Window', 'Screen', '3D View', 'Object Mode', 'Mesh'}

    for km in kc.keymaps:
        if km.name not in watched:
            continue
        for kmi in km.keymap_items:
            if kmi.idname == "blender_guide.popup" or not kmi.active:
                continue
            try:
                sig = (kmi.type, kmi.ctrl, kmi.shift, kmi.alt, kmi.oskey)
            except Exception:
                continue
            if sig in ours:
                conflicts.append((km.name, kmi.idname, kmi.to_string()))

    return conflicts
