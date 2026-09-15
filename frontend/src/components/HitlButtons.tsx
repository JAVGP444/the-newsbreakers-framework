import { useLocale } from "../locale";

export function HitlButtons({
  busy,
  onAct,
  labels,
}: {
  busy?: boolean;
  onAct: (label: "validado" | "descartado" | "modificado") => void;
  labels?: { validado: string; descartado: string; modificado: string };
}) {
  const { t } = useLocale();
  const text = labels || { validado: t("hitl.ok"), descartado: t("hitl.no"), modificado: t("hitl.fix") };
  return (
    <div className="hitl-actions">
      <button type="button" className="run" disabled={busy} onClick={() => onAct("validado")}>
        {text.validado}
      </button>
      <button type="button" className="hitl-discard" disabled={busy} onClick={() => onAct("descartado")}>
        {text.descartado}
      </button>
      <button type="button" className="hitl-edit" disabled={busy} onClick={() => onAct("modificado")}>
        {text.modificado}
      </button>
    </div>
  );
}
