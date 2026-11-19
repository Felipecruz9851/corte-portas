import React from "react";
import {
  Layers,
  Frame,
  Ruler,
  Maximize2,
  GripVertical,
  SplitSquareVertical,
} from "lucide-react";

export default function MetricsCards({ kpis, meta }) {
  if (!kpis) return null;

  const datas = (meta?.datas_abertura || []).join(", ") || "-";

  const cards = [
    {
      label: "Linhas / OPs",
      value: kpis.total_linhas_op ?? 0,
      sub: `${kpis.total_pecas_op ?? 0} peças no total`,
      icon: Layers,
    },
    {
      label: "Quadros / Escadas",
      value: kpis.total_estruturas ?? 0,
      sub: `${kpis.itens_especiais ?? 0} especiais`,
      icon: Frame,
    },
    {
      label: "Barras a Cortar",
      value: kpis.total_barras_corte ?? 0,
      sub: `${kpis.total_metros_lineares ?? 0} m lineares`,
      icon: Ruler,
    },
    {
      label: "Vidros / Placas",
      value: kpis.total_pecas_vidro ?? 0,
      sub: `${kpis.total_area_vidro_m2 ?? 0} m² calculados`,
      icon: Maximize2,
    },
    {
      label: "Puxadores",
      value: kpis.total_puxadores ?? 0,
      sub: `${kpis.itens_com_puxador ?? 0} itens c/ puxador`,
      icon: GripVertical,
    },
    {
      label: "Com Divisórias",
      value: kpis.itens_com_divisoria ?? 0,
      sub: `Abertura: ${datas}`,
      icon: SplitSquareVertical,
    },
  ];

  return (
    <section
      aria-label="Indicadores da extração"
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-6 gap-4"
    >
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <article
            key={card.label}
            className="bg-lider-surface border border-lider-border rounded-[2px] shadow-lider p-5 flex flex-col justify-between gap-3 transition-colors hover:border-lider-wood/40"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-display text-[11px] uppercase tracking-[0.1em] text-lider-muted font-medium">
                {card.label}
              </span>
              <Icon className="w-4 h-4 text-lider-wood shrink-0" strokeWidth={1.5} />
            </div>

            <div>
              <strong className="block font-display font-normal text-2xl sm:text-[28px] leading-tight text-lider-ink tabular-nums">
                {card.value}
              </strong>
              <span className="block text-xs text-lider-slate mt-1 truncate" title={card.sub}>
                {card.sub}
              </span>
            </div>
          </article>
        );
      })}
    </section>
  );
}
