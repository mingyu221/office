#!/usr/bin/env bash
# =============================================================================
# compare-colors.sh  -  색 시안들을 후처리해서 사이트에 올린다
#
#   17_export_color_variants.py 가 만든 o2_color_v*.usda / .glb 를 받아서
#     usda -> freeze (scale 을 visibility 로)  -> _frozen.usdz   아이폰
#     glb  -> fix    (애니메이션 병합 + STEP)  -> _fixed.glb     윈도우/갤럭시
#   둘을 docs/color/v<N>/ 에 배치하고 목록을 갱신한다.
#
#   사용: 블렌더 출력 파일이 있는 폴더에서
#     bash compare-colors.sh [저장소경로]
#   기본 저장소 경로: ~/Desktop/vision/office
# =============================================================================
set -uo pipefail

REPO="${1:-$HOME/Desktop/vision/office}"
WORK="$(pwd)"

declare -a TAGS=(v0 v1 v2 v3)
declare -a DESCS=(
  "기준점 - 현재 색 (#FF0D0D, 발광 그대로)"
  "선명한 빨강 + 강한 발광 (#FF0000, 세기 3.0)"
  "진한 빨강 + 약한 발광 (#E00000, 세기 1.0)"
  "진한 빨강, 발광 끔 (#B00000, 세기 0)"
)

echo "=============================================================================="
echo "작업 폴더 : $WORK"
echo "저장소    : $REPO"
echo "=============================================================================="

[ -d "$REPO/viewer" ] || { echo "!! 저장소를 찾지 못했습니다: $REPO"; exit 1; }
for t in "${TAGS[@]}"; do
  [ -f "$WORK/o2_color_${t}.usda" ] || { echo "!! o2_color_${t}.usda 없음 - 17 을 먼저 돌리세요"; exit 1; }
  [ -f "$WORK/o2_color_${t}.glb" ]  || { echo "!! o2_color_${t}.glb 없음 - 17 을 먼저 돌리세요"; exit 1; }
done

# 후처리 도구 받기
for f in 10_freeze_to_visibility.py 15_fix_glb.py; do
  [ -f "$WORK/$f" ] || cp "$REPO/blender/$f" "$WORK/$f"
done
python3 -c "import pxr" 2>/dev/null || {
  echo "-- pxr 설치 (usdz 를 바이너리로 작게 담기 위함)"
  python3 -m pip install -q usd-core || echo "   (실패 - ASCII 로 담깁니다. 파일이 큽니다)"
}

fail=0
for i in "${!TAGS[@]}"; do
  t="${TAGS[$i]}"; d="${DESCS[$i]}"
  echo
  echo "###################### $t  $d ######################"

  python3 "$WORK/10_freeze_to_visibility.py" "$WORK/o2_color_${t}.usda" \
    | tail -8 || { echo "!! freeze 실패: $t"; fail=1; continue; }
  python3 "$WORK/15_fix_glb.py" "$WORK/o2_color_${t}.glb" \
    | tail -6 || { echo "!! glb fix 실패: $t"; fail=1; continue; }

  U="$WORK/o2_color_${t}_frozen.usdz"
  G="$WORK/o2_color_${t}_fixed.glb"
  [ -f "$U" ] || { echo "!! $U 없음"; fail=1; continue; }
  [ -f "$G" ] || { echo "!! $G 없음"; fail=1; continue; }

  ( cd "$REPO" && ./viewer/add-model.sh "color/$t" "$G" "$U" "$d" )
done

echo
echo "=============================================================================="
if [ "$fail" -ne 0 ]; then
  echo "★ 일부 단계가 실패했습니다. 위 로그를 확인하세요."
else
  du -sh "$REPO/docs/color" 2>/dev/null
  echo "■ 준비 완료. 올리려면:"
  echo "    cd $REPO && git add docs && git commit -m 'add color variants' && git push"
  echo
  echo "  올린 뒤 1~2분 뒤부터 비교 가능:"
  for t in "${TAGS[@]}"; do
    echo "    https://mingyu221.github.io/office/color/$t/"
  done
  echo
  echo "  색을 고르신 뒤 정리하려면:"
  echo "    cd $REPO && git rm -r --cached docs/color && rm -rf docs/color \\"
  echo "      && python3 -c \"import json,io;p='docs/models.json';d=json.load(io.open(p,encoding='utf-8'));d['items']=[i for i in d['items'] if i['path']!='color'];json.dump(d,io.open(p,'w',encoding='utf-8'),ensure_ascii=False,indent=2)\" \\"
  echo "      && git add -A docs && git commit -m 'remove color variants' && git push"
fi
echo "=============================================================================="
