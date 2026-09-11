# ═══════════════════════════════════════════════════════════════════════
# 팝업 — 단축키를 누르면 뜨는 가이드 창.
#
# 책임: 검색창과 결과, 그리고 지금 상황에서 바로 쓸 수 있는 기능 목록을 그린다.
#
# ⭐ 핵심 제약 (이 파일의 구조를 결정한 것):
#   블렌더 팝업은 '버튼(오퍼레이터)'을 누르면 닫힌다. 그래서 즐겨찾기 별표나
#   펼치기 화살표를 버튼으로 만들면 누를 때마다 팝업이 사라져 버린다.
#   반면 '속성(프로퍼티)'은 눌러도 팝업이 닫히지 않는다.
#   그래서 팝업 안에 머무르며 눌러야 하는 것은 전부 속성으로 만들었고,
#   항목별 상태를 담기 위해 PropertyGroup 묶음을 창(WindowManager)에 붙여 둔다.
#
#   팝업을 닫아야 마땅한 것(기능 실행)만 버튼으로 두었다.
# ═══════════════════════════════════════════════════════════════════════

# ⚠️ 이 파일에는 `from __future__ import annotations` 를 쓰지 않는다.
# 그것을 쓰면 bpy.props 어노테이션이 글자로 미뤄지고, 블렌더가 나중에 그 글자를
# 평가할 때 이 모듈 바깥에서 평가한다. 그래서 update 로 건네는 함수 이름을
# 찾지 못해 NameError 가 난다. 실제로 한 번 겪었다.

import bpy

from . import guide_data, search

# ── 아이콘 안전장치 ───────────────────────────────────────────────────
# 블렌더 판에 따라 아이콘 이름이 사라지는 일이 있는데, 없는 이름을 쓰면
# 팝업 전체가 그려지지 않고 오류가 난다. 그래서 그리기 전에 있는지 확인한다.

_valid_icons: set | None = None


def safe_icon(name: str, fallback: str = 'NONE') -> str:
    """그 아이콘이 이 블렌더에 있으면 그대로, 없으면 대체 이름을 돌려준다."""
    global _valid_icons
    if _valid_icons is None:
        try:
            items = bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items
            _valid_icons = {e.identifier for e in items}
        except Exception:
            _valid_icons = set()
    if not _valid_icons:
        return fallback
    return name if name in _valid_icons else fallback


# ── 긴 글 줄바꿈 ──────────────────────────────────────────────────────
# 블렌더의 label 은 스스로 줄을 바꾸지 않는다. 긴 설명은 창 밖으로 잘려 나가므로
# 직접 잘라 줘야 한다.

def _display_width(text: str) -> int:
    """글자가 차지하는 가로 칸을 센다. 한글은 영문의 두 배로 친다."""
    width = 0
    for ch in text:
        width += 2 if ord(ch) > 0x1100 else 1
    return width


def wrap_text(text: str, limit: int) -> list:
    """긴 글을 limit 칸에 맞춰 여러 줄로 자른다. 낱말 중간에서 자르지 않는다."""
    if not text:
        return []
    lines = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and _display_width(candidate) > limit:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


# ── 항목별 상태 (즐겨찾기·펼침) ───────────────────────────────────────

def _on_favorite_changed(self, context):
    """별표를 눌렀을 때 설정 파일에 바로 적어 둔다.

    왜 즉시 적는가: 블렌더를 그냥 닫으면 설정이 저장되지 않아서, 애써 모아 둔
    즐겨찾기가 사라진다.
    """
    from . import prefs
    prefs.save_favorites(context)


class BLENDERGUIDE_PG_entry_state(bpy.types.PropertyGroup):
    """가이드 항목 하나의 화면 상태를 담는다. 항목마다 하나씩 만들어진다."""

    entry_id: bpy.props.StringProperty(name="항목 id")
    favorite: bpy.props.BoolProperty(
        name="즐겨찾기",
        description="자주 쓰는 기능으로 표시한다. 검색어가 비었을 때 맨 위에 뜬다",
        default=False,
        update=_on_favorite_changed,
    )
    expanded: bpy.props.BoolProperty(
        name="자세히",
        description="메뉴 위치와 주의할 점을 펼쳐 본다",
        default=False,
    )


