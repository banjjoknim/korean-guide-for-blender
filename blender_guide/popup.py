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

from . import agent, focus, guide_data, history, nl, search

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

def _on_expanded_changed(self, context):
    """자세히 펼치면 그 항목을 골랐다고 본다.

    왜 펼치기를 신호로 삼는가: 안내 모드를 끈 사람은 이름을 눌러도 아무 일이
    없으므로, 무엇에 관심을 두었는지 알 방법이 펼치기밖에 없다.
    """
    if self.expanded:
        history.record(context, self.entry_id)


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
        update=_on_expanded_changed,
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

# ⚠️ 팝업에서 기능을 직접 실행하는 단추는 일부러 두지 않는다.
#
# 예전에는 '지금 실행' 단추가 있었는데, 걷어냈다. 까닭은 이렇다.
#
# invoke_popup 으로 띄운 팝업은 **단추를 눌러도 닫히지 않는다.** 마우스를
# 움직이지 않고 같은 자리를 두 번 누르면 단추가 두 번 눌리는 것으로 확인했다.
# 그래서 돌리기처럼 마우스를 끄는 기능을 여기서 실행하면, 변형은 시작되지만
# 팝업이 그 위를 덮은 채로 남는다. 점선 안내선은 기준점에서 마우스까지 그어지는데
# 마우스가 팝업 위에 있으니 가려지고, 팝업이 키 입력을 먼저 가져가므로
# X · Y · Z 축 고정도 안 먹는다.
#
# 시도했다가 듣지 않은 것들을 적어 둔다. 같은 길을 다시 가지 않기 위해서이다.
#   - operator_context 를 INVOKE_REGION_WIN 으로 바로잡기. 재어 보니 팝업의
#     기본값이 이미 그 값이라 원인과 무관했다.
#   - 타이머로 한 박자 미뤄서 부르기. 팝업이 닫히지 않으니 미뤄도 소용이 없다.
#   - Window.cursor_warp 로 커서를 팝업 밖으로 내보내 닫기. 이벤트를 흉내 낸
#     시험에서는 통했지만 실제 사용에서는 증상이 그대로였다.
#
# 블렌더에는 팝업을 닫는 API 가 아예 없다. bpy.ops 전체를 훑어도 없다.
# 그래서 반쪽으로 시작되는 실행 단추를 두느니, 무엇을 눌러야 하는지 알려 주는
# 가이드 본래 역할에 집중하는 편이 낫다고 판단했다. 단축키와 메뉴 위치는
# 그대로 보여 주고, 안내 모드에서는 실제 메뉴를 펼쳐 준다.


def _draw_entry_name(row, context, entry: dict, available: bool,
                     learner: bool) -> None:
    """항목 이름을 그린다.

    안내 모드면 이름이 '어디에 있는지 보기' 단추가 되고, 안내 모드를 끄면
    누를 것이 없는 글자로 둔다.

    왜 겉모습(emboss=False)을 글자처럼 두는가: 목록이 단추 밭처럼 보이면
    무엇을 눌러야 할지 고르는 데 시간이 들어서, 훑어보는 화면으로서는 나빠진다.
    """
    ko = entry.get("ko", "이름 없음")
    name = row.row(align=True)
    # 왼쪽으로 붙여야 원래의 글자 배치와 같아 보인다.
    name.alignment = 'LEFT'

    if learner:
        op = name.operator("blender_guide.focus", text=ko, emboss=False)
        op.entry_id = entry.get("id", "")
        return

    name.label(text=ko)


