type Props = {
  name: string
  jp?: string
  small?: boolean
}

export function SectionHead({ name, jp, small }: Props) {
  return (
    <header className="section-head">
      <div className="section-head__rules" aria-hidden="true">
        <hr className="section-head__rule section-head__rule--top" />
        <hr className="section-head__rule section-head__rule--bottom" />
      </div>
      <div className="section-head__title-row">
        <h2 className={`section-head__title${small ? ' section-head__title--small' : ''}`}>
          {name}
        </h2>
        {jp && (
          <h2 className={`section-head__title${small ? ' section-head__title--small' : ''}`}>
            {jp}
          </h2>
        )}
      </div>
    </header>
  )
}
