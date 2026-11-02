#!/usr/bin/env bash
# =============================================================================
# add-model.sh  -  docs/ 에 모델을 추가한다 (여러 단계 폴더 지원)
#
#   ./viewer/add-model.sh <경로> <모델.glb> [모델.usdz] ["설명"]
#
#   <경로> 는 슬래시로 단계를 나눈다. 단계 수에 제한이 없다.
#     ./viewer/add-model.sh video/codh-tunnel a.glb a.usdz "CODH 터널"
#     -> docs/video/codh-tunnel/{index.html, model.glb, model.usdz}
#     -> https://<사용자>.github.io/<저장소>/video/codh-tunnel/
#
#   거쳐 가는 모든 단계에 목록 페이지를 만들어 둔다.
#     docs/index.html        -> video 가 보임
#     docs/video/index.html  -> codh-tunnel 이 보임
#
#   같은 경로로 다시 돌리면 덮어쓴다.
# =============================================================================
set -euo pipefail

REL="${1:-}"; GLB="${2:-}"; USDZ="${3:-}"; NOTE="${4:-}"
if [ -z "$REL" ] || [ -z "$GLB" ]; then
  echo "usage: $0 <경로> <모델.glb> [모델.usdz] [\"설명\"]" >&2
  echo "  예: $0 video/codh-tunnel ~/a.glb ~/a.usdz \"CODH 터널\"" >&2
  exit 1
fi
[ -f "$GLB" ] || { echo "!! GLB 가 없습니다: $GLB" >&2; exit 1; }
[ -n "$USDZ" ] && [ ! -f "$USDZ" ] && { echo "!! USDZ 가 없습니다: $USDZ" >&2; exit 1; }

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

REL="$REL" GLB="$GLB" USDZ="$USDZ" NOTE="$NOTE" HERE="$HERE" ROOT="$ROOT" \
python3 <<'PY'
import json, os, re, shutil, sys

rel  = os.environ["REL"].strip("/")
glb  = os.environ["GLB"]
usdz = os.environ["USDZ"]
note = os.environ["NOTE"]
here = os.environ["HERE"]
docs = os.path.join(os.environ["ROOT"], "docs")

segs = [s for s in rel.split("/") if s]
if not segs:
    sys.exit("!! 경로가 비어 있습니다")
bad = [s for s in segs if not re.fullmatch(r"[A-Za-z0-9._가-힣-]+", s)]
if bad:
    sys.exit(f"!! 폴더 이름에 쓸 수 없는 문자: {bad}\n"
             "   영문/숫자/한글/하이픈/언더스코어만 쓰세요 (공백·슬래시 금지)")

leaf = os.path.join(docs, *segs)
os.makedirs(leaf, exist_ok=True)

shutil.copy2(os.path.join(here, "index.html"), os.path.join(leaf, "index.html"))
shutil.copy2(glb, os.path.join(leaf, "model.glb"))
print(f"  model.glb   <- {glb}  ({os.path.getsize(glb):,} 바이트)")
if usdz:
    shutil.copy2(usdz, os.path.join(leaf, "model.usdz"))
    print(f"  model.usdz  <- {usdz}  ({os.path.getsize(usdz):,} 바이트)")
else:
    print("  model.usdz  (없음 - 아이폰 AR 은 동작하지 않습니다)")


def pretty(name):
    return re.sub(r"[-_]+", " ", name).strip()


def upsert(dirpath, child, is_leaf):
    """dirpath 에 목록 페이지와 models.json 을 두고 child 항목을 갱신한다."""
    os.makedirs(dirpath, exist_ok=True)
    shutil.copy2(os.path.join(here, "gallery.html"),
                 os.path.join(dirpath, "index.html"))
    jp = os.path.join(dirpath, "models.json")
    # {title, root, items[]} 형식. 목록 페이지가 URL 깊이를 추측하지 않도록
    # 자기 제목과 루트 여부를 파일에 적어 둔다.
    data = {}
    try:
        with open(jp, encoding="utf-8") as fh:
            loaded = json.load(fh)
        data = {"items": loaded} if isinstance(loaded, list) else (loaded or {})
    except Exception:
        data = {}
    items = data.get("items") or []
    if not isinstance(items, list):
        items = []
    prev = next((i for i in items if i.get("path") == child), None)
    items = [i for i in items if i.get("path") != child]
    entry = {"path": child, "title": (prev or {}).get("title") or pretty(child)}
    if is_leaf and note:
        entry["note"] = note
    elif prev and prev.get("note"):
        entry["note"] = prev["note"]
    items.append(entry)
    items.sort(key=lambda i: i.get("path", ""))

    is_root = os.path.abspath(dirpath) == os.path.abspath(docs)
    data["root"] = is_root
    data.setdefault("title", "3D Models" if is_root
                    else pretty(os.path.basename(dirpath.rstrip("/"))))
    data["items"] = items
    with open(jp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    rp = os.path.relpath(dirpath, docs)
    rp = "" if rp == "." else rp + "/"
    print(f"  목록 갱신: docs/{rp}models.json  ({len(items)}개) <- {child}")


# 루트부터 한 단계씩 내려가며 목록 페이지를 둔다
for i, seg in enumerate(segs):
    upsert(os.path.join(docs, *segs[:i]), seg, is_leaf=(i == len(segs) - 1))

print()
print(f"완료: docs/{'/'.join(segs)}/")
print(f"  주소: /{'/'.join(segs)}/")
PY

echo "  git add docs && git commit -m 'add model: $REL' && git push"
