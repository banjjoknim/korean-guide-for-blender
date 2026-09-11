#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# 블렌더 가이드 애드온을 블렌더에 연결한다.
#
# 복사하지 않고 심볼릭 링크(바로가기)를 건다.
# 왜: 저장소에서 파일을 고치면 블렌더 쪽에 바로 반영된다. 복사해 두면
#     고칠 때마다 다시 복사해야 하고, 어느 쪽이 최신인지 헷갈린다.
#
# 쓰는 법:
#   ./install.sh           연결한다
#   ./install.sh --remove  연결을 끊는다
# ═══════════════════════════════════════════════════════════════════════
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$REPO_ROOT/blender_guide"
ADDON_NAME="blender_guide"

BLENDER_APP="/Applications/Blender.app/Contents/MacOS/Blender"
if [[ ! -x "$BLENDER_APP" ]]; then
  echo "블렌더를 찾지 못했습니다: $BLENDER_APP" >&2
  echo "다른 자리에 설치했다면 BLENDER_APP 환경변수로 알려 주세요." >&2
  exit 1
fi
BLENDER_APP="${BLENDER_APP_OVERRIDE:-$BLENDER_APP}"

# 애드온 폴더는 블렌더에게 직접 물어본다.
# 왜: 블렌더 판이 올라가면 폴더 이름이 바뀌는데, 손으로 적어 두면 그때 깨진다.
ADDON_ROOT="$("$BLENDER_APP" --background --factory-startup --python-expr \
  'import bpy,sys; sys.stdout.write("PATH>>>" + bpy.utils.user_resource("SCRIPTS", path="addons", create=True) + "<<<")' \
  2>/dev/null | sed -n 's/.*PATH>>>\(.*\)<<<.*/\1/p')"

if [[ -z "$ADDON_ROOT" ]]; then
  echo "블렌더의 애드온 폴더를 알아내지 못했습니다." >&2
  exit 1
fi

TARGET="$ADDON_ROOT/$ADDON_NAME"

if [[ "${1:-}" == "--remove" ]]; then
  if [[ -L "$TARGET" ]]; then
    rm "$TARGET"
    echo "연결을 끊었습니다: $TARGET"
  elif [[ -e "$TARGET" ]]; then
    echo "그 자리에 있는 것은 바로가기가 아니라 실제 폴더입니다." >&2
    echo "직접 확인한 뒤 지워 주세요: $TARGET" >&2
    exit 1
  else
    echo "연결되어 있지 않습니다."
  fi
  exit 0
fi

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "애드온 원본을 찾지 못했습니다: $SOURCE_DIR" >&2
  exit 1
fi

if [[ -L "$TARGET" ]]; then
  CURRENT="$(readlink "$TARGET")"
  if [[ "$CURRENT" == "$SOURCE_DIR" ]]; then
    echo "이미 연결되어 있습니다: $TARGET"
    exit 0
  fi
  echo "다른 곳을 가리키는 바로가기를 바꿉니다 (이전: $CURRENT)"
  rm "$TARGET"
elif [[ -e "$TARGET" ]]; then
  echo "그 자리에 이미 실제 폴더가 있습니다: $TARGET" >&2
  echo "덮어쓰지 않겠습니다. 직접 확인한 뒤 옮기거나 지워 주세요." >&2
  exit 1
fi

ln -s "$SOURCE_DIR" "$TARGET"
echo "연결했습니다."
echo "  원본  : $SOURCE_DIR"
echo "  블렌더: $TARGET"
echo
echo "이제 블렌더에서 이렇게 켭니다:"
echo "  Edit > Preferences > Add-ons 에서 '가이드' 로 찾아 체크를 켭니다."
echo "  켠 뒤 3D 화면에서 Ctrl+Shift+H 를 누르면 팝업이 뜹니다."
