# ═══════════════════════════════════════════════════════════════════════
# 카탈로그를 만든다 — blender_guide/data/catalog_ko.json 을 새로 쓴다.
#
# 블렌더를 띄워야 돌아간다. 블렌더 판이 올라가면 다시 돌려서 새 판에 생긴
# 모디파이어·노드·설정값을 받아 온다.
#
#     /Applications/Blender.app/Contents/MacOS/Blender --background \
#         --factory-startup --python probe/build_catalog.py
#
# 무엇을 담나
#   기능이 아닌 것  모디파이어 · 제약 · 노드 · 브러시 · 도구
#   설정값          렌더 · EEVEE · 화면 · 도구 설정 · 환경 설정 · 물체 · 재질 …
#
# 한국어 이름은 블렌더에 딸려 오는 번역(.mo)을 그대로 쓴다. 블렌더를 한국어로
# 쓰는 사람이 화면에서 보는 말과 같아야 헷갈리지 않기 때문이다.
#
# 번역이 없는 것은 음차를 이름으로 삼는다. 블렌더 자신이 '섀도우', '페이스
# 오리엔테이션' 처럼 음차를 즐겨 쓰므로, 뜻으로 옮긴 말을 이름 자리에 두면
# 그것만 말투가 달라진다. 뜻으로 옮긴 말은 이름 아래에 한 줄로 밝히고
# 검색어로도 받는다. '스네이크 훅' 이라고 부르는 사람과 '길게 뽑아내기' 를
# 찾는 사람이 모두 같은 것에 닿아야 하기 때문이다.
#
# 여기에 더해, 손으로 옮긴 것에는 영어 이름을 낱말로 쪼개 블렌더가 그 낱말을
# 뭐라고 옮겼는지도 별칭으로 넣는다. 'Rip Region' 의 'Rip' 을 블렌더는
# '떼어내기' 라고 옮겼으므로, 그 말로 찾는 사람이 닿아야 한다.
# ═══════════════════════════════════════════════════════════════════════
import bpy
import gettext
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, os.pardir, "blender_guide", "data", "catalog_ko.json")


# ─── 블렌더에 번역이 없어서 손으로 옮긴 이름 ───────────────────────────
MY_KO = {
    # 지오메트리 노드
    "Bone Info": "뼈 정보",
    "Cube Grid Topology": "정육면체 격자 구조",
    "Spiral": "나선",
    "Field to List": "필드를 목록으로",
    "Get Geometry Bundle": "지오메트리 묶음 가져오기",
    "Clip Grid": "격자 잘라내기",
    "Grid Dilate & Erode": "격자 부풀리기·깎기",
    "Grid Mean": "격자 평균",
    "Grid Median": "격자 중앙값",
    "Grid to Points": "격자를 점으로",
    "ID": "고유 번호",
    "Is Face Planar": "면이 평평한지",
    "Is Spline Cyclic": "곡선이 닫혀 있는지",
    "Set Geometry Bundle": "지오메트리 묶음 넣기",
    # 컴포지터 노드
    "Mask To SDF": "마스크를 거리장으로",
    "Sequencer Strip Info": "시퀀서 스트립 정보",
    # 텍스처 노드
    "Compose": "색 합치기",
    "Decompose": "색 나누기",
    # 스컬프트 브러시
    "Draw Sharp": "날카롭게 그리기",
    "Clay": "점토",
    "Clay Strips": "점토 띠",
    "Clay Thumb": "점토 문지르기",
    "Blob": "방울처럼 부풀리기",
    "Multi-plane Scrape": "각지게 깎기",
    "Grab": "잡아 끌기",
    "Elastic Deform": "탄력 있게 늘이기",
    "Snake Hook": "길게 뽑아내기",
    "Thumb": "엄지로 밀기",
    "Nudge": "살짝 밀기",
    "Slide Relax": "미끄러뜨려 고르기",
    "Draw Face Sets": "면 묶음 칠하기",
    "Multires Displacement Eraser": "멀티레스 요철 지우개",
    "Multires Displacement Smear": "멀티레스 요철 번지기",
    # 3D 화면 도구
    "Select Box": "상자로 고르기",
    "Select Circle": "원으로 고르기",
    "Select Lasso": "올가미로 고르기",
    "Scale Cage": "상자로 크기 조절",
    "Annotate": "메모 그리기",
    "Annotate Line": "메모 직선",
    "Annotate Polygon": "메모 다각형",
    "Annotate Eraser": "메모 지우개",
    "Add Cube": "정육면체 추가",
    "Add Cone": "원뿔 추가",
    "Add Cylinder": "원기둥 추가",
    "Add UV Sphere": "구 추가 (UV 방식)",
    "Add Ico Sphere": "구 추가 (삼각형 방식)",
    "Breakdowner": "중간 포즈 만들기",
    "Relax": "포즈 누그러뜨리기",
    "Extrude to Cursor": "커서 자리까지 밀어내기",
    "Extrude Manifold": "겹치지 않게 밀어내기",
    "Extrude Along Normals": "면이 보는 쪽으로 밀어내기",
    "Extrude Individual": "면마다 따로 밀어내기",
    "Offset Edge Loop Cut": "간격을 두고 가로줄 넣기",
    "Knife": "칼로 자르기",
    "Vertex Slide": "점을 모서리 따라 밀기",
    "Rip Region": "면을 뜯어내기",
    "Rip Edge": "모서리를 뜯어내기",
    "Lasso Mask": "올가미로 가리기",
    "Line Mask": "직선으로 가리기",
    "Polyline Mask": "꺾은선으로 가리기",
    "Box Hide": "상자로 숨기기",
    "Lasso Hide": "올가미로 숨기기",
    "Line Hide": "직선으로 숨기기",
    "Polyline Hide": "꺾은선으로 숨기기",
    "Box Face Set": "상자로 면 묶기",
    "Lasso Face Set": "올가미로 면 묶기",
    "Line Face Set": "직선으로 면 묶기",
    "Polyline Face Set": "꺾은선으로 면 묶기",
    "Box Trim": "상자로 잘라내기",
    "Lasso Trim": "올가미로 잘라내기",
    "Line Trim": "직선으로 잘라내기",
    "Polyline Trim": "꺾은선으로 잘라내기",
    "Sample Weight": "웨이트 값 찍어 보기",
    "Sample Vertex Group": "버텍스 그룹 찍어 보기",
}

