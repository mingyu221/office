#!/usr/bin/env python3
# =============================================================================
# 15_fix_glb.py  -  내보낸 GLB 를 고친다 (의존성 없음, python3 만 필요)
#
#  블렌더 glTF 익스포터가 두 가지 문제를 만든다.
#
#  1. interpolation 이 LINEAR 다.
#     export_force_sampling=False 를 줘도 매 프레임을 샘플링하며 LINEAR 로 쓴다.
#     키가 매 프레임에 있으니 보간 구간은 1/24초지만, 그 사이에 scale 이
#     0.001 -> 1 로 변하면서 오브젝트가 아주 짧게 '자라난다'.
#     STEP 으로 바꾸면 다음 키까지 값을 그대로 유지하므로 보간이 사라진다.
#
#  2. 오브젝트마다 애니메이션을 따로 만든다 (animation 5개, 각 1채널).
#     model-viewer / three.js / Scene Viewer 는 한 번에 애니메이션 하나만
#     재생하므로 첫 번째 오브젝트만 움직이고 나머지는 멈춘다.
#     채널을 하나의 애니메이션으로 합쳐야 전부 재생된다.
#
#  GLB 는 [헤더][JSON 청크][BIN 청크] 다. JSON 만 고치고 BIN 은 그대로 둔다.
#  bufferView 의 offset 은 BIN 청크 '내부' 기준이라 JSON 길이가 변해도 안전하다.
#
#  사용: python3 15_fix_glb.py o2_tunnel_final.glb
#  결과: o2_tunnel_final_fixed.glb
# =============================================================================
import json
import os
import struct
import sys

# ---------------------------- 설정 -------------------------------------------
MERGE_ANIMATIONS = True    # 여러 애니메이션을 하나로 합친다
FORCE_STEP       = True    # scale 채널의 보간을 STEP 으로
ANIM_NAME        = "Scene"
# -----------------------------------------------------------------------------

GLTF_MAGIC, JSON_CHUNK, BIN_CHUNK = 0x46546C67, 0x4E4F534A, 0x004E4942


def read_glb(path):
    with open(path, "rb") as fh:
        blob = fh.read()
    if len(blob) < 12:
        raise ValueError("파일이 너무 작습니다")
    magic, ver, total = struct.unpack("<III", blob[:12])
    if magic != GLTF_MAGIC:
        raise ValueError(f"GLB 매직이 아닙니다: {magic:#x}")
    if total != len(blob):
        print(f"  ! 헤더의 전체 길이 {total:,} 와 실제 {len(blob):,} 가 다릅니다")
    chunks, pos = [], 12
    while pos + 8 <= len(blob):
        clen, ctype = struct.unpack("<II", blob[pos:pos + 8])
        chunks.append((ctype, blob[pos + 8:pos + 8 + clen]))
        pos += 8 + clen
    js = next((json.loads(d.decode("utf-8")) for t, d in chunks if t == JSON_CHUNK),
              None)
    binc = next((d for t, d in chunks if t == BIN_CHUNK), None)
    if js is None:
        raise ValueError("JSON 청크를 찾지 못했습니다")
    return ver, js, binc, chunks


