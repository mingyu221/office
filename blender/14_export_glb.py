# =============================================================================
# 14_export_glb.py  -  윈도우 / 갤럭시(안드로이드) 용 GLB 내보내기 + 검증
#
#  USDZ 는 애플 포맷이라 윈도우·안드로이드가 기본 지원하지 않는다.
#  두 플랫폼의 표준은 glTF/GLB 다 (안드로이드 Scene Viewer, 윈도우 '3D 보기').
#
#  glTF 에는 visibility token 이 없다. 대신 애니메이션 샘플러에
#  interpolation = "STEP" 이 있다. STEP 은 다음 키프레임까지 값을 그대로 유지하므로
#  보간이 전혀 일어나지 않는다 -> USDZ 의 visibility 와 같은 효과.
#  그래서 scale 0.001 <-> 1 을 STEP 으로 내보내면 이동 없이 깔끔히 팝된다.
#
#  ※ 13_full_fix.py 를 먼저 돌린 상태(240프레임/24fps, 중심 교정 완료)에서 실행하세요.
#  ※ 내보낸 GLB 의 JSON 청크를 직접 파싱해 STEP 인지 측정합니다. 추측하지 않습니다.
# =============================================================================
import json
import os
import struct
import bpy

# ---------------------------- 설정 -------------------------------------------
PATTERNS  = ("O2_Trajectory_F",)
OUT_NAME  = "o2_tunnel_final"      # -> o2_tunnel_final.glb
# -----------------------------------------------------------------------------

scn = bpy.context.scene
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
cams = [o for o in bpy.data.objects if o.type == 'CAMERA']
lights = [o for o in bpy.data.objects if o.type == 'LIGHT']

print("\n" + "=" * 92)
print(f"Blender {bpy.app.version_string}")
print(f"프레임 {scn.frame_start}-{scn.frame_end} @ {scn.render.fps}fps"
      f"  -> 전체 {(scn.frame_end - scn.frame_start) / scn.render.fps:.2f}초")
print(f"메쉬 {len(meshes)}개 / 카메라 {len(cams)}개 / 라이트 {len(lights)}개")
print("=" * 92)

if scn.frame_end < 100:
    print("!! 프레임 범위가 짧습니다. 13_full_fix.py 를 먼저 돌리세요.")
    print(f"   현재 {scn.frame_start}-{scn.frame_end} (240 이어야 함)")

folder = bpy.path.abspath("//")
if not folder:
    print("!! .blend 를 먼저 저장하세요.")
    raise SystemExit

# ---- 메쉬만 선택 (카메라/라이트 배제: bbox 를 늘리지 않게) -------------------
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

# ---- 내보내기 ---------------------------------------------------------------
wanted = {
    "export_format": 'GLB',
    "use_selection": True,
    "export_animations": True,
    "export_frame_range": True,
    "export_force_sampling": False,   # ★ False 여야 CONSTANT 키가 STEP 으로 나간다
    "export_optimize_animation_size": False,
    "export_animation_mode": 'SCENE',
    "export_cameras": False,
    "export_lights": False,
    "export_apply": True,
    "export_yup": True,               # glTF 는 Y-up
    "export_materials": 'EXPORT',
    "export_normals": True,
    "export_texcoords": True,
}
props = bpy.ops.export_scene.gltf.get_rna_type().properties
opts = {k: v for k, v in wanted.items() if k in props}
dropped = sorted(set(wanted) - set(opts))
print("-" * 92)
if dropped:
    print(f"  이 버전이 지원하지 않아 생략된 옵션: {dropped}")
for k in sorted(opts):
    print(f"  {k:34s} = {opts[k]!r}")

glb = os.path.join(folder, OUT_NAME + ".glb")
try:
    bpy.ops.export_scene.gltf(filepath=glb, **opts)
    print(f"  -> {glb}")
except Exception as exc:
    print(f"  !! 실패: {exc}")
    raise SystemExit

# ---- GLB JSON 청크 파싱해서 실제로 STEP 인지 측정 ---------------------------
print("-" * 92)
if not os.path.exists(glb):
    print("!! glb 가 없습니다.")
    raise SystemExit