# ─── 뜻으로 옮긴 이름에 음차를 함께 붙인다 ─────────────────────────────
# 영어를 소리 나는 대로 읽어 찾는 사람이 많다. 뜻으로 옮긴 이름만으로는
# '스네이크 훅' 을 찾는 사람이 '길게 뽑아내기' 에 닿지 못한다.
TRANSLIT = {
    "Bone Info": "본 인포",
    "Cube Grid Topology": "큐브 그리드 토폴로지",
    "Spiral": "스파이럴",
    "Field to List": "필드 투 리스트",
    "Get Geometry Bundle": "겟 지오메트리 번들",
    "Clip Grid": "클립 그리드",
    "Grid Dilate & Erode": "그리드 다일레이트 이로드",
    "Grid Mean": "그리드 민",
    "Grid Median": "그리드 미디안",
    "Grid to Points": "그리드 투 포인트",
    "ID": "아이디",
    "Is Face Planar": "이즈 페이스 플레이너",
    "Is Spline Cyclic": "이즈 스플라인 사이클릭",
    "Set Geometry Bundle": "셋 지오메트리 번들",
    "Mask To SDF": "마스크 투 에스디에프",
    "Sequencer Strip Info": "시퀀서 스트립 인포",
    "Compose": "컴포즈",
    "Decompose": "디컴포즈",
    "Draw Sharp": "드로우 샤프",
    "Clay": "클레이",
    "Clay Strips": "클레이 스트립스",
    "Clay Thumb": "클레이 썸",
    "Blob": "블롭",
    "Multi-plane Scrape": "멀티 플레인 스크레이프",
    "Grab": "그랩",
    "Elastic Deform": "일래스틱 디폼",
    "Snake Hook": "스네이크 훅",
    "Thumb": "썸",
    "Nudge": "너지",
    "Slide Relax": "슬라이드 릴랙스",
    "Draw Face Sets": "드로우 페이스 셋",
    "Multires Displacement Eraser": "멀티레스 디스플레이스먼트 이레이저",
    "Multires Displacement Smear": "멀티레스 디스플레이스먼트 스미어",
    "Select Box": "셀렉트 박스",
    "Select Circle": "셀렉트 서클",
    "Select Lasso": "셀렉트 라쏘",
    "Scale Cage": "스케일 케이지",
    "Annotate": "어노테이트",
    "Annotate Line": "어노테이트 라인",
    "Annotate Polygon": "어노테이트 폴리곤",
    "Annotate Eraser": "어노테이트 이레이저",
    "Add Cube": "애드 큐브",
    "Add Cone": "애드 콘",
    "Add Cylinder": "애드 실린더",
    "Add UV Sphere": "애드 유브이 스피어",
    "Add Ico Sphere": "애드 아이코 스피어",
    "Breakdowner": "브레이크다우너",
    "Relax": "릴랙스",
    "Extrude to Cursor": "익스트루드 투 커서",
    "Extrude Manifold": "익스트루드 매니폴드",
    "Extrude Along Normals": "익스트루드 얼롱 노멀",
    "Extrude Individual": "익스트루드 인디비주얼",
    "Offset Edge Loop Cut": "오프셋 에지 루프 컷",
    "Knife": "나이프",
    "Vertex Slide": "버텍스 슬라이드",
    "Rip Region": "립 리전",
    "Rip Edge": "립 에지",
    "Lasso Mask": "라쏘 마스크",
    "Line Mask": "라인 마스크",
    "Polyline Mask": "폴리라인 마스크",
    "Box Hide": "박스 하이드",
    "Lasso Hide": "라쏘 하이드",
    "Line Hide": "라인 하이드",
    "Polyline Hide": "폴리라인 하이드",
    "Box Face Set": "박스 페이스 셋",
    "Lasso Face Set": "라쏘 페이스 셋",
    "Line Face Set": "라인 페이스 셋",
    "Polyline Face Set": "폴리라인 페이스 셋",
    "Box Trim": "박스 트림",
    "Lasso Trim": "라쏘 트림",
    "Line Trim": "라인 트림",
    "Polyline Trim": "폴리라인 트림",
    "Sample Weight": "샘플 웨이트",
    "Sample Vertex Group": "샘플 버텍스 그룹",
}

