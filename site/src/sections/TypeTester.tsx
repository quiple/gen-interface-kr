import { useState, useSyncExternalStore } from "react";
import { SectionHead } from "./SectionHead";
import { Slider } from "./Slider";

type TesterRow = { weight: number; label: string; en: string; jp: string };

// Split into separate en/jp halves so the mobile layout can break between
// them — desktop joins with a space, mobile joins with a newline.
const ROWS: TesterRow[] = [
  { weight: 100, label: "Thin", en: "Gyroscope", jp: "자이로스코프" },
  { weight: 200, label: "ExtraLight", en: "Central Gate", jp: "중앙개찰구" },
  { weight: 300, label: "Light", en: "Driving Range", jp: "주행가능거리" },
  { weight: 400, label: "Regular", en: "Depth 123m", jp: "수심 123m" },
  { weight: 500, label: "Medium", en: "Breakfast Included", jp: "조식 포함" },
  {
    weight: 600,
    label: "SemiBold",
    en: "Cruise Control",
    jp: "크루즈 컨트롤",
  },
  { weight: 700, label: "Bold", en: "Thermography", jp: "열화상 카메라" },
  {
    weight: 800,
    label: "ExtraBold",
    en: "Seoul Clear 27℃",
    jp: "서울 맑음 27℃",
  },
];

const MOBILE_QUERY = "(max-width: 48.75rem)";

function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (onStoreChange) => {
      if (typeof window === "undefined") return () => {};
      const mq = window.matchMedia(query);
      mq.addEventListener("change", onStoreChange);
      return () => mq.removeEventListener("change", onStoreChange);
    },
    () => (typeof window === "undefined" ? false : window.matchMedia(query).matches),
    () => false,
  );
}

const FAMILY_NORMAL = "'Gen Interface KR', sans-serif";
const FAMILY_DISPLAY = "'Gen Interface KR Display', sans-serif";

const SIZE_MIN = 16;
const SIZE_MAX = 128;
const SIZE_DEFAULT = 48;

type TesterRowsProps = {
  activeStyle: "normal" | "display";
  size: number;
  sep: string;
};

function createInitialValues(sep: string): Record<string, string> {
  return Object.fromEntries(
    ROWS.map(({ label, en, jp }) => [label, `${en}${sep}${jp}`]),
  );
}

function TesterRows({ activeStyle, size, sep }: TesterRowsProps) {
  const [values, setValues] = useState(() => createInitialValues(sep));

  const updateValue = (label: string, value: string) => {
    setValues((prev) => ({ ...prev, [label]: value }));
  };

  return (
    <div className="tester__rows" style={{ fontSize: `${size / 16}rem` }}>
      {ROWS.map(({ weight, label }) => {
        const value = values[label] ?? "";

        return (
          <div key={label} className="tester__row">
            <div className="tester__row-head">
              <hr className="tester__row-rule" />
              <span className="tester__row-label">{label}</span>
            </div>
            <div className="tester__phrase-stack">
              {(
                [
                  ["normal", FAMILY_NORMAL],
                  ["display", FAMILY_DISPLAY],
                ] as const
              ).map(([familyKey, fontFamily]) => {
                const active = activeStyle === familyKey;

                return (
                  <textarea
                    key={familyKey}
                    className={`tester__row-phrase${active ? " is-active" : ""}`}
                    value={value}
                    spellCheck={false}
                    autoComplete="off"
                    rows={1}
                    readOnly={!active}
                    tabIndex={active ? 0 : -1}
                    aria-hidden={!active}
                    onChange={(event) => updateValue(label, event.target.value)}
                    style={{ fontFamily, fontWeight: weight }}
                  />
                );
              })}
            </div>
          </div>
        );
      })}
      <hr className="tester__row-rule" />
    </div>
  );
}

export function TypeTester() {
  const [style, setStyle] = useState<"normal" | "display">("normal");
  const [size, setSize] = useState(SIZE_DEFAULT);
  const isMobile = useMediaQuery(MOBILE_QUERY);
  const sep = isMobile ? "\n" : " ";

  return (
    <section className="tester">
      <SectionHead name="Type Tester" />

      <div className="tester__body">
        <div className="controls">
          <hr className="controls__rule" />

          <div className="radio-group">
            <button
              type="button"
              className={`radio${style === "normal" ? " radio--active" : ""}`}
              onClick={() => setStyle("normal")}
            >
              <span className="radio__circle" />
              Normal
            </button>
            <button
              type="button"
              className={`radio${style === "display" ? " radio--active" : ""}`}
              onClick={() => setStyle("display")}
            >
              <span className="radio__circle" />
              Display
            </button>
          </div>

          <Slider
            kind="size"
            value={size}
            min={SIZE_MIN}
            max={SIZE_MAX}
            onChange={setSize}
            label={`${size}px`}
            /* Reserve pill width for the widest 3-digit value so the track
               stays put as size changes from "16px" to "128px". */
            pillLabels={[`${SIZE_MAX}px`]}
          />
        </div>

        <TesterRows
          key={sep}
          activeStyle={style}
          size={size}
          sep={sep}
        />
      </div>
    </section>
  );
}
