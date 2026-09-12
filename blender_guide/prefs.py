# ═══════════════════════════════════════════════════════════════════════
# 설정 — 팝업 크기, 즐겨찾기 저장, 단축키 바꾸기.
#
# 책임: Preferences > Add-ons 에서 보이는 설정 화면을 그리고, 즐겨찾기를
#       블렌더를 껐다 켜도 남도록 저장한다.
#
# 핵심 패턴: 즐겨찾기는 항목 id 목록을 글자 하나(JSON)로 눌러 담아 둔다.
# 왜: 블렌더 설정에는 목록을 그대로 저장하는 자리가 없다. 글자로 바꿔 두면
#     설정 파일에 그대로 실려 가고, 항목이 늘어나도 저장 구조를 안 바꿔도 된다.
# ═══════════════════════════════════════════════════════════════════════

# ⚠️ 이 파일에는 `from __future__ import annotations` 를 쓰지 않는다.
# 그것을 쓰면 bpy.props 어노테이션이 글자로 미뤄지고, 블렌더가 나중에 그 글자를
# 평가할 때 이 모듈 바깥에서 평가한다. 그래서 update 로 건네는 함수 이름을
# 찾지 못해 NameError 가 난다. 실제로 한 번 겪었다.

import json

import bpy

from . import guide_data, popup


def _on_pack_dir_changed(context) -> None:
    """팩 폴더를 바꾸면 항목을 처음부터 다시 읽는다.

    왜 즉시 다시 읽는가: 폴더만 바꾸고 아무 일도 안 일어나면 설정이 안 먹은 것처럼
    보인다. 바로 아래 줄에 개수가 바뀌어 나와야 제대로 잡혔는지 알 수 있다.
    """
    guide_data.invalidate_caches(drop_entries=True)
    guide_data.load_entries(force=True)
    from . import similar
    similar.invalidate()
    popup.rebuild_tag_items()
    try:
        popup.sync_states(context)
    except Exception:
        # 아직 등록이 끝나지 않은 때에도 불릴 수 있다. 다음에 팝업을 열면 맞춰진다.
        pass


