import { useEffect, useState } from "react";
import { thumbSrc, type Article } from "../api";
import { kindLabel, sourceInitials, type SourceKind } from "../display";
import { useLocale } from "../locale";

export function ContextualThumb({
  kind,
  sourceName,
}: {
  kind: SourceKind;
  sourceName: string;
}) {
  const { lang } = useLocale();
  return (
    <div className={`art-placeholder initials kind-${kind}`}>
      <b>{sourceInitials(sourceName, lang)}</b>
      <span>{kindLabel(kind, lang)}</span>
    </div>
  );
}

export default function CardThumb({
  article,
  kind,
  sourceName,
}: {
  article: Article;
  kind: SourceKind;
  sourceName: string;
}) {
  const src = article.is_news_thumb === false ? "" : thumbSrc(article) || "";
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    setFailed(false);
  }, [src]);
  return (
    <div className={`art-media kind-${kind}`}>
      {src && !failed ? (
        <img src={src} alt="" onError={() => setFailed(true)} />
      ) : (
        <ContextualThumb kind={kind} sourceName={sourceName} />
      )}
    </div>
  );
}
