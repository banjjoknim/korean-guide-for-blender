# ═══════════════════════════════════════════════════════════════════════
# 자료 — 가이드 항목을 읽어 오고, 블렌더에게 현재 사정을 물어본다.
#
# 책임 셋:
#   ① guide_ko.json 을 읽어 항목 목록을 만든다.
#   ② 각 기능의 단축키를 블렌더의 키맵에서 직접 읽는다.
#   ③ 지금 이 순간 그 기능을 쓸 수 있는지 블렌더에게 물어본다(poll).
#
# 핵심 패턴: 손으로 적은 값보다 블렌더에게 물어본 값을 앞세운다.
# 왜: 사용자가 단축키를 바꿔 놓았거나 블렌더 판이 올라가면 손으로 적은 값은
#     틀린 값이 된다. 틀린 단축키를 알려 주는 가이드는 없느니만 못하다.
#     물어봐서 못 얻었을 때만 손으로 적어 둔 값으로 물러난다(폴백).
# ═══════════════════════════════════════════════════════════════════════

from __future__ import annotations

import json
import os
import sys

import bpy

# ── 가이드 항목 ───────────────────────────────────────────────────────
#
# 항목은 파일 하나가 아니라 여러 파일에서 모은다.
#   ① 애드온에 들어 있는 기본 파일 (data/guide_ko.json)
#   ② 설정에서 지정한 폴더 안의 모든 .json 파일 ("팩")
#
# 왜 나누는가: 직접 더한 항목을 기본 파일에 적으면 애드온을 새 판으로 바꿀 때
# 통째로 덮여서 사라진다. 팩으로 따로 두면 애드온과 따로 산다.
# 프로젝트마다 다른 항목(그 프로젝트의 폴더 구조나 규칙)을 그 저장소에 두고
# 쓸 수도 있다.

BUILTIN_LABEL = "기본"

_BUILTIN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "data", "guide_ko.json")

_entries: list | None = None
_load_errors: list = []
_source_counts: dict = {}