def _draw_entry(layout, context, entry: dict, available: bool,
                text_width: int, force_expand: bool = False, p=None) -> None:
    """가이드 항목 하나를 그린다."""
    if p is None:
        from . import prefs
        p = prefs.get_prefs(context)
    learner = bool(getattr(p, "learner_mode", True))

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
    _draw_entry_name(name_row, context, entry, available, learner)

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

        # 안내만 해 두고 사용자가 Tab 을 누르게 하면, 고른 물체가 없는 경우처럼
        # Tab 이 듣지 않는 상황에서 왜 안 되는지 알 길이 없다. 그래서 직접
        # 모드를 바꿔 주는 단추를 붙인다.
        target = _mode_target(entry, context)
        if target:
            fix = sub.row(align=True)
            fix.alignment = 'RIGHT'
            fix.operator("blender_guide.set_mode", text="바꾸기",
                         icon=safe_icon('ARROW_LEFTRIGHT',
                                        fallback='NONE')).mode = target

    if not expanded:
        return

    # ── 펼쳤을 때: 메뉴 위치 · 주의할 점 · 실행 버튼 ──
    col.separator()

    where = entry.get("where")
    if where:
        steps = focus.path_steps(entry)
        if learner and getattr(p, "focus_show_path", True) and steps:
            # 경로를 한 줄로 붙여 두면 어디까지가 한 단계인지 헷갈린다.
            # 번호를 붙여 끊어 주면 그대로 따라 누르기만 하면 된다.
            for i, step in enumerate(steps, start=1):
                row = col.row()
                row.label(text=f"{i}. {step}",
                          icon=safe_icon('KEYINGSET', fallback='NONE')
                          if i == 1 else 'BLANK1')
        else:
            for i, line in enumerate(wrap_text(where, text_width)):
                row = col.row()
                row.label(text=line,
                          icon=safe_icon('KEYINGSET', fallback='NONE')
                          if i == 0 else 'BLANK1')

    note = entry.get("note")
    if note:
        col.separator()
        for i, line in enumerate(wrap_text(note, text_width)):
            row = col.row()
            row.active = False
            row.label(text=line,
                      icon=safe_icon('INFO', fallback='NONE') if i == 0 else 'BLANK1')

    if learner:
        col.separator()
        actions = col.row(align=True)
        actions.operator("blender_guide.focus", text="어디에 있는지 보기",
                         icon=safe_icon('VIEWZOOM', fallback='NONE')
                         ).entry_id = entry.get("id", "")


# 에디트 모드가 있는 물체 종류이다. 여기 없는 종류는 Tab 을 눌러도 아무 일이 없다.
_EDITABLE_TYPES = {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT', 'ARMATURE',
                   'LATTICE', 'CURVES', 'GREASEPENCIL', 'POINTCLOUD'}


def _active_object(context):
    """지금 활성 물체를 돌려준다. 없으면 None 이다."""
    try:
        return context.view_layer.objects.active
    except Exception:
        return None


def _mode_target(entry: dict, context) -> str:
    """모드가 안 맞아서 못 쓰는 항목이면 어느 모드로 바꿔야 하는지 돌려준다.

    바꿀 만한 모드가 없으면 빈 글자를 돌려준다. 그때는 단추를 그리지 않는다.
    """
    modes = entry.get("modes") or []
    mode = getattr(context, "mode", "") or ""
    if not modes or mode in modes:
        return ""
    if any(m.startswith("EDIT") for m in modes):
        return 'EDIT'
    if "OBJECT" in modes:
        return 'OBJECT'
    if "POSE" in modes:
        return 'POSE'
    if "SCULPT" in modes:
        return 'SCULPT'
    return ""


