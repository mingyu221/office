# O2 터널 애니메이션 작업 인계서 (2026-11-02, 해결 완료)

처음 인계서의 **"4. 현재 남은 이슈 — 원점에서 이동(날아오는) 현상"** 은 해결됐다.
원인을 측정으로 확정했고, 같은 문제를 다시 만나지 않도록 아래에 전부 적는다.

## 1. 최종 결과물

| | |
|---|---|
| 공개 주소 | https://mingyu221.github.io/office_claude/video/codh-tunnel/ |
| 아이폰 | `model.usdz` (21.8MB) — AR Quick Look |
| 윈도우·갤럭시 | `model.glb` (20.5MB) — Scene Viewer / 웹뷰어 |
| 애니메이션 | 240프레임 @ 24fps = 9.96초, 5구간 × 2초 |
| 저장소 위치 | `docs/video/codh-tunnel/` |

측정된 최종 지표 (`UsdGeom.BBoxCache` 로 실제 usdz 를 열어 확인):

```
timeCode 1.0-240.0  tps=24.0
visibility 애니메이션 prim 5개 (F2~F6)
xformOp 타임샘플을 가진 prim 0개     <- 이동이 수학적으로 불가능
AR 회전축 (0.0, 0.0, 0.0)            <- 단백질 중앙
```

## 2. 실제 원인 (둘이 겹쳐 있었다)

### 2-1. 타임코드 1칸이 0.5초였다

내보낸 usda 를 열어보니:

```
startTimeCode=1  endTimeCode=6  timeCodesPerSecond=2.0
-> 타임코드 1칸 = 0.500초
```

ARKit 은 샘플 사이를 **선형 보간**한다. 그래서 `scale 0.0001 → 1` 이 0.5초에
걸쳐 일어났다. 이것이 "스윽 날아오는" 의 정체다.

**프레임 수를 6개로 줄여 '순간이동' 을 만들려던 전략이 오히려 보간 시간을
늘렸다.** 전환을 빠르게 하려면 프레임이 더 **많아야** 한다. 240프레임/24fps 로
되돌려 0.042초로 줄였다 (12배 단축).

### 2-2. 오리진이 월드 원점에 있었다

블렌더에서 스케일은 항상 **오리진을 향해** 수축한다. 측정값:

| 오브젝트 | 반경 | 붕괴 시 중심 이동 | 단백질 반경(51.4) 대비 |
|---|---|---|---|
| O2_Trajectory_F2 | 10.90 | 13.71 | 26.7% |
| O2_Trajectory_F3 | 15.42 | 15.84 | 30.9% |
| O2_Trajectory_F4 | 14.49 | 16.01 | 31.3% |
| O2_Trajectory_F5 | 28.36 | 19.46 | 38.1% |
| O2_Trajectory_F6 | 23.29 | 24.00 | 46.7% |

Location 키프레임이 **하나도 없어도** 증상이 같다. `translate` 는 끝까지
`(0,0,0)` 정적이었다.

또 하나: **각 오브젝트가 분자 하나가 아니다.** 버텍스 수의 최대공약수가 484 이고
각각 484 단위의 2, 5, 6, 8, 11 개 배수(합계 32개)다. 즉 **여러 구체가 합쳐진
궤적 묶음**이라, 오리진을 그룹 중심으로 옮겨도 scale 수축 시 내부 구체들이
중심으로 모이는 움직임이 남는다. 그래서 최종적으로는 scale 자체를 버렸다.

## 3. 최종 해법

`scale` 애니메이션을 **USD `visibility` token** 으로 치환했다.
`visibility` 는 숫자가 아니라 `inherited` / `invisible` 토큰이라 **보간이 정의되지
않는다.** ARKit 이 중간값을 만들 방법이 없다. `scale` 을 정적 값으로 고정하면
보간할 트랜스폼 채널이 하나도 남지 않는다.

```usda
def Xform "O2_Trajectory_F6"
{
    float3 xformOp:scale = (1, 1, 1)                   # 정적
    double3 xformOp:translate = (17.03, -17.63, 0.31)  # 정적
    token visibility.timeSamples = {
        1: "invisible",
        193: "inherited",
    }
}
```

glTF 에는 `visibility` 가 없지만 애니메이션 샘플러에 `interpolation: "STEP"` 이
있다. 같은 효과다.

## 4. 별개 이슈: AR 조작 회전축이 단백질 바깥에 생김

AR Quick Look 은 **씬 전체 바운딩 박스 중심**을 조작 회전축으로 쓴다.
씬의 `Viewpoint` 카메라 6개가 `(0, -279.84, 0)` 에 있어서:

```
카메라 포함: bbox y [-279.8, 51.4]  중심 y = -114.2   <- 단백질 반경의 2.2배
카메라 제외: bbox y [ -51.4, 51.4]  중심 y =    0.0
```

메쉬만 선택해 `selected_objects_only=True` 로 내보내고, 씬 전체를 평행이동해
bbox 중심을 원점에 맞춰 해결했다.

**주의: bbox 중심 ≠ 버텍스 median.** 처음 인계서의 "바운딩 박스 중심을 원점으로
정렬" 과 오리진 교정은 둘 다 median 기준이었다. median 은 버텍스 밀집 영역으로
치우치므로 bbox 중심과 어긋난다 (테스트에서 32.99 차이).

## 5. 최종 파이프라인

