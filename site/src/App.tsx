import { lazy, Suspense, useEffect, useState, type ReactNode } from 'react'
import { DOWNLOAD_LABEL } from './config'
import { Composition } from './sections/Composition'
import { HERO_COPY_EN, HERO_COPY_JA, HERO_TITLE, Hero } from './sections/Hero'

const loadVariations = () => import('./sections/Variations')
const loadTypeTester = () => import('./sections/TypeTester')
const loadReading = () => import('./sections/Reading')
const loadFooter = () => import('./sections/Footer')

const Variations = lazy(() =>
  loadVariations().then((mod) => ({ default: mod.Variations })),
)
const TypeTester = lazy(() =>
  loadTypeTester().then((mod) => ({ default: mod.TypeTester })),
)
const Reading = lazy(() =>
  loadReading().then((mod) => ({ default: mod.Reading })),
)
const Footer = lazy(() =>
  loadFooter().then((mod) => ({ default: mod.Footer })),
)

const FIRST_VIEW_REVEAL_DELAY_MS = 100
const FIRST_VIEW_FONT_TIMEOUT_MS = 2000
const SECTION_LOAD_GAP_MS = 140
const FIRST_VIEW_FONT = "400 84px 'Gen Interface KR'"
const FIRST_VIEW_TEXT = [
  HERO_TITLE,
  DOWNLOAD_LABEL,
  HERO_COPY_JA,
  HERO_COPY_EN,
].join(' ')

type SectionKey = 'variations' | 'typeTester' | 'reading' | 'footer'

const SECTION_SEQUENCE: Array<{
  key: SectionKey
  load: () => Promise<unknown>
}> = [
  { key: 'variations', load: loadVariations },
  { key: 'typeTester', load: loadTypeTester },
  { key: 'reading', load: loadReading },
  { key: 'footer', load: loadFooter },
]

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function loadFirstViewFont(): Promise<void> {
  if (!('fonts' in document)) return Promise.resolve()
  return Promise.race([
    document.fonts.load(FIRST_VIEW_FONT, FIRST_VIEW_TEXT).then(() => undefined),
    delay(FIRST_VIEW_FONT_TIMEOUT_MS),
  ])
}

function SectionSlot({
  loaded,
  children,
  minHeight,
}: {
  loaded: boolean
  children: ReactNode
  minHeight: string
}) {
  const placeholder = (
    <div
      className="deferred-section__placeholder"
      style={{ minHeight }}
      aria-hidden="true"
    />
  )

  return (
    <div className="deferred-section">
      {loaded ? <Suspense fallback={placeholder}>{children}</Suspense> : placeholder}
    </div>
  )
}

export default function App() {
  const [firstViewReady, setFirstViewReady] = useState(false)
  const [loadedSections, setLoadedSections] = useState<Record<SectionKey, boolean>>({
    variations: false,
    typeTester: false,
    reading: false,
    footer: false,
  })

  useEffect(() => {
    let cancelled = false
    document.body.classList.add('site-loading')
    document.body.classList.remove('site-ready')

    Promise.all([delay(FIRST_VIEW_REVEAL_DELAY_MS), loadFirstViewFont()])
      .catch(() => undefined)
      .then(() => {
        if (cancelled) return
        document.body.classList.remove('site-loading')
        document.body.classList.add('site-ready')
        setFirstViewReady(true)
      })

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!firstViewReady) return
    let cancelled = false

    const loadSequentially = async () => {
      for (const section of SECTION_SEQUENCE) {
        await delay(SECTION_LOAD_GAP_MS)
        if (cancelled) return
        await section.load().catch(() => undefined)
        if (cancelled) return
        setLoadedSections((prev) => ({ ...prev, [section.key]: true }))
      }
    }

    void loadSequentially()

    return () => {
      cancelled = true
    }
  }, [firstViewReady])

  return (
    <div className="page">
      <Hero />
      <main className="main">
        <Composition />
        <SectionSlot loaded={loadedSections.variations} minHeight="64rem">
          <Variations />
        </SectionSlot>
        <SectionSlot loaded={loadedSections.typeTester} minHeight="42rem">
          <TypeTester />
        </SectionSlot>
        <SectionSlot loaded={loadedSections.reading} minHeight="44rem">
          <Reading />
        </SectionSlot>
      </main>
      <SectionSlot loaded={loadedSections.footer} minHeight="28rem">
        <Footer />
      </SectionSlot>
    </div>
  )
}
