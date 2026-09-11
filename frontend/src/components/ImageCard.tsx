import { Link } from "react-router-dom";
import type { ImageRow } from "../api";
import { imageSrc } from "../api";
import { articleHref } from "../safeUrl";

const CLASS_LABEL: Record<string, string> = {
  OFFICIAL_DOCUMENT: "Documento oficial",
  NEWS_SCREENSHOT: "Captura de noticia",
  SOCIAL_MEDIA: "Red social",
  MEME: "Meme",
  INFOGRAPHIC: "Infografía",
  ANIMAL_HEALTH_CONTENT: "Salud animal",
  PHOTOGRAPH: "Fotografía",
  POTENTIALLY_MANIPULATED: "Posible manipulación",
};

export function SoftmaxBars({ scores }: { scores?: Record<string, number> | null }) {
  const entries = Object.entries(scores || {}).sort((a, b) => b[1] - a[1]);
  if (!entries.length) return null;
  return (
    <ul className="softmax">
      {entries.map(([k, v]) => (
        <li key={k}>
          <span>{CLASS_LABEL[k] || k}</span>
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
  const inner = (
    <>
      <img src={imageSrc(image)} alt={image.cnn_class || "imagen analizada"} />
      <div>
        <strong>{CLASS_LABEL[image.cnn_class || ""] || image.cnn_class || "Sin clase"}</strong>
        <span>{(((image.cnn_confidence || 0) as number) * 100).toFixed(0)}%</span>
        {image.reuse_label && <em className="reuse">{image.reuse_label}</em>}
        {detailed && <SoftmaxBars scores={image.cnn_scores} />}
        {detailed && (
          <p className="ocr">{image.ocr_text?.trim() ? image.ocr_text.slice(0, 280) : "Sin texto en la imagen"}</p>
        )}
        {!detailed && <p>{(image.ocr_text || "").slice(0, 72) || "Abrir ficha del artículo"}</p>}
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
  const real = images.filter((im) => im.image_id);
  if (!real.length) return <p className="muted">Sin imágenes en el filtro actual.</p>;
  return (
    <div className="img-strip">
      {real.map((im) => (
        <ImageCard key={im.image_id} image={im} />
      ))}
    </div>
  );
}
