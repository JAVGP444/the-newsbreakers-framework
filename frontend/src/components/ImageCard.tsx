import { Link } from "react-router-dom";
import type { ImageRow } from "../api";
import { imageSrc } from "../api";
import { articleHref } from "../safeUrl";
import { cnnConfidenceWhy } from "../display";
import { useLocale } from "../locale";

export function SoftmaxBars({ scores }: { scores?: Record<string, number> | null }) {
  const { t } = useLocale();
  const entries = Object.entries(scores || {}).sort((a, b) => b[1] - a[1]);
  if (!entries.length) return null;
  return (
    <ul className="softmax">
      {entries.map(([k, v]) => (
        <li key={k}>
          <span>{t(`cnn.type.${k}`) === `cnn.type.${k}` ? k : t(`cnn.type.${k}`)}</span>
          <b>
            <i style={{ width: `${Math.max(2, v * 100)}%` }} />
          </b>
          <em>{(v * 100).toFixed(0)}%</em>
        </li>
      ))}
    </ul>
  );
}

export function ImageCard({ image, detailed }: { image: ImageRow; detailed?: boolean }) {
  const { t } = useLocale();
  const klass = t(`cnn.type.${image.cnn_class || ""}`);
  const label = klass.startsWith("cnn.type.") ? image.cnn_class || t("cnn.noClass") : klass;
  const inner = (
    <>
      <img src={imageSrc(image)} alt={image.cnn_class || t("image.alt")} />
      <div>
        <strong>{label}</strong>
        <span>{(((image.cnn_confidence || 0) as number) * 100).toFixed(0)}%</span>
        {image.reuse_label && <em className="reuse">{image.reuse_label}</em>}
        {detailed && <p className="muted cnn-why">{cnnConfidenceWhy(image)}</p>}
        {detailed && <SoftmaxBars scores={image.cnn_scores} />}
        {detailed && (
          <p className="ocr">{image.ocr_text?.trim() ? image.ocr_text.slice(0, 280) : t("article.noOcr")}</p>
        )}
        {!detailed && <p>{(image.ocr_text || "").slice(0, 72) || t("image.openCard")}</p>}
      </div>
    </>
  );
  if (!image.content_id) return <div className="img-card">{inner}</div>;
  return (
    <Link className="img-card" to={articleHref(image.content_id)}>
      {inner}
    </Link>
  );
}

export function ImageStrip({ images }: { images: ImageRow[] }) {
  const { t } = useLocale();
  const real = images.filter((im) => im.image_id);
  if (!real.length) return <p className="muted">{t("image.none")}</p>;
  return (
    <div className="img-strip">
      {real.map((im) => (
        <ImageCard key={im.image_id} image={im} />
      ))}
    </div>
  );
}