with open(glb, "rb") as fh:
    blob = fh.read()

magic, ver, total = struct.unpack("<III", blob[:12])
if magic != 0x46546C67:                      # 'glTF'
    print(f"!! GLB 매직이 맞지 않습니다: {magic:#x}")
    raise SystemExit
pos, js = 12, None
while pos + 8 <= len(blob):
    clen, ctype = struct.unpack("<II", blob[pos:pos + 8])
    body = blob[pos + 8:pos + 8 + clen]
    if ctype == 0x4E4F534A:                  # 'JSON'
        js = json.loads(body.decode("utf-8"))
        break
    pos += 8 + clen
if js is None:
    print("!! JSON 청크를 찾지 못했습니다.")
    raise SystemExit

size = os.path.getsize(glb)
print(f"측정: {glb}")
print(f"  GLB version={ver}  크기 {size:,} 바이트 = {size/1048576:.1f} MB")
print(f"  node {len(js.get('nodes', []))}개  mesh {len(js.get('meshes', []))}개"
      f"  animation {len(js.get('animations', []))}개"
      f"  camera {len(js.get('cameras', []))}개")

node_name = {i: n.get("name", f"node{i}")
             for i, n in enumerate(js.get("nodes", []))}

ok = True
if not js.get("animations"):
    print("  ★ 애니메이션이 없습니다. export_animations 를 확인하세요.")
    ok = False

for ai, anim in enumerate(js.get("animations", [])):
    print(f"  animation[{ai}] '{anim.get('name', '')}'"
          f"  채널 {len(anim.get('channels', []))}개")
    samplers = anim.get("samplers", [])
    per_target = {}
    for ch in anim.get("channels", []):
        tgt = ch.get("target", {})
        nm = node_name.get(tgt.get("node"), "?")
        path = tgt.get("path")
        interp = samplers[ch["sampler"]].get("interpolation", "LINEAR") \
            if ch.get("sampler") is not None and ch["sampler"] < len(samplers) else "?"
        n_keys = None
        try:
            inp = samplers[ch["sampler"]]["input"]
            n_keys = js["accessors"][inp].get("count")
        except Exception:
            pass
        per_target.setdefault(nm, []).append((path, interp, n_keys))

    for nm in sorted(per_target):
        if not any(p in nm for p in PATTERNS):
            continue
        entries = sorted(per_target[nm])
        paths = {p for p, _, _ in entries}
        interps = {i for _, i, _ in entries}
        step_ok = interps == {"STEP"}
        no_move = "translation" not in paths
        good = step_ok and no_move
        ok &= good
        detail = ", ".join(f"{p}:{i}({k}키)" for p, i, k in entries)
        print(f"    {'✓' if good else '★'} {nm:<26} {detail}")
        if not step_ok:
            print(f"      ★ 보간이 STEP 이 아닙니다: {interps}"
                  f"  -> 키프레임 보간을 CONSTANT 로 두고"
                  f" export_force_sampling=False 로 내보내세요")
        if not no_move:
            print(f"      ★ translation 이 애니메이션됩니다 -> 이동이 생깁니다")

print("=" * 92)
if ok:
    print("✓ 통과. scale 이 STEP 보간이고 translation 애니메이션이 없습니다.")
    print("  STEP 은 다음 키까지 값을 그대로 유지하므로 보간이 일어나지 않습니다.")
    print()
    print("  열어보는 방법")
    print("   - 윈도우: Microsoft Store 의 '3D 보기'(3D Viewer) 앱이 GLB 를 바로 엽니다.")
    print("             또는 블렌더 File > Import > glTF 2.0")
    print("   - 갤럭시: 웹 페이지에 <model-viewer> 로 올리면 'AR 로 보기' 가 됩니다.")
    print("             (안드로이드 Scene Viewer 는 https 주소가 필요합니다)")
    print("   - 둘 다: https://gltf-viewer.donmccurdy.com 에 드래그&드롭")
else:
    print("★ 위 경고를 확인하세요.")
print("=" * 92)
