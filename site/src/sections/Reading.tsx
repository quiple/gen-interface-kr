import { useEffect, useState } from "react";
import { SectionHead } from "./SectionHead";
import { Slider } from "./Slider";

const KR =
  "Gen Interface KR은 디지털 인터페이스를 위해 설계된 영문과 국문의 조화를 목표로 하는 서체입니다. 명쾌한 UI용 서체인 Inter에 Noto Sans KR의 국문 글리프를 맞추어, 다국어 환경에서 일관된 가독성을 실현합니다.";

const EN =
  "Gen Interface KR is a typeface designed for digital interfaces that aims to harmonize Latin script with Korean. Blending Inter with Noto Sans KR, it ensures consistent readability across multiple languages.";

const WEIGHT_NAMES: Record<number, string> = {
  100: "Thin",
  200: "ExtraLight",
  300: "Light",
  400: "Regular",
  500: "Medium",
  600: "SemiBold",
  700: "Bold",
  800: "ExtraBold",
};

/** Reading-section size labels: the desktop string ("32px" etc.) is shown
 *  above the breakpoint, the mobile string is shown below it — matches the
 *  CSS overrides on .reading__row-text--{32,21,12} that swap to absolute
 *  px on mobile so the text doesn't shrink with the html font-size scaling. */
function PxLabel({ desktop, mobile }: { desktop: string; mobile: string }) {
  return (
    <span className="reading__row-label">
      <span className="sp-none">{desktop}</span>
      <span className="pc-none">{mobile}</span>
    </span>
  );
}

export function Reading() {
  const [weight, setWeight] = useState(400);

  // Preload every weight × the rendered KR/EN text on mount so dragging
  // the slider doesn't trigger first-time WOFF2 fetches that briefly
  // swap fallback fonts in. The webfont is sliced via unicode-range, so
  // each weight's WOFF2 chunks for these specific characters need to be
  // primed individually — passing the actual text to `document.fonts.load`
  // resolves the unicode-range matching and pulls only the chunks that
  // cover it. We fire and forget; subsequent slider moves consult the
  // now-warm font cache.
  useEffect(() => {
    if (typeof document === "undefined" || !("fonts" in document)) return;
    const text = KR + EN;
    for (const w of Object.keys(WEIGHT_NAMES)) {
      document.fonts.load(`${w} 16px 'Gen Interface KR'`, text);
    }
  }, []);

  return (
    <section className="reading">
      <SectionHead name="Reading" />

      <div className="reading__body">
        <div className="controls">
          <hr className="controls__rule" />
          <Slider
            kind="weight"
            value={weight}
            min={100}
            max={800}
            step={100}
            onChange={setWeight}
            label={WEIGHT_NAMES[weight]}
            pillLabels={Object.values(WEIGHT_NAMES)}
          />
        </div>

        <div className="reading__rows" style={{ fontWeight: weight }}>
          <div className="reading__row">
            <hr className="reading__row-rule" />
            <div className="reading__row-inner">
              <PxLabel desktop="32px" mobile="24px" />
              <p className="reading__row-text--32">{KR}</p>
            </div>
          </div>

          <div className="reading__row">
            <hr className="reading__row-rule" />
            <div className="reading__row-inner">
              <PxLabel desktop="32px" mobile="24px" />
              <p className="reading__row-text--32">{EN}</p>
            </div>
          </div>

          <div className="reading__row">
            <hr className="reading__row-rule" />
            <div className="reading__row-cols">
              <div className="reading__col-21">
                <PxLabel desktop="21px" mobile="15px" />
                <p className="reading__row-text--21">{KR}</p>
              </div>
              <div className="reading__col-12">
                <PxLabel desktop="12px" mobile="10px" />
                <p className="reading__row-text--12">{KR}</p>
              </div>
            </div>
          </div>

          <div className="reading__row">
            <hr className="reading__row-rule" />
            <div className="reading__row-cols">
              <div className="reading__col-21">
                <PxLabel desktop="21px" mobile="15px" />
                <p className="reading__row-text--21">{EN}</p>
              </div>
              <div className="reading__col-12">
                <PxLabel desktop="12px" mobile="10px" />
                <p className="reading__row-text--12">{EN}</p>
              </div>
            </div>
          </div>

          {/* Mobile-only: at desktop the 12px sample sits next to the 21px in
              the same row; on narrow viewports it reflows into its own row to
              avoid a long, awkward stretch of body copy at one column width. */}
          <div className="reading__row reading__row--mobile-only">
            <hr className="reading__row-rule" />
            <div className="reading__row-inner">
              <PxLabel desktop="12px" mobile="10px" />
              <p className="reading__row-text--12">{KR}</p>
            </div>
          </div>

          <div className="reading__row reading__row--mobile-only">
            <hr className="reading__row-rule" />
            <div className="reading__row-inner">
              <PxLabel desktop="12px" mobile="10px" />
              <p className="reading__row-text--12">{EN}</p>
            </div>
          </div>

          <hr className="reading__row-rule" />
        </div>
      </div>
    </section>
  );
}