# 클래스 이름이 그대로 새어 들어온 것은 영어 이름도 바로잡는다.
FIX_EN = {
    "CompositorNodeGamma": "Gamma",
    "TextureNodeCompose": "Compose",
    "TextureNodeDecompose": "Decompose",
}


# ─── 설정값을 어디서 뽑고 어디서 바꾸는지 ──────────────────────────────
# (묶음 이름, bpy.types 이름, 바꾸러 가는 길)
SETTING_GROUPS = [
    ("렌더", "RenderSettings",
     "속성 패널의 카메라 뒷면 아이콘 (Render Properties)"),
    ("출력", "ImageFormatSettings",
     "속성 패널의 프린터 아이콘 (Output Properties) > Output"),
    ("EEVEE", "SceneEEVEE",
     "속성 패널의 카메라 뒷면 아이콘 (Render Properties) — 렌더 엔진이 EEVEE 일 때"),
    ("씬", "Scene", "속성 패널의 원뿔·공 아이콘 (Scene Properties)"),
    ("단위", "UnitSettings",
     "속성 패널의 원뿔·공 아이콘 (Scene Properties) > Units"),
    ("화면 오버레이", "View3DOverlay",
     "3D 화면 오른쪽 위의 Overlays 단추 (두 원이 겹친 그림) 옆 화살표"),
    ("화면 음영", "View3DShading",
     "3D 화면 오른쪽 위의 공 네 개 중 하나 옆 화살표"),
    ("3D 화면", "SpaceView3D", "3D 화면 > View 메뉴, 또는 사이드바 (N)"),
    ("도구 설정", "ToolSettings", "3D 화면 위쪽 머리글의 도구 설정"),
    ("환경 설정 · 보기", "PreferencesView",
     "Edit > Preferences > Interface"),
    ("환경 설정 · 입력", "PreferencesInput", "Edit > Preferences > Input"),
    ("환경 설정 · 시스템", "PreferencesSystem", "Edit > Preferences > System"),
    ("환경 설정 · 편집", "PreferencesEdit", "Edit > Preferences > Editing"),
    ("물체", "Object", "속성 패널의 주황 사각형 아이콘 (Object Properties)"),
    ("메시", "Mesh",
     "속성 패널의 초록 삼각형 아이콘 (Object Data Properties)"),
    ("월드", "World", "속성 패널의 지구 아이콘 (World Properties)"),
    ("카메라", "Camera",
     "카메라를 고른 뒤 속성 패널의 초록 카메라 아이콘 (Object Data Properties)"),
    ("조명", ["Light", "PointLight", "SunLight", "SpotLight", "AreaLight"],
     "조명을 고른 뒤 속성 패널의 초록 전구 아이콘 (Object Data Properties)"),
    ("심도", "CameraDOFSettings",
     "카메라를 고른 뒤 속성 패널의 초록 카메라 아이콘 > Depth of Field"),
    ("머티리얼", "Material",
     "속성 패널의 체크무늬 공 아이콘 (Material Properties)"),
]

