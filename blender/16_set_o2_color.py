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
DRY_RUN  = True       # True = 보기만 함. 확인 후 False 로 바꿔 실행

# ---- 시안 고르기 --------------------------------------------------------
#  VARIANT 번호만 바꿔 Alt+P 를 누르고 뷰포트(Material Preview)를 보면 된다.
#  발광 머티리얼이라 '색' 과 '발광 세기' 두 축을 같이 봐야 한다.
#
#    발광이 세면 선명한 빨강도 허옇게 날아가 분홍처럼 보인다.
#    "더 진한 붉은색" 이 '어둡게' 가 아니라 '빨갛게 제대로' 라는 뜻이면
#    색이 아니라 세기를 낮춰야 한다. 2~4번이 그 방향이다.
VARIANT = 3
# -------------------------------------------------------------------------
VARIANTS = {
    0: ("FF0D0D", None, "현재 계열 유지 (CPK 표준 산소색), 세기 그대로"),
    1: ("FF0000", 3.0,  "선명한 빨강 + 강한 발광  (더 밝게)"),
    2: ("FF0000", 1.5,  "선명한 빨강 + 중간 발광  (빨강이 살아남)"),
    3: ("E00000", 1.0,  "진한 빨강 + 약한 발광    (추천 - 색이 또렷)"),
    4: ("CC0000", 0.5,  "진한 빨강 + 아주 약한 발광"),
    5: ("B00000", 0.0,  "진한 빨강, 발광 끔       (순수 디퓨즈)"),
    6: ("8B0000", 1.0,  "진한 적갈색 + 약한 발광  (가장 어두움)"),
}
RESTORE = False   # True 로 두고 실행하면 처음 값으로 되돌린다
# -------------------------------------------------------------------------

if VARIANT not in VARIANTS:
    raise ValueError(f"VARIANT 는 {sorted(VARIANTS)} 중 하나여야 합니다")
HEX, EMISSION_STRENGTH, _DESC = VARIANTS[VARIANT]
SET_EMISSION_ALWAYS = True   # 발광이 꺼져 있어도 Emission Color 를 맞춰 둔다


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
print(f"대상 {len(objs)}개")
if RESTORE:
    print("RESTORE = True  -> 처음 값으로 되돌립니다")
else:
    print(f"VARIANT {VARIANT}: {_DESC}")
    print(f"  색 #{HEX.upper()}  -> 선형 ({rgba[0]:.4f}, {rgba[1]:.4f}, {rgba[2]:.4f})"
          + (f"   발광 세기 {EMISSION_STRENGTH}"
             if EMISSION_STRENGTH is not None else "   발광 세기 그대로"))
print(f"DRY_RUN = {DRY_RUN}")
print("-" * 88)
print("다른 시안:")
for k in sorted(VARIANTS):
    h, st, d = VARIANTS[k]
    mark = " <-- 지금" if k == VARIANT and not RESTORE else ""
    print(f"  {k}: #{h}  세기 {str(st):>4}   {d}{mark}")
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

        # 처음 값을 머티리얼에 적어 둔다 (한 번만). RESTORE 로 되돌릴 수 있게.
        if "_orig_base" not in mat.keys():
            if not DRY_RUN:
                if base is not None:
                    mat["_orig_base"] = list(base.default_value)
                if emis is not None:
                    mat["_orig_emis"] = list(emis.default_value)
                if stren is not None:
                    mat["_orig_strength"] = float(sv)
            print(f"     (처음 값 기록"
                  + ("" if not DRY_RUN else " 예정") + " - RESTORE=True 로 복원 가능)")

        if RESTORE:
            if "_orig_base" not in mat.keys():
                print(f"     !! 기록된 처음 값이 없습니다 - 건너뜀")
                skipped.append(f"{o.name}[{i}] {mat.name}")
                continue
            print(f"     처음 값으로 복원: base={tuple(round(c,4) for c in mat['_orig_base'])}"
                  f"  strength={mat.get('_orig_strength')}")
            if not DRY_RUN:
                if base is not None and "_orig_base" in mat.keys():
                    base.default_value = tuple(mat["_orig_base"])
                if emis is not None and "_orig_emis" in mat.keys():
                    emis.default_value = tuple(mat["_orig_emis"])
                if stren is not None and "_orig_strength" in mat.keys():
                    stren.default_value = mat["_orig_strength"]
                mat.diffuse_color = tuple(mat.get("_orig_base", (1, 0, 0, 1)))
                changed += 1
            done.add(mat.name)
            continue

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
