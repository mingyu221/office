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

# 이 머티리얼은 이름이 O2_Red_Emission 인 발광 머티리얼이다.
# 발광이 켜져 있으면 Base Color 가 아니라 Emission Color 가 보이는 색을 정한다.
# 그래서 둘 다 바꾼다.
EMISSION_STRENGTH   = None   # 숫자를 넣으면 발광 세기도 바꾼다 (None = 그대로)
SET_EMISSION_ALWAYS = True   # 발광이 꺼져 있어도 Emission Color 를 맞춰 둔다
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
    # Material.use_nodes 는 Blender 6.0 에서 제거 예정이라 getattr 로 읽는다
    if not mat or not getattr(mat, "use_nodes", True) or not mat.node_tree:
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
done = set()        # 5개가 머티리얼 하나를 공유하므로 중복 처리 방지
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
                copied += 1
                print(f"           사본 생성: '{mat.name}' (단백질 색은 그대로)")

        if mat.name in done:
            print(f"  슬롯 {i}: '{mat.name}'  (이미 처리함 - 5개가 공유)")
            continue

        base = node.inputs.get("Base Color")
        # Blender 4.x 는 'Emission Color', 그 이전은 'Emission'
        emis = node.inputs.get("Emission Color") or node.inputs.get("Emission")
        stren = node.inputs.get("Emission Strength")
        sv = stren.default_value if stren is not None else 0.0

        print(f"  슬롯 {i}: '{mat.name}'")
        if base is not None:
            print(f"     Base Color       {tuple(round(c,4) for c in base.default_value)}"
                  + ("  !! 다른 노드가 연결됨" if base.is_linked else ""))
        if emis is not None:
            print(f"     Emission Color   {tuple(round(c,4) for c in emis.default_value)}"
                  + ("  !! 다른 노드가 연결됨" if emis.is_linked else ""))
        if stren is not None:
            print(f"     Emission Strength {sv:.3f}"
                  + ("   <- 0 보다 크므로 '발광 색'이 화면을 지배합니다"
                     if sv > 0 else "   (발광 꺼짐)"))

        targets = []
        if base is not None:
            targets.append(("Base Color", base))
        # 발광이 켜져 있으면 Emission Color 도 같이 바꿔야 실제 색이 바뀐다
        if emis is not None and (sv > 0 or SET_EMISSION_ALWAYS):
            targets.append(("Emission Color", emis))

        if not targets:
            print(f"     !! 바꿀 입력이 없습니다 - 건너뜀")
            skipped.append(f"{o.name}[{i}] {mat.name}")
            continue

        print(f"     -> {', '.join(t[0] for t in targets)} 를 "
              f"({rgba[0]:.4f}, {rgba[1]:.4f}, {rgba[2]:.4f}) 로 변경"
              + (f", Emission Strength {sv:.2f} -> {EMISSION_STRENGTH}"
                 if EMISSION_STRENGTH is not None and stren is not None else ""))
        if not DRY_RUN:
            for _, sock in targets:
                sock.default_value = rgba
            if EMISSION_STRENGTH is not None and stren is not None:
                stren.default_value = EMISSION_STRENGTH
            mat.diffuse_color = rgba          # 뷰포트 솔리드 표시용
            changed += 1
        done.add(mat.name)

print("=" * 88)
if DRY_RUN:
    print("DRY_RUN = True 였습니다. 아무것도 바꾸지 않았습니다.")
    print("위 내용이 맞으면 DRY_RUN = False 로 바꾸고 다시 실행하세요.")
else:
    print(f"■ 머티리얼 {changed}종 변경"
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