class BLENDERGUIDE_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    # ── 팝업 모양 ──
    popup_width: bpy.props.IntProperty(
        name="팝업 너비",
        description="팝업 창의 가로 크기이다. 설명이 잘려 보이면 늘린다",
        default=560, min=320, max=1200,
    )
    max_results: bpy.props.IntProperty(
        name="검색 결과 개수",
        description="검색했을 때 한 번에 보여 줄 항목 수이다",
        default=8, min=1, max=30,
    )
    max_browse: bpy.props.IntProperty(
        name="상황별 추천 개수",
        description="검색어가 없을 때 보여 줄 '지금 쓸 수 있는 기능' 수이다",
        default=14, min=1, max=40,
    )
    max_fallback: bpy.props.IntProperty(
        name="영어 검색 결과 개수",
        description="한국어 항목에서 못 찾았을 때 블렌더 전체에서 찾아 보여 줄 수이다",
        default=5, min=1, max=20,
    )

    # ── 동작 ──
    auto_expand_first: bpy.props.BoolProperty(
        name="첫 결과를 펼쳐서 보여 준다",
        description="검색 결과 중 첫 번째의 설명을 자동으로 펼친다",
        default=True,
    )
    focus_search_on_open: bpy.props.BoolProperty(
        name="팝업을 열면 바로 칠 수 있게 한다",
        description=("팝업이 뜨자마자 검색창에 커서를 넣습니다. 단축키를 누르고 곧바로 "
                     "칠 수 있습니다. 다만 커서가 검색창에 있는 동안에는 팝업 안의 "
                     "첫 클릭이 그 상태를 빠져나오는 데 쓰여서 단추까지 닿지 않습니다. "
                     "치고 나서 Enter 를 한 번 누르면 그다음 클릭부터 바로 닿습니다"),
        default=True,
    )
    use_op_index: bpy.props.BoolProperty(
        name="한국어로 못 찾으면 블렌더 전체에서 찾는다",
        description="한국어 항목에 없는 것은 블렌더에 등록된 기능 전체에서 영어로 찾아 준다",
        default=True,
    )

    # ── 자연어와 에이전트 ──
    use_natural: bpy.props.BoolProperty(
        name="문장으로 쳐도 찾는다",
        description=("'면을 둘로 나누고 싶어' 처럼 문장으로 쳐도 찾아 줍니다. "
                     "군더더기를 걷어내고 핵심 낱말로 찾습니다"),
        default=True,
    )
    use_similar: bpy.props.BoolProperty(
        name="못 찾으면 비슷한 것을 보여 준다",
        description=("오타나 소리대로 적은 말도 닿게 합니다. '모서라' 를 쳐도 "
                     "'모서리 둥글게 깎기' 가 나옵니다. 정확히 찾은 것이 있으면 "
                     "끼어들지 않습니다"),
        default=True,
    )
    use_agent: bpy.props.BoolProperty(
        name="못 찾으면 에이전트에게 물어본다",
        description=("규칙으로 아무것도 못 찾았을 때만, 컴퓨터에 깔린 에이전트에게 "
                     "물어봅니다. 바깥 프로그램을 실행하는 일이므로 기본은 꺼져 있습니다"),
        default=False,
    )
    agent_command: bpy.props.StringProperty(
        name="물어볼 명령",
        description=("보통은 비워 두면 됩니다. claude 명령줄 도구를 알아서 찾습니다. "
                     "다른 도구를 쓰거나 자동으로 못 찾을 때만 적으십시오. "
                     "{prompt} 자리에 질문이 들어갑니다. 예: claude -p {prompt}"),
        default="",
    )
    agent_timeout: bpy.props.FloatProperty(
        name="기다릴 시간",
        description="이 시간 안에 답이 없으면 그만둡니다. 단위는 초입니다",
        default=30.0, min=5.0, max=180.0,
    )

    # ── 검색 기록 ──
    # 즐겨찾기는 일부러 남기는 것이고, 기록은 쓰다 보면 저절로 쌓이는 것이다.
    # 초보자는 무엇을 즐겨찾기할지 판단할 만큼 알지 못하므로 기록이 먼저 돕는다.
    use_history: bpy.props.BoolProperty(
        name="골라 본 것을 기억한다",
        description=("한 번 고른 항목을 기억해 두었다가, 다음에 검색할 때 위로 올려 주고 "
                     "검색어가 없을 때 '최근에 본 것' 으로 보여 줍니다"),
        default=True,
    )
    max_history: bpy.props.IntProperty(
        name="기억할 개수",
        description="이보다 많아지면 오래된 것부터 잊습니다",
        default=10, min=1, max=50,
    )

    # ── 안내 모드 ──
    # 왜 토글로 두는가: 익숙해지면 '어디에 있는지'는 이미 알고 있어서, 단축키만
    # 확인하고 바로 닫는다. 그때 안내가 계속 끼어들면 오히려 느려진다.
    learner_mode: bpy.props.BoolProperty(
        name="안내 모드",
        description=("켜면 항목을 누를 때 그 기능이 화면 어디에 있는지 짚어 줍니다. "
                     "끄면 이름과 단축키만 조용히 보여 줍니다"),
        default=True,
    )
    focus_open_menu: bpy.props.BoolProperty(
        name="실제 메뉴를 펼친다",
        description="안내할 때 그 기능이 들어 있는 블렌더 메뉴를 실제로 펼쳐 보여 준다",
        default=True,
    )
    focus_highlight: bpy.props.BoolProperty(
        name="화면에 강조 표시를 그린다",
        description="안내할 때 그 메뉴가 있는 자리에 주황색 테두리와 쪽지를 띄운다",
        default=True,
    )
    focus_show_path: bpy.props.BoolProperty(
        name="메뉴 경로를 단계별로 보여 준다",
        description="펼친 설명에서 메뉴 경로를 1, 2, 3 으로 끊어서 보여 준다",
        default=True,
    )
    focus_duration: bpy.props.FloatProperty(
        name="강조 표시가 머무는 시간",
        description="강조 표시가 화면에 남아 있는 시간이다. 단위는 초이다",
        default=5.0, min=1.0, max=30.0, soft_max=15.0,
    )

    # ── 항목 팩 ──
    pack_dir: bpy.props.StringProperty(
        name="추가 항목 폴더",
        description=("이 폴더 안의 .json 파일을 모두 읽어서 기본 항목에 더합니다. "
                     "직접 쓴 항목이나 프로젝트별 항목을 여기에 둡니다"),
        subtype='DIR_PATH',
        default="",
        update=lambda self, context: _on_pack_dir_changed(context),
    )

    # ── 저장되는 값 (화면에는 안 보인다) ──
    favorites_json: bpy.props.StringProperty(
        name="즐겨찾기 저장소",
        description="즐겨찾기한 항목 id 목록이다. 직접 고칠 일은 없다",
        default="[]",
    )
    history_json: bpy.props.StringProperty(
        name="검색 기록 저장소",
        description="골라 본 항목과 횟수를 담아 둔다. 직접 고칠 일은 없다",
        default="[]",
    )

    def draw(self, context):
        layout = self.layout

        # ── 단축키 ──
        box = layout.box()
        box.label(text="팝업을 여는 단축키",
                  icon=popup.safe_icon('EVENT_TAB', fallback='NONE'))

        from . import keymaps as km
        why = box.column(align=True)
        why.active = False
        why.label(text=f"두 개인 까닭: 한글 입력 중에는 글자 글쇠가 듣지 않습니다.")
        why.label(text=f"{km.default_shortcut_text()} 는 영문 입력일 때, "
                       f"{km.ime_safe_shortcut_text()} 는 언제나 듣습니다.")

        _draw_keymap_ui(box, context)

        # ── 모양 ──
        box = layout.box()
        box.label(text="팝업 모양")
        col = box.column(align=True)
        col.prop(self, "popup_width")
        col.prop(self, "max_results")
        col.prop(self, "max_browse")

        # ── 동작 ──
        box = layout.box()
        box.label(text="동작")
        col = box.column(align=True)
        col.prop(self, "focus_search_on_open")
        col.prop(self, "auto_expand_first")
        col.prop(self, "use_op_index")
        sub = col.column(align=True)
        sub.active = self.use_op_index
        sub.prop(self, "max_fallback")

        col.separator()
        col.prop(self, "use_natural")
        col.prop(self, "use_similar")
        col.prop(self, "use_agent")

        from . import agent
        sub = col.column(align=True)
        sub.active = self.use_agent
        sub.prop(self, "agent_command")
        sub.prop(self, "agent_timeout")

        tool = agent.available(self)
        note = box.column(align=True)
        if not self.use_agent:
            note.active = False
            note.label(text="에이전트는 규칙으로 아무것도 못 찾았을 때만 부릅니다.")
        elif tool:
            note.active = False
            note.label(text="'물어볼 명령' 은 비워 두어도 됩니다. 알아서 찾습니다.")
            note.label(text=f"찾은 도구: {tool}")
        else:
            warn = note.column(align=True)
            warn.alert = True
            warn.label(text="물어볼 도구를 못 찾았습니다.",
                       icon=popup.safe_icon('ERROR', fallback='NONE'))
            hint = note.column(align=True)
            hint.active = False
            hint.label(text="claude 명령줄 도구를 깔면 알아서 찾습니다.")
            hint.label(text="다른 도구를 쓰려면 위에 명령을 적으십시오.")
            hint.label(text="예: claude -p {prompt}")

        col.separator()
        col.prop(self, "use_history")
        sub = col.column(align=True)
        sub.active = self.use_history
        sub.prop(self, "max_history")

        # ── 안내 모드 ──
        box = layout.box()
        head = box.row()
        head.prop(self, "learner_mode", toggle=True,
                  icon=popup.safe_icon('QUESTION', fallback='NONE'))

        col = box.column(align=True)
        col.active = self.learner_mode
        col.prop(self, "focus_open_menu")
        col.prop(self, "focus_highlight")
        sub = col.column(align=True)
        sub.active = self.learner_mode and self.focus_highlight
        sub.prop(self, "focus_duration")
        col.prop(self, "focus_show_path")

        info = box.column(align=True)
        info.active = False
        info.label(text="안내 모드를 끄면 이름과 단축키만 조용히 보여 줍니다.")
        info.label(text="블렌더는 펼친 메뉴 안의 특정 줄을 강조하지 못하므로,")
        info.label(text="강조는 메뉴가 있는 영역까지만 하고 정확한 줄은 경로 글자로 알려 줍니다.")

        # ── 항목 관리 ──
        box = layout.box()
        entries = guide_data.load_entries()
        row = box.row()
        row.label(text=f"가이드 항목 {len(entries)}개",
                  icon=popup.safe_icon('BOOKMARKS', fallback='NONE'))
        row.operator("blender_guide.reload_data",
                     icon=popup.safe_icon('FILE_REFRESH', fallback='NONE'))

        # 어느 파일에서 몇 개를 읽었는지 보여 준다.
        counts = guide_data.get_source_counts()
        if len(counts) > 1:
            detail = box.column(align=True)
            detail.active = False
            for label, count in counts.items():
                detail.label(text=f"    {label} — {count}개")

        errors = guide_data.get_load_errors()
        if errors:
            warn = box.column(align=True)
            warn.alert = True
            for label, reason in errors:
                warn.label(text=f"{label} 을(를) 읽지 못했습니다 — {reason}",
                           icon=popup.safe_icon('ERROR', fallback='NONE'))

        box.separator()
        box.prop(self, "pack_dir")

        info = box.column(align=True)
        info.active = False
        info.label(text="직접 쓴 항목은 위 폴더에 .json 으로 두면 기본 항목에 더해집니다.")
        info.label(text="같은 id 를 쓰면 기본 항목을 덮어씁니다.")
        info.label(text="기본 항목 파일 (애드온을 새로 받으면 덮입니다):")
        info.label(text=guide_data._BUILTIN_PATH)
        info.label(text="고친 뒤 위의 '항목 다시 읽기'를 누르면 블렌더를 껐다 켜지 않아도 반영됩니다.")

        favorites = load_favorites_list(self)
        if favorites:
            row = box.row()
            row.label(text=f"즐겨찾기 {len(favorites)}개")
            row.operator("blender_guide.clear_favorites",
                         icon=popup.safe_icon('X', fallback='NONE'))

        from . import history
        kept = history.load(self)
        if kept:
            row = box.row()
            row.label(text=f"검색 기록 {len(kept)}개")
            row.operator("blender_guide.clear_history",
                         icon=popup.safe_icon('X', fallback='NONE'))


