#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# 배포용 확장 파일(.zip)을 만든다.
#
# 만들어진 zip 은 블렌더 4.2 이상에서 창에 떨구는 것만으로 설치된다.
# 옛 판을 쓰는 사람은 install.sh 를 쓰거나 폴더를 직접 복사한다.
# ═══════════════════════════════════════════════════════════════════════
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 환경변수를 먼저 보고, 그다음 PATH, 그다음 맥의 흔한 자리를 본다.
# 맥 경로 하나만 두면 다른 기기에서는 시작도 못 한다.
if [[ -z "${BLENDER_APP:-}" ]]; then
  BLENDER_APP="$(command -v blender 2>/dev/null || true)"
fi
if [[ -z "${BLENDER_APP:-}" && -x "/Applications/Blender.app/Contents/MacOS/Blender" ]]; then
  BLENDER_APP="/Applications/Blender.app/Contents/MacOS/Blender"
fi

if [[ -z "${BLENDER_APP:-}" || ! -x "$BLENDER_APP" ]]; then
  echo "블렌더를 찾지 못했습니다." >&2
  echo "설치한 자리를 BLENDER_APP 환경변수로 알려 주세요. 예:" >&2
  echo "  BLENDER_APP=/path/to/blender ./build_extension.sh" >&2
  exit 1
fi

mkdir -p "$REPO_ROOT/dist"
"$BLENDER_APP" --command extension build \
  --source-dir "$REPO_ROOT/blender_guide" \
  --output-dir "$REPO_ROOT/dist"

echo
echo "만들었습니다:"
ls -lh "$REPO_ROOT/dist"/*.zip | awk '{print "  " $9 " (" $5 ")"}'
