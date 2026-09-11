import {
  Children,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
  type ElementType,
  type ReactNode,
} from "react";

type Props = {
  maxLines?: number;
  maxItems?: number;
  children: ReactNode;
  className?: string;
  as?: ElementType;
  moreLabel?: string;
  lessLabel?: string;
};

export default function LeerMas({
  maxLines,
  maxItems,
  children,
  className = "",
  as,
  moreLabel = "Leer más",
  lessLabel = "Leer menos",
}: Props) {
  const lines = maxItems == null ? maxLines ?? 4 : maxLines;
  const [open, setOpen] = useState(false);
  const [needed, setNeeded] = useState(false);
  const bodyRef = useRef<HTMLElement | null>(null);
  const all = Children.toArray(children);
  const Tag: ElementType = as || "div";
  const shown = !open && maxItems != null ? all.slice(0, maxItems) : all;
  const clamp = Boolean(lines) && !open && maxItems == null;

  useLayoutEffect(() => {
    if (maxItems != null) {
      setNeeded(all.length > maxItems);
      return;
    }
    const el = bodyRef.current;
    if (!el || open || !lines) return;
    const measure = () => {
      const width = el.clientWidth;
      if (!width) return;
      const cs = getComputedStyle(el);
      const probe = document.createElement("div");
      probe.style.cssText = [
        "position:absolute",
        "left:-9999px",
        "top:0",
        "visibility:hidden",
        `width:${width}px`,
        `font:${cs.font}`,
        `letter-spacing:${cs.letterSpacing}`,
        `word-spacing:${cs.wordSpacing}`,
        "white-space:normal",
        "overflow-wrap:anywhere",
        "line-height:" + cs.lineHeight,
      ].join(";");
      probe.innerHTML = el.innerHTML;
      document.body.appendChild(probe);
      const full = probe.scrollHeight;
      probe.remove();
      const lineH = Number.parseFloat(cs.lineHeight) || 22;
      setNeeded(full > lineH * lines + 2);
    };
    measure();
    const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(measure) : null;
    ro?.observe(el);
    return () => ro?.disconnect();
  }, [all.length, children, lines, maxItems, open]);

  return (
    <div className="leer-mas">
      <Tag
        ref={(node: HTMLElement | null) => {
          bodyRef.current = node;
        }}
        className={["leer-mas-body", clamp ? "is-clamped" : "", className].filter(Boolean).join(" ")}
        style={
          clamp && lines
            ? ({ WebkitLineClamp: lines, lineClamp: lines, ["--leer-mas-lines"]: String(lines) } as CSSProperties)
            : undefined
        }
      >
        {shown}
      </Tag>
      {needed ? (
        <button
          type="button"
          className="leer-mas-btn"
          aria-expanded={open}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setOpen((v) => !v);
          }}
        >
          {open ? lessLabel : moreLabel}
        </button>
      ) : null}
    </div>
  );
}