def _draw_keymap_ui(layout, context) -> None:
    """설정 화면에서 단축키를 직접 바꿀 수 있게 그린다.

    블렌더 내장 모듈(rna_keymap_ui)을 쓰는데, 판에 따라 없을 수 있으므로
    실패하면 안내 문구로 대신한다.
    """
    from . import keymaps

    kc = context.window_manager.keyconfigs.user
    drawn = 0

    try:
        import rna_keymap_ui
    except Exception:
        rna_keymap_ui = None

    if rna_keymap_ui is not None and kc is not None:
        for km_name in set(keymaps.iter_registered_keymap_names()):
            km = kc.keymaps.get(km_name)
            if km is None:
                continue
            for user_kmi in km.keymap_items:
                if user_kmi.idname == "blender_guide.popup":
                    rna_keymap_ui.draw_kmi([], kc, km, user_kmi, layout, 0)
                    drawn += 1
                    break

    if drawn == 0:
        col = layout.column(align=True)
        col.active = False
        col.label(text="여기서 단축키를 바꿀 수 없습니다.")
        col.label(text="Preferences > Keymap 에서 'blender_guide' 로 찾아 바꾸세요.")

    # 같은 키를 쓰는 다른 기능이 있으면 알려 준다.
    # 왜: 키가 겹치면 두 기능이 함께 돌거나 한쪽이 안 먹히는데, 초보자는
    #     그것을 '애드온이 고장 났다'로 받아들이기 쉽다.
    try:
        conflicts = keymaps.find_conflicts(context)
    except Exception:
        conflicts = []

    if conflicts:
        warn = layout.column(align=True)
        warn.alert = True
        warn.label(text="이 단축키를 이미 쓰고 있는 기능이 있습니다:",
                   icon=popup.safe_icon('ERROR', fallback='NONE'))
        for km_name, idname, keys in conflicts[:5]:
            warn.label(text=f"    {keys} — {idname} ({km_name})")
        note = layout.column(align=True)
        note.active = False
        note.label(text="위에서 다른 키로 바꾸면 겹침이 사라집니다.")


