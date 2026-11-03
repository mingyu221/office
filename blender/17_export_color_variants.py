# =============================================================================
# 17_export_color_variants.py  -  색 시안별로 완성 파일을 한 번에 내보낸다
#
#  뷰포트로는 발광 느낌을 판단하기 어렵다. AR 에서 실제로 봐야 안다.
#  그래서 시안마다 usda/usdz/glb 를 통째로 만들어 기기에서 비교한다.
#
#  ■ 먼저 13_full_fix.py 를 돌려 리타이밍·오리진·중심 교정이 끝난 상태여야 한다.
#    이 스크립트는 '색만' 바꿔가며 내보낸다. 지오메트리와 애니메이션은 안 건드린다.
#
#  ■ File > Export > USD 를 쓰면 안 된다. 카메라가 같이 들어가 AR 회전축이
#    씬 바깥으로 끌려간다 (Viewpoint 6개가 y=-279.84 에 있음).
#    이 스크립트는 메쉬만 선택해 내보낸다.
#
#  ■ 끝나면 머티리얼을 원래 색으로 되돌린다. .blend 는 그대로 남는다.
#
#  결과: <OUT_BASE>_v0.usda/.usdz/.glb , _v1..., _v2..., _v3...
#  이어서 터미널에서 compare-colors.sh 를 돌린다.
# =============================================================================
import os
import bpy

# ---------------------------- 설정 -------------------------------------------
PATTERNS = ("O2_Trajectory_F",)
OUT_BASE = "o2_color"

#  (이름, HEX, 발광세기 or None=그대로, 설명)
VARIANTS = [
    ("v0", "FF0D0D", None, "현재 색 (기준점)"),
    ("v1", "FF0000", 3.0,  "선명한 빨강 + 강한 발광"),
    ("v2", "E00000", 1.0,  "진한 빨강 + 약한 발광"),
    ("v3", "B00000", 0.0,  "진한 빨강, 발광 끔"),
]
# -----------------------------------------------------------------------------


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_to_rgba(h):
    h = h.strip().lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(srgb_to_linear(c) for c in srgb) + (1.0,)


def principled(mat):
    if not mat or not getattr(mat, "use_nodes", True) or not mat.node_tree:
        return None
    for n in mat.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            return n
    return None


scn = bpy.context.scene
folder = bpy.path.abspath("//")
objs = [o for o in bpy.data.objects
        if o.type == 'MESH' and any(p in o.name for p in PATTERNS)]
cams = [o for o in bpy.data.objects if o.type == 'CAMERA']
lights = [o for o in bpy.data.objects if o.type == 'LIGHT']

print("\n" + "=" * 90)
print(f"Blender {bpy.app.version_string}")
print(f"파일 {bpy.data.filepath or '(저장 안 됨)'}")
print(f"프레임 {scn.frame_start}-{scn.frame_end} @ {scn.render.fps}fps"
      f"  -> 타임코드 1칸 {1.0/scn.render.fps:.3f}초")
print(f"O2 {len(objs)}개 / 카메라 {len(cams)}개 / 라이트 {len(lights)}개 (내보낼 때 제외)")
print("=" * 90)

if not folder:
    print("!! .blend 를 먼저 저장하세요.")
    raise SystemExit
if not objs:
    print(f"!! PATTERNS={PATTERNS} 에 맞는 메쉬가 없습니다.")
    raise SystemExit
if scn.frame_end < 100 or scn.render.fps < 12:
    print("!! 프레임 범위/fps 가 이상합니다. 13_full_fix.py 를 먼저 돌리세요.")
    print(f"   현재 {scn.frame_start}-{scn.frame_end} @ {scn.render.fps}fps"
          f" (1-240 @ 24 여야 함)")
    raise SystemExit

# ---- 대상 머티리얼 수집 + 원래 값 보관 --------------------------------------
mats = {}
for o in objs:
    for sl in o.material_slots:
        if sl.material and sl.material.name not in mats:
            node = principled(sl.material)
            if node is None:
                print(f"!! '{sl.material.name}' 에 Principled BSDF 가 없습니다")
                continue
            mats[sl.material.name] = (sl.material, node)

if not mats:
    print("!! 바꿀 머티리얼을 찾지 못했습니다.")
    raise SystemExit

backup = {}
for name, (mat, node) in mats.items():
    b = node.inputs.get("Base Color")
    e = node.inputs.get("Emission Color") or node.inputs.get("Emission")
    s = node.inputs.get("Emission Strength")
    backup[name] = (
        list(b.default_value) if b else None,
        list(e.default_value) if e else None,
        float(s.default_value) if s else None,
    )
    print(f"머티리얼 '{name}'  base={tuple(round(c,3) for c in b.default_value) if b else '-'}"
          f"  emis={tuple(round(c,3) for c in e.default_value) if e else '-'}"
          f"  strength={round(s.default_value,3) if s else '-'}")

