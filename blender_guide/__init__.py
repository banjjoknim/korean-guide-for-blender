# ═══════════════════════════════════════════════════════════════════════
# 한국어 가이드 — 애드온 입구.
#
# 무엇을 하는 애드온인가:
#   Cmd+Shift+H(맥) 또는 Ctrl+Shift+H 를 누르면 팝업이 뜨고, 한국어로 치면
#   그에 해당하는 블렌더 기능 이름과 단축키, 메뉴 위치를 알려 준다.
#   검색어를 치지 않으면 지금 모드에서 바로 쓸 수 있는 기능을 늘어놓는다.
#
# 책임: 각 부품을 블렌더에 등록하고, 애드온을 끌 때 깨끗이 되돌린다.
#
# 파일 구성:
#   search.py     — 한국어 검색 (블렌더 없이도 시험할 수 있다)
#   focus.py      — 안내: 기능이 화면 어디에 있는지 짚어 주기
#   history.py    — 골라 본 항목을 기억해서 다음에 빨리 찾게 하기
#   nl.py         — 문장으로 쳐도 찾기 (규칙, 블렌더 없이도 시험할 수 있다)
#   similar.py    — 오타나 소리대로 적은 말도 닿게 하기 (글자 조각 겹침)
#   catalog.py    — 기능이 아닌 것들(모디파이어·노드·브러시·도구) 찾기
#   data/catalog_ko.json — 그 667가지의 한국어·영어 이름과 자리
#   agent.py      — 규칙으로 못 찾았을 때 바깥 에이전트에게 물어보기
#   guide_data.py — 항목 읽기 · 단축키 조회 · 지금 쓸 수 있는지 판단
#   popup.py      — 팝업 화면
#   sidebar.py    — N 패널의 '가이드' 탭
#   prefs.py      — 설정 화면 · 즐겨찾기 저장
#   keymaps.py    — 팝업을 여는 단축키
#   data/guide_ko.json — 한국어 항목 (이 파일만 고쳐도 내용이 바뀐다)
# ═══════════════════════════════════════════════════════════════════════

bl_info = {
    "name": "한국어 가이드",
    "author": "banjjoknim",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "Cmd/Ctrl+Shift+H · View3D > Sidebar(N) > 가이드 · Help 메뉴",
    "description": "하고 싶은 일을 한국어로 치면 블렌더 기능과 단축키를 알려 주는 팝업",
    "category": "Interface",
}

import bpy

# 애드온을 고쳐 가며 만들 때, 블렌더가 기억해 둔 옛 코드를 버리고 다시 읽게 한다.
# 이것이 없으면 파일을 고쳐도 블렌더를 껐다 켜기 전까지 바뀌지 않는다.
if "guide_data" in locals():
    import importlib
    for _name in ("search", "nl", "similar", "catalog", "guide_data",
                  "history", "agent", "focus", "results", "popup", "sidebar",
                  "prefs", "keymaps"):
        if _name in locals():
            importlib.reload(locals()[_name])

from . import (agent, catalog, focus, guide_data, history, keymaps, nl,
               popup, prefs, results, search, sidebar, similar)


def register():
    # ① 클래스를 등록한다. 항목 상태(PropertyGroup)가 먼저여야
    #    아래의 CollectionProperty 가 그것을 가리킬 수 있다.
    for cls in results.classes:
        bpy.utils.register_class(cls)
    for cls in popup.classes:
        bpy.utils.register_class(cls)
    for cls in focus.classes:
        bpy.utils.register_class(cls)
    for cls in agent.classes:
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
        update=popup.on_query_changed,
    )
    # 검색 결과 목록이다. 그리는 도중에는 채울 수 없어서 따로 들고 있는다.
    wm.blender_guide_results = bpy.props.CollectionProperty(
        type=results.BLENDERGUIDE_result)
    wm.blender_guide_result_index = bpy.props.IntProperty(
        name="고른 줄", default=0)
    wm.blender_guide_tag = bpy.props.EnumProperty(
        name="분류",
        description="분류로 걸러 본다",
        items=popup._tag_items,
        update=popup.on_query_changed,
    )
    wm.blender_guide_only_available = bpy.props.BoolProperty(
        name="지금 쓸 수 있는 것만",
        description="지금 모드에서 바로 쓸 수 있는 기능만 보여 준다",
        default=False,
        update=popup.on_query_changed,
    )
    wm.blender_guide_states = bpy.props.CollectionProperty(
        type=popup.BLENDERGUIDE_PG_entry_state,
    )

    # ④ 단축키와 화면에 그리는 강조 표시를 등록한다.
    keymaps.register_keymaps()
    focus.register_handlers()

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

    # 그리기 손잡이는 반드시 걷어야 한다. 남겨 두면 애드온을 껐는데도 강조가
    # 화면에 계속 그려지고, 블렌더를 껐다 켜기 전까지 지울 방법이 없다.
    focus.stop()
    focus.unregister_handlers()
    agent.stop()

    wm = bpy.types.WindowManager
    for prop_name in ("blender_guide_query", "blender_guide_tag",
                      "blender_guide_only_available", "blender_guide_states",
                      "blender_guide_results", "blender_guide_result_index"):
        if hasattr(wm, prop_name):
            delattr(wm, prop_name)

    # 등록한 역순으로 지운다. 남을 것부터 지우면 참조가 끊겨 오류가 난다.
    for cls in reversed(sidebar.classes):
        bpy.utils.unregister_class(cls)
    for cls in reversed(prefs.classes):
        bpy.utils.unregister_class(cls)
    for cls in reversed(agent.classes):
        bpy.utils.unregister_class(cls)
    for cls in reversed(focus.classes):
        bpy.utils.unregister_class(cls)
    for cls in reversed(popup.classes):
        bpy.utils.unregister_class(cls)
    for cls in reversed(results.classes):
        bpy.utils.unregister_class(cls)

    guide_data.invalidate_caches()
    similar.invalidate()
    catalog.invalidate()
    popup.reset_favorites_restored()


if __name__ == "__main__":
    register()