def get_state(context, entry_id: str):
    """항목 id 에 해당하는 상태 묶음을 찾는다. 없으면 새로 만든다."""
    wm = context.window_manager
    states = wm.blender_guide_states
    for st in states:
        if st.entry_id == entry_id:
            return st
    st = states.add()
    st.entry_id = entry_id
    return st


# 저장해 둔 즐겨찾기를 이미 되살렸는지 기억해 둔다.
# 왜 필요한가: 되살리는 일은 블렌더를 켠 뒤 한 번이면 된다. 팝업을 열 때마다
# 하면, 방금 별표를 끈 항목이 저장된 값 때문에 다시 켜져 버린다.
_favorites_restored = False


def sync_states(context) -> None:
    """가이드 항목마다 상태 묶음이 하나씩 있도록 맞추고, 즐겨찾기를 되살린다.

    애드온을 켠 뒤 팝업이나 사이드바가 처음 그려질 때 불린다.
    """
    global _favorites_restored

    wm = context.window_manager
    if not hasattr(wm, "blender_guide_states"):
        return   # 아직 등록이 끝나지 않았다.

    existing = {st.entry_id for st in wm.blender_guide_states}
    for entry in guide_data.load_entries():
        eid = entry.get("id")
        if eid and eid not in existing:
            st = wm.blender_guide_states.add()
            st.entry_id = eid

    if not _favorites_restored:
        from . import prefs
        prefs.restore_favorites(context)
        _favorites_restored = True


def reset_favorites_restored() -> None:
    """다음 sync 때 즐겨찾기를 다시 읽게 한다. 애드온을 끌 때 부른다."""
    global _favorites_restored
    _favorites_restored = False


# ── 분류(태그) 목록 ───────────────────────────────────────────────────
# EnumProperty 에 넘기는 목록은 파이썬이 중간에 지워 버리면 글자가 깨지는
# 알려진 문제가 있다. 그래서 전역 변수에 담아 두고 계속 살려 둔다.
_tag_items_cache: list = [("ALL", "전체", "모든 분류를 본다")]


def rebuild_tag_items() -> list:
    """가이드 항목에 실제로 쓰인 분류만 모아서 목록을 만든다."""
    global _tag_items_cache
    seen = []
    for entry in guide_data.load_entries():
        for tag in entry.get("tags", []):
            if tag not in seen:
                seen.append(tag)
    items = [("ALL", "전체", "모든 분류를 본다")]
    for tag in seen:
        items.append((tag, tag, f"{tag} 분류만 본다"))
    _tag_items_cache = items
    return _tag_items_cache


def _tag_items(self, context):
    return _tag_items_cache


# ── 결과 한 줄 그리기 ─────────────────────────────────────────────────