# ---- 메쉬만 선택 (카메라/라이트 제외) ---------------------------------------
for o in bpy.data.objects:
    try:
        o.select_set(False)
    except RuntimeError:
        pass
picked = []
for o in bpy.data.objects:
    if o.type not in ('MESH', 'EMPTY'):
        continue
    try:
        o.hide_select = False
        o.select_set(True)
        picked.append(o.name)
    except RuntimeError:
        pass
if picked:
    bpy.context.view_layer.objects.active = bpy.data.objects[picked[0]]
print(f"내보낼 오브젝트 {len(picked)}개")

USD_OPTS = {
    "export_animation": True, "xform_op_mode": 'TRS',
    "selected_objects_only": True, "export_materials": True,
    "generate_preview_surface": True, "relative_paths": True,
    "evaluation_mode": 'RENDER', "triangulate_meshes": True,
    "use_instancing": False, "export_cameras": False, "export_lights": False,
}
GLB_OPTS = {
    "export_format": 'GLB', "use_selection": True, "export_animations": True,
    "export_frame_range": True, "export_force_sampling": False,
    "export_optimize_animation_size": False, "export_animation_mode": 'SCENE',
    "export_cameras": False, "export_lights": False, "export_apply": True,
    "export_yup": True, "export_materials": 'EXPORT',
    "export_normals": True, "export_texcoords": True,
}
usd_ok = {k: v for k, v in USD_OPTS.items()
          if k in bpy.ops.wm.usd_export.get_rna_type().properties}
glb_ok = {k: v for k, v in GLB_OPTS.items()
          if k in bpy.ops.export_scene.gltf.get_rna_type().properties}

made = []
try:
    for tag, hexcode, strength, desc in VARIANTS:
        rgba = hex_to_rgba(hexcode)
        print("-" * 90)
        print(f"[{tag}] #{hexcode}  세기 {strength if strength is not None else '그대로'}"
              f"   {desc}")
        print(f"      선형 ({rgba[0]:.4f}, {rgba[1]:.4f}, {rgba[2]:.4f})")

        for name, (mat, node) in mats.items():
            ob, oe, os_ = backup[name]
            b = node.inputs.get("Base Color")
            e = node.inputs.get("Emission Color") or node.inputs.get("Emission")
            s = node.inputs.get("Emission Strength")
            if b:
                b.default_value = rgba
            if e:
                e.default_value = rgba
            if s:
                s.default_value = os_ if strength is None else strength
            mat.diffuse_color = rgba
        bpy.context.view_layer.update()

        base = os.path.join(folder, f"{OUT_BASE}_{tag}")
        for ext, op, opts in ((".usda", bpy.ops.wm.usd_export, usd_ok),
                              (".usdz", bpy.ops.wm.usd_export, usd_ok),
                              (".glb", bpy.ops.export_scene.gltf, glb_ok)):
            path = base + ext
            try:
                op(filepath=path, **opts)
                sz = os.path.getsize(path)
                print(f"      -> {os.path.basename(path):<22} {sz:>12,} 바이트")
                made.append(path)
            except Exception as exc:
                print(f"      !! {os.path.basename(path)} 실패: {exc}")
finally:
    # 머티리얼 원복 — .blend 는 손대지 않은 상태로 남긴다
    for name, (mat, node) in mats.items():
        ob, oe, os_ = backup[name]
        b = node.inputs.get("Base Color")
        e = node.inputs.get("Emission Color") or node.inputs.get("Emission")
        s = node.inputs.get("Emission Strength")
        if b and ob:
            b.default_value = ob
        if e and oe:
            e.default_value = oe
        if s and os_ is not None:
            s.default_value = os_
        if ob:
            mat.diffuse_color = ob
    bpy.context.view_layer.update()
    print("-" * 90)
    print("■ 머티리얼을 원래 색으로 되돌렸습니다 (.blend 는 그대로).")

print("=" * 90)
print(f"파일 {len(made)}개 생성  (총 {sum(os.path.getsize(p) for p in made)/1048576:.0f} MB)")
print()
print("  (.usda 는 freeze 용 중간 파일입니다. 끝나면 지워도 됩니다)")
print()
print("다음: 터미널에서 (compare-colors.sh 는 저장소의 viewer/ 안에 있습니다)")
print(f"  cd {folder.rstrip('/')}")
print("  bash ~/Desktop/vision/office/viewer/compare-colors.sh ~/Desktop/vision/office")
print("=" * 90)
