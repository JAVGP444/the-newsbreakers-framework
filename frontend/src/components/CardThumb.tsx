import { useEffect, useState } from "react";
import { thumbSrc, type Article } from "../api";
import { KIND_LABEL, sourceInitials, type SourceKind } from "../display";

export function ContextualThumb({
  kind,
  sourceName,
}: {
  kind: SourceKind;
  sourceName: string;
}) {
  return (
    <div className={`art-placeholder initials kind-${kind}`}>
      <b>{sourceInitials(sourceName)}</b>
      <span>{KIND_LABEL[kind]}</span>
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
