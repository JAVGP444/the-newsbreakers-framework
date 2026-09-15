import { Link } from "react-router-dom";
import { verdictClass, type Article } from "../api";
import {
  cardExcerpt,
  displaySourceName,
  formatPublishedAt,
  riskTone,
  sourceKind,
  verdictLabel,
} from "../display";
import { useLocale } from "../locale";
import { articleHref, isSafeExternalHttp } from "../safeUrl";
import CardThumb from "./CardThumb";

export default function ArticleCard({
  article,
  sourceName,
  title: titleOverride,
  summary: summaryOverride,
}: {
  article: Article;
  sourceName?: string;
  title?: string;
  summary?: string;
}) {
  const { t, lang } = useLocale();
  const kind = sourceKind(article);
  const summary = summaryOverride ?? cardExcerpt(article.text, article.title);
  const when = formatPublishedAt(article.published_at, lang);
  const risk = article.risk_score;
  const name = displaySourceName(article, sourceName);
  const href = articleHref(article.content_id);
  const title = titleOverride ?? (article.title || article.url || article.content_id);

  return (
    <article className="art-card">
      <Link className="art-media-hit" to={href} aria-hidden="true" tabIndex={-1}>
        <CardThumb article={article} kind={kind} sourceName={name} />
      </Link>
      <div className="art-body">
        <div className="art-pills">
          <span className={`pill ${verdictClass(article.verdict)}`}>{verdictLabel(article.verdict, lang)}</span>
          <span className={`pill risk-pill ${riskTone(risk)}`}>
            {risk == null ? t("risk.dash") : t("risk.n", { n: risk })}
          </span>
        </div>
        <h2 className="art-title">
          <Link to={href}>{title}</Link>
        </h2>
        {summary ? <p className="art-summary">{summary}</p> : null}
        <p className="art-meta">
          <span className="art-meta-src">{name}</span>
          <time dateTime={article.published_at || undefined}>{when}</time>
          {isSafeExternalHttp(article.url) ? (
            <a
              className="noticia"
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
            >
              {t("article.original")}
            </a>
          ) : null}
        </p>
      </div>
    </article>
  );
}
