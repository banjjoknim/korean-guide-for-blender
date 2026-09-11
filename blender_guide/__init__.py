# ═══════════════════════════════════════════════════════════════════════
# 블렌더 가이드 (한국어) — 애드온 입구.
#
# 무엇을 하는 애드온인가:
#   Ctrl+Shift+H 를 누르면 팝업이 뜨고, 하고 싶은 일을 한국어로 치면
#   그에 해당하는 블렌더 기능 이름과 단축키, 메뉴 위치를 알려 준다.
#   검색어를 치지 않으면 지금 모드에서 바로 쓸 수 있는 기능을 늘어놓는다.
#
# 책임: 각 부품을 블렌더에 등록하고, 애드온을 끌 때 깨끗이 되돌린다.
#
# 파일 구성:
#   search.py     — 한국어 검색 (블렌더 없이도 시험할 수 있다)
#   guide_data.py — 항목 읽기 · 단축키 조회 · 지금 쓸 수 있는지 판단
#   popup.py      — 팝업 화면
#   sidebar.py    — N 패널의 '가이드' 탭
#   prefs.py      — 설정 화면 · 즐겨찾기 저장
#   keymaps.py    — 팝업을 여는 단축키
#   data/guide_ko.json — 한국어 항목 (이 파일만 고쳐도 내용이 바뀐다)
# ═══════════════════════════════════════════════════════════════════════

bl_info = {
    "name": "블렌더 가이드 (한국어)",
    "author": "banjjoknim",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "Ctrl+Shift+H · View3D > Sidebar(N) > 가이드 · Help 메뉴",
    "description": "하고 싶은 일을 한국어로 치면 블렌더 기능과 단축키를 알려 주는 팝업",
    "category": "Interface",
}

import bpy

# 애드온을 고쳐 가며 만들 때, 블렌더가 기억해 둔 옛 코드를 버리고 다시 읽게 한다.
# 이것이 없으면 파일을 고쳐도 블렌더를 껐다 켜기 전까지 바뀌지 않는다.
if "guide_data" in locals():
    import importlib
    for _name in ("search", "guide_data", "popup", "sidebar", "prefs", "keymaps"):
        if _name in locals():
            importlib.reload(locals()[_name])

from . import guide_data, keymaps, popup, prefs, search, sidebar


def register():
    # ① 클래스를 등록한다. 항목 상태(PropertyGroup)가 먼저여야
    #    아래의 CollectionProperty 가 그것을 가리킬 수 있다.
    for cls in popup.classes:
        bpy.utils.register_class(cls)
    for cls in prefs.classes:
        bpy.utils.register_class(cls)
    for cls in sidebar.classes:
        bpy.utils.register_class(cls)

    # ② 분류 목록을 만든다. 항목 파일을 읽는 첫 순간이기도 하다.
    popup.rebuild_tag_items()

    # ③ 팝업이 쓰는 값을 창(WindowManager)에 붙인다.
    #    왜 창에 붙이는가: 블렌더 파일(.blend)에 저장되지 않아서, 검색어 같은
    #    일시적인 값이 작업 파일을 더럽히지 않는다.
    wm = bpy.types.WindowManager
    wm.blender_guide_query = bpy.props.StringProperty(
        name="검색",
        description="하고 싶은 일을 한국어로 칩니다. 예: 면 나누기, 대칭, 뒤집힘",
        default="",
        options={'TEXTEDIT_UPDATE'},   # 한 글자 칠 때마다 결과가 바뀐다.
    )
    wm.blender_guide_tag = bpy.props.EnumProperty(
        name="분류",
        description="분류로 걸러 본다",
        items=popup._tag_items,
    )
    wm.blender_guide_only_available = bpy.props.BoolProperty(
        name="지금 쓸 수 있는 것만",
        description="지금 모드에서 바로 쓸 수 있는 기능만 보여 준다",
        default=False,
    )
    wm.blender_guide_states = bpy.props.CollectionProperty(
        type=popup.BLENDERGUIDE_PG_entry_state,
    )

    # ④ 단축키를 등록한다.
    keymaps.register_keymaps()

    # ⑤ Help 메뉴에 항목을 더한다. 단축키를 잊었을 때의 두 번째 입구이다.
    try:
        bpy.types.TOPBAR_MT_help.append(sidebar.draw_help_menu)
    except Exception:
        # 이 판에 그 메뉴가 없어도 애드온 전체가 멈추면 안 된다.
        pass


def unregister():
    try:
        bpy.types.TOPBAR_MT_help.remove(sidebar.draw_help_menu)
    except Exception:
        pass

    keymaps.unregister_keymaps()

    wm = bpy.types.WindowManager
    for prop_name in ("blender_guide_query", "blender_guide_tag",
                      "blender_guide_only_available", "blender_guide_states"):
        if hasattr(wm, prop_name):
            delattr(wm, prop_name)

    # 등록한 역순으로 지운다. 남을 것부터 지우면 참조가 끊겨 오류가 난다.
    for cls in reversed(sidebar.classes):
        bpy.utils.unregister_class(cls)
    for cls in reversed(prefs.classes):
        bpy.utils.unregister_class(cls)
    for cls in reversed(popup.classes):
        bpy.utils.unregister_class(cls)

    guide_data.invalidate_caches()
    popup.reset_favorites_restored()


if __name__ == "__main__":
    register()