def _read_entry_file(path: str):
    """항목 파일 하나를 읽는다. (항목 목록, 실패 사유) 를 돌려준다."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"

    entries = data.get("entries")
    if not isinstance(entries, list):
        return [], "entries 목록이 들어 있지 않습니다"
    return entries, None


def get_pack_dir() -> str:
    """설정에 적어 둔 팩 폴더의 실제 경로를 돌려준다. 없으면 빈 글자를 준다."""
    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
        raw = prefs.pack_dir
    except (KeyError, AttributeError):
        return ""
    if not raw:
        return ""
    try:
        # 블렌더는 '//' 로 시작하는 상대 경로를 쓸 수 있으므로 실제 경로로 편다.
        return bpy.path.abspath(raw)
    except Exception:
        return raw


def _collect_sources() -> list:
    """읽을 파일들을 순서대로 모은다. 뒤에 오는 것이 앞의 것을 덮는다."""
    sources = [(BUILTIN_LABEL, _BUILTIN_PATH)]

    pack_dir = get_pack_dir()
    if pack_dir and os.path.isdir(pack_dir):
        try:
            names = sorted(os.listdir(pack_dir))
        except OSError:
            names = []
        for name in names:
            if name.lower().endswith(".json"):
                sources.append((name, os.path.join(pack_dir, name)))
    return sources


def load_entries(force: bool = False) -> list:
    """모든 항목 파일을 읽어 하나로 합친다. 한 번 읽으면 기억해 두고 다시 읽지 않는다.

    같은 id 가 여러 파일에 있으면 나중에 읽은 팩이 이긴다.
    그래야 기본 항목의 설명을 자기 식으로 고쳐 쓸 수 있다.

    force 를 참으로 주면 파일을 다시 읽는다. 항목을 고치고 블렌더를 껐다 켜지
    않고 확인할 때 쓴다.
    """
    global _entries, _load_errors, _source_counts
    if _entries is not None and not force:
        return _entries

    merged: dict = {}
    errors: list = []
    counts: dict = {}

    for label, path in _collect_sources():
        entries, error = _read_entry_file(path)
        if error:
            errors.append((label, error))
            continue
        count = 0
        for entry in entries:
            entry_id = entry.get("id")
            if not entry_id:
                continue
            # 어느 파일에서 왔는지 적어 둔다. 설정 화면에서 보여 준다.
            entry["_source"] = label
            # 앞서 만들어 둔 검색용 임시 값이 남아 있으면 버린다.
            entry.pop("_search_cache", None)
            merged[entry_id] = entry
            count += 1
        counts[label] = count

    _entries = list(merged.values())
    _load_errors = errors
    _source_counts = counts
    return _entries


def get_load_errors() -> list:
    """읽다가 실패한 파일들을 (이름, 사유) 목록으로 돌려준다."""
    return _load_errors


def get_source_counts() -> dict:
    """어느 파일에서 몇 개를 읽었는지 돌려준다."""
    return _source_counts


def find_entry(entry_id: str) -> dict | None:
    """id 로 항목 하나를 찾는다."""
    for e in load_entries():
        if e.get("id") == entry_id:
            return e
    return None


# ── 단축키 조회 ───────────────────────────────────────────────────────

_shortcut_map: dict | None = None

# 어느 키맵을 먼저 믿을지 정한다. 앞에 있을수록 우선한다.
# '3D View' 안의 설정이 전역 설정보다 실제 상황에 가깝기 때문에 앞에 둔다.
_KEYMAP_PRIORITY = (
    "Mesh", "Object Mode", "Object Non-modal", "3D View",
    "3D View Generic", "Window", "Screen",
)


def _keymap_rank(keymap_name: str) -> int:
    """키맵 이름의 우선순위를 숫자로 돌려준다. 작을수록 먼저 쓴다."""
    try:
        return _KEYMAP_PRIORITY.index(keymap_name)
    except ValueError:
        return len(_KEYMAP_PRIORITY)


def build_shortcut_map(force: bool = False) -> dict:
    """블렌더의 키맵 전체를 훑어서 '기능 이름 -> 단축키 글자'로 만든다.

    사용자 설정(user)을 먼저 보고, 없으면 기본 설정(default)을 본다.
    사용자가 단축키를 바꿔 놓았다면 바꾼 쪽이 보여야 하기 때문이다.
    """
    global _shortcut_map
    if _shortcut_map is not None and not force:
        return _shortcut_map

    found: dict = {}
    try:
        kcs = bpy.context.window_manager.keyconfigs
        # 사용자 설정을 먼저 넣어야 나중에 오는 기본 설정에 덮이지 않는다.
        for kc in (kcs.user, kcs.addon, kcs.default):
            if kc is None:
                continue
            for km in kc.keymaps:
                rank = _keymap_rank(km.name)
                for kmi in km.keymap_items:
                    idname = kmi.idname
                    if not idname or not kmi.active:
                        continue
                    try:
                        keys = kmi.to_string()
                    except Exception:
                        continue
                    if not keys:
                        continue
                    mods = _modifier_count(kmi)
                    prev = found.get(idname)
                    # 우선순위가 더 높은 키맵을 먼저 쓰고, 같은 키맵 안에서는
                    # 수식키(Ctrl·Shift·Alt)가 적은 것을 고른다.
                    # 왜: 한 기능에 단축키가 여럿 걸려 있을 때, 초보자가 배워야 할
                    #     기본 키는 수식키가 없는 쪽이다. 실제로 '선택한 것을 화면
                    #     가운데로'가 'Numpad .' 대신 'Cmd+Numpad .' 로 나온 적이 있다.
                    if prev is None or (rank, mods) < (prev[1], prev[2]):
                        found[idname] = (keys, rank, mods)
    except Exception:
        # 키맵을 못 읽어도 애드온 전체가 멈추면 안 된다. 손으로 적은 값으로 간다.
        found = {}

    _shortcut_map = {k: v[0] for k, v in found.items()}
    return _shortcut_map


def _modifier_count(kmi) -> int:
    """그 단축키가 함께 누르는 수식키가 몇 개인지 센다."""
    count = 0
    for attr in ("ctrl", "shift", "alt", "oskey"):
        try:
            if getattr(kmi, attr):
                count += 1
        except Exception:
            pass
    return count


IS_MAC = sys.platform == "darwin"


def fit_platform(text: str, is_mac: bool | None = None) -> str:
    """손으로 적어 둔 단축키를 이 기기의 표기로 바꾼다.

    항목 파일의 예비 값은 맥 기준으로 적혀 있다. 맥이 아닌 기기에서 'Cmd+B' 를
    그대로 보여 주면 없는 글쇠를 누르라는 말이 된다. 블렌더에서 직접 읽은 값은
    이미 그 기기의 것이므로 손대지 않는다.
    """
    if is_mac is None:
        is_mac = IS_MAC
    if is_mac or not text:
        return text
    for mac, other in (("Cmd+", "Ctrl+"), ("⌘", "Ctrl+"),
                       ("Option+", "Alt+"), ("⌥", "Alt+")):
        text = text.replace(mac, other)
    return text


def get_shortcut(entry: dict) -> tuple[str, bool]:
    """항목의 단축키를 돌려준다.

    돌려주는 값은 (단축키 글자, 블렌더에서 직접 읽었는지) 두 개짜리이다.
    두 번째 값이 거짓이면 손으로 적어 둔 값이라는 뜻이므로, 화면에 옅게 표시한다.
    """
    manual = entry.get("shortcut")

    # 마우스를 끄는 조작처럼, 블렌더가 알려 주는 글자가 오히려 알아보기 어려운
    # 항목이 있다. 그런 항목은 JSON 에 prefer_manual 을 켜 두고 손으로 적은 값을 쓴다.
    # 왜: '시점 돌리기'의 자동 조회 값이 'Mouse/Trackpad Rotate' 로 나왔는데,
    #     이것으로는 무엇을 눌러야 하는지 알 수 없다. 실제 화면에서 보고 잡은 흠이다.
    if entry.get("prefer_manual") and manual:
        return fit_platform(manual), False

    op = entry.get("op")
    if op:
        auto = build_shortcut_map().get(op)
        if auto:
            return auto, True
    if manual:
        return fit_platform(manual), False
    return "", False


# ── 지금 쓸 수 있는지 물어보기 ────────────────────────────────────────

_availability_cache: dict = {}
_availability_mode: str | None = None


def _op_callable(op_idname: str):
    """'mesh.subdivide' 같은 글자를 실제 오퍼레이터 객체로 바꾼다. 없으면 None."""
    module_name, _, op_name = op_idname.partition(".")
    if not module_name or not op_name:
        return None
    try:
        module = getattr(bpy.ops, module_name)
        return getattr(module, op_name)
    except AttributeError:
        return None


def op_exists(op_idname: str | None) -> bool:
    """그 기능이 이 블렌더 판에 실제로 있는지 본다.

    판이 올라가면서 사라진 기능을 버튼으로 그리면 블렌더가 오류를 내므로,
    버튼을 그리기 전에 반드시 확인한다.
    """
    if not op_idname:
        return False
    return _op_callable(op_idname) is not None


def get_availability(context) -> dict:
    """모든 항목에 대해 '지금 쓸 수 있는지'를 한 번에 계산한다.

    모드가 바뀌지 않았으면 앞서 계산한 값을 다시 쓴다.
    왜: 팝업을 그리는 함수는 마우스가 움직일 때마다 다시 불리는데, 그때마다
        61개 기능에 일일이 물어보면 팝업이 버벅인다.
    """
    global _availability_cache, _availability_mode

    mode = getattr(context, "mode", "") or ""
    if mode == _availability_mode and _availability_cache:
        return _availability_cache

    result = {}
    for entry in load_entries():
        result[entry.get("id")] = _check_available(entry, mode)

    _availability_cache = result
    _availability_mode = mode
    return result


def _check_available(entry: dict, mode: str) -> bool:
    """항목 하나가 지금 쓸 수 있는 상태인지 판단한다.

    순서가 중요하다. modes 를 먼저 보고, 거기를 통과한 것만 poll 로 더 따진다.

    왜 이 순서인가: poll 은 '지금 당장 되는가'가 아니라 '부를 수 있는 상태인가'를
    답하는 경우가 있다. 실제로 mesh.separate(하나를 여러 물체로 쪼개기)는
    에디트 모드 전용인데도 오브젝트 모드에서 poll 이 참을 돌려주어서,
    오브젝트 모드 추천 목록에 잘못 끼어들었다. 화면에서 눈으로 보고 잡은 흠이다.
    그래서 사람이 적어 둔 modes 를 최소 조건으로 두고, poll 은 그 위에 얹는다.
    """
    modes = entry.get("modes") or []
    if modes and mode not in modes:
        return False

    op_idname = entry.get("op")
    if op_idname:
        op = _op_callable(op_idname)
        if op is not None:
            try:
                return bool(op.poll())
            except Exception:
                # poll 이 상황을 못 읽어 오류를 내는 경우가 있다.
                # 모드는 이미 맞다는 것을 확인했으므로 쓸 수 있다고 본다.
                pass

    return True


def invalidate_caches(drop_entries: bool = False) -> None:
    """기억해 둔 값을 버린다.

    drop_entries 를 참으로 주면 항목 목록까지 버려서 다음에 파일을 다시 읽게 한다.
    팩 폴더를 바꿨을 때 쓴다.
    """
    global _shortcut_map, _availability_cache, _availability_mode, _entries
    _shortcut_map = None
    _availability_cache = {}
    _availability_mode = None
    if drop_entries:
        _entries = None


# ── 블렌더에 등록된 기능 전체를 훑어 만드는 보조 색인 ─────────────────

_op_index: list | None = None


# ── 블렌더가 가진 한국어 번역 ─────────────────────────────────────────

_ko_catalog = None


def load_blender_korean():
    """블렌더에 딸려 오는 한국어 번역을 읽는다. 없으면 None 이다.

    왜 번역 파일을 직접 읽는가: bpy.app.translations.pgettext 는 사용자가 지금
    쓰는 언어로만 번역한다. 영어로 쓰는 사람에게는 영어가 돌아온다. 그렇다고
    설정의 언어를 잠깐 바꾸면, 저장 설정이 켜져 있을 때 사용자의 화면 언어가
    한국어로 바뀌어 버린다. 실제로 저장 설정이 켜져 있는 것을 확인했다.

    번역 파일은 파이썬 기본 기능으로 그냥 읽을 수 있다. 설정을 건드리지 않고,
    사용자가 무슨 언어로 쓰든 한국어 이름을 꺼낼 수 있다.
    """
    global _ko_catalog
    if _ko_catalog is not None:
        return _ko_catalog or None

    import gettext

    try:
        root = bpy.utils.resource_path('LOCAL')
    except Exception:
        _ko_catalog = False
        return None

    path = os.path.join(root, "datafiles", "locale", "ko",
                        "LC_MESSAGES", "blender.mo")
    if not os.path.exists(path):
        _ko_catalog = False
        return None

    try:
        with open(path, "rb") as handle:
            _ko_catalog = gettext.GNUTranslations(handle)
    except Exception:
        _ko_catalog = False
        return None
    return _ko_catalog


def to_korean(text: str) -> str:
    """블렌더가 아는 한국어 이름을 돌려준다. 모르면 원래 글자를 그대로 준다."""
    if not text:
        return ""
    catalog = load_blender_korean()
    if catalog is None:
        return text
    return catalog.gettext(text)


def build_op_index(force: bool = False) -> list:
    """블렌더에 등록된 기능 전부(2천 개가 넘는다)를 훑어서 색인을 만든다.

    한국어 항목에서 아무것도 못 찾았을 때만 쓰는 예비 수단이다. 설명이 영어라서
    초보자에게 바로 도움이 되지는 않지만, 적어도 '그런 기능이 있기는 하다'와
    '메뉴에서 어떤 영어 이름을 찾아야 한다'를 알려 줄 수 있다.

    시간이 걸리므로 처음 필요해진 순간에 한 번만 만든다.
    """
    global _op_index
    if _op_index is not None and not force:
        return _op_index

    index = []
    known_ops = {e.get("op") for e in load_entries() if e.get("op")}

    for module_name in dir(bpy.ops):
        if module_name.startswith("_"):
            continue
        try:
            module = getattr(bpy.ops, module_name)
        except Exception:
            continue
        for op_name in dir(module):
            if op_name.startswith("_"):
                continue
            idname = f"{module_name}.{op_name}"
            if idname in known_ops:
                continue   # 한국어 항목에 이미 있는 것은 넣지 않는다.
            try:
                rna = getattr(module, op_name).get_rna_type()
                label = rna.name or op_name
                desc = rna.description or ""
            except Exception:
                continue
            # 블렌더가 아는 한국어 이름이 있으면 함께 담는다. 한국어로 쳐도
            # 걸리게 하려는 것이다. 2,459개 가운데 406개에 번역이 있다.
            ko_label = to_korean(label)
            ko_desc = to_korean(desc)
            index.append({
                "idname": idname,
                "label": label,
                "desc": desc,
                "ko": ko_label if ko_label != label else "",
                "ko_desc": ko_desc if ko_desc != desc else "",
                # 검색에 쓸 비교용 한 덩어리이다. 미리 만들어 둔다.
                "hay": " ".join((idname, label, desc, ko_label, ko_desc)).lower(),
            })

    _op_index = index
    return _op_index


def search_op_index(query: str, limit: int = 6) -> list:
    """보조 색인에서 영어로 찾는다. 한글 검색어는 여기서 걸리지 않는다."""
    q = query.strip().lower()
    if len(q) < 2:
        return []
    hits = []
    for item in build_op_index():
        pos = item["hay"].find(q)
        if pos < 0:
            continue
        # 이름(label)에 걸린 것을 설명문에 걸린 것보다 위에 둔다.
        rank = 0 if q in item["label"].lower() else 1
        hits.append((rank, pos, item))
    hits.sort(key=lambda t: (t[0], t[1], len(t[2]["label"])))
    return [item for _, _, item in hits[:limit]]


def op_index_ready() -> bool:
    """보조 색인이 이미 만들어져 있는지 본다. 팝업에서 안내 문구를 고를 때 쓴다."""
    return _op_index is not None
