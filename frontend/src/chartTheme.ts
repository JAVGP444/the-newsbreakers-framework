/** Paleta Okabe–Ito (segura para daltonismo) + tokens de gráficas. */
export const OKABE_ITO = ["#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7"] as const;

export const DISEASE_COLOR: Record<string, string> = {
  gripe_aviar: "#56B4E9",
  gusano_barrenador: "#E69F00",
  fiebre_porcina_clasica: "#009E73",
  otras: "#CC79A7",
};

export const ORIGIN_COLOR: Record<string, string> = {
  oficial: "#0072B2",
  cientifico: "#009E73",
  social: "#CC79A7",
  youtube: "#D55E00",
  prensa: "#56B4E9",
};

export const VERDICT_COLOR: Record<string, string> = {
  respaldado: "#0072B2",
  Respaldado: "#0072B2",
  insuficiente: "#E69F00",
  Insuficiente: "#E69F00",
  contradicho: "#D55E00",
  Contradicho: "#D55E00",
  revision_humana: "#CC79A7",
  "Revisión humana": "#CC79A7",
  enganoso: "#F0E442",
  "Posiblemente engañoso": "#F0E442",
  sin_verificar: "#7a7a7a",
  "Sin verificar": "#7a7a7a",
};

export const STANCE_COLOR: Record<string, string> = {
  Supported: "#0072B2",
  Respaldado: "#0072B2",
  Contradicted: "#D55E00",
  Contradicho: "#D55E00",
  Unknown: "#7a7a7a",
  "Sin verificar": "#7a7a7a",
};

export const AXIS = "#c5d5dc";
export const GRID = "#1e3a4c";
export const TICK = { fill: AXIS, fontSize: 12 };
export const CHART_MARGIN = { top: 8, right: 16, left: 8, bottom: 28 };

export function seriesColor(id: string, index = 0): string {
  return DISEASE_COLOR[id] || OKABE_ITO[index % OKABE_ITO.length];
}

export function axisLabel(value: string, vertical = false) {
  if (vertical) {
    return {
      value,
      angle: -90,
      position: "insideLeft" as const,
      offset: 8,
      style: { textAnchor: "middle" as const, fill: AXIS, fontSize: 12 },
    };
  }
  return { value, position: "insideBottom" as const, offset: -4, style: { fill: AXIS, fontSize: 12 } };
}
