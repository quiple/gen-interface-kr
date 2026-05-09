# Gen Interface KR

<p><strong><a href="https://github.com/quiple/gen-interface-kr/blob/main/README.md">English</a></strong> | 한국어</p>

Gen Interface KR은 디지털 인터페이스를 위해 설계된 영문과 국문의 조화를 목표로 하는 서체입니다.  
명쾌한 UI용 서체인 Inter에 Noto Sans KR의 국문 글리프를 맞추어, 다국어 환경에서 일관된 가독성을 실현합니다.

## 개요

### 2개 패밀리

- **Gen Interface KR**: 범용/본문용
- **Gen Interface KR Display**: 제목용

### 8개 웨이트

- 100: Thin
- 200: ExtraLight
- 300: Light
- 400: Regular
- 500: Medium
- 600: SemiBold
- 700: Bold
- 800: ExtraBold

### 웹 폰트

웹 프로젝트에서 head 내의 스타일시트 로드만으로 웹 폰트를 사용할 수 있습니다.  
[Google Fonts와 동일한 서브셋화](https://developers.googleblog.com/google-fonts-launches-korean-support/)를 통해, 단일 폰트 데이터와 비교해 빠른 표시를 실현했습니다.

#### Gen Interface KR

```html
<!-- 
 index.html 
 100.css ... 800.css
 -->
<head>
  <link
    rel="stylesheet"
    href="https://cdn.jsdelivr.net/npm/gen-interface-kr@latest/400.css"
  />
</head>
```

```css
/* style.css */
body {
  font-family: "Gen Interface KR", sans-serif;
  font-weight: 400; /* 100–800 */
}
```

#### Gen Interface KR Display

```html
<!-- 
 index.html 
 display-100.css ... display-800.css
 -->
<head>
  <link
    rel="stylesheet"
    href="https://cdn.jsdelivr.net/npm/gen-interface-kr@latest/display-800.css"
  />
</head>
```

```css
/* style.css */
h1,
h2 {
  font-family: "Gen Interface KR Display", sans-serif;
  font-weight: 800; /* 100–800 */
}
```

### CSS 목록

- `all.css`: 전체 16개 웨이트의 CSS
- `400.css`: Gen Interface KR Regular (400)의 CSS
- `display-400.css`: Gen Interface KR Display Regular (400)의 CSS

## 리포지터리

```text
src/
  font/       # 핵심 폰트 생성
  webfont/    # 웹 폰트 배포용 CSS + 서브셋 WOFF2
  release/    # GitHub Release / npm 배포용 패키징
site/         # 랜딩 페이지 겸 폰트 표시 확인 사이트
vendor/
  fonts/      # Inter와 Noto Sans KR의 입력 폰트
  nam-files/  # 웹 폰트 분할용 googlefonts/nam-files 데이터
docs/
  ARCHITECTURE.md  # 빌드 파이프라인 전체 사양
```

이 저장소의 주요 성과물은 `src/font/`에서 생성하는 폰트 패밀리입니다. `src/webfont/`와 `src/release/`는 해당 생성물로부터 파생되는 배포·공개용 공정입니다. 생성물은 `dist/` 아래에 위치하며, 저장소에는 커밋하지 않습니다.

빌드 파이프라인이나 내부 사양의 상세한 내용은 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)를 참조해 주세요.

## 빠른 시작

```bash
make font     # dist/ttf/에 폰트 생성
make site     # 사이트 빌드 (site/dist/)
make serve    # 사이트 로컬 개발 서버
```

웹 폰트 서브셋화, 릴리스 패키징, 테스트, npm 공개 등의 모든 명령어는[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)의 'Commands' 섹션을 참조해 주세요.

## 라이선스

이 저장소의 소스 코드는 [MIT License](LICENSE), 생성된 폰트 본체는 [SIL Open Font License 1.1](https://scripts.sil.org/OFL)입니다.

`vendor/` 하위 폴더는 각각 동봉된 라이선스를 따릅니다.

## 레퍼런스

- [Noto Sans KR](https://github.com/notofonts/noto-cjk)
- [Inter](https://github.com/rsms/inter)
