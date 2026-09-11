# ═══════════════════════════════════════════════════════════════════════
# 안내 — 기능이 블렌더 화면의 어디에 있는지 짚어 준다.
#
# 세 가지를 한꺼번에 한다:
#   ① 그 기능이 들어 있는 메뉴를 실제로 펼친다 (wm.call_menu)
#   ② 그 메뉴가 있는 영역에 강조 테두리를 그린다 (GPU 오버레이)
#   ③ 메뉴 경로를 단계별로 끊어서 보여 준다
#
# 블렌더 API 의 한계와 그에 대한 대응을 적어 둔다. 나중에 '왜 호버가 아니라
# 클릭인가'를 다시 묻지 않도록 하기 위해서이다.
#
#   - 레이아웃 요소에 마우스가 올라왔다는 사건을 받을 방법이 없다. UILayout 에는
#     hover · highlight · focus 라는 이름의 속성이 하나도 없고, 팝업이 열려 있는
#     동안에는 모달 오퍼레이터도 이벤트를 받지 못한다. 그래서 호버 대신 클릭으로
#     안내를 띄운다.
#   - 펼친 메뉴 안에서 특정 항목만 강조하는 API 는 없다. bpy.ops.ui 를 전부
#     훑어도 그런 기능이 없다. 그래서 강조는 '메뉴가 들어 있는 영역' 단위로 하고,
#     정확히 어느 항목인지는 ③의 경로 글자로 알려 준다.
#   - 화면 맨 위 막대에는 그림을 얹을 수 없다. bpy.types 에 SpaceTopBar 자체가
#     없어서 그리기 손잡이를 걸 자리가 없기 때문이다. File · Edit 메뉴는
#     3D 화면 위쪽에 화살표를 띄워서 위를 보라고 가리킨다.
# ═══════════════════════════════════════════════════════════════════════

from __future__ import annotations

import time

import bpy

# 백그라운드로 띄운 블렌더에는 그리기 모듈이 없다. 없어도 애드온 전체가
# 멈추면 안 되므로, 없으면 강조 표시만 조용히 건너뛴다.
try:
    import blf
    import gpu
    from gpu_extras.batch import batch_for_shader
except Exception:
    blf = None
    gpu = None
    batch_for_shader = None


# ── 메뉴 경로를 실제 블렌더 메뉴로 바꾸기 ─────────────────────────────

# 경로 첫 칸(예: "Object > Apply > All Transforms" 의 "Object")을 블렌더가 아는
# 메뉴 이름으로 옮긴다. 같은 이름이라도 모드에 따라 다른 메뉴이므로 모드별로 적는다.
# "*" 는 그 밖의 모든 모드에 쓰는 값이다.
_MENU_BY_HEAD = {
    "View":   {"*": "VIEW3D_MT_view"},
    "Select": {"EDIT_MESH": "VIEW3D_MT_select_edit_mesh",
               "*": "VIEW3D_MT_select_object"},
    "Add":    {"EDIT_MESH": "VIEW3D_MT_mesh_add",
               "*": "VIEW3D_MT_add"},
    "Object": {"*": "VIEW3D_MT_object"},
    "Mesh":   {"*": "VIEW3D_MT_edit_mesh"},
    "Vertex": {"*": "VIEW3D_MT_edit_mesh_vertices"},
    "Edge":   {"*": "VIEW3D_MT_edit_mesh_edges"},
    "Face":   {"*": "VIEW3D_MT_edit_mesh_faces"},
    "UV":     {"*": "VIEW3D_MT_uv_map"},
    "File":   {"*": "TOPBAR_MT_file"},
    "Edit":   {"*": "TOPBAR_MT_edit"},
}

# 이 둘은 3D 화면이 아니라 화면 맨 위 막대에 있다. 강조를 그릴 수 없는 자리이다.
_TOPBAR_HEADS = ("File", "Edit")

