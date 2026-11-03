# office

3D 모델을 웹과 AR 로 공유하는 저장소. 블렌더에서 만든 모델을
USDZ(아이폰) 와 GLB(윈도우·안드로이드) 로 내보내고, GitHub Pages 에 올려
링크 하나로 공유한다. 설치할 것이 없고 휴대폰에서는 AR 로 볼 수 있다.

현재 올라와 있는 것은 단백질 터널을 통과하는 산소(O2) 분자 궤적
애니메이션이며, 분류 폴더를 나눠 다른 모델도 같이 둘 수 있다.

## 보기

| 주소 | 내용 |
|---|---|
| **https://mingyu221.github.io/office/** | 전체 목록 |
| https://mingyu221.github.io/office/video/ | `video` 분류 목록 |
| https://mingyu221.github.io/office/video/codh-tunnel/ | CODH 터널 모델 |

| 기기 | 동작 |
|---|---|
| 윈도우·맥 브라우저 | 3D 뷰 + 재생/타임라인 (AR 버튼은 안 뜸) |
| 안드로이드(갤럭시) | 3D 뷰 + **AR 로 보기** → Scene Viewer |
| 아이폰·아이패드 | 3D 뷰 + **AR 로 보기** → AR Quick Look |

## 모델 추가하기

명령 한 줄이면 된다. 폴더 생성, 파일 복사, 목록 갱신까지 한다.

```bash
cd ~/Desktop/vision/office
./viewer/add-model.sh <경로> <모델.glb> [모델.usdz] ["설명"]
git add docs && git commit -m "add model: <경로>" && git push
```

실제 예:

```bash
./viewer/add-model.sh video/codh-tunnel \
  ~/Desktop/vision/frame/chcodh2_o2_tunnel_10sec_video.glb \
  ~/Desktop/vision/frame/o2_tunnel_10sec_video.usdz \
  "단백질 터널 산소 궤적 · 10초 · 5구간"
git add docs && git commit -m "add model: video/codh-tunnel" && git push
```

푸시하고 1~2분 뒤 `https://mingyu221.github.io/office/video/codh-tunnel/`
에서 열린다. 브라우저 캐시가 남으면 강력 새로고침(맥 `Cmd+Shift+R`).

### 인자 설명

| 인자 | 설명 |
|---|---|
| `<경로>` | 슬래시로 나눈 폴더 경로. 그대로 주소가 된다. 단계 수 제한 없음 |
| `<모델.glb>` | 필수. 윈도우·안드로이드용 |
| `[모델.usdz]` | 선택. 없으면 아이폰 AR 만 동작하지 않음 |
| `["설명"]` | 선택. 목록 페이지에 작게 표시됨 |

폴더 이름에는 영문·숫자·한글·하이픈·언더스코어만 쓴다 (공백·슬래시 금지).
같은 경로로 다시 돌리면 덮어쓴다 — 모델 교체도 같은 명령으로 한다.

### 분류를 새로 만들려면

경로만 바꾸면 중간 단계 목록 페이지까지 알아서 생긴다.

```bash
./viewer/add-model.sh paper/fig3/mechanism ~/어디/x.glb "" "논문 Figure 3"
# -> /paper/ , /paper/fig3/ , /paper/fig3/mechanism/ 이 모두 생성됨
```

## 폴더 구조

`docs/` 아래가 그대로 웹 주소가 된다. GitHub Pages 가 이 폴더만 서빙한다.

```
docs/
  index.html                      목록 (video 가 보임)
  models.json
  video/
    index.html                    목록 (codh-tunnel 이 보임)
    models.json
    codh-tunnel/
      index.html                  뷰어 — 고칠 것 없음
      model.glb                   윈도우·안드로이드
      model.usdz                  아이폰 AR
```

뷰어는 **자기 폴더의 `model.glb` / `model.usdz`** 를 읽는다. 그래서 폴더를
복사하면 아무것도 안 고쳐도 동작하고, 제목은 폴더 이름에서 자동으로 만든다.

## 목록 제목 바꾸기

`docs/<경로>/models.json` 의 `title` 을 고치고 푸시한다.

```json
{
  "root": false,
  "title": "동영상",
  "items": [
    { "path": "codh-tunnel", "title": "CODH 터널", "note": "10초 · 5구간" }
  ]
}
```

`add-model.sh` 를 다시 돌려도 고쳐 둔 `title` 과 `note` 는 유지된다.

## 파일을 직접 지정하기

폴더 규칙을 벗어나야 할 때 주소 뒤에 붙인다.

```
?model=다른.glb&usdz=다른.usdz
?model=https://raw.githubusercontent.com/mingyu221/office/main/경로/x.glb
?title=제목&note=설명
```

`raw.githubusercontent.com` 은 `access-control-allow-origin: *` 를 보내므로
저장소 어느 브랜치·폴더의 파일이든 불러올 수 있다.
(구글 드라이브는 이 헤더가 없어서 안 된다.)

## 작업 기록

원래 이슈("산소가 원점에서 날아옴")의 진단 과정, 측정값, 막다른 길, 도구별 함정은
**[`HANDOVER.md`](HANDOVER.md)** 에 정리돼 있다. 같은 문제를 다시 만나면 거기부터
읽으면 된다.

## 모델은 어떻게 만들었나

블렌더 → USDZ/GLB 파이프라인과, ARKit 에서 "산소가 원점에서 날아오던" 문제를
어떻게 잡았는지는 **[`blender/README.md`](blender/README.md)** 에 있다.

요약하면 두 가지였다.

1. **타임코드 1칸이 0.5초였다.** ARKit 은 샘플 사이를 선형 보간하므로
   `scale 0.0001 → 1` 이 0.5초에 걸쳐 일어났다. 240프레임/24fps 로 되돌려
   0.042초로 줄였다.
2. **오리진이 월드 원점에 있었다.** 스케일은 오리진을 향해 수축하므로
   지오메트리가 원점에서 자라나듯 보였다. 오리진을 각자 지오메트리 중심으로
   옮기고, 최종적으로는 `scale` 애니메이션을 USD `visibility` token 으로
   바꿔 보간 자체를 불가능하게 만들었다.

AR 조작 회전축이 단백질 바깥에 생기던 문제는 카메라 6개가 usdz 에 포함돼
바운딩 박스를 늘린 탓이었다. 메쉬만 내보내고 씬 중심을 원점에 맞춰 해결했다.

## 폴더

| 폴더 | 내용 |
|---|---|
| `docs/` | 웹에 서빙되는 것 — 목록 페이지, 뷰어, 모델 파일 |
| `viewer/` | 원본 템플릿과 `add-model.sh`. 여기를 고치면 다음 추가분부터 반영 |
| `blender/` | 블렌더 스크립트와 USD/GLB 후처리 도구 |