| 단계 | 도구 | 실행 위치 | 결과 |
|---|---|---|---|
| 0 | `00_list_objects.py` | 블렌더 | 오브젝트 이름 파악, `PATTERNS` 값 |
| 1 | `13_full_fix.py` | 블렌더 | 리타이밍 + 오리진 + 중심 교정 + usda/usdz |
| 2 | `10_freeze_to_visibility.py` | 터미널 | `scale → visibility`, usdc 변환, usdz 재패키징 |
| 3 | `14_export_glb.py` | 블렌더 | GLB 내보내기 |
| 4 | `15_fix_glb.py` | 터미널 | 애니메이션 병합 + STEP 보간 |
| 5 | `viewer/add-model.sh` | 터미널 | `docs/` 에 배치, 목록 갱신 |

**1단계 끝나면 반드시 `File > Save`.** 저장 안 하고 블렌더를 다시 열어서 09 의
작업이 통째로 날아간 적이 있다 (centered 파일이 6프레임 2fps 로 나왔다).
13 이 09+11 을 합친 이유다.

## 6. Blender 5.3.0 Beta 에서 확인된 제약

- **애니메이션 `visibility` 를 내보내지 않는다.** `hide_viewport` 키를 넣어도
  usda 에 `visibility.timeSamples` 가 0개다.
- **숨겨진 프레임의 `scale` 샘플을 쓰지 않는다.** `hide_viewport` 키를 넣으면
  오히려 scale 키프레임이 유실된다. 블렌더에서 6키였던 것이 usda 에서 1~3개로
  줄고, 마지막 프레임에만 보이던 F6 은 샘플 1개(1.0)만 남아 **영구 표시**됐다.
  → `07_visibility_fix.py` 는 이 버전에서 쓰면 안 된다.
- `export_textures`, `visible_objects_only` 옵션이 없다.
- **glTF: `export_force_sampling=False` 를 줘도 매 프레임 샘플링하며 LINEAR 로
  쓴다** (채널당 240키). STEP 이 필요하면 15 로 후처리해야 한다.
- **glTF: 오브젝트마다 애니메이션을 따로 만든다** (animation 5개, 각 1채널).
  model-viewer / three.js / Scene Viewer 는 한 번에 애니메이션 하나만 재생하므로
  첫 오브젝트만 움직이고 나머지는 멈춘 채 계속 보인다. 실측으로 확인했다:
  고치기 전 5초 시점에 큐브 4개 동시 노출, 고친 후 1개.

## 7. 막다른 길 (다시 시도하지 말 것)

| 시도 | 결과 |
|---|---|
| `scale` 을 완전한 `0` 으로 | ARKit 이 위치를 월드 원점으로 리셋 (처음 인계서 3-2) |
| 블렌더에서 `CONSTANT` 보간 지정 | USD/glTF 는 per-key 보간을 그대로 가져가지 않음 |
| 프레임 수를 6개로 줄여 순간이동 | 타임코드 1칸이 0.5초가 되어 **역효과** |
| `hide_viewport` 키프레임 (Blender 5.3) | visibility 미지원 + scale 샘플 유실 |
| 오리진만 교정 | 묶음 메쉬라 내부 구체들이 그룹 중심으로 모임 |
| 구글 드라이브로 웹뷰어 연결 | CORS 헤더 없음. `raw.githubusercontent.com` 은 됨 |
| Microsoft 3D Viewer 로 GLB 열기 | 2026-02 지원 종료, 2026-07-01 스토어 제거 |

## 8. 도구 중 함정이 있었던 것

- `Usd.Stage.Open().Export()` 는 애셋 경로를 **절대 경로로 바꾼다.**
  usdz 안의 `@./textures/x.exr@` 참조가 깨져 기기에서 텍스처가 사라진다.
  `Sdf.Layer.FindOrOpen().Export()` 를 써야 상대 경로가 보존된다.
- `obj.location` 을 바꿔도 `matrix_world` 는 depsgraph 가 다시 돌기 전까지 낡은
  값이다. `bpy.context.view_layer.update()` 를 불러야 한다. 이게 없어서 중심
  교정 후 bbox 를 재계산했더니 이동 전과 같은 값이 나왔다.
- `model-viewer` 에 `mv.src = ...` 로 **프로퍼티 설정 금지.** 스크립트가 CDN 에서
  늦게 도착해 커스텀 엘리먼트가 아직 업그레이드되지 않았으면 그 할당이 접근자를
  가려버려 모델이 영원히 로드되지 않는다. `setAttribute('src', ...)` 를 쓴다.
- 목록 페이지에서 **URL 깊이로 루트 판별 금지.** GitHub Pages 프로젝트 사이트는
  `/<저장소>/` 접두사가 붙어 깊이가 1 늘어난다. `models.json` 에 `root` 를 적는다.
- zsh 는 대화형 셸에서 `#` 를 주석으로 보지 않는다 (`interactive_comments` 기본
  꺼짐). 명령에 주석을 섞으면 `command not found: #` 가 난다.

## 9. 검증 방법

추측하지 말고 내보낸 파일을 직접 읽어 확인한다.

```bash
# usda/usdz 타이밍·이동 측정 (pip 불필요)
python3 blender/08_inspect_usda.py <파일>.usda

# AR 회전축을 ARKit 과 같은 방식으로 계산 (pip install usd-core 필요)
python3 blender/12_verify_center.py <파일>.usdz

# GLB 의 보간·애니메이션 구조 (15 가 끝에 자동으로 함)
python3 blender/15_fix_glb.py <파일>.glb
```

## 10. 남은 것

- **갤럭시에서 미확인.** GLB·STEP 보간·애니메이션 병합은 브라우저로 검증했지만
  실제 Scene Viewer AR 은 아직 안 해봤다.
- 블렌더 실행이 필요한 스크립트(`13`, `14`)는 이 세션에서 직접 돌려볼 수 없어
  문법 검사와 로직 단위 테스트만 했다. 실행 결과는 출력으로 확인했다.