# 어느 묶음에나 딸려 오지만 설정값이 아닌 것들. 이름만 보고 걸러 낸다.
SETTING_SKIP = {
    "Name", "Full Name", "Type", "Original", "Library", "Users", "Fake User",
    "Extra User", "Tag", "Embedded Data", "Missing Data", "Runtime Data",
    "Preview", "Override Library", "Asset Data", "Animation Data",
    "Session UID", "Library Weak Reference", "Is Evaluated", "Is Editable",
    "ID Properties",
}

# 설정값 가운데 블렌더에 번역이 없는 것. 이름만으로 뜻이 안 서는 것은
# 어느 묶음의 것인지까지 밝혀 적는다.
SETTING_KO = {
    ("RenderSettings", "fps"): "초당 프레임 수",
    ("RenderSettings", "hair_type"): "헤어 커브 모양",
    ("ImageFormatSettings", "use_jpeg2k_ycc"): "YCC 색 공간을 쓴다",
    ("SceneEEVEE", "direct_light_intensity"): "직접광 세기",
    ("SceneEEVEE", "indirect_light_intensity"): "간접광 세기",
    ("Scene", "time_jump_unit"): "시간 건너뛰기 단위",
    ("View3DOverlay", "show_performance"): "성능 표시",
    ("View3DShading", "cavity_type"): "굴곡 음영 방식",
    ("ToolSettings", "snap_anim_element"): "애니메이션 스냅 대상",
    ("ToolSettings", "snap_playhead_element"): "재생 머리 스냅 대상",
    ("PreferencesInput", "show_tablet_debug_values"): "태블릿 디버그 값 표시",
    ("PreferencesEdit", "keyframe_new_interpolation_type"):
        "새 키프레임 보간 방식",
    ("Object", "empty_image_side"): "엠프티 이미지의 보이는 면",
    ("Object", "use_mesh_mirror_x"): "X 축 대칭 편집",
    ("Object", "use_mesh_mirror_y"): "Y 축 대칭 편집",
    ("Object", "use_mesh_mirror_z"): "Z 축 대칭 편집",
    ("Mesh", "use_mirror_x"): "X 축 대칭 편집",
    ("Mesh", "use_mirror_y"): "Y 축 대칭 편집",
    ("Mesh", "use_mirror_z"): "Z 축 대칭 편집",
    ("Light", "use_temperature"): "색온도로 빛깔 정하기",
    ("Light", "use_shadow"): "그림자 켜기",
    ("Material", "preview_render_type"): "미리 보기 모양",
}

