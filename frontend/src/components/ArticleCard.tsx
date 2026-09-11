import { Link } from "react-router-dom";
import { verdictClass, type Article } from "../api";
import LeerMas from "./LeerMas";
import {
  cardExcerpt,
  displaySourceName,
  formatDate,
  riskTone,
  sourceKind,
  verdictLabel,
} from "../display";
import { articleHref } from "../safeUrl";
import CardThumb from "./CardThumb";

export default function ArticleCard({
  article,
  sourceName,
}: {
  article: Article;
  sourceName?: string;
}) {
  const kind = sourceKind(article);
  const summary = cardExcerpt(article.text, article.title);
  const when = formatDate(article.published_at || article.collected_at);
  const risk = article.risk_score;
  const name = displaySourceName(article, sourceName);
  const href = articleHref(article.content_id);
  const title = article.title || article.url || article.content_id;

  return (
    <article className="art-card">
      <Link className="art-media-hit" to={href} aria-hidden="true" tabIndex={-1}>
        <CardThumb article={article} kind={kind} sourceName={name} />
      </Link>
      <div className="art-body">
        <div className="art-pills">
          <span className={`pill ${verdictClass(article.verdict)}`}>{verdictLabel(article.verdict)}</span>
          <span className={`pill risk-pill ${riskTone(risk)}`}>
            {risk == null ? "Riesgo —" : `Riesgo ${risk}`}
          </span>
        </div>
        <h2 className="art-title">
          <Link to={href}>{title}</Link>
        </h2>
        {summary ? (
          <LeerMas maxLines={3} className="art-summary">
            {summary}
          </LeerMas>
        ) : null}
        <p className="art-meta">
          <span>{name}</span>
          <span aria-hidden="true">·</span>
          <time dateTime={article.published_at || article.collected_at || undefined}>{when}</time>
        </p>
      </div>
    </article>
  );
}