# 경로 첫 칸이 "면 위에서 우클릭" 처럼 한국어 설명인 항목이 있다. 우클릭 메뉴는
# 블렌더가 메뉴로 갖고 있으므로, 낱말을 보고 알아채서 그대로 펼쳐 준다.
_CONTEXT_MENUS = {
    "EDIT_MESH": "VIEW3D_MT_edit_mesh_context_menu",
    "OBJECT": "VIEW3D_MT_object_context_menu",
}


def path_steps(entry: dict) -> list:
    """항목의 메뉴 경로를 단계 목록으로 끊는다.

    "Object > Apply > All Transforms" 를 ["Object", "Apply", "All Transforms"] 로
    바꾼다. 경로 꼴이 아닌 설명문(예: "면 위에서 우클릭")이면 빈 목록을 돌려준다.
    """
    where = (entry.get("where") or "").strip()
    if ">" not in where:
        return []
    return [part.strip() for part in where.split(">") if part.strip()]


def mode_matches(entry: dict, context) -> bool:
    """이 항목이 지금 모드에서 쓰이는 것인지 본다."""
    modes = entry.get("modes") or []
    if not modes:
        return True
    return (getattr(context, "mode", "") or "") in modes


def resolve_menu(entry: dict, context) -> str:
    """이 항목을 펼쳐 보여 줄 블렌더 메뉴 이름을 돌려준다. 없으면 빈 글자이다."""
    steps = path_steps(entry)
    if not steps:
        return ""

    mode = getattr(context, "mode", "") or ""

    table = _MENU_BY_HEAD.get(steps[0])
    if not table:
        if "우클릭" in steps[0]:
            name = _CONTEXT_MENUS.get(mode, "")
            return name if name and hasattr(bpy.types, name) else ""
        return ""

    name = table.get(mode) or table.get("*", "")

    # 판이 바뀌어 메뉴가 사라졌을 수 있으므로 반드시 있는지 확인하고 돌려준다.
    return name if name and hasattr(bpy.types, name) else ""


# ── 강조 테두리를 어디에 그릴지 정하기 ────────────────────────────────

# 경로 꼴이 아닌 한국어 설명문은 낱말을 보고 자리를 짐작한다.
# 앞에 적힌 것부터 차례로 맞춰 보므로, 더 좁게 가리키는 낱말을 위에 둔다.
_KEYWORD_REGIONS = (
    (("속성 패널", "렌치", "모디파이어", "머티리얼", "빨간 공", "원뿔+공"),
     ('PROPERTIES', 'WINDOW', "오른쪽 속성 패널")),
    (("오버레이", "공 모양 아이콘", "겹친 사각형", "모드 드롭다운",
      "점·선·면", "자석", "화면 위쪽 가운데", "화면 오른쪽 위", "화면 왼쪽 위"),
     ('VIEW_3D', 'HEADER', "3D 화면 머리말")),
)


def resolve_region(entry: dict, context) -> tuple:
    """강조를 그릴 자리를 정한다. (영역 종류, 구역 종류, 사람이 읽을 자리 이름)."""
    steps = path_steps(entry)
    if steps:
        if steps[0] in _TOPBAR_HEADS:
            # 맨 위 막대에는 그릴 수 없다. 그렇다고 3D 화면에 테두리를 두르면
            # 엉뚱한 자리를 가리키는 셈이 되므로, 테두리는 걸지 않고
            # 위쪽 화살표가 붙은 쪽지로만 가리킨다.
            return ('TOPBAR', 'NONE', "화면 맨 위 막대")
        if steps[0] in _MENU_BY_HEAD:
            return ('VIEW_3D', 'HEADER', "3D 화면 머리말")

    where = entry.get("where") or ""
    for keywords, target in _KEYWORD_REGIONS:
        if any(word in where for word in keywords):
            return target

    return ('VIEW_3D', 'WINDOW', "3D 화면")


# ── 화면에 그리는 강조 표시 ───────────────────────────────────────────