def _draw_entry(layout, context, entry: dict, available: bool,
                text_width: int, force_expand: bool = False) -> None:
    """가이드 항목 하나를 그린다."""
    state = get_state(context, entry.get("id", ""))
    expanded = state.expanded or force_expand
    shortcut, from_blender = guide_data.get_shortcut(entry)

    box = layout.box()
    col = box.column(align=True)

    # ── 첫 줄: 펼치기 · 이름 · 단축키 · 즐겨찾기 ──
    head = col.row(align=True)

    tri = safe_icon('DISCLOSURE_TRI_DOWN' if expanded else 'DISCLOSURE_TRI_RIGHT',
                    fallback='NONE')
    head.prop(state, "expanded", text="", icon=tri, emboss=False)

    name_row = head.row(align=True)
    # 지금 쓸 수 없는 기능은 흐리게 보여 준다. 숨기지는 않는다.
    # 왜: 없애 버리면 '검색이 안 된다'로 오해하게 되고, 모드를 바꾸면 쓸 수 있다는
    #     사실 자체를 배우지 못한다.
    name_row.active = available
    name_row.label(text=entry.get("ko", "이름 없음"))

    if shortcut:
        key_row = head.row(align=True)
        key_row.alignment = 'RIGHT'
        # 블렌더에서 직접 읽은 단축키가 아니면 괄호를 씌워 구분한다.
        key_row.label(text=shortcut if from_blender else f"({shortcut})")

    head.prop(state, "favorite", text="",
              icon=safe_icon('SOLO_ON' if state.favorite else 'SOLO_OFF'),
              emboss=False)

    # ── 둘째 줄: 영어 이름과 지금 쓸 수 있는지 ──
    sub = col.row(align=True)
    en = entry.get("en") or ""
    if en:
        sub_left = sub.row()
        sub_left.active = False   # 보조 정보이므로 옅게 둔다.
        sub_left.label(text=en)

    if not available:
        warn = sub.row()
        warn.alignment = 'RIGHT'
        warn.alert = True   # 빨갛게 표시한다.
        warn.label(text=_mode_hint(entry, context),
                   icon=safe_icon('ERROR', fallback='NONE'))

    if not expanded:
        return

    # ── 펼쳤을 때: 메뉴 위치 · 주의할 점 · 실행 버튼 ──
    col.separator()

    where = entry.get("where")
    if where:
        for i, line in enumerate(wrap_text(where, text_width)):
            row = col.row()
            row.label(text=line,
                      icon=safe_icon('KEYINGSET', fallback='NONE') if i == 0 else 'BLANK1')

    note = entry.get("note")
    if note:
        col.separator()
        for i, line in enumerate(wrap_text(note, text_width)):
            row = col.row()
            row.active = False
            row.label(text=line,
                      icon=safe_icon('INFO', fallback='NONE') if i == 0 else 'BLANK1')

    op_idname = entry.get("op")
    if op_idname and guide_data.op_exists(op_idname):
        col.separator()
        run = col.row(align=True)
        run.enabled = available
        # INVOKE_DEFAULT 로 두어야 이동·회전처럼 마우스로 조작하는 기능이
        # 평소 단축키를 누른 것과 똑같이 동작한다.
        run.operator_context = 'INVOKE_DEFAULT'
        try:
            run.operator(op_idname, text="지금 실행",
                         icon=safe_icon('PLAY', fallback='NONE'))
        except Exception:
            # 실행 버튼을 못 그려도 설명은 남아야 하므로 조용히 넘어간다.
            pass


def _mode_hint(entry: dict, context) -> str:
    """왜 지금 쓸 수 없는지를 한 줄로 알려 준다."""
    modes = entry.get("modes") or []
    if "EDIT_MESH" in modes and context.mode != "EDIT_MESH":
        return "Tab 을 눌러 에디트 모드로"
    if "OBJECT" in modes and context.mode != "OBJECT":
        return "Tab 을 눌러 오브젝트 모드로"
    if not context.selected_objects and context.mode == "OBJECT":
        return "물체를 먼저 고르세요"
    return "지금은 쓸 수 없음"


# ── 팝업 본체 ─────────────────────────────────────────────────────────

