# ═══════════════════════════════════════════════════════════════════════
# 한국어 가이드 UI 설명 페이지를 만든다.
#
# 하는 일: 블렌더에서 찍은 화면에서 팝업 부분만 잘라 내고, 그것을 template.html
#          안에 직접 박아 넣어 out/index.html 을 만든다.
#
# 왜 박아 넣는가: 만들어진 페이지는 아티팩트로 올라가서 개발자가 원격에서 본다.
#                그림을 따로 두면 링크가 끊겨서 아무것도 안 보인다.
#
# 쓰는 법:
#   ① 먼저 화면을 찍는다 (블렌더 창이 필요하다):
#      BL=/Applications/Blender.app/Contents/MacOS/Blender
#      GUIDE_SHOT_MODE=search $BL --factory-startup \
#          --python probe/gui_shot.py
#      GUIDE_SHOT_MODE=edit   $BL --factory-startup \
#          --python probe/gui_shot.py
#   ② 이 스크립트를 돌린다:
#      python3 docs/ui_page/build.py
# ═══════════════════════════════════════════════════════════════════════

import base64
import io
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SHOTS = os.path.join(REPO, "probe")
OUT = os.path.join(HERE, "out", "index.html")
TEMPLATE = os.path.join(HERE, "template.html")

# 팝업이 화면 어디에 떴는지를 가로·세로 비율로 적어 둔다.
# 팝업은 마우스 자리에 뜨기 때문에 찍을 때마다 조금씩 달라진다.
# 잘린 그림이 이상하면 이 값을 손본다.
CROPS = {
    "search": (0.598, 0.766, 0.981, 0.997),
    "edit":   (0.598, 0.575, 0.981, 0.997),
}


def crop_shot(name: str) -> str:
    """화면에서 팝업만 잘라 내어, HTML 에 바로 넣을 수 있는 글자로 바꾼다."""
    path = os.path.join(SHOTS, f"shot_{name}.png")
    if not os.path.exists(path):
        print(f"  화면 파일이 없습니다: {path}")
        print("  먼저 gui_shot.py 로 찍으세요. 이 절은 그림 없이 나갑니다.")
        return ""

    im = Image.open(path).convert("RGB")
    w, h = im.size
    l, t, r, b = CROPS[name]
    crop = im.crop((int(w * l), int(h * t), int(w * r), int(h * b)))

    # 페이지에 박아 넣을 것이므로 너무 크면 안 된다. 가로 1100픽셀이면 충분히 읽힌다.
    if crop.width > 1100:
        ratio = 1100 / crop.width
        crop = crop.resize((1100, int(crop.height * ratio)), Image.LANCZOS)

    buf = io.BytesIO()
    crop.save(buf, format="PNG", optimize=True)
    data = base64.b64encode(buf.getvalue()).decode("ascii")
    print(f"  {name}: {crop.width}x{crop.height} · {len(data) // 1024}KB")
    return f"data:image/png;base64,{data}"


def main() -> int:
    if not os.path.exists(TEMPLATE):
        print(f"틀 파일이 없습니다: {TEMPLATE}")
        return 1

    print("화면을 잘라 냅니다:")
    images = {name: crop_shot(name) for name in CROPS}

    html = open(TEMPLATE, encoding="utf-8").read()
    for name, uri in images.items():
        placeholder = f"{{{{SHOT_{name.upper()}}}}}"
        if placeholder not in html:
            print(f"  틀에 {placeholder} 자리가 없습니다.")
        html = html.replace(placeholder, uri)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)

    size_kb = os.path.getsize(OUT) // 1024
    print(f"\n만들었습니다: {OUT} ({size_kb}KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