# 설정값 몇 가지에는 사람들이 실제로 쓰는 말을 덧붙인다. 블렌더 번역이
# 늘 우리 입말과 같지는 않기 때문이다.
SETTING_ALIAS = {
    ("RenderSettings", "resolution_x"): ["가로 해상도", "렌더 크기"],
    ("RenderSettings", "resolution_y"): ["세로 해상도", "렌더 크기"],
    ("RenderSettings", "fps"): ["프레임 레이트", "fps", "프레임률"],
    ("RenderSettings", "engine"): ["렌더러 바꾸기", "사이클스", "eevee"],
    ("RenderSettings", "film_transparent"): ["배경 투명하게", "알파 배경"],
    ("SceneEEVEE", "taa_render_samples"): ["샘플 수", "렌더 품질"],
    ("SceneEEVEE", "taa_samples"): ["화면 샘플 수", "미리 보기 품질"],
    ("SceneEEVEE", "use_shadows"): ["그림자 끄기", "그림자 켜기"],
    ("SceneEEVEE", "use_raytracing"): ["레이트레이싱", "반사 켜기"],
    ("Light", "use_shadow"): ["그림자 끄기", "조명 그림자"],
    ("PointLight", "energy"): ["조명 밝기", "빛 세기"],
    ("Object", "hide_render"): ["렌더에서 숨기기"],
    ("Object", "hide_viewport"): ["화면에서 숨기기"],
    ("View3DOverlay", "show_overlays"): ["오버레이 끄기", "화면 표시 끄기"],
    ("View3DOverlay", "show_wireframes"): ["와이어프레임 보기"],
    ("View3DOverlay", "show_face_orientation"): ["면 방향 보기", "노멀 뒤집힘"],
    ("View3DOverlay", "show_stats"): ["통계 보기", "폴리곤 수 보기"],
    ("SpaceView3D", "clip_start"): ["가까운 면 잘림", "클리핑"],
    ("SpaceView3D", "clip_end"): ["먼 데가 잘림", "클리핑"],
    ("SpaceView3D", "lens"): ["화면 화각", "시야각"],
    ("ToolSettings", "use_snap"): ["스냅 켜기", "자석"],
    ("ToolSettings", "use_proportional_edit"): ["비례 편집", "부드럽게 끌기"],
    ("ToolSettings", "transform_pivot_point"): ["중심점 바꾸기", "피벗"],
    ("PreferencesView", "ui_scale"): ["글씨 크기", "화면 배율"],
    ("PreferencesInput", "use_emulate_numpad"): ["넘버패드 흉내"],
    ("PreferencesSystem", "memory_cache_limit"): ["메모리 한계"],
    ("Camera", "lens"): ["초점 거리", "화각"],
    ("CameraDOFSettings", "use_dof"): ["아웃포커싱", "심도"],
    ("CameraDOFSettings", "focus_distance"): ["초점 거리", "아웃포커싱"],
    ("Material", "blend_method"): ["투명 처리 방식"],
}


# ─── 블렌더 번역 읽기 ──────────────────────────────────────────────────
_mo = os.path.join(bpy.utils.resource_path('LOCAL'), "datafiles", "locale",
                   "ko", "LC_MESSAGES", "blender.mo")
_catalog = None
if os.path.exists(_mo):
    with open(_mo, "rb") as handle:
        _catalog = gettext.GNUTranslations(handle)


def blender_ko(text: str) -> str:
    """블렌더에 딸려 온 한국어 번역을 찾는다. 없으면 빈 글자."""
    if not _catalog or not text:
        return ""
    got = _catalog.gettext(text)
    return got if got != text else ""


# 낱말을 이어 주기만 하는 말들이다. 블렌더는 이런 것까지 번역해 두어서
# 'Field to List' 가 '필드 다음으로 목록' 이 되어 버린다. 건너뛴다.
JOINERS = {"to", "of", "with", "along", "is", "a", "an", "the", "for",
           "on", "in", "by", "and", "from", "at", "as"}


def words_ko(en: str) -> str:
    """영어 이름을 낱말로 쪼개, 블렌더가 그 낱말을 뭐라고 옮겼는지 이어 붙인다.

    'Extrude Manifold' 는 통째로는 번역이 없지만 'Extrude' 는 '돌출' 이다.
    블렌더 화면에서 '돌출' 을 본 사람이 그 말로도 찾을 수 있어야 한다.
    """
    parts = []
    for word in re.split(r"[\s&/\-]+", en):
        if not word or word.lower() in JOINERS:
            continue
        got = blender_ko(word) or blender_ko(word.capitalize())
        if got and got not in parts:
            parts.append(got)
    return " ".join(parts)


def as_text(value) -> str:
    """글자가 아닌 것(함수 같은 것)이 섞여 들어오므로 걸러서 글자로 만든다."""
    return value if isinstance(value, str) else ""


items = []
my_ko_used = set()
translit_used = set()

KIND_KO = {
    "modifier": "모디파이어", "constraint": "제약",
    "geometry_node": "지오메트리 노드", "shader_node": "셰이더 노드",
    "compositor_node": "컴포지터 노드", "texture_node": "텍스처 노드",
    "brush": "브러시", "tool": "도구", "setting": "설정값",
}