# 지금 무엇을 강조하고 있는지를 담아 둔다. 그리기 손잡이는 이 값만 보고 그린다.
# 왜 전역에 두는가: 블렌더의 그리기 손잡이는 오퍼레이터가 끝난 뒤에도 계속
# 불리므로, 오퍼레이터 인스턴스에 담아 두면 그때는 이미 사라지고 없다.
_state = {
    "active": False,
    "area": 'VIEW_3D',
    "region": 'WINDOW',
    "title": "",
    "steps": [],
    "place": "",
    "where": "",
    "topbar": False,
    "started": 0.0,
    "duration": 5.0,
}

_handles: list = []

_ACCENT = (1.0, 0.62, 0.16)          # 주황. 블렌더 기본 UI 에 없는 색이라 눈에 띈다.
_FADE_SECONDS = 1.0                  # 사라지기 전 몇 초 동안 옅어지는가.


def _with_particle(word: str, has_final: str, no_final: str) -> str:
    """앞 글자의 받침에 맞춰 조사를 붙인다.

    왜 필요한가: '머리말 를 보세요' 처럼 조사가 틀리면, 한국어 안내를 만들어 놓고
    정작 그 안내가 한국어 같지 않아 보인다. 자리 이름은 설정과 항목 팩에 따라
    바뀌므로 손으로 적어 둘 수 없어서 그때그때 골라야 한다.
    """
    if not word:
        return ""
    last = word[-1]
    if '가' <= last <= '힣':
        return word + (has_final if (ord(last) - 0xAC00) % 28 else no_final)
    # 한글로 끝나지 않으면 소리를 알 수 없다. 받침 있는 쪽이 어색함이 덜하다.
    return word + has_final


def _remaining() -> float:
    return _state["started"] + _state["duration"] - time.time()


def _alpha() -> float:
    """남은 시간에 따른 진하기. 끝날 때 서서히 옅어져서 언제 사라지는지 보인다."""
    left = _remaining()
    if left <= 0.0:
        return 0.0
    return min(1.0, left / _FADE_SECONDS)


def _fill(x, y, w, h, color) -> None:
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    verts = ((x, y), (x + w, y), (x, y + h), (x + w, y + h))
    batch = batch_for_shader(shader, 'TRI_STRIP', {"pos": verts})
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def _outline(x, y, w, h, thickness, color) -> None:
    """테두리를 네 개의 채운 사각형으로 그린다.

    왜 선이 아니라 사각형인가: 선 굵기는 그래픽 카드에 따라 1픽셀로 잘려서
    강조가 거의 안 보이는 일이 있다. 사각형은 어디서나 같은 굵기로 나온다.
    """
    _fill(x, y, w, thickness, color)
    _fill(x, y + h - thickness, w, thickness, color)
    _fill(x, y, thickness, h, color)
    _fill(x + w - thickness, y, thickness, h, color)


def _triangle(points, color) -> None:
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'TRIS', {"pos": points})
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def _set_font(size: float) -> None:
    blf.size(0, size)


def _text_width(text: str) -> float:
    return blf.dimensions(0, text)[0]


def _draw_text(x, y, text, color) -> None:
    blf.color(0, *color)
    blf.position(0, x, y, 0)
    blf.draw(0, text)


def _should_draw(area_type: str, region_type: str) -> bool:
    return (_state["active"]
            and gpu is not None
            and _remaining() > 0.0
            and _state["area"] == area_type
            and _state["region"] == region_type)


def draw_frame(area_type: str, region_type: str) -> None:
    """강조 대상 구역에 테두리와 옅은 바탕색을 그린다."""
    if not _should_draw(area_type, region_type):
        return

    region = getattr(bpy.context, "region", None)
    if region is None:
        return

    alpha = _alpha()
    gpu.state.blend_set('ALPHA')
    try:
        width, height = region.width, region.height

        # 머리말처럼 낮은 구역은 옅게 칠해야 눈에 들어온다. 3D 화면처럼 넓은
        # 구역까지 칠하면 화면 전체가 주황으로 물들어서 작업을 방해한다.
        if height <= 120:
            _fill(0, 0, width, height, _ACCENT + (0.14 * alpha,))
        _outline(0, 0, width, height, 3, _ACCENT + (0.95 * alpha,))
    finally:
        gpu.state.blend_set('NONE')


