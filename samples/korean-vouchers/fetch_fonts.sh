#!/usr/bin/env bash
# 한글 폰트(나눔고딕/나눔명조) 내려받기 - PDF 생성 전 1회 실행
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/fonts"
mkdir -p "$DIR"
BASE="https://raw.githubusercontent.com/google/fonts/main"
for f in ofl/nanumgothic/NanumGothic-Regular.ttf \
         ofl/nanumgothic/NanumGothic-Bold.ttf \
         ofl/nanummyeongjo/NanumMyeongjo-Regular.ttf \
         ofl/nanummyeongjo/NanumMyeongjo-Bold.ttf; do
  out="$DIR/$(basename "$f")"
  [ -s "$out" ] || curl -fsSL -o "$out" "$BASE/$f"
  echo "ready: $(basename "$f")"
done
