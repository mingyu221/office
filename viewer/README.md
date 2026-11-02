# O2 Tunnel 웹 뷰어

`index.html` 하나로 윈도우·안드로이드·아이폰에서 같은 모델을 본다.
[`<model-viewer>`](https://modelviewer.dev) 를 쓰며 빌드 과정이 없다.

| 플랫폼 | 동작 |
|---|---|
| 윈도우 / 맥 브라우저 | 3D 뷰 + 재생/타임라인 (AR 버튼은 안 뜸) |
| 안드로이드 (갤럭시) | 3D 뷰 + **AR 로 보기** → Scene Viewer |
| 아이폰 / 아이패드 | 3D 뷰 + **AR 로 보기** → AR Quick Look (`ios-src` 의 USDZ 사용) |

## 필요한 파일

`index.html` 과 **같은 폴더**에 두 파일을 둔다.

```
index.html
o2_tunnel_final.glb            # 14_export_glb.py 결과 (안드로이드/윈도우)
o2_tunnel_final_frozen.usdz    # 10_freeze_to_visibility.py 결과 (아이폰 AR)
```

이름이 다르면 `index.html` 상단의 `DEFAULT_GLB` / `DEFAULT_USDZ` 를 고치거나,
주소에 붙여서 덮어쓴다: `index.html?model=다른이름.glb&usdz=다른이름.usdz`

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
