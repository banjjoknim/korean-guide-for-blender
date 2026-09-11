# 팝업을 여는 단축키로 쓸 수 있는, 겹치지 않는 조합을 실제로 찾는다.
import bpy, json, os, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "probe", "free_keys.json")

# 어디서 눌러도 팝업이 떠야 하므로, 널리 듣는 키맵들을 모두 살핀다.
WATCHED = {'Window', 'Screen', 'Screen Editing', '3D View', '3D View Generic',
           'Object Mode', 'Object Non-modal', 'Mesh', 'Frames', 'User Interface'}

def collect_used():
    used = {}
    kc = bpy.context.window_manager.keyconfigs.user
    for km in kc.keymaps:
        if km.name not in WATCHED:
            continue
        for kmi in km.keymap_items:
            if not kmi.active:
                continue
            try:
                sig = (kmi.type, kmi.ctrl, kmi.shift, kmi.alt, kmi.oskey)
            except Exception:
                continue
            used.setdefault(sig, []).append((km.name, kmi.idname))
    return used

def run():
    used = collect_used()
    # 기억하기 쉬운 후보들이다. G 는 Guide, H 는 Help 를 떠올리게 한다.
    candidates = []
    for key in ('G', 'H', 'Y', 'J', 'SLASH', 'SEMI_COLON', 'F1', 'F2', 'F4'):
        for ctrl, shift, alt, oskey in (
            (True, True, False, False),
            (False, True, True, False),
            (True, False, True, False),
            (False, False, True, False),
            (True, True, True, False),
        ):
            sig = (key, ctrl, shift, alt, oskey)
            mods = []
            if ctrl: mods.append("Ctrl")
            if shift: mods.append("Shift")
            if alt: mods.append("Alt")
            label = "+".join(mods + [key])
            candidates.append({
                "key": key, "ctrl": ctrl, "shift": shift, "alt": alt,
                "label": label,
                "used_by": used.get(sig, []),
                "free": sig not in used,
            })
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"candidates": candidates,
                   "watched_keymaps": sorted(WATCHED)}, f,
                  ensure_ascii=False, indent=1)
    bpy.ops.wm.quit_blender()
    return None

bpy.app.timers.register(run, first_interval=3.0)