class BLENDERGUIDE_OT_popup(bpy.types.Operator):
    """한국어로 블렌더 기능을 찾는 가이드 팝업을 연다"""

    bl_idname = "blender_guide.popup"
    bl_label = "블렌더 가이드"
    bl_description = "한국어로 하고 싶은 일을 치면 블렌더 기능과 단축키를 알려 준다"
    bl_options = {'REGISTER'}

    def invoke(self, context, event):
        from . import prefs
        p = prefs.get_prefs(context)
        sync_states(context)
        # 팝업을 열 때마다 커서를 검색창에 넣기 위한 표시이다.
        self._needs_focus = True
        return context.window_manager.invoke_popup(self, width=p.popup_width)

    def execute(self, context):
        # 팝업은 그리기만 하므로 실행할 것이 없다.
        return {'FINISHED'}

    def draw(self, context):
        from . import prefs
        p = prefs.get_prefs(context)
        layout = self.layout
        wm = context.window_manager

        # 설명문을 몇 칸에 맞춰 자를지 정한다. 창 너비에서 여백과 아이콘을 뺀 값이다.
        text_width = max(30, int(p.popup_width / 7) - 8)

        errors = guide_data.get_load_errors()
        if errors:
            err = layout.column(align=True)
            err.alert = True
            err.label(text="읽지 못한 항목 파일이 있습니다.",
                      icon=safe_icon('ERROR', fallback='NONE'))
            for label, reason in errors[:3]:
                err.label(text=f"{label} — {reason}")
            # 기본 파일까지 못 읽었으면 보여 줄 것이 없으므로 여기서 멈춘다.
            if not guide_data.load_entries():
                return
            layout.separator()

        # ── 검색창 ──
        search_row = layout.row(align=True)
        search_row.label(text="", icon=safe_icon('VIEWZOOM', fallback='NONE'))

        field = search_row.row(align=True)
        # 팝업이 처음 그려질 때만 커서를 넣는다. 계속 걸면 타이핑을 방해한다.
        if getattr(self, "_needs_focus", False) and p.focus_search_on_open:
            field.activate_init = True
            self._needs_focus = False
        field.prop(wm, "blender_guide_query", text="")

        # ── 거르개 ──
        filter_row = layout.row(align=True)
        filter_row.prop(wm, "blender_guide_tag", text="")
        filter_row.prop(wm, "blender_guide_only_available",
                        text="지금 쓸 수 있는 것만", toggle=True)

        availability = guide_data.get_availability(context)
        entries = guide_data.load_entries()
        query = wm.blender_guide_query.strip()
        tag = wm.blender_guide_tag

        # 분류로 먼저 거른다.
        if tag != "ALL":
            entries = [e for e in entries if tag in e.get("tags", [])]
        if wm.blender_guide_only_available:
            entries = [e for e in entries if availability.get(e.get("id"))]

        layout.separator()

        if query:
            self._draw_search_results(layout, context, entries, query,
                                      availability, text_width, p)
        else:
            self._draw_browse(layout, context, entries, availability,
                              text_width, p)

    # ── 검색어가 있을 때 ──
    def _draw_search_results(self, layout, context, entries, query,
                             availability, text_width, p):
        results = search.search(entries, query, availability,
                                limit=p.max_results)

        if results:
            for i, entry in enumerate(results):
                _draw_entry(layout, context, entry,
                            bool(availability.get(entry.get("id"))),
                            text_width,
                            # 첫 번째 결과는 펼쳐서 보여 준다. 대개 그것을 찾고 있다.
                            force_expand=(i == 0 and p.auto_expand_first))
            return

        # ── 한국어 항목에서 못 찾았을 때: 블렌더 전체에서 영어로 찾아본다 ──
        none = layout.column(align=True)
        none.label(text=f"'{query}' 에 맞는 한국어 항목이 없습니다.",
                   icon=safe_icon('QUESTION', fallback='NONE'))

        if not p.use_op_index:
            none.active = False
            none.label(text="다른 말로 바꿔서 쳐 보세요. 예: 둥글게, 대칭, 뒤집힘")
            return

        fallback = guide_data.search_op_index(query, limit=p.max_fallback)
        if not fallback:
            hint = layout.column(align=True)
            hint.active = False
            hint.label(text="다른 말로 바꿔서 쳐 보세요. 예: 둥글게, 대칭, 뒤집힘")
            hint.label(text="영어 이름을 안다면 영어로 쳐도 찾습니다.")
            return

        layout.separator()
        head = layout.row()
        head.active = False
        head.label(text="블렌더 전체에서 찾은 것 (설명이 영어입니다)")

        for item in fallback:
            box = layout.box()
            col = box.column(align=True)
            row = col.row(align=True)
            row.label(text=item["label"])
            key = guide_data.build_shortcut_map().get(item["idname"])
            if key:
                kr = row.row()
                kr.alignment = 'RIGHT'
                kr.label(text=key)
            idrow = col.row()
            idrow.active = False
            idrow.label(text=item["idname"])
            if item["desc"]:
                for line in wrap_text(item["desc"], text_width)[:3]:
                    dr = col.row()
                    dr.active = False
                    dr.label(text=line)

    # ── 검색어가 없을 때: 즐겨찾기와 지금 쓸 수 있는 것 ──
    def _draw_browse(self, layout, context, entries, availability,
                     text_width, p):
        wm = context.window_manager

        favorites = [e for e in entries
                     if get_state(context, e.get("id", "")).favorite]
        if favorites:
            head = layout.row()
            head.label(text="즐겨찾기",
                       icon=safe_icon('SOLO_ON', fallback='NONE'))
            for entry in favorites[:p.max_results]:
                _draw_entry(layout, context, entry,
                            bool(availability.get(entry.get("id"))),
                            text_width)
            layout.separator()

        # 지금 상황을 한 줄로 알려 준다.
        mode_row = layout.row()
        mode_row.label(text=f"지금 상황: {_mode_label(context)}",
                       icon=safe_icon('INFO', fallback='NONE'))

        usable = [e for e in entries if availability.get(e.get("id"))]
        # 즐겨찾기에 이미 나온 것은 빼서 같은 항목이 두 번 보이지 않게 한다.
        fav_ids = {e.get("id") for e in favorites}
        usable = [e for e in usable if e.get("id") not in fav_ids]

        if not usable:
            empty = layout.column()
            empty.active = False
            empty.label(text="지금 상황에서 바로 쓸 수 있는 항목이 없습니다.")
            return

        # 자주 쓰는 것부터 보여 주려고 분류 순서를 정해 둔다.
        priority = ["기본조작", "메시편집", "선택", "화면조작"]
        usable.sort(key=lambda e: min(
            [priority.index(t) for t in e.get("tags", []) if t in priority]
            or [len(priority)]))

        grid = layout.column(align=True)
        for entry in usable[:p.max_browse]:
            shortcut, from_blender = guide_data.get_shortcut(entry)
            row = grid.row(align=True)
            state = get_state(context, entry.get("id", ""))
            row.prop(state, "favorite", text="",
                     icon=safe_icon('SOLO_ON' if state.favorite else 'SOLO_OFF'),
                     emboss=False)
            row.label(text=entry.get("ko", ""))
            if shortcut:
                kr = row.row()
                kr.alignment = 'RIGHT'
                kr.label(text=shortcut if from_blender else f"({shortcut})")

        if len(usable) > p.max_browse:
            more = layout.row()
            more.active = False
            more.label(text=f"…그 밖에 {len(usable) - p.max_browse}개. "
                            f"검색창에 치면 찾을 수 있습니다.")