def draw_callout() -> None:
    """3D 화면 위쪽에 '무엇을 어디서 찾는지' 적은 쪽지를 띄운다.

    테두리와 따로 그리는 이유: 머리말 구역은 높이가 30픽셀 남짓이라 글자를
    넣을 자리가 없다. 그래서 테두리는 머리말에, 설명은 넓은 3D 화면에 그린다.
    """
    if not _state["active"] or gpu is None or blf is None:
        return
    if _remaining() <= 0.0:
        return

    region = getattr(bpy.context, "region", None)
    if region is None:
        return

    alpha = _alpha()
    scale = getattr(bpy.context.preferences.system, "ui_scale", 1.0)

    title = _state["title"] or "가이드"
    steps = _state["steps"]
    path = "   >   ".join(f"{i}. {step}" for i, step in enumerate(steps, start=1))
    if not path:
        # 메뉴 경로가 아니라 손으로 하는 조작이면 원래 설명문을 그대로 보여 준다.
        # 자리 이름을 여기에도 쓰면 아래 줄과 똑같은 말이 두 번 나온다.
        path = _state["where"] or _state["place"]
    place = _with_particle(_state["place"], "을", "를") + " 보세요"

    pad = 14 * scale
    gap = 8 * scale
    title_size = 15 * scale
    path_size = 17 * scale
    place_size = 12 * scale

    _set_font(title_size)
    title_w = _text_width(title)
    _set_font(path_size)
    path_w = _text_width(path)
    _set_font(place_size)
    place_w = _text_width(place)

    box_w = max(title_w, path_w, place_w) + pad * 2
    line_h = (title_size + path_size + place_size) + gap * 2
    box_h = line_h + pad * 2

    x = (region.width - box_w) / 2
    # 맨 위 막대를 가리킬 때는 쪽지 위에 화살표가 붙으므로 자리를 더 비운다.
    top_gap = (48 if _state["topbar"] else 24) * scale
    y = region.height - box_h - top_gap
    # 화면이 좁아도 쪽지가 밖으로 나가지 않게 한다.
    x = max(8 * scale, x)
    y = max(8 * scale, y)

    gpu.state.blend_set('ALPHA')
    try:
        _fill(x, y, box_w, box_h, (0.05, 0.05, 0.06, 0.88 * alpha))
        _outline(x, y, box_w, box_h, 2, _ACCENT + (0.9 * alpha,))

        # 맨 위 막대를 가리켜야 하면 쪽지 위에 위쪽 화살표를 붙인다.
        if _state["topbar"]:
            cx = x + box_w / 2
            base = y + box_h + 4 * scale
            half = 16 * scale
            _triangle(((cx - half, base), (cx + half, base),
                       (cx, base + 18 * scale)), _ACCENT + (0.95 * alpha,))

        cursor = y + box_h - pad

        cursor -= title_size
        _set_font(title_size)
        _draw_text(x + pad, cursor, title, (1.0, 1.0, 1.0, 0.95 * alpha))

        cursor -= gap + path_size
        _set_font(path_size)
        _draw_text(x + pad, cursor, path, _ACCENT + (1.0 * alpha,))

        cursor -= gap + place_size
        _set_font(place_size)
        _draw_text(x + pad, cursor, place, (0.75, 0.75, 0.78, 0.9 * alpha))
    finally:
        gpu.state.blend_set('NONE')


def _draw_view3d_window() -> None:
    draw_frame('VIEW_3D', 'WINDOW')
    draw_callout()


def _draw_view3d_header() -> None:
    draw_frame('VIEW_3D', 'HEADER')


def _draw_properties_window() -> None:
    draw_frame('PROPERTIES', 'WINDOW')


# ── 강조를 켜고 끄기 ──────────────────────────────────────────────────

