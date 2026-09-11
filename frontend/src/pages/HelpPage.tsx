import { HELP_SECTIONS } from "../help-content";
import { useI18n } from "../i18n";

// Read-only guide. Everything here is chrome (translated); the terms in the
// left column are the literal identifiers the UI and records use, untranslated.
export function HelpPage() {
  const { language, t } = useI18n();
  return (
    <section>
      <header className="page-head">
        <div>
          <h2>{t("help.title")}</h2>
          <p className="page-lede">{t("help.lede")}</p>
        </div>
      </header>
      <nav className="help-toc" aria-label={t("help.contents")}>
        {HELP_SECTIONS.map((section) => (
          <a key={section.id} href={`#help-${section.id}`}>
            {section.title[language]}
          </a>
        ))}
      </nav>
      <div className="help-grid">
        {HELP_SECTIONS.map((section) => (
          <article
            key={section.id}
            id={`help-${section.id}`}
            className="analytics-card help-card"
            aria-labelledby={`help-${section.id}-title`}
          >
            <h3 id={`help-${section.id}-title`}>{section.title[language]}</h3>
            {section.paragraphs[language].map((paragraph, index) => (
              <p key={index}>{paragraph}</p>
            ))}
            {section.terms && (
              <table className="term-table">
                <tbody>
                  {section.terms.map((entry) => (
                    <tr key={entry.term}>
                      <th scope="row">
                        <code>{entry.term}</code>
                      </th>
                      <td>{entry[language]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