# ── 설정 읽기 ─────────────────────────────────────────────────────────

class _FallbackPrefs:
    """설정을 못 찾았을 때 쓰는 기본값 묶음.

    왜 필요한가: 애드온이 이상하게 설치되면 설정을 못 읽는 일이 있는데,
    그때 팝업까지 같이 죽으면 무엇이 잘못됐는지 알 길이 없다. 기본값으로라도
    팝업은 떠야 한다.
    """
    popup_width = 560
    max_results = 8
    max_browse = 14
    max_fallback = 5
    auto_expand_first = True
    focus_search_on_open = True
    use_op_index = True
    use_natural = True
    use_similar = True
    use_agent = False
    agent_command = ""
    agent_timeout = 30.0
    use_history = True
    max_history = 10
    history_json = "[]"
    learner_mode = True
    focus_open_menu = True
    focus_highlight = True
    focus_show_path = True
    focus_duration = 5.0
    pack_dir = ""
    favorites_json = "[]"


_fallback = _FallbackPrefs()


def get_prefs(context):
    """이 애드온의 설정을 돌려준다. 못 찾으면 기본값 묶음을 돌려준다."""
    try:
        return context.preferences.addons[__package__].preferences
    except (KeyError, AttributeError):
        return _fallback


# ── 즐겨찾기 저장과 복원 ──────────────────────────────────────────────

