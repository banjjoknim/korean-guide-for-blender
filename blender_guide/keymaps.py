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

# 맥에서는 Command 를, 그 밖에서는 Control 을 쓴다. 맥 사용자에게 익은 자리이다.
IS_MAC = sys.platform == "darwin"

# 팝업을 여는 단축키를 둘 등록한다. 하나만으로는 한글 입력 중에 열 수 없다.
#
# ⚠️ 한글 입력 상태에서는 글자 글쇠를 쓸 수 없다. 블렌더가 받는 사건을 직접
# 기록해서 확인했다. 한글 입력기가 H 를 자모로 바꿔 넘기는데, 블렌더에는 자모에
# 해당하는 글쇠가 없어서 '종류가 빈 사건' 이 된다. 맞출 대상이 없으므로 어떤
# 수식키를 붙여도 소용없다. Command 로 바꾸는 것도 도움이 되지 않았다.
#
#     한글 상태에서 Cmd+Shift+H  →  type=''            (쓸 수 없다)
#     글쇠를 뗄 때               →  unicode='ㅗ'       (자모로 바뀌어 있다)
#     한글 상태에서 Cmd+Shift+;  →  type='SEMI_COLON'  (그대로 들어온다)
#     한글 상태에서 Cmd+Shift+F9 →  type='F9'          (그대로 들어온다)
#
# 기호와 기능키는 자모로 바뀌지 않아서 입력기를 타지 않는다. 그래서 글자 글쇠
# 하나와 기호 글쇠 하나를 같이 등록한다. 영문으로 칠 때는 H 가 기억하기 쉽고,
# 한글로 칠 때는 세미콜론이 언제나 듣는다.
#
# 왜 H 인가: 블렌더 5.1 의 키맵 7,726개를 훑어서 비어 있는 조합을 찾았다.
# 처음에 고른 Ctrl+Shift+G 는 이미 collection.objects_add_active 가 쓰고 있었다.
# H 는 Help 를 떠올리게 해서 기억하기도 낫다.
#
# 왜 세미콜론인가: 비어 있는 후보 중에서 macOS 가 가로채지 않는 것을 골랐다.
# Cmd+Shift+/ 는 도움말, Cmd+Shift+4 는 화면 찍기, Cmd+Shift+` 는 창 넘기기로
# 운영체제가 먼저 가져가서 블렌더까지 오지도 않았다. 세미콜론은 그대로 들어온다.
# 다시 확인하려면: probe/find_free_key.py
DEFAULT_KEY = 'H'
IME_SAFE_KEY = 'SEMI_COLON'
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
    for key in (DEFAULT_KEY, IME_SAFE_KEY):
        kmi = km.keymap_items.new(
            "blender_guide.popup", key, 'PRESS',
            ctrl=DEFAULT_CTRL, shift=DEFAULT_SHIFT, alt=DEFAULT_ALT,
            oskey=DEFAULT_OSKEY,
        )
        addon_keymaps.append((km, kmi))


def _text_for(key: str) -> str:
    parts = []
    if DEFAULT_OSKEY:
        parts.append("Cmd")
    if DEFAULT_CTRL:
        parts.append("Ctrl")
    if DEFAULT_SHIFT:
        parts.append("Shift")
    if DEFAULT_ALT:
        parts.append("Alt")
    parts.append(";" if key == 'SEMI_COLON' else key)
    return "+".join(parts)


def default_shortcut_text() -> str:
    """기본 단축키를 사람이 읽는 글자로 만든다. 설명에 쓴다."""
    return _text_for(DEFAULT_KEY)


def ime_safe_shortcut_text() -> str:
    """한글 입력 중에도 듣는 단축키를 사람이 읽는 글자로 만든다."""
    return _text_for(IME_SAFE_KEY)


def shortcut_texts() -> list:
    """지금 등록된 단축키를 사람이 읽는 글자로 모두 돌려준다."""
    found = []
    for _, kmi in addon_keymaps:
        try:
            text = kmi.to_string()
        except Exception:
            continue
        if text and text not in found:
            found.append(text)
    return found


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
