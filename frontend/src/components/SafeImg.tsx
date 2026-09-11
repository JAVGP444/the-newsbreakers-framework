import { useEffect, useState } from "react";

export default function SafeImg({
  src,
  alt,
  className,
}: {
  src?: string | null;
  alt: string;
  className?: string;
}) {
  const [ok, setOk] = useState(Boolean(src));

  useEffect(() => {
    setOk(Boolean(src));
  }, [src]);

  if (!src || !ok) return null;
  return <img src={src} alt={alt} className={className} onError={() => setOk(false)} />;
}
