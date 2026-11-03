# =============================================================================
# 16_set_o2_color.py  -  산소 오브젝트 색을 바꾼다
#
#  블렌더 Scripting 탭 -> Text > Open 또는 붙여넣고 Alt+P
#
#  ■ 먼저 DRY_RUN = True 로 한 번 돌려 어떤 머티리얼이 걸리는지 보세요.
#    산소와 단백질이 머티리얼을 공유하고 있으면 단백질까지 빨개집니다.
#    이 스크립트는 공유를 감지하면 산소용으로 사본을 만들어 분리합니다.
#
#  ■ 색은 HEX 로 적습니다. 블렌더의 Base Color 는 선형(linear) 공간이라
#    HEX(sRGB) 를 그대로 넣으면 더 밝게 보입니다. 변환해서 넣습니다.
# =============================================================================
import bpy

# ---------------------------- 설정 -------------------------------------------
PATTERNS = ("O2_Trajectory_F",)
HEX      = "8B0000"   # 진한 붉은색. 아래 참고표에서 골라 바꾸세요
DRY_RUN  = True       # True = 보기만 함. 확인 후 False 로 바꿔 실행
# -----------------------------------------------------------------------------
#  HEX 참고 (왼쪽일수록 밝음)
#    FF0D0D  CPK 표준 산소색 (현재 보통 이 계열)
#    CC0000  진한 빨강
#    B22222  벽돌색 (firebrick)
#    8B0000  진한 적갈색 (dark red)   <- 기본값
#    6B0000  더 어두움
# -----------------------------------------------------------------------------


def srgb_to_linear(c):
    """HEX 는 sRGB. 블렌더 Base Color 는 선형이라 변환이 필요하다."""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_to_rgba(h):
    h = h.strip().lstrip("#")
    if len(h) != 6:
        raise ValueError(f"HEX 는 6자리여야 합니다: {h}")
    srgb = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(srgb_to_linear(c) for c in srgb) + (1.0,)


def principled(mat):
    """머티리얼의 Principled BSDF 노드. 이름이 아니라 타입으로 찾는다
    (블렌더 한글 UI 에서는 노드 이름이 '프린시플드_BSDF' 다)."""
    if not mat or not mat.use_nodes or not mat.node_tree:
        return None
    for n in mat.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            return n
    return None


rgba = hex_to_rgba(HEX)
objs = [o for o in bpy.data.objects
        if o.type == 'MESH' and any(p in o.name for p in PATTERNS)]
o2_names = {o.name for o in objs}

print("\n" + "=" * 88)
print(f"Blender {bpy.app.version_string}")
print(f"대상 {len(objs)}개  색 #{HEX.lstrip('#').upper()}"
      f"  -> 선형 ({rgba[0]:.4f}, {rgba[1]:.4f}, {rgba[2]:.4f})")
print(f"DRY_RUN = {DRY_RUN}")
print("=" * 88)
if not objs:
    print(f"!! PATTERNS={PATTERNS} 에 맞는 메쉬가 없습니다.")
    raise SystemExit

# 머티리얼별로 어떤 오브젝트가 쓰는지 모은다 (공유 감지)
users = {}
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    for sl in o.material_slots:
        if sl.material:
            users.setdefault(sl.material.name, set()).add(o.name)

changed, copied, skipped = 0, 0, []
for o in objs:
    print("-" * 88)
    print(f"[{o.name}]  머티리얼 슬롯 {len(o.material_slots)}개")
    if not o.material_slots:
        print("  !! 슬롯이 없습니다 - 머티리얼이 할당돼 있지 않습니다")
        skipped.append(o.name)
        continue

    for i, sl in enumerate(o.material_slots):
        mat = sl.material
        if mat is None:
            print(f"  슬롯 {i}: (비어 있음)")
            continue

        shared_with = users.get(mat.name, set()) - o2_names
        node = principled(mat)
        if node is None:
            print(f"  슬롯 {i}: '{mat.name}'  !! Principled BSDF 를 찾지 못함"
                  f" (use_nodes={mat.use_nodes}) - 건너뜀")
            skipped.append(f"{o.name}[{i}] {mat.name}")
            continue

        base = node.inputs.get("Base Color")
        if base is None:
            print(f"  슬롯 {i}: '{mat.name}'  !! Base Color 입력이 없음 - 건너뜀")
            skipped.append(f"{o.name}[{i}] {mat.name}")
            continue

        old = tuple(round(c, 4) for c in base.default_value)
        tag = ""
        if base.is_linked:
            tag = "  !! Base Color 에 다른 노드가 연결돼 있어 색이 안 바뀔 수 있음"

        if shared_with:
            print(f"  슬롯 {i}: '{mat.name}'  공유 중 -> {sorted(shared_with)[:3]}"
                  f"{' 외' if len(shared_with) > 3 else ''}")
            if DRY_RUN:
                print(f"           사본을 만들어 분리할 예정")
            else:
                mat = mat.copy()
                mat.name = f"{mat.name}_O2"
                sl.material = mat
                node = principled(mat)
                base = node.inputs.get("Base Color")
                copied += 1
                print(f"           사본 생성: '{mat.name}' (단백질 색은 그대로)")

        print(f"  슬롯 {i}: '{mat.name}'  {old} -> "
              f"({rgba[0]:.4f}, {rgba[1]:.4f}, {rgba[2]:.4f}){tag}")
        if not DRY_RUN:
            base.default_value = rgba
            mat.diffuse_color = rgba          # 뷰포트 솔리드 표시용
            changed += 1

print("=" * 88)
if DRY_RUN:
    print("DRY_RUN = True 였습니다. 아무것도 바꾸지 않았습니다.")
    print("위 내용이 맞으면 DRY_RUN = False 로 바꾸고 다시 실행하세요.")
else:
    print(f"■ 머티리얼 {changed}개 변경"
          + (f", 사본 {copied}개 생성" if copied else ""))
    if skipped:
        print(f"  건너뛴 것: {skipped}")
    print()
    print("  뷰포트를 Material Preview 또는 Rendered 로 보면 색이 확인됩니다.")
    print("  ★ File > Save 로 .blend 를 저장하세요.")
    print()
    print("  이후 다시 내보내야 합니다:")
    print("    1) 13_full_fix.py   (블렌더)  -> o2_tunnel_final.usda/.usdz")
    print("    2) freeze.py        (터미널)  -> ..._frozen.usdz   아이폰")
    print("    3) 14_export_glb.py (블렌더)  -> o2_tunnel_final.glb")
    print("    4) 15_fix_glb.py    (터미널)  -> ..._fixed.glb      윈도우/갤럭시")
    print("    5) add-model.sh     (터미널)  -> docs 배치 후 push")
print("=" * 88)