def _redraw_all() -> None:
    """강조가 걸릴 수 있는 화면을 다시 그리게 한다."""
    wm = getattr(bpy.context, "window_manager", None)
    if wm is None:
        return
    for window in wm.windows:
        screen = getattr(window, "screen", None)
        if screen is None:
            continue
        for area in screen.areas:
            if area.type in ('VIEW_3D', 'PROPERTIES'):
                area.tag_redraw()


def _tick() -> float | None:
    """시간이 다 되면 강조를 끈다. 그동안은 계속 다시 그리게 해서 옅어짐을 보인다."""
    if not _state["active"]:
        return None
    if _remaining() <= 0.0:
        _state["active"] = False
        _redraw_all()
        return None
    _redraw_all()
    return 0.05


def start(context, entry: dict, duration: float = 5.0) -> None:
    """항목 하나에 대한 강조 표시를 켠다."""
    area, region_type, place = resolve_region(entry, context)
    _state.update(
        active=True,
        area=area,
        region=region_type,
        title=entry.get("ko", ""),
        steps=path_steps(entry),
        place=place,
        where=(entry.get("where") or "").strip(),
        topbar=place == "화면 맨 위 막대",
        started=time.time(),
        duration=max(1.0, duration),
    )
    if not bpy.app.timers.is_registered(_tick):
        bpy.app.timers.register(_tick, first_interval=0.05)
    _redraw_all()


def stop() -> None:
    """강조를 끈다. 애드온을 끌 때도 부른다."""
    _state["active"] = False
    if bpy.app.timers.is_registered(_tick):
        try:
            bpy.app.timers.unregister(_tick)
        except Exception:
            pass
    _redraw_all()


# ── 그리기 손잡이 등록 ────────────────────────────────────────────────

_HANDLER_SPECS = (
    ('SpaceView3D', 'HEADER', _draw_view3d_header),
    ('SpaceView3D', 'WINDOW', _draw_view3d_window),
    ('SpaceProperties', 'WINDOW', _draw_properties_window),
)


def register_handlers() -> None:
    if gpu is None or _handles:
        return
    for space_name, region_type, callback in _HANDLER_SPECS:
        space = getattr(bpy.types, space_name, None)
        if space is None:
            continue
        try:
            handle = space.draw_handler_add(callback, (), region_type, 'POST_PIXEL')
        except Exception:
            # 이 판에 그 구역이 없어도 애드온 전체가 멈추면 안 된다.
            continue
        _handles.append((space, region_type, handle))


def unregister_handlers() -> None:
    for space, region_type, handle in _handles:
        try:
            space.draw_handler_remove(handle, region_type)
        except Exception:
            pass
    _handles.clear()


# ── 오퍼레이터 ────────────────────────────────────────────────────────

class BLENDERGUIDE_OT_focus(bpy.types.Operator):
    """이 기능이 블렌더 화면의 어디에 있는지 짚어 준다"""

    bl_idname = "blender_guide.focus"
    bl_label = "어디에 있는지 보기"
    bl_description = ("이 기능이 들어 있는 메뉴를 실제로 펼치고, 그 자리를 "
                      "화면에 강조해서 보여 준다")
    bl_options = {'REGISTER'}

    entry_id: bpy.props.StringProperty(name="항목 id", default="")

    def execute(self, context):
        from . import guide_data, prefs

        entry = guide_data.find_entry(self.entry_id)
        if entry is None:
            self.report({'WARNING'}, "항목을 찾지 못했습니다.")
            return {'CANCELLED'}

        p = prefs.get_prefs(context)

        if getattr(p, "focus_highlight", True):
            start(context, entry, duration=getattr(p, "focus_duration", 5.0))

        if getattr(p, "focus_open_menu", True):
            # 모드가 안 맞으면 그 메뉴 자체가 지금 화면에 없다. 그때 억지로
            # 펼치면 엉뚱한 메뉴가 뜨거나 오류가 나므로, 강조와 경로 안내만
            # 남기고 무엇을 먼저 해야 하는지 알린다.
            if not mode_matches(entry, context):
                self.report({'INFO'},
                            "지금 모드에는 그 메뉴가 없습니다. 모드를 먼저 바꾸세요.")
                return {'FINISHED'}

            menu = resolve_menu(entry, context)
            if menu:
                try:
                    bpy.ops.wm.call_menu('INVOKE_DEFAULT', name=menu)
                except Exception as exc:
                    # 메뉴를 못 펼쳐도 강조와 경로 안내는 이미 떠 있으므로,
                    # 작업을 멈추지 않고 까닭만 알린다.
                    self.report({'INFO'}, f"메뉴를 펼치지 못했습니다 ({exc}).")
            elif not path_steps(entry):
                self.report({'INFO'},
                            entry.get("where") or "메뉴가 아니라 손으로 하는 조작입니다.")

        return {'FINISHED'}