def add(kind, key, en, where, desc="", aliases=None):
    en = FIX_EN.get(as_text(en), as_text(en))
    if not en:
        return
    ko = blender_ko(en)
    alias = list(aliases or [])
    gloss = ""
    if not ko:
        # 블렌더에 번역이 없다. 음차를 이름으로 삼고, 뜻으로 옮긴 말은
        # 이름 아래에 밝히면서 검색어로도 받는다.
        meaning = MY_KO.get(en, "")
        if meaning:
            my_ko_used.add(en)
        sound = TRANSLIT.get(en, "")
        if sound:
            translit_used.add(en)
            ko = sound
            gloss = meaning
            if meaning:
                alias.append(meaning)
            joined = sound.replace(" ", "")
            if joined != sound:
                alias.append(joined)
        else:
            ko = meaning
        # 블렌더가 낱말 단위로는 뭐라고 옮겼는지도 함께 받는다.
        by_word = words_ko(en)
        if by_word and by_word not in alias:
            alias.append(by_word)
    note = as_text(desc)
    note = blender_ko(note) or note
    made = {
        "kind": kind, "kind_ko": KIND_KO.get(kind, kind),
        "key": as_text(key) or en, "ko": ko or en, "en": en,
        "aliases": alias, "where": where, "note": note[:200],
    }
    if gloss:
        made["gloss"] = gloss
    items.append(made)


# ─── 기능이 아닌 것 ────────────────────────────────────────────────────
seen = set()
for i in bpy.types.Modifier.bl_rna.properties["type"].enum_items:
    # 그리스 펜슬용과 메시용이 같은 이름을 쓰는 것이 아홉 가지 있다.
    # 두 줄로 나오면 고르는 사람만 헷갈리므로 먼저 나온 것만 남긴다.
    if i.name in seen:
        continue
    seen.add(i.name)
    add("modifier", i.identifier, i.name,
        "속성 패널의 파란 렌치 아이콘 > Add Modifier", i.description)

for i in bpy.types.Constraint.bl_rna.properties["type"].enum_items:
    add("constraint", i.identifier, i.name,
        "속성 패널의 뼈와 사슬 아이콘 > Add Object Constraint", i.description)

NODE_WHERE = {
    "ShaderNode": ("shader_node", "Shading 작업 공간 > Add"),
    "GeometryNode": ("geometry_node", "Geometry Nodes 작업 공간 > Add"),
    "CompositorNode": ("compositor_node", "Compositing 작업 공간 > Add"),
    "TextureNode": ("texture_node", "텍스처 노드 편집기 > Add"),
}
for prefix, (kind, where) in NODE_WHERE.items():
    seen = set()
    for name in dir(bpy.types):
        if not name.startswith(prefix) or name == prefix:
            continue
        if name.endswith(("Socket", "Tree", "Item", "Items")):
            continue
        try:
            rna = getattr(bpy.types, name).bl_rna
        except Exception:
            continue
        label = rna.name or name
        if label in seen:
            continue
        seen.add(label)
        add(kind, name, label, where, rna.description or "")

for prop in ("sculpt_brush_type", "sculpt_tool"):
    try:
        for i in bpy.types.Brush.bl_rna.properties[prop].enum_items:
            add("brush", i.identifier, i.name,
                "스컬프트 모드 > 왼쪽 도구 막대", i.description)
        break
    except Exception:
        continue

try:
    from bl_ui.space_toolsystem_common import ToolSelectPanelHelper
    cls = ToolSelectPanelHelper._tool_class_from_space_type("VIEW_3D")
    seen = set()
    for mode, group in (cls.tools_all() if cls else []):
        for item in (group or []):
            for t in (item if isinstance(item, (list, tuple)) else [item]):
                if t is None or not getattr(t, "label", None):
                    continue
                if t.label in seen:
                    continue
                seen.add(t.label)
                add("tool", t.idname or t.label, t.label,
                    "3D 화면 왼쪽 도구 막대", getattr(t, "description", "") or "")
except Exception as exc:
    print("도구 뽑기 실패:", exc)

n_thing = len(items)


# ─── 설정값 ────────────────────────────────────────────────────────────
alias_used = set()
setting_ko_used = set()