def write_glb(path, ver, js, binc):
    jb = json.dumps(js, separators=(",", ":")).encode("utf-8")
    jb += b" " * ((4 - len(jb) % 4) % 4)            # JSON 은 공백으로 패딩
    parts = [struct.pack("<II", len(jb), JSON_CHUNK), jb]
    if binc is not None:
        bb = binc + b"\x00" * ((4 - len(binc) % 4) % 4)   # BIN 은 0 으로 패딩
        parts += [struct.pack("<II", len(bb), BIN_CHUNK), bb]
    body = b"".join(parts)
    with open(path, "wb") as fh:
        fh.write(struct.pack("<III", GLTF_MAGIC, ver, 12 + len(body)))
        fh.write(body)


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python3 15_fix_glb.py <file.glb>")
    src = sys.argv[1]
    ver, js, binc, chunks = read_glb(src)

    nodes = js.get("nodes", [])
    name_of = {i: n.get("name", f"node{i}") for i, n in enumerate(nodes)}
    anims = js.get("animations", [])

    print("=" * 88)
    print(f"IN : {src}  ({os.path.getsize(src):,} 바이트)")
    print(f"     glTF {ver}  node {len(nodes)}개  animation {len(anims)}개"
          f"  청크 {[hex(t) for t, _ in chunks]}")
    print("-" * 88)
    if not anims:
        sys.exit("!! 애니메이션이 없습니다.")

    print("고치기 전:")
    for ai, a in enumerate(anims):
        smp = a.get("samplers", [])
        for ch in a.get("channels", []):
            s = smp[ch["sampler"]]
            nkeys = js["accessors"][s["input"]].get("count")
            print(f"  animation[{ai}] '{a.get('name','')}'"
                  f"  {name_of.get(ch['target'].get('node'),'?')}"
                  f"  {ch['target'].get('path')}"
                  f"  {s.get('interpolation','LINEAR')}  {nkeys}키")

    # ---- 1) 애니메이션 병합 ----
    if MERGE_ANIMATIONS and len(anims) > 1:
        samplers, channels = [], []
        for a in anims:
            base = len(samplers)
            samplers.extend(a.get("samplers", []))
            for ch in a.get("channels", []):
                ch2 = dict(ch)
                ch2["sampler"] = ch["sampler"] + base
                channels.append(ch2)
        js["animations"] = [{"name": ANIM_NAME,
                             "samplers": samplers, "channels": channels}]
        print("-" * 88)
        print(f"■ 애니메이션 {len(anims)}개 -> 1개로 병합"
              f" (샘플러 {len(samplers)}개, 채널 {len(channels)}개)")

    # ---- 2) scale 채널 보간을 STEP 으로 ----
    changed = 0
    if FORCE_STEP:
        for a in js["animations"]:
            smp = a.get("samplers", [])
            for ch in a.get("channels", []):
                if ch["target"].get("path") != "scale":
                    continue
                s = smp[ch["sampler"]]
                if s.get("interpolation") != "STEP":
                    s["interpolation"] = "STEP"
                    changed += 1
        print(f"■ scale 샘플러 {changed}개를 STEP 으로 변경")

    base, _ = os.path.splitext(src)
    out = base + "_fixed.glb"
    write_glb(out, ver, js, binc)

    # ---- 검증: 다시 읽어서 확인 ----
    print("-" * 88)
    ver2, js2, bin2, chunks2 = read_glb(out)
    size = os.path.getsize(out)
    print(f"OUT: {out}  ({size:,} 바이트 = {size/1048576:.1f} MB)")

    ok = True
    if bin2 != (binc or b"")[:len(bin2)] and binc is not None:
        if bin2[:len(binc)] != binc:
            print("  ★ BIN 청크가 바뀌었습니다")
            ok = False
    anims2 = js2.get("animations", [])
    if MERGE_ANIMATIONS and len(anims2) != 1:
        print(f"  ★ 애니메이션이 {len(anims2)}개입니다 (1개여야 함)")
        ok = False

    print("  고친 후:")
    seen_nodes = set()
    for a in anims2:
        smp = a.get("samplers", [])
        for ch in a.get("channels", []):
            s = smp[ch["sampler"]]
            nm = name_of.get(ch["target"].get("node"), "?")
            path = ch["target"].get("path")
            interp = s.get("interpolation", "LINEAR")
            nkeys = js2["accessors"][s["input"]].get("count")
            good = (path != "scale") or interp == "STEP"
            if path == "scale":
                seen_nodes.add(nm)
            if path in ("translation", "rotation"):
                print(f"    ★ {nm} 에 {path} 애니메이션이 있습니다 -> 이동이 생깁니다")
                good = False
            ok &= good
            print(f"    {'✓' if good else '★'} {nm:<26} {path:<12}"
                  f" {interp:<7} {nkeys}키")

    print("=" * 88)
    if ok:
        print("✓ 통과.")
        print("  - 애니메이션이 1개라 모든 오브젝트가 함께 재생됩니다.")
        print("  - scale 이 STEP 이라 보간이 일어나지 않습니다 (이동 없음).")
        print(f"  {os.path.basename(out)} 를 뷰어/기기에서 확인하세요.")
    else:
        print("★ 위 경고를 확인하세요.")
    print("=" * 88)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
