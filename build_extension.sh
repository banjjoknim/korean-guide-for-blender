#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# 배포용 확장 파일(.zip)을 만든다.
#
# 만들어진 zip 은 블렌더 4.2 이상에서 창에 떨구는 것만으로 설치된다.
# 옛 판을 쓰는 사람은 install.sh 를 쓰거나 폴더를 직접 복사한다.
# ═══════════════════════════════════════════════════════════════════════
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BLENDER_APP="${BLENDER_APP:-/Applications/Blender.app/Contents/MacOS/Blender}"

if [[ ! -x "$BLENDER_APP" ]]; then
  echo "블렌더를 찾지 못했습니다: $BLENDER_APP" >&2
  echo "다른 자리에 설치했다면 BLENDER_APP 환경변수로 알려 주세요." >&2
  exit 1
fi

mkdir -p "$REPO_ROOT/dist"
"$BLENDER_APP" --command extension build \
  --source-dir "$REPO_ROOT/blender_guide" \
  --output-dir "$REPO_ROOT/dist"

echo
echo "만들었습니다:"
ls -lh "$REPO_ROOT/dist"/*.zip | awk '{print "  " $9 " (" $5 ")"}'
