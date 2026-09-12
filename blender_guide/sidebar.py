# ═══════════════════════════════════════════════════════════════════════
# 사이드바 — N 키를 눌렀을 때 나오는 '가이드' 탭.
#
# 왜 팝업만으로는 부족한가: 팝업은 단축키를 알아야 열 수 있는데, 초보자는
# 그 단축키부터 잊어버린다. 화면에 늘 보이는 자리가 하나 있어야
# '가이드로 돌아가는 길'이 끊기지 않는다.
#
# 팝업과 달리 여기서는 버튼을 눌러도 화면이 닫히지 않으므로 제약이 적다.
# ═══════════════════════════════════════════════════════════════════════

from __future__ import annotations

import bpy

from . import guide_data, keymaps, popup, prefs


class BLENDERGUIDE_PT_sidebar(bpy.types.Panel):
    bl_label = "블렌더 가이드"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "가이드"

    def draw(self, context):
        layout = self.layout
        p = prefs.get_prefs(context)

        # ── 팝업 열기 ──
        # 단축키를 같이 적어 두어, 다음부터는 이 패널을 거치지 않게 한다.
        shortcut = _popup_shortcut()
        col = layout.column(align=True)
        col.scale_y = 1.5
        col.operator("blender_guide.popup",
                     text="기능 찾기" + (f"   ({shortcut})" if shortcut else ""),
                     icon=popup.safe_icon('VIEWZOOM', fallback='NONE'))

        # ── 안내 모드 ──
        # 팝업 안에도 같은 토글이 있지만, 팝업을 열지 않고도 껐다 켤 수 있어야
        # '지금은 안내가 거슬린다'는 순간에 바로 끌 수 있다.
        if hasattr(p, "bl_rna"):
            toggle = layout.row(align=True)
            toggle.prop(p, "learner_mode", text="안내 모드", toggle=True,
                        icon=popup.safe_icon('QUESTION', fallback='NONE'))

        # ── 에이전트에게 물어본 것 ──
        # 팝업은 몇 초 뒤에 닫히지만 여기는 남아 있으므로, 답을 여기서 본다.
        from . import agent
        state = agent.get_state()
        if state["status"] == "asking":
            box = layout.box()
            box.label(text="에이전트에게 물어보는 중",
                      icon=popup.safe_icon('SORTTIME', fallback='NONE'))
            inner = box.column(align=True)
            inner.active = False
            inner.label(text=state["question"])
        elif state["status"] == "done" and agent.found_entries():
            box = layout.box()
            box.label(text=f"에이전트가 찾은 것 ({state['took']}초)",
                      icon=popup.safe_icon('COMMUNITY', fallback='NONE'))
            col = box.column(align=True)
            for entry in agent.found_entries():
                row = col.row(align=True)
                popup._draw_entry_name(row, context, entry, True,
                                       bool(getattr(p, "learner_mode", True)))
        elif state["status"] == "failed":
            box = layout.box()
            box.alert = True
            box.label(text="에이전트에게 묻지 못했습니다",
                      icon=popup.safe_icon('ERROR', fallback='NONE'))
            inner = box.column(align=True)
            inner.active = False
            inner.label(text=state["error"])

        # ── 지금 상황 ──
        box = layout.box()
        box.label(text=popup._mode_label(context),
                  icon=popup.safe_icon('INFO', fallback='NONE'))

        # ── 즐겨찾기 ──
        popup.sync_states(context)
        entries = guide_data.load_entries()
        availability = guide_data.get_availability(context)

        favorites = [e for e in entries
                     if popup.get_state(context, e.get("id", "")).favorite]

        box = layout.box()
        head = box.row()
        head.label(text="즐겨찾기",
                   icon=popup.safe_icon('SOLO_ON', fallback='NONE'))

        if not favorites:
            hint = box.column(align=True)
            hint.active = False
            hint.label(text="아직 없습니다.")
            hint.label(text="팝업에서 별표를 누르면")
            hint.label(text="여기에 모입니다.")
            return

        col = box.column(align=True)
        for entry in favorites:
            shortcut_text, from_blender = guide_data.get_shortcut(entry)
            available = bool(availability.get(entry.get("id")))

            row = col.row(align=True)
            row.active = available
            popup._draw_entry_name(row, context, entry, available,
                                   bool(getattr(p, "learner_mode", True)))
            if shortcut_text:
                key = row.row()
                key.alignment = 'RIGHT'
                key.label(text=shortcut_text if from_blender
                          else f"({shortcut_text})")


def _popup_shortcut() -> str:
    """팝업을 여는 단축키를 글자로 만든다. 사용자가 바꿨으면 바꾼 것이 나온다."""
    for _, kmi in keymaps.addon_keymaps:
        try:
            return kmi.to_string()
        except Exception:
            continue
    return ""


def draw_help_menu(self, context):
    """블렌더의 Help 메뉴에 가이드 열기 항목을 더한다.

    왜 Help 인가: 막힌 사람이 가장 먼저 열어 보는 메뉴이기 때문이다.
    """
    self.layout.operator("blender_guide.popup",
                         text="블렌더 가이드 (한국어)",
                         icon=popup.safe_icon('VIEWZOOM', fallback='NONE'))


classes = (
    BLENDERGUIDE_PT_sidebar,
)
