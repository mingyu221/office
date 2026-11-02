# O2 Tunnel 웹 뷰어

`index.html` 하나로 윈도우·안드로이드·아이폰에서 같은 모델을 본다.
[`<model-viewer>`](https://modelviewer.dev) 를 쓰며 빌드 과정이 없다.

| 플랫폼 | 동작 |
|---|---|
| 윈도우 / 맥 브라우저 | 3D 뷰 + 재생/타임라인 (AR 버튼은 안 뜸) |
| 안드로이드 (갤럭시) | 3D 뷰 + **AR 로 보기** → Scene Viewer |
| 아이폰 / 아이패드 | 3D 뷰 + **AR 로 보기** → AR Quick Look (`ios-src` 의 USDZ 사용) |

## 폴더 구조가 곧 주소

`?model=...` 로 파일을 지정하지 않는다. **폴더 이름이 곧 주소**다.

단계 수에 제한이 없다. 거쳐 가는 모든 폴더에 목록 페이지가 생긴다.

```
docs/
  index.html                      <- 목록 (video, paper 가 보임)
  models.json
  video/
    index.html                    <- 목록 (codh-tunnel, o2-tunnel 이 보임)
    models.json
    codh-tunnel/
      index.html                  <- 뷰어 (고칠 것 없음)
      model.glb
      model.usdz
    o2-tunnel/
      index.html
      model.glb
  paper/
    fig3/
      mechanism/
        index.html
        model.glb
```

주소:

```
https://mingyu221.github.io/office_claude/                      목록
https://mingyu221.github.io/office_claude/video/               video 목록
https://mingyu221.github.io/office_claude/video/codh-tunnel/   모델
https://mingyu221.github.io/office_claude/paper/fig3/mechanism/
```

뷰어는 **자기 폴더의 `model.glb` / `model.usdz`** 를 읽는다. 그래서 폴더째
복사하면 아무것도 안 고쳐도 동작하고, 제목은 폴더 이름에서 자동으로 만든다.

### 모델 추가

```bash
./viewer/add-model.sh <경로> <모델.glb> [모델.usdz] ["설명"]
```

예:

```bash
./viewer/add-model.sh video/codh-tunnel ~/Desktop/a.glb ~/Desktop/a.usdz "CODH 터널 10초"
git add docs && git commit -m "add model: video/codh-tunnel" && git push
```

폴더 생성, 파일 복사, 거쳐 가는 모든 단계의 `models.json` 갱신, 목록 페이지
배치까지 한다. 같은 경로로 다시 돌리면 덮어쓰고, 제목/설명은 유지한다.

폴더 이름에는 영문·숫자·한글·하이픈·언더스코어만 쓴다 (공백 금지).

### 목록 제목 바꾸기

`docs/<경로>/models.json` 의 `title` 을 고치면 된다.

```json
{ "root": false, "title": "동영상", "items": [ { "path": "codh-tunnel", "title": "CODH 터널" } ] }
```

목록 페이지는 **URL 깊이를 추측하지 않고** 이 파일의 `title` / `root` 를 읽는다.
GitHub Pages 의 `/<저장소>/` 접두사, 로컬 서버, user 사이트에서 깊이가 제각각
달라지기 때문이다.

### 그래도 파일을 직접 지정하고 싶으면

```
?model=다른.glb&usdz=다른.usdz     폴더 안의 다른 파일
?model=https://raw.githubusercontent.com/<사용자>/<저장소>/<브랜치>/<경로>.glb
?title=제목&note=설명              제목 덮어쓰기
```

`raw.githubusercontent.com` 은 `access-control-allow-origin: *` 를 보내므로
저장소 어디에 있는 파일이든 불러올 수 있다 (구글 드라이브는 이 헤더가 없어서 안 된다).

## 윈도우/맥에서 바로 보기 (로컬)

브라우저가 `file://` 에서 모델 파일 읽는 것을 막기 때문에 간단한 서버가 필요하다.

```bash
cd <파일들이 있는 폴더>
python3 -m http.server 8000
```

브라우저에서 `http://localhost:8000` 을 연다.

## 갤럭시에서 AR 로 보기 (GitHub Pages)

안드로이드의 Scene Viewer 는 **https 주소**를 요구하므로 호스팅이 필요하다.
이 저장소가 공개라면 GitHub Pages 가 가장 간단하다.

```bash
# 저장소 루트에서
mkdir -p docs
cp viewer/index.html docs/
cp /path/to/o2_tunnel_final.glb docs/
cp /path/to/o2_tunnel_final_frozen.usdz docs/
git add docs && git commit -m "add web viewer" && git push
```

그 다음 GitHub 저장소 → **Settings → Pages** → Source 를 `Deploy from a branch`,
브랜치를 현재 브랜치, 폴더를 `/docs` 로 지정한다. 몇 분 뒤
`https://<사용자>.github.io/<저장소>/` 로 열린다. 그 주소를 갤럭시 브라우저에서
열고 **AR 로 보기** 를 누른다.

GLB 가 20MB 안팎이면 git 에 올려도 되지만, 100MB 를 넘으면 GitHub 가 거부한다.

## 참고

- `mv.src = ...` 처럼 **프로퍼티로 설정하면 안 된다.** model-viewer 스크립트가
  CDN 에서 늦게 도착해 커스텀 엘리먼트가 아직 업그레이드되지 않았으면, 그 할당이
  엘리먼트의 접근자를 가려버려 모델이 영원히 로드되지 않는다. 이 페이지는
  `setAttribute('src', ...)` 를 쓴다.
- Microsoft 3D Viewer 는 2026년 2월 지원 종료, 7월 1일 스토어에서 제거됐다.
  이미 설치돼 있으면 계속 쓸 수 있지만 새로 설치할 수 없다. 이 페이지나
  Babylon.js Sandbox, gltf-viewer.donmccurdy.com 을 쓴다.