def _view3d_override(context) -> dict:
    """3D 화면을 쓰는 것처럼 문맥을 바꿔 줄 값을 찾는다.

    왜 필요한가: 팝업은 Window 키맵에 걸려 있어서 어느 화면에서나 열린다.
    그래서 모드 바꾸기를 그냥 부르면 '여기서는 못 한다'는 오류가 난다.
    """
    wm = getattr(context, "window_manager", None)
    if wm is None:
        return {}
    for window in wm.windows:
        screen = getattr(window, "screen", None)
        if screen is None:
            continue
        for area in screen.areas:
            if area.type != 'VIEW_3D':
                continue
            for region in area.regions:
                if region.type == 'WINDOW':
                    return {"window": window, "area": area, "region": region}
    return {}


class BLENDERGUIDE_OT_set_mode(bpy.types.Operator):
    """모드를 바꾼다. Tab 을 눌러도 안 바뀔 때 쓴다"""

    bl_idname = "blender_guide.set_mode"
    bl_label = "모드 바꾸기"
    bl_description = "이 기능을 쓸 수 있는 모드로 바꾼다"
    bl_options = {'REGISTER', 'UNDO'}

    mode: bpy.props.StringProperty(name="모드", default='EDIT')

    def execute(self, context):
        from . import guide_data

        obj = context.view_layer.objects.active if context.view_layer else None
        if obj is None:
            # Tab 이 안 듣는 가장 흔한 까닭이 이것이다. 고른 물체가 없으면
            # 블렌더는 어느 물체를 편집할지 몰라서 아무 일도 하지 않는다.
            self.report({'WARNING'},
                        "고른 물체가 없습니다. 물체를 먼저 누른 뒤에 다시 해 보세요.")
            return {'CANCELLED'}

        if self.mode == 'EDIT' and obj.type not in {
                'MESH', 'CURVE', 'SURFACE', 'META', 'FONT', 'ARMATURE', 'LATTICE',
                'CURVES', 'GREASEPENCIL', 'POINTCLOUD'}:
            self.report({'WARNING'},
                        f"'{obj.name}' 은(는) 편집할 수 없는 종류라서 에디트 모드가 없습니다.")
            return {'CANCELLED'}

        if not obj.select_get():
            # 활성 물체인데 고르지 않은 상태일 수 있다. 그대로 두면 편집이 안 된다.
            try:
                obj.select_set(True)
            except Exception:
                pass

        override = _view3d_override(context)
        try:
            if override:
                with context.temp_override(**override):
                    bpy.ops.object.mode_set(mode=self.mode)
            else:
                bpy.ops.object.mode_set(mode=self.mode)
        except Exception as exc:
            self.report({'WARNING'}, f"모드를 바꾸지 못했습니다 ({exc}).")
            return {'CANCELLED'}

        # 모드가 바뀌었으니 '지금 쓸 수 있는가' 판단을 다시 하게 한다.
        guide_data.invalidate_caches()
        return {'FINISHED'}


classes = (
    BLENDERGUIDE_OT_focus,
    BLENDERGUIDE_OT_set_mode,
)
