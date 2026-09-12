# ═══════════════════════════════════════════════════════════════════════
# 검색 결과 목록 — 길어도 화면을 덮지 않게 한다.
#
# 무엇이 문제였나: 결과를 하나씩 상자로 그렸더니, 설정값 여덟 개만 걸려도
# 마흔 줄이 되어 화면을 거의 덮었다. 팝업은 스크롤이 없어서 길어지면 그냥
# 길어진다.
#
# 어떻게 하나: 블렌더의 template_list 는 정해진 줄 수만 보여 주고 나머지는
# 스크롤로 넘긴다. 그래서 결과는 한 줄짜리 목록으로 보여 주고, 고른 것
# 하나만 아래에 자세히 펼친다. 목록은 여덟 줄을 넘지 않는다.
#
# ⚠️ 목록은 그리는 도중에 채울 수 없다. 블렌더는 draw 안에서 데이터를
#    바꾸는 것을 막는다. 그래서 검색어가 바뀔 때와 팝업을 열 때만 채운다.
# ═══════════════════════════════════════════════════════════════════════

from __future__ import annotations

import bpy

# 목록에 한 번에 보여 줄 줄 수이다. 이보다 많으면 스크롤로 넘긴다.
MAX_ROWS = 8


class BLENDERGUIDE_result(bpy.types.PropertyGroup):
    """목록 한 줄에 담기는 것. 그리기에 필요한 만큼만 담는다."""

    entry_id: bpy.props.StringProperty()
    ko: bpy.props.StringProperty()
    en: bpy.props.StringProperty()
    right: bpy.props.StringProperty()      # 오른쪽 끝에 적는 말 (단축키·종류)
    how: bpy.props.StringProperty()        # 사용 방법 한 줄 요약
    kind: bpy.props.StringProperty()       # entry · catalog · index
    available: bpy.props.BoolProperty(default=True)


class BLENDERGUIDE_UL_results(bpy.types.UIList):
    """결과 한 줄을 그린다. 이름 · 사용 방법 · 단축키를 한 줄에 담는다."""

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):
        row = layout.row(align=True)
        if not item.available:
            # 지금 모드에서는 못 쓰는 것이다. 흐리게 두어 구분한다.
            row.active = False

        split = row.split(factor=0.42)
        split.label(text=item.ko)

        rest = split.split(factor=0.66)
        mid = rest.row()
        mid.active = False
        mid.label(text=item.how)

        tail = rest.row()
        tail.alignment = 'RIGHT'
        tail.label(text=item.right)


def summarize(text: str, limit: int = 34) -> str:
    """사용 방법을 목록 한 줄에 들어갈 만큼 줄인다.

    첫 문장만 남긴다. 사용 방법은 대개 첫 문장에 '무엇을 누른다' 가 있고
    그다음부터 곁가지가 붙기 때문이다.
    """
    text = " ".join((text or "").split())
    if not text:
        return ""
    for mark in ("니다.", "습니다.", "세요.", "한다.", "된다."):
        head = text.split(mark)[0]
        if head != text:
            text = head + mark.rstrip(".")
            break
    if len(text) > limit:
        text = text[:limit - 1].rstrip() + "…"
    return text


def clear(context) -> None:
    wm = context.window_manager
    if hasattr(wm, "blender_guide_results"):
        wm.blender_guide_results.clear()
        wm.blender_guide_result_index = 0


def fill(context, rows: list) -> None:
    """목록을 새로 채운다. ⚠️ 그리는 도중에는 부르면 안 된다."""
    wm = context.window_manager
    if not hasattr(wm, "blender_guide_results"):
        return
    kept = wm.blender_guide_results
    kept.clear()
    for row in rows:
        item = kept.add()
        item.entry_id = row.get("id", "")
        item.ko = row.get("ko", "")
        item.en = row.get("en", "")
        item.right = row.get("right", "")
        item.how = row.get("how", "")
        item.kind = row.get("kind", "entry")
        item.available = bool(row.get("available", True))
    wm.blender_guide_result_index = 0


def picked(context):
    """지금 고른 줄을 돌려준다. 없으면 None 이다."""
    wm = context.window_manager
    kept = getattr(wm, "blender_guide_results", None)
    if not kept:
        return None
    index = wm.blender_guide_result_index
    if 0 <= index < len(kept):
        return kept[index]
    return kept[0] if len(kept) else None


classes = (BLENDERGUIDE_result, BLENDERGUIDE_UL_results)