# 블렌더가 쓰는 모드 이름을 한국어로 바꾼다. 목록에 없는 모드는 원래 이름을 쓴다.
_MODE_LABELS = {
    "OBJECT": "오브젝트 모드",
    "EDIT_MESH": "에디트 모드 (메시)",
    "EDIT_CURVE": "에디트 모드 (커브)",
    "EDIT_ARMATURE": "에디트 모드 (뼈대)",
    "POSE": "포즈 모드",
    "SCULPT": "스컬프트 모드",
    "PAINT_WEIGHT": "웨이트 페인트 모드",
    "PAINT_VERTEX": "버텍스 페인트 모드",
    "PAINT_TEXTURE": "텍스처 페인트 모드",
    "PARTICLE": "파티클 모드",
}


def _mode_label(context) -> str:
    """지금 모드와 무엇을 골랐는지를 한국어 한 줄로 만든다."""
    mode = getattr(context, "mode", "") or ""
    label = _MODE_LABELS.get(mode, mode or "알 수 없음")

    try:
        count = len(context.selected_objects)
    except Exception:
        count = 0

    if mode == "OBJECT":
        if count == 0:
            return f"{label} · 고른 물체 없음"
        return f"{label} · 물체 {count}개 선택"
    return label


classes = (
    BLENDERGUIDE_PG_entry_state,
    BLENDERGUIDE_OT_popup,
)