def _mode_hint(entry: dict, context) -> str:
    """왜 지금 쓸 수 없는지를 한 줄로 알려 준다.

    예전에는 'Tab 을 눌러 에디트 모드로' 라고만 적었는데, 고른 물체가 없거나
    편집할 수 없는 종류이면 Tab 을 눌러도 모드가 바뀌지 않는다. 그 상태에서
    Tab 을 누르라고만 하면 사용자는 애드온이 틀린 줄 안다. 그래서 바뀌지 않는
    까닭을 먼저 짚어 준다.
    """
    modes = entry.get("modes") or []
    mode = getattr(context, "mode", "") or ""
    obj = _active_object(context)

    if modes and mode not in modes:
        wants_edit = any(m.startswith("EDIT") for m in modes)
        if obj is None:
            return "물체를 먼저 고르세요"
        if wants_edit and obj.type not in _EDITABLE_TYPES:
            return f"'{obj.name}' 은(는) 편집할 수 없는 종류입니다"
        if wants_edit:
            return "에디트 모드에서 됩니다"
        if "OBJECT" in modes:
            return "오브젝트 모드에서 됩니다"
        return "다른 모드에서 됩니다"

    if mode == "OBJECT" and not getattr(context, "selected_objects", None):
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

        # 안내 모드를 여기서 바로 껐다 켤 수 있게 둔다.
        # 왜 설정 화면에만 두지 않는가: 익숙해지는 시점은 사람마다 다르고,
        # 그때마다 Preferences 를 여는 것은 번거로워서 결국 안 끄게 된다.
        # _FallbackPrefs 는 RNA 가 아니라서 prop 으로 그릴 수 없으므로 걸러 낸다.
        if hasattr(p, "bl_rna"):
            filter_row.prop(p, "learner_mode", text="안내", toggle=True,
                            icon=safe_icon('QUESTION', fallback='NONE'))

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
        # 문장으로 쳤으면 군더더기를 걷어내고 핵심 낱말로 찾는다.
        # 낱말로 친 것까지 손대면 멀쩡하던 검색이 틀어지므로, 문장일 때만 그렇게 한다.
        words = []
        if getattr(p, "use_natural", True) and nl.looks_like_sentence(query):
            results, words = nl.search(entries, query, availability,
                                       limit=p.max_results,
                                       boosts=history.boosts(context))
        else:
            results = search.search(entries, query, availability,
                                    limit=p.max_results,
                                    boosts=history.boosts(context))

        # 에이전트가 찾아 준 것이 있으면 먼저 보여 준다.
        _draw_agent_answer(layout, context, query)

        if words and results:
            hint = layout.row()
            hint.active = False
            hint.label(text="이렇게 알아들었습니다: " + " · ".join(words))

        if results:
            for i, entry in enumerate(results):
                _draw_entry(layout, context, entry,
                            bool(availability.get(entry.get("id"))),
                            text_width,
                            # 첫 번째 결과는 펼쳐서 보여 준다. 대개 그것을 찾고 있다.
                            force_expand=(i == 0 and p.auto_expand_first),
                            p=p)
            return

        # ── 한국어 항목에서 못 찾았을 때: 블렌더 전체에서 영어로 찾아본다 ──
        none = layout.column(align=True)
        none.label(text=f"'{query}' 에 맞는 한국어 항목이 없습니다.",
                   icon=safe_icon('QUESTION', fallback='NONE'))

        _draw_agent_ask(layout, context, query)

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

        _draw_history(layout, context, entries, availability, p)

        favorites = [e for e in entries
                     if get_state(context, e.get("id", "")).favorite]
        if favorites:
            head = layout.row()
            head.label(text="즐겨찾기",
                       icon=safe_icon('SOLO_ON', fallback='NONE'))
            for entry in favorites[:p.max_results]:
                _draw_entry(layout, context, entry,
                            bool(availability.get(entry.get("id"))),
                            text_width, p=p)
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
            _draw_entry_name(row, context, entry, True,
                             bool(getattr(p, "learner_mode", True)))
            if shortcut:
                kr = row.row()
                kr.alignment = 'RIGHT'
                kr.label(text=shortcut if from_blender else f"({shortcut})")

        if len(usable) > p.max_browse:
            more = layout.row()
            more.active = False
            more.label(text=f"…그 밖에 {len(usable) - p.max_browse}개. "
                            f"검색창에 치면 찾을 수 있습니다.")


