import { DOWNLOAD_LABEL, DOWNLOAD_URL } from "../config";

export const HERO_TITLE = "Gen Interface KR";
export const HERO_COPY_KO =
  "Gen Interface KR은 디지털 인터페이스를 위해 설계된 영문과 국문의 조화를 목표로 하는 서체입니다. 명쾌한 UI용 서체인 Inter에 Noto Sans KR의 국문 글리프를 맞추어, 다국어 환경에서 일관된 가독성을 실현합니다.";
export const HERO_COPY_EN =
  "Gen Interface KR is a typeface designed for digital interfaces that aims to harmonize Latin script with Korean. Blending Inter with Noto Sans KR, it ensures consistent readability across multiple languages.";

export function Hero() {
  return (
    <section className="hero">
      <h1 className="hero__title">{HERO_TITLE}</h1>

      {/* `hero__row` + `hero__descs` are no-op containers at desktop (children are
          absolutely positioned), but at <=1100px they switch to flex layout so
          download sits next to a stacked description column. */}
      <div className="hero__row">
        <a className="hero__download" href={DOWNLOAD_URL}>
          <Download />
        </a>

        <div className="hero__descs">
          <p className="hero__desc hero__desc--ko">{HERO_COPY_KO}</p>
          <p className="hero__desc hero__desc--en">{HERO_COPY_EN}</p>
        </div>
      </div>
    </section>
  );
}

export function Download() {
  return (
    <>
      <span className="download-icon-block">
        <DownloadIcon />
        <span className="download-icon-rule" aria-hidden="true" />
      </span>
      <span className="download-text-block">
        <span className="download-text">{DOWNLOAD_LABEL}</span>
        <span className="download-text-rule" aria-hidden="true" />
      </span>
    </>
  );
}

function DownloadIcon() {
  return (
    <svg
      className="download-icon"
      viewBox="0 0 24 27"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeMiterlimit="10"
      aria-hidden="true"
    >
      <path d="M11.707 0L11.707 25" />
      <path d="M0.707 14L11.707 25L22.707 14" />
    </svg>
  );
}