for label, type_names, where in SETTING_GROUPS:
    if isinstance(type_names, str):
        type_names = [type_names]
    props = []
    seen_id = set()
    seen_name = set()
    for type_name in type_names:
        rna = getattr(bpy.types, type_name, None)
        if rna is None:
            print(f"설정 묶음 없음: {type_name}")
            continue
        for prop in rna.bl_rna.properties:
            # 조명처럼 종류가 여럿인 묶음은 같은 설정이 되풀이된다.
            if prop.identifier in seen_id:
                continue
            seen_id.add(prop.identifier)
            # 이름까지 같은 것도 있다. use_stamp_frame 과
            # use_stamp_frame_range 가 둘 다 'Stamp Frame' 이다. 화면에
            # 똑같은 줄이 두 개 뜨면 고르는 사람만 헷갈린다.
            if prop.name in seen_name:
                continue
            seen_name.add(prop.name)
            props.append((type_name, prop))
    for type_name, prop in props:
        if prop.identifier == "rna_type" or prop.is_hidden or prop.is_readonly:
            continue
        if prop.type in {"POINTER", "COLLECTION"}:
            continue
        if not prop.name or prop.name in SETTING_SKIP:
            continue
        pair = (type_name, prop.identifier)
        # 이름을 안 붙여 둔 설정이 몇 개 있다. Light 의 use_shadow 가 그렇다.
        # 속기명이 그대로 화면에 나오면 읽기 어려우니 낱말로 풀어 준다.
        en = prop.name
        if en.islower() and "_" in en:
            en = " ".join(w.capitalize() for w in en.split("_"))
        ko = blender_ko(prop.name)
        if not ko:
            ko = SETTING_KO.get(pair, "")
            if ko:
                setting_ko_used.add(pair)
        alias = list(SETTING_ALIAS.get(pair, []))
        if alias:
            alias_used.add(pair)
        if not blender_ko(prop.name):
            # 이름째로는 번역이 없다. 낱말 단위로라도 블렌더가 옮긴 말을
            # 받아 둔다. 'Use Shadow' 의 'Shadow' 는 '그림자' 이다.
            by_word = words_ko(en)
            if by_word and by_word not in alias:
                alias.append(by_word)
        # 속성 이름 자체로도 찾게 한다. 다만 한 낱말짜리는 넣지 않는다.
        # 'color' 같은 흔한 말이 별칭이 되면 엉뚱한 것이 먼저 잡힌다.
        if "_" in prop.identifier:
            alias.append(prop.identifier)
        note = blender_ko(prop.description) or prop.description or ""
        items.append({
            "kind": "setting", "kind_ko": "설정값", "group": label,
            "key": f"{type_name}.{prop.identifier}",
            "ko": ko or en, "en": en,
            "aliases": alias, "where": where,
            "note": note[:200],
        })

n_setting = len(items) - n_thing


# ─── 적어 두고 쓰이지 않은 것을 알린다 ─────────────────────────────────
for name, table, used in (("MY_KO", MY_KO, my_ko_used),
                          ("TRANSLIT", TRANSLIT, translit_used)):
    left = set(table) - used
    if left:
        print(f"⚠️ {name} 에 적었지만 쓰이지 않은 이름 {len(left)}개: "
              + ", ".join(sorted(left)[:8]))
for name, table, used in (("SETTING_KO", SETTING_KO, setting_ko_used),
                          ("SETTING_ALIAS", SETTING_ALIAS, alias_used)):
    left = set(table) - used
    if left:
        print(f"⚠️ {name} 에 적었지만 쓰이지 않은 것 {len(left)}개: "
              + ", ".join(f"{a}.{b}" for a, b in sorted(left)))

missing = [i for i in items if not blender_ko(i["en"]) and i["ko"] == i["en"]]
if missing:
    print(f"⚠️ 한국어 이름이 없는 항목 {len(missing)}개: "
          + ", ".join(i["en"] for i in missing[:12]))

# 블렌더에서 그대로 가져온 말이 섞여 있다는 것을 데이터 파일 자신이 들고 있게 한다.
# 왜: 이 json 만 따로 퍼져 나가도 어디서 온 말인지 함께 따라가야 하기 때문이다.
NOTICE = ("이 파일의 ko 이름과 note 설명은 블렌더 프로젝트에 딸려 오는 한국어 번역과, "
          "블렌더가 각 설정에 붙여 둔 설명을 그대로 가져온 것이다. 그 부분의 저작권은 "
          "블렌더 재단과 블렌더 번역에 참여한 사람들에게 있으며, 블렌더 프로젝트의 GPL 을 "
          "따른다. https://projects.blender.org/blender/blender")

with open(OUT, "w", encoding="utf-8") as handle:
    json.dump({"schema_version": 1, "notice": NOTICE, "catalog": items}, handle,
              ensure_ascii=False, indent=1)

from collections import Counter
print(f"\n담은 것 {len(items):,}개 → {os.path.normpath(OUT)}")
for k, n in Counter(i["kind_ko"] for i in items).most_common():
    print(f"  {k:<16} {n:>4}개")
print(f"  기능이 아닌 것 {n_thing}개 · 설정값 {n_setting}개")
print(f"  음차를 붙인 항목 {len(translit_used)}개")
