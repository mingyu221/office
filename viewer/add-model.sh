#!/usr/bin/env bash
# =============================================================================
# add-model.sh  -  docs/ 에 모델 폴더를 하나 추가한다
#
#   ./add-model.sh <폴더이름> <모델.glb> [모델.usdz] ["설명"]
#
#   예) ./add-model.sh o2-tunnel ~/Desktop/a.glb ~/Desktop/a.usdz "산소 궤적 10초"
#   ->  docs/o2-tunnel/{index.html, model.glb, model.usdz} 생성
#       models.json 에 항목 추가
#       주소: https://<사용자>.github.io/<저장소>/o2-tunnel/
# =============================================================================
set -euo pipefail

NAME="${1:-}"; GLB="${2:-}"; USDZ="${3:-}"; NOTE="${4:-}"
if [ -z "$NAME" ] || [ -z "$GLB" ]; then
  echo "usage: $0 <폴더이름> <모델.glb> [모델.usdz] [\"설명\"]" >&2
  exit 1
fi
[ -f "$GLB" ] || { echo "!! GLB 가 없습니다: $GLB" >&2; exit 1; }

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
DOCS="$ROOT/docs"
mkdir -p "$DOCS/$NAME"

cp "$HERE/index.html" "$DOCS/$NAME/index.html"
cp "$GLB" "$DOCS/$NAME/model.glb"
echo "  model.glb   <- $GLB  ($(wc -c < "$GLB" | tr -d ' ') 바이트)"
if [ -n "$USDZ" ] && [ -f "$USDZ" ]; then
  cp "$USDZ" "$DOCS/$NAME/model.usdz"
  echo "  model.usdz  <- $USDZ  ($(wc -c < "$USDZ" | tr -d ' ') 바이트)"
else
  [ -n "$USDZ" ] && echo "  ! usdz 를 찾지 못해 건너뜁니다: $USDZ"
fi

cp "$HERE/gallery.html" "$DOCS/index.html"
[ -f "$DOCS/models.json" ] || cp "$HERE/models.json" "$DOCS/models.json"

NAME="$NAME" NOTE="$NOTE" python3 - "$DOCS/models.json" <<'PY'
import json, os, sys
path = sys.argv[1]
name, note = os.environ["NAME"], os.environ.get("NOTE", "")
try:
    items = json.load(open(path, encoding="utf-8"))
    if not isinstance(items, list):
        items = []
except Exception:
    items = []
items = [i for i in items if i.get("path") != name]
entry = {"path": name, "title": name.replace("-", " ").replace("_", " ")}
if note:
    entry["note"] = note
items.append(entry)
items.sort(key=lambda i: i.get("path", ""))
with open(path, "w", encoding="utf-8") as fh:
    json.dump(items, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
print(f"  models.json 갱신: {len(items)}개 항목")
PY

echo
echo "완료. docs/$NAME/ 생성됨."
echo "  git add docs && git commit -m 'add model: $NAME' && git push"