def _draw_agent_answer(layout, context, query: str) -> None:
    """에이전트가 찾아 준 것을 보여 준다.

    왜 팝업이 다시 열릴 때 보여 주는가: 물어보는 데 몇 초가 걸리는데, 그동안
    팝업은 이미 닫힌다. 블렌더에는 팝업을 다시 띄워 알릴 방법이 마땅치 않아서,
    답을 담아 두었다가 다음에 열 때 보여 준다. 사이드바에서도 볼 수 있다.
    """
    state = agent.get_state()
    if state["status"] == "idle":
        return
    # 지금 친 말과 물어본 말이 다르면 남의 답이므로 보여 주지 않는다.
    if query and state["question"] and query.strip() != state["question"]:
        return

    if state["status"] == "asking":
        row = layout.row()
        row.label(text=f"'{state['question']}' 을(를) 에이전트에게 물어보는 중입니다.",
                  icon=safe_icon('SORTTIME', fallback='NONE'))
        layout.separator()
        return

    if state["status"] == "failed":
        warn = layout.column(align=True)
        warn.alert = True
        warn.label(text=f"에이전트에게 묻지 못했습니다 — {state['error']}",
                   icon=safe_icon('ERROR', fallback='NONE'))
        layout.separator()
        return

    found = agent.found_entries()
    if not found:
        return

    head = layout.row()
    head.label(text=f"에이전트가 찾은 것 ({state['took']}초)",
               icon=safe_icon('COMMUNITY', fallback='NONE'))
    from . import prefs as _prefs
    p = _prefs.get_prefs(context)
    availability = guide_data.get_availability(context)
    for entry in found:
        _draw_entry(layout, context, entry,
                    bool(availability.get(entry.get("id"))),
                    max(30, int(p.popup_width / 7) - 8), p=p)
    layout.separator()


def _draw_agent_ask(layout, context, query: str) -> None:
    """규칙으로 못 찾았을 때 에이전트에게 넘기는 단추를 그린다."""
    from . import prefs as _prefs

    p = _prefs.get_prefs(context)
    state = agent.get_state()
    if state["status"] == "asking":
        return

    row = layout.row()
    if not getattr(p, "use_agent", False):
        row.active = False
        row.label(text="설정에서 '못 찾으면 에이전트에게 물어본다' 를 켜면 "
                       "여기서 물어볼 수 있습니다.")
        return

    if not agent.available(p):
        row.active = False
        row.label(text="물어볼 도구를 못 찾았습니다. 설정에 명령을 적어 주세요.")
        return

    row.operator("blender_guide.ask_agent",
                 icon=safe_icon('COMMUNITY', fallback='NONE')).question = query


def _draw_history(layout, context, entries, availability, p) -> None:
    """최근에 골라 본 항목을 보여 준다. 없으면 아무것도 안 그린다.

    즐겨찾기보다 위에 두는 이유: 즐겨찾기는 일부러 남긴 것이라 이미 어디 있는지
    알고 있다. 방금 보던 것을 다시 찾는 일이 더 잦다.
    """
    ids = history.recent(context, limit=5)
    if not ids:
        return

    by_id = {e.get("id"): e for e in entries}
    picked = [by_id[i] for i in ids if i in by_id]
    if not picked:
        return

    head = layout.row()
    head.label(text="최근에 본 것",
               icon=safe_icon('RECOVER_LAST', fallback='NONE'))

    learner = bool(getattr(p, "learner_mode", True))
    col = layout.column(align=True)
    for entry in picked:
        shortcut, from_blender = guide_data.get_shortcut(entry)
        available = bool(availability.get(entry.get("id")))
        row = col.row(align=True)
        row.active = available
        _draw_entry_name(row, context, entry, available, learner)

        right = row.row(align=True)
        right.alignment = 'RIGHT'
        count = history.pick_count(context, entry.get("id", ""))
        if count > 1:
            times = right.row()
            times.active = False
            times.label(text=f"{count}번")
        if shortcut:
            right.label(text=shortcut if from_blender else f"({shortcut})")

    layout.separator()


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