def load_favorites_list(prefs_obj) -> list:
    """저장해 둔 글자를 항목 id 목록으로 되돌린다."""
    try:
        value = json.loads(prefs_obj.favorites_json)
        return [str(v) for v in value] if isinstance(value, list) else []
    except Exception:
        return []


def save_favorites(context) -> None:
    """지금 별표가 켜진 항목들을 설정에 적어 둔다."""
    p = get_prefs(context)
    if p is _fallback:
        return
    ids = [st.entry_id for st in context.window_manager.blender_guide_states
           if st.favorite]
    p.favorites_json = json.dumps(ids, ensure_ascii=False)


def restore_favorites(context) -> None:
    """설정에 적힌 즐겨찾기를 항목 상태에 되돌려 놓는다.

    애드온을 켤 때 부른다. 이때 별표를 켜면 저장 함수가 다시 불리는데,
    같은 값을 쓰는 것이라 문제가 되지 않는다.
    """
    p = get_prefs(context)
    saved = set(load_favorites_list(p))
    if not saved:
        return
    for st in context.window_manager.blender_guide_states:
        if st.entry_id in saved and not st.favorite:
            st.favorite = True


# ── 설정 화면에서 쓰는 버튼들 ─────────────────────────────────────────

class BLENDERGUIDE_OT_reload_data(bpy.types.Operator):
    """가이드 항목 파일을 다시 읽는다"""

    bl_idname = "blender_guide.reload_data"
    bl_label = "항목 다시 읽기"
    bl_options = {'REGISTER'}

    def execute(self, context):
        from . import similar
        guide_data.invalidate_caches(drop_entries=True)
        guide_data.load_entries(force=True)
        similar.invalidate()
        popup.rebuild_tag_items()
        popup.sync_states(context)

        errors = guide_data.get_load_errors()
        count = len(guide_data.load_entries())
        if errors:
            names = ", ".join(label for label, _ in errors)
            self.report({'WARNING'},
                        f"{count}개를 읽었지만 실패한 파일이 있습니다 — {names}")
            return {'FINISHED'}

        self.report({'INFO'}, f"가이드 항목 {count}개를 다시 읽었습니다.")
        return {'FINISHED'}


class BLENDERGUIDE_OT_clear_favorites(bpy.types.Operator):
    """즐겨찾기를 모두 지운다"""

    bl_idname = "blender_guide.clear_favorites"
    bl_label = "즐겨찾기 비우기"
    bl_options = {'REGISTER'}

    def execute(self, context):
        for st in context.window_manager.blender_guide_states:
            st.favorite = False
        save_favorites(context)
        self.report({'INFO'}, "즐겨찾기를 모두 지웠습니다.")
        return {'FINISHED'}


class BLENDERGUIDE_OT_clear_history(bpy.types.Operator):
    """골라 본 기록을 모두 지운다"""

    bl_idname = "blender_guide.clear_history"
    bl_label = "기록 지우기"
    bl_options = {'REGISTER'}

    def execute(self, context):
        from . import history
        count = len(history.load(get_prefs(context)))
        history.clear(context)
        self.report({'INFO'}, f"검색 기록 {count}개를 지웠습니다.")
        return {'FINISHED'}


classes = (
    BLENDERGUIDE_OT_reload_data,
    BLENDERGUIDE_OT_clear_favorites,
    BLENDERGUIDE_OT_clear_history,
    BLENDERGUIDE_AddonPreferences,
)
