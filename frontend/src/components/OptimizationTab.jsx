import React, { useEffect, useId, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  ChevronDown,
  ChevronRight,
  Clock,
  Download,
  Filter,
  Layers,
  Loader2,
  Play,
  RotateCcw,
  Scissors,
  Search,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { fmtNum } from "../utils/formatters";

const SEGMENT_COLORS = [
  "#222222",
  "#8B5A2B",
  "#444444",
  "#6E4722",
  "#595959",
  "#A0522D",
];

function pieceMatchesQuery(p, q) {
  if (!q) return true;
  return [
    p.op,
    p.codigo,
    p.modelo,
    p.tipo_perfil,
    p.funcao_barra,
    p.acabamento_perfil,
    p.angulos_corte,
    p.tipo_corte,
    p.medida_corte_mm,
  ]
    .join(" ")
    .toLowerCase()
    .includes(q);
}

function barMatchesFilter(bar, grupoFilter, q) {
  if (grupoFilter && bar.grupo_key !== grupoFilter) return false;
  if (!q) return true;
  const headerHay = [
    bar.grupo_nome,
    bar.codigo_perfil,
    bar.angulos_resumo,
    bar.padrao_corte,
    bar.sequencia_corte,
    bar.ops,
  ]
    .join(" ")
    .toLowerCase();
  if (headerHay.includes(q)) return true;
  return (bar.pecas || []).some((p) => pieceMatchesQuery(p, q));
}

function normPieceAngles(p) {
  const e = Number(p.angulo_esq) === 90 ? 90 : 45;
  const d = Number(p.angulo_dir) === 90 ? 90 : 45;
  return [e, d];
}

function formatCanonAngleSig(e, d) {
  const lo = Math.min(e, d);
  const hi = Math.max(e, d);
  return `${lo}° / ${hi}°`;
}

function reannotateSequentialAdjustments(bars, { countMeasure = true } = {}) {
  let totalChanges = 0;
  let totalAngleChanges = 0;
  let prevMed = null;
  let prevAngle = null;

  const annotated = bars.map((b) => {
    let internalChanges = 0;
    let entryChange = false;
    let internalAng = 0;
    let entryAng = false;
    const anglesSeen = new Set();

    const pieces = (b.pecas || []).map((p, idx) => {
      const med = Math.round((Number(p.medida_corte_mm) || 0) * 1000) / 1000;
      const [aEsq, aDir] = normPieceAngles(p);
      anglesSeen.add(formatCanonAngleSig(aEsq, aDir));

      if (countMeasure && prevMed !== null && med !== prevMed) {
        totalChanges += 1;
        if (idx === 0) {
          entryChange = true;
        } else {
          internalChanges += 1;
        }
      }
      prevMed = med;

      let pEntryAng = false;
      if (prevAngle !== null && aEsq !== prevAngle) {
        totalAngleChanges += 1;
        pEntryAng = true;
        if (idx === 0) {
          entryAng = true;
        } else {
          internalAng += 1;
        }
      }
      const pIntraAng = aEsq !== aDir;
      if (pIntraAng) {
        totalAngleChanges += 1;
        internalAng += 1;
      }
      prevAngle = aDir;

      return {
        ...p,
        angulo_esq: aEsq,
        angulo_dir: aDir,
        angulos_corte: p.angulos_corte || `${aEsq}° / ${aDir}°`,
        troca_angulo_entrada: pEntryAng,
        troca_angulo_interna: pIntraAng,
      };
    });

    return {
      ...b,
      pecas: pieces,
      ...(countMeasure
        ? {
            troca_entrada: entryChange,
            ajustes_internos: internalChanges,
            ajustes_barra: internalChanges + (entryChange ? 1 : 0),
          }
        : {}),
      troca_angulo_entrada: entryAng,
      trocas_angulo_internas: internalAng,
      trocas_angulo_barra: internalAng + (entryAng ? 1 : 0),
      angulos_resumo: Array.from(anglesSeen).sort().join(", "),
    };
  });

  return { annotated, totalChanges, totalAngleChanges };
}

function filterScenarioAndComputeMetrics(
  scenarioData,
  scenarioId,
  grupoFilter,
  searchTerm,
  activeBarraMm,
  pecasInviaveisFlat = []
) {
  if (!scenarioData) {
    return {
      filteredGroups: [],
      filteredBarsFlat: [],
      filteredRoteiroFlat: [],
      filteredInviaveis: [],
      metrics: {
        totalBarras: 0,
        totalPecas: 0,
        totalMetrosPecas: 0,
        aproveitamentoMedioPct: 0,
        totalPerdaMm: 0,
        totalPerdaMetros: 0,
        perdaMediaBarraMm: 0,
        totalAjustes: 0,
        totalTrocasAngulo: 0,
        totalEconomiaChanfroMm: 0,
        totalCortesParalelos: 0,
        totalCortesV: 0,
        gruposExibidos: 0,
        totalGrupos: 0,
        pecasInviaveis: 0,
      },
    };
  }

  const q = searchTerm.trim().toLowerCase();
  const hasFilter = Boolean(grupoFilter || q);
  const allGroups = scenarioData.grupos || [];

  const filteredGroups = [];
  const filteredBarsFlat = [];
  const filteredRoteiroFlat = [];

  for (const g of allGroups) {
    if (grupoFilter && g.grupo_key !== grupoFilter) continue;

    const rawVisBars = (g.barras || []).filter((b) => barMatchesFilter(b, "", q));
    if (!rawVisBars.length) continue;

    let visBars = rawVisBars;
    let groupAjustes = 0;
    let groupTrocasAngulo = 0;
    let visRoteiro = [];

    if (scenarioId === "material") {
      if (!hasFilter) {
        visBars = rawVisBars;
        groupAjustes = Number(g.ajustes_corte) || 0;
        groupTrocasAngulo = Number(g.trocas_angulo) || 0;
      } else {
        const re = reannotateSequentialAdjustments(rawVisBars, { countMeasure: true });
        visBars = re.annotated;
        groupAjustes = re.totalChanges;
        groupTrocasAngulo = re.totalAngleChanges;
      }
    } else {
      const visBarNumSet = new Set(visBars.map((b) => b.barra_numero));
      const groupHeaderMatches =
        !q ||
        [
          g.grupo_nome,
          g.codigo_perfil,
          ...(g.modelos || []),
          ...(g.acabamentos || []),
          ...(g.angulos_presentes || []),
        ]
          .join(" ")
          .toLowerCase()
          .includes(q);

      for (const step of g.roteiro_medidas || []) {
        const matchingAllocs = (step.alocacoes || []).filter((alloc) => {
          if (!visBarNumSet.has(alloc.barra_numero)) return false;
          if (!q || groupHeaderMatches) return true;
          if (String(step.medida_corte_mm).toLowerCase().includes(q)) return true;
          if (String(step.angulos_corte || "").toLowerCase().includes(q)) return true;
          if ((alloc.ops || "").toLowerCase().includes(q)) return true;
          return (alloc.pecas || []).some((p) => pieceMatchesQuery(p, q));
        });
        if (matchingAllocs.length > 0) {
          visRoteiro.push({
            ...step,
            alocacoes: matchingAllocs,
          });
        }
      }

      if (hasFilter) {
        const reTmp = reannotateSequentialAdjustments(rawVisBars, { countMeasure: false });
        visBars = reTmp.annotated;
        let curRouteAngle = null;
        let sumStepAng = 0;
        visRoteiro = visRoteiro.map((step, sIdx) => {
          let stepAngChanges = 0;
          for (const alloc of step.alocacoes || []) {
            for (const p of alloc.pecas || []) {
              const [aEsq, aDir] = normPieceAngles(p);
              if (curRouteAngle !== null && aEsq !== curRouteAngle) {
                stepAngChanges += 1;
              }
              if (aEsq !== aDir) {
                stepAngChanges += 1;
              }
              curRouteAngle = aDir;
            }
          }
          sumStepAng += stepAngChanges;
          return {
            ...step,
            passo: sIdx + 1,
            troca_medida: sIdx > 0,
            troca_angulo: stepAngChanges > 0,
            trocas_angulo_passo: stepAngChanges,
          };
        });
        groupAjustes = Math.max(0, visRoteiro.length - 1);
        groupTrocasAngulo = sumStepAng;
      } else {
        groupAjustes = Number(g.ajustes_corte) || 0;
        groupTrocasAngulo = Number(g.trocas_angulo) || 0;
      }
    }

    const somaPecasMm = visBars.reduce(
      (acc, b) => acc + (Number(b.soma_pecas_mm) || 0),
      0
    );
    const econChanfroMm = visBars.reduce(
      (acc, b) => acc + (Number(b.economia_chanfro_mm) || 0),
      0
    );
    const somaUtilMm = Math.max(0, somaPecasMm - econChanfroMm);
    const cortesParalelos = visBars.reduce(
      (acc, b) => acc + (Number(b.cortes_paralelos_qtd) || 0),
      0
    );
    const cortesV = visBars.reduce(
      (acc, b) => acc + (Number(b.cortes_v_qtd) || 0),
      0
    );
    const perdaMm = visBars.reduce((acc, b) => acc + (Number(b.perda_mm) || 0), 0);
    const totalPecas = visBars.reduce((acc, b) => acc + (Number(b.qtd_pecas) || 0), 0);
    const qtdBarras = visBars.length;
    const aprovPct =
      qtdBarras > 0 && activeBarraMm > 0
        ? Math.min(100, (somaUtilMm / (qtdBarras * activeBarraMm)) * 100)
        : 0;
    const perdaMediaMm = qtdBarras > 0 ? perdaMm / qtdBarras : 0;

    filteredGroups.push({
      ...g,
      qtd_barras: qtdBarras,
      total_pecas_alocadas: totalPecas,
      total_metros_pecas: Math.round(somaPecasMm) / 1000,
      economia_chanfro_mm: Math.round(econChanfroMm * 1000) / 1000,
      cortes_paralelos_qtd: cortesParalelos,
      cortes_v_qtd: cortesV,
      total_perda_mm: Math.round(perdaMm * 1000) / 1000,
      total_perda_metros: Math.round(perdaMm) / 1000,
      perda_media_barra_mm: Math.round(perdaMediaMm * 100) / 100,
      aproveitamento_medio_pct: Math.round(aprovPct * 100) / 100,
      ajustes_corte: groupAjustes,
      trocas_angulo: groupTrocasAngulo,
      barras: visBars,
      roteiro_medidas: visRoteiro,
    });

    visBars.forEach((b) => filteredBarsFlat.push(b));
    visRoteiro.forEach((s) => filteredRoteiroFlat.push(s));
  }

  filteredBarsFlat.sort((a, b) => {
    const cmp = String(a.grupo_nome || "").localeCompare(String(b.grupo_nome || ""), "pt-BR");
    if (cmp !== 0) return cmp;
    return (Number(a.barra_numero) || 0) - (Number(b.barra_numero) || 0);
  });

  filteredRoteiroFlat.sort((a, b) => {
    const diffMed = (Number(b.medida_corte_mm) || 0) - (Number(a.medida_corte_mm) || 0);
    if (diffMed !== 0) return diffMed;
    const cmp = String(a.grupo_nome || "").localeCompare(String(b.grupo_nome || ""), "pt-BR");
    if (cmp !== 0) return cmp;
    return (Number(a.passo) || 0) - (Number(b.passo) || 0);
  });

  const filteredInviaveis = (pecasInviaveisFlat || []).filter((p) => {
    if (grupoFilter && p.grupo_key !== grupoFilter) return false;
    if (!q) return true;
    return (
      String(p.grupo_nome || "").toLowerCase().includes(q) ||
      String(p.codigo_perfil || "").toLowerCase().includes(q) ||
      pieceMatchesQuery(p, q)
    );
  });

  const totalBarras = filteredBarsFlat.length;
  const totalPecas = filteredGroups.reduce((acc, g) => acc + g.total_pecas_alocadas, 0);
  const somaPecasMm = filteredBarsFlat.reduce(
    (acc, b) => acc + (Number(b.soma_pecas_mm) || 0),
    0
  );
  const totalEconomiaChanfroMm = filteredBarsFlat.reduce(
    (acc, b) => acc + (Number(b.economia_chanfro_mm) || 0),
    0
  );
  const totalCortesParalelos = filteredBarsFlat.reduce(
    (acc, b) => acc + (Number(b.cortes_paralelos_qtd) || 0),
    0
  );
  const totalCortesV = filteredBarsFlat.reduce(
    (acc, b) => acc + (Number(b.cortes_v_qtd) || 0),
    0
  );
  const somaUtilMm = Math.max(0, somaPecasMm - totalEconomiaChanfroMm);
  const totalPerdaMm = filteredBarsFlat.reduce(
    (acc, b) => acc + (Number(b.perda_mm) || 0),
    0
  );
  const totalAjustes = filteredGroups.reduce((acc, g) => acc + g.ajustes_corte, 0);
  const totalTrocasAngulo = filteredGroups.reduce(
    (acc, g) => acc + (g.trocas_angulo || 0),
    0
  );
  const aproveitamentoMedioPct =
    totalBarras > 0 && activeBarraMm > 0
      ? Math.round(Math.min(100, (somaUtilMm / (totalBarras * activeBarraMm)) * 100) * 100) / 100
      : 0;
  const perdaMediaBarraMm =
    totalBarras > 0 ? Math.round((totalPerdaMm / totalBarras) * 100) / 100 : 0;

  return {
    filteredGroups,
    filteredBarsFlat,
    filteredRoteiroFlat,
    filteredInviaveis,
    metrics: {
      totalBarras,
      totalPecas,
      totalMetrosPecas: Math.round(somaPecasMm) / 1000,
      aproveitamentoMedioPct,
      totalPerdaMm: Math.round(totalPerdaMm * 1000) / 1000,
      totalPerdaMetros: Math.round(totalPerdaMm) / 1000,
      perdaMediaBarraMm,
      totalAjustes,
      totalTrocasAngulo,
      totalEconomiaChanfroMm: Math.round(totalEconomiaChanfroMm * 1000) / 1000,
      totalCortesParalelos,
      totalCortesV,
      gruposExibidos: filteredGroups.length,
      totalGrupos: allGroups.length,
      pecasInviaveis: filteredInviaveis.length,
    },
  };
}

function AngleLegend() {
  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-2 px-3.5 py-2 border border-lider-border rounded-[2px] bg-lider-canvas/60 text-[11px] text-lider-slate">
      <span className="font-display uppercase tracking-[0.06em] text-[10px] text-lider-muted font-medium">
        Legenda dos Cortes 1D
      </span>
      <span className="inline-flex items-center gap-1.5">
        <svg viewBox="0 0 38 14" className="w-9 h-3.5 shrink-0" aria-hidden="true">
          <polygon points="5,1 19,1 23,13 1,13" fill="#222222" />
          <polygon points="19,1 37,1 33,13 23,13" fill="#8B5A2B" />
        </svg>
        <span>Simétrico // (Girar 180°)</span>
      </span>
      <span className="inline-flex items-center gap-1.5">
        <svg viewBox="0 0 38 14" className="w-9 h-3.5 shrink-0" aria-hidden="true">
          <polygon points="5,1 14,1 18,13 1,13" fill="#222222" />
          <polygon points="24,1 33,1 37,13 20,13" fill="#444444" />
        </svg>
        <span>Assimétrico \/ (Sem giro)</span>
      </span>
      <span className="inline-flex items-center gap-1.5">
        <svg viewBox="0 0 24 14" className="w-6 h-3.5 shrink-0" aria-hidden="true">
          <polygon points="5,1 23,1 23,13 1,13" fill="#8B5A2B" />
        </svg>
        <span>45° / 90° (Misto)</span>
      </span>
      <span className="inline-flex items-center gap-1.5">
        <svg viewBox="0 0 24 14" className="w-6 h-3.5 shrink-0" aria-hidden="true">
          <polygon points="1,1 23,1 23,13 1,13" fill="#444444" />
        </svg>
        <span>90° / 90° (Topo)</span>
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className="w-0.5 h-3.5 bg-lider-terracotta inline-block" aria-hidden="true" />
        <span>Troca de ângulo (45°↔90°)</span>
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className="w-4 h-3 border border-lider-border loss-hatch inline-block" aria-hidden="true" />
        <span>Sobra / Perda</span>
      </span>
    </div>
  );
}

function BarCard({ bar, desponteMm = 0, showGroupBadge = false, isMaterial = true }) {
  const [showPieces, setShowPieces] = useState(false);
  const hatchId = useId();
  const barLen = Number(bar.comprimento_barra_mm) || 6000;
  const pieces = bar.pecas || [];
  const despontePct = desponteMm > 0 ? Math.min(100, (desponteMm / barLen) * 100) : 0;
  const perdaPct = Math.max(0, ((Number(bar.perda_mm) || 0) / barLen) * 100);
  const kerfTotalMm = Math.max(0, (Number(bar.perda_serra_desponte_mm) || 0) - desponteMm);
  const kerfTotalPct = (kerfTotalMm / barLen) * 100;

  const badgeCls = isMaterial
    ? "bg-lider-charcoal text-white"
    : "bg-lider-wood text-white";

  const seqText = bar.sequencia_corte || bar.padrao_corte;
  const ajustesBarra = Number(bar.ajustes_barra) || 0;
  const trocasAnguloBarra = Number(bar.trocas_angulo_barra) || 0;
  const econChanfroMm = Number(bar.economia_chanfro_mm) || 0;
  const isBarSimetrico = Boolean(bar.perfil_simetrico);

  const svgGeometry = useMemo(() => {
    let cursorX = (despontePct / 100) * 1000;
    const desponteW = cursorX;
    let prevBR = 0;
    const segments = pieces.map((p, idx) => {
      const medMm = Number(p.medida_corte_mm) || 0;
      const econMm = Number(p.economia_chanfro_mm) || 0;
      const segW = (medMm / barLen) * 1000;
      const econW = (econMm / barLen) * 1000;
      const x0 = cursorX;
      const x1 = Math.max(x0 + 1, x0 + segW - econW);
      cursorX = x1;
      const effPct = ((x1 - x0) / 1000) * 100;

      const [aEsq, aDir] = normPieceAngles(p);
      const inv = Boolean(p.invertida);
      const juncao = p.juncao_entrada || "";

      const bR = aDir === 45 ? Math.min(10, segW * 0.26) : 0;
      const bL =
        aEsq === 45
          ? juncao === "//"
            ? Math.min(prevBR, segW * 0.45)
            : Math.min(10, segW * 0.26)
          : 0;
      prevBR = bR;

      let topLeft;
      let botLeft;
      let topRight;
      let botRight;
      if (!inv) {
        topLeft = juncao === "//" ? x0 : x0 + bL;
        botLeft = juncao === "//" ? x0 - bL : x0;
        topRight = x1 - bR;
        botRight = x1;
      } else {
        topLeft = juncao === "//" ? x0 - bL : x0;
        botLeft = juncao === "//" ? x0 : x0 + bL;
        topRight = x1;
        botRight = x1 - bR;
      }

      return {
        idx,
        p,
        effPct,
        x0,
        x1,
        topLeft,
        topRight,
        botRight,
        botLeft,
        aEsq,
        aDir,
        inv,
        juncao,
        econMm,
        bg: SEGMENT_COLORS[idx % SEGMENT_COLORS.length],
      };
    });
    const kerfX = cursorX;
    const kerfW = (kerfTotalPct / 100) * 1000;
    const lossX = Math.min(1000, kerfX + kerfW);
    const lossW = Math.max(0, 1000 - lossX);
    return { desponteW, segments, kerfX, kerfW, lossX, lossW };
  }, [pieces, barLen, despontePct, kerfTotalPct]);

  return (
    <div className="border border-lider-border rounded-[2px] bg-lider-surface p-4 space-y-3">
      {/* Cabeçalho da Barra */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-2.5">
        <div className="flex flex-wrap items-center gap-2 min-w-0">
          <span
            className={`inline-flex items-center px-2 py-0.5 font-mono text-xs font-medium rounded-[2px] ${badgeCls}`}
          >
            #{showGroupBadge ? bar.barra_global_numero || bar.barra_numero : bar.barra_numero}
          </span>
          {showGroupBadge && (
            <span
              className={[
                "inline-flex items-center px-2 py-0.5 text-[11px] font-medium border rounded-[2px]",
                bar.origem_agrupamento === "codigo_perfil"
                  ? "border-lider-wood/40 bg-lider-wood/5 text-lider-wood font-mono"
                  : "border-lider-border bg-lider-canvas text-lider-charcoal",
              ].join(" ")}
            >
              {bar.grupo_nome}
            </span>
          )}
          {bar.angulos_resumo && (
            <span className="inline-flex items-center px-2 py-0.5 font-mono text-[11px] border border-lider-border bg-lider-canvas text-lider-charcoal rounded-[2px]">
              {bar.angulos_resumo}
            </span>
          )}
          <span
            className={[
              "inline-flex items-center px-2 py-0.5 font-mono text-[11px] border rounded-[2px]",
              isBarSimetrico
                ? "border-lider-wood/40 bg-lider-wood/10 text-lider-wood"
                : "border-lider-border bg-lider-canvas text-lider-slate",
            ].join(" ")}
            title={
              isBarSimetrico
                ? "Perfil simétrico: gira 180° para encaixe paralelo //"
                : "Perfil assimétrico: não pode girar, corte em \\/"
            }
          >
            {isBarSimetrico ? "Simétrico //" : "Assimétrico \\/"}
          </span>
          <span className="font-mono text-xs sm:text-[13px] font-medium text-lider-ink">
            {seqText}
          </span>
          <span className="text-xs text-lider-muted">
            ({bar.qtd_pecas} {bar.qtd_pecas === 1 ? "peça" : "peças"})
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-x-3.5 gap-y-1 text-xs tabular-nums shrink-0">
          {isMaterial && (
            <span
              className={[
                "inline-flex items-center px-2 py-0.5 text-[11px] border rounded-[2px]",
                bar.troca_entrada
                  ? "border-lider-terracotta/40 bg-lider-terracotta/5 text-lider-terracotta"
                  : "border-lider-border bg-lider-canvas text-lider-slate",
              ].join(" ")}
              title="Trocas de medida na entrada e dentro desta barra"
            >
              {bar.troca_entrada ? "+1 troca entrada" : "0 troca entrada"} ·{" "}
              {ajustesBarra} {ajustesBarra === 1 ? "ajuste" : "ajustes"}
            </span>
          )}
          {trocasAnguloBarra > 0 && (
            <span
              className="inline-flex items-center px-2 py-0.5 text-[11px] border border-lider-terracotta/40 bg-lider-terracotta/5 text-lider-terracotta rounded-[2px]"
              title="Trocas de ângulo (45° ↔ 90°) nesta barra"
            >
              {trocasAnguloBarra} {trocasAnguloBarra === 1 ? "troca âng." : "trocas âng."}
            </span>
          )}
          {econChanfroMm > 0 && (
            <span
              className="inline-flex items-center px-2 py-0.5 text-[11px] border border-lider-wood/40 bg-lider-wood/10 text-lider-wood rounded-[2px]"
              title="Material recuperado pelo encaixe paralelo // de chanfros 45°"
            >
              Econ. //: {fmtNum(econChanfroMm)} mm
            </span>
          )}
          <span className="text-lider-slate">
            Usado:{" "}
            <strong className="font-medium text-lider-ink">
              {fmtNum(bar.soma_pecas_mm)} mm
            </strong>
          </span>
          {Number(bar.perda_serra_desponte_mm) > 0 && (
            <span className="text-lider-muted">
              Serra/Desp.: {fmtNum(bar.perda_serra_desponte_mm)} mm
            </span>
          )}
          <span className="text-lider-terracotta">
            Perda:{" "}
            <strong className="font-medium">
              {fmtNum(bar.perda_mm)} mm
            </strong>{" "}
            <span className="text-[11px]">({fmtNum(bar.perda_cm)} cm)</span>
          </span>
          <span className="inline-flex items-center px-2 py-0.5 text-[11px] font-medium border border-lider-wood/40 bg-lider-wood/5 text-lider-wood rounded-[2px]">
            {fmtNum(bar.aproveitamento_pct)}%
          </span>
        </div>
      </div>

      {/* Diagrama 1D proporcional da barra em SVG com chanfros reais (// vs \/) */}
      <div className="relative w-full h-9 border border-lider-border rounded-[2px] bg-lider-canvas overflow-hidden select-none">
        <svg
          viewBox="0 0 1000 36"
          preserveAspectRatio="none"
          className="w-full h-full block"
          role="img"
          aria-label={`Barra ${bar.barra_numero}: ${seqText}, ${
            isBarSimetrico ? "perfil simétrico //" : "perfil assimétrico \\/"
          }, ângulos ${bar.angulos_resumo || "45° / 45°"}, perda ${fmtNum(
            bar.perda_mm
          )} mm (${fmtNum(bar.aproveitamento_pct)}% aproveitamento)`}
        >
          <defs>
            <pattern
              id={hatchId}
              width="8"
              height="8"
              patternUnits="userSpaceOnUse"
              patternTransform="rotate(-45)"
            >
              <rect width="8" height="8" fill="rgba(160, 82, 45, 0.08)" />
              <line
                x1="0"
                y1="0"
                x2="0"
                y2="8"
                stroke="rgba(160, 82, 45, 0.25)"
                strokeWidth="3"
              />
            </pattern>
          </defs>

          {svgGeometry.desponteW > 0 && (
            <rect
              x="0"
              y="2"
              width={svgGeometry.desponteW.toFixed(2)}
              height="32"
              fill="rgba(117, 117, 117, 0.35)"
            />
          )}

          {svgGeometry.segments.map(
            ({ idx, p, x0, topLeft, topRight, botRight, botLeft, bg }) => (
              <g key={`svg-${p.op}-${p.codigo}-${idx}`}>
                <polygon
                  points={`${topLeft.toFixed(2)},2 ${topRight.toFixed(
                    2
                  )},2 ${botRight.toFixed(2)},34 ${botLeft.toFixed(2)},34`}
                  fill={bg}
                  stroke="#FFFFFF"
                  strokeWidth="1.4"
                  vectorEffect="non-scaling-stroke"
                />
                {p.troca_angulo_entrada && (
                  <line
                    x1={x0.toFixed(2)}
                    y1="0"
                    x2={x0.toFixed(2)}
                    y2="36"
                    stroke="#A0522D"
                    strokeWidth="2.5"
                    vectorEffect="non-scaling-stroke"
                  />
                )}
              </g>
            )
          )}

          {svgGeometry.kerfW > 0.5 && (
            <rect
              x={svgGeometry.kerfX.toFixed(2)}
              y="2"
              width={svgGeometry.kerfW.toFixed(2)}
              height="32"
              fill="rgba(117, 117, 117, 0.25)"
            />
          )}

          {svgGeometry.lossW > 0 && (
            <rect
              x={svgGeometry.lossX.toFixed(2)}
              y="2"
              width={svgGeometry.lossW.toFixed(2)}
              height="32"
              fill={`url(#${hatchId})`}
            />
          )}
        </svg>

        {/* Overlay tipográfico 1:1 alinhado com cada segmento (sem distorção de texto) */}
        <div aria-hidden="true" className="absolute inset-0 flex">
          {despontePct > 0 && (
            <div
              style={{ width: `${despontePct}%` }}
              title={`Desponte: ${fmtNum(desponteMm)} mm`}
              className="h-full shrink-0"
            />
          )}
          {svgGeometry.segments.map(
            ({ idx, p, effPct, aEsq, aDir, inv, juncao, econMm }) => (
              <div
                key={`ov-${p.op}-${p.codigo}-${idx}`}
                style={{ width: `${effPct}%` }}
                title={`${idx + 1}º corte: ${fmtNum(
                  p.medida_corte_mm
                )} mm · ${aEsq}° / ${aDir}° · ${
                  p.perfil_simetrico
                    ? inv
                      ? "Girado 180° (//)"
                      : juncao === "//"
                      ? "Normal (//)"
                      : "Simétrico"
                    : juncao === "\\/"
                    ? "Sem giro (\\/)"
                    : "Assimétrico"
                }${econMm > 0 ? ` · Econ. chanfro: ${fmtNum(econMm)} mm` : ""} · ${
                  p.modelo
                } (${p.funcao_barra}) · OP ${p.op} · ${p.acabamento_perfil}${
                  p.troca_angulo_entrada ? " · Troca de ângulo na entrada" : ""
                }`}
                className="h-full flex items-center justify-between px-1.5 font-mono text-white shrink-0 overflow-hidden"
              >
                {effPct >= 11 ? (
                  <>
                    <span className="text-[9px] opacity-85 shrink-0">{aEsq}°</span>
                    <span className="truncate text-[11px] font-medium px-0.5">
                      {fmtNum(p.medida_corte_mm)}
                    </span>
                    <span className="text-[9px] opacity-85 shrink-0">{aDir}°</span>
                  </>
                ) : effPct >= 5.5 ? (
                  <span className="truncate mx-auto text-[11px]">
                    {fmtNum(p.medida_corte_mm)}
                  </span>
                ) : null}
              </div>
            )
          )}
          {kerfTotalPct > 0.2 && (
            <div
              style={{ width: `${kerfTotalPct}%` }}
              title={`Serra (kerf): ${fmtNum(kerfTotalMm)} mm`}
              className="h-full shrink-0"
            />
          )}
          {perdaPct > 0 && (
            <div
              style={{ width: `${perdaPct}%` }}
              title={`Sobra / Perda na barra: ${fmtNum(bar.perda_mm)} mm (${fmtNum(
                bar.perda_cm
              )} cm)`}
              className="h-full flex items-center justify-center overflow-hidden px-1 text-[10px] font-mono text-lider-terracotta flex-1 min-w-0"
            >
              {perdaPct >= 3.5 && (
                <span className="truncate">-{fmtNum(bar.perda_mm)}</span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Rodapé da barra: OPs e toggle de peças */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <span className="font-mono text-lider-slate truncate">
          OPs: {bar.ops || "-"}
        </span>
        <button
          type="button"
          onClick={() => setShowPieces((v) => !v)}
          aria-expanded={showPieces}
          className="inline-flex items-center gap-1 px-2 py-1 text-xs text-lider-charcoal hover:text-lider-ink border border-lider-border hover:border-lider-charcoal rounded-[2px] bg-lider-canvas transition-colors"
        >
          {showPieces ? (
            <ChevronDown className="w-3.5 h-3.5" strokeWidth={1.5} />
          ) : (
            <ChevronRight className="w-3.5 h-3.5" strokeWidth={1.5} />
          )}
          <span>{showPieces ? "Ocultar peças" : "Ver sequência de cortes"}</span>
        </button>
      </div>

      {showPieces && (
        <div
          tabIndex={0}
          role="region"
          aria-label={`Peças da barra ${bar.barra_numero}`}
          className="table-wrapper stack-narrow max-h-[300px]"
        >
          <table className="lider-table">
            <caption className="visually-hidden">
              Sequência de cortes na barra {bar.barra_numero}
            </caption>
            <thead>
              <tr>
                <th className="num-header">Ordem</th>
                <th>OP</th>
                <th>Código</th>
                <th>Entrega</th>
                <th>Modelo</th>
                <th>Tipo</th>
                <th>Função</th>
                <th>Ângulos</th>
                <th>Acabamento</th>
                <th className="num-header">Medida Corte (mm)</th>
              </tr>
            </thead>
            <tbody>
              {pieces.map((p, idx) => {
                const [aEsq, aDir] = normPieceAngles(p);
                const isMixed = aEsq !== aDir;
                return (
                  <tr key={`${p.op}-${p.codigo}-${idx}`}>
                    <th scope="row" data-label="Ordem" className="font-mono text-xs">
                      {idx + 1}º
                    </th>
                    <td data-label="OP" className="font-mono text-xs">
                      {p.op}
                    </td>
                    <td data-label="Código">
                      <code className="font-mono text-xs">{p.codigo}</code>
                    </td>
                    <td data-label="Entrega" className="whitespace-nowrap">
                      {p.data_entrega || "-"}
                    </td>
                    <td data-label="Modelo">{p.modelo}</td>
                    <td data-label="Tipo">{p.tipo_perfil}</td>
                    <td data-label="Função">{p.funcao_barra}</td>
                    <td data-label="Ângulos" className="whitespace-nowrap">
                      <div className="inline-flex items-center gap-1.5">
                        <span
                          className={[
                            "inline-flex items-center px-1.5 py-0.5 font-mono text-[11px] border rounded-[2px]",
                            isMixed
                              ? "border-lider-wood/40 bg-lider-wood/10 text-lider-wood font-medium"
                              : "border-lider-border bg-lider-canvas text-lider-charcoal",
                          ].join(" ")}
                        >
                          {p.angulos_corte || `${aEsq}° / ${aDir}°`}
                        </span>
                        {p.invertida && (
                          <span className="inline-flex items-center px-1 py-0.5 font-mono text-[10px] border border-lider-wood/40 bg-lider-wood/10 text-lider-wood rounded-[2px]">
                            // gir.
                          </span>
                        )}
                        {p.juncao_entrada === "\\/" && (
                          <span className="inline-flex items-center px-1 py-0.5 font-mono text-[10px] border border-lider-border bg-lider-canvas text-lider-slate rounded-[2px]">
                            \/
                          </span>
                        )}
                        {p.troca_angulo_entrada && (
                          <span className="inline-flex items-center px-1 py-0.5 text-[10px] border border-lider-terracotta/40 bg-lider-terracotta/5 text-lider-terracotta rounded-[2px]">
                            Troca
                          </span>
                        )}
                      </div>
                    </td>
                    <td data-label="Acabamento" className="text-xs text-lider-slate">
                      {p.acabamento_perfil}
                    </td>
                    <td data-label="Medida Corte (mm)" className="num font-medium">
                      {fmtNum(p.medida_corte_mm)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ExecutionRouteTable({
  steps = [],
  showGroupCol = false,
  captionId,
}) {
  const flatRows = useMemo(() => {
    const out = [];
    for (const step of steps) {
      for (const alloc of step.alocacoes || []) {
        out.push({ step, alloc });
      }
    }
    return out;
  }, [steps]);

  if (!flatRows.length) {
    return (
      <div className="border border-lider-border rounded-[2px] bg-lider-canvas/60 px-4 py-6 text-center text-xs text-lider-slate">
        Nenhum passo de corte corresponde aos filtros aplicados.
      </div>
    );
  }

  return (
    <div
      tabIndex={0}
      role="region"
      aria-labelledby={captionId}
      className="table-wrapper stack-narrow"
    >
      <table className="lider-table">
        <caption id={captionId} className="visually-hidden">
          Roteiro de execução por medida da maior para a menor com reaproveitamento de sobras
        </caption>
        <thead>
          <tr>
            <th className="num-header">Passo</th>
            <th className="num-header">Medida (mm)</th>
            <th>Ângulos</th>
            {showGroupCol && <th>Grupo / Cód. Perfil</th>}
            <th>Origem na Barra</th>
            <th className="num-header">Qtd Cortes</th>
            <th className="num-header">Sobra Antes → Depois (mm)</th>
            <th>OPs</th>
          </tr>
        </thead>
        <tbody>
          {flatRows.map(({ step, alloc }, idx) => {
            const barNumDisplay = showGroupCol
              ? alloc.barra_global_numero || alloc.barra_numero
              : alloc.barra_numero;
            return (
              <tr
                key={`${step.grupo_key}-${step.passo}-${alloc.barra_numero}-${idx}`}
              >
                <th scope="row" data-label="Passo" className="font-mono text-xs">
                  <div className="inline-flex flex-wrap items-center gap-1.5">
                    <span>#{step.passo}</span>
                    {step.troca_medida && (
                      <span className="inline-flex items-center px-1.5 py-0.5 text-[10px] border border-lider-wood/40 bg-lider-wood/5 text-lider-wood rounded-[2px]">
                        Troca
                      </span>
                    )}
                    {step.troca_angulo && (
                      <span className="inline-flex items-center px-1.5 py-0.5 text-[10px] border border-lider-terracotta/40 bg-lider-terracotta/5 text-lider-terracotta rounded-[2px]">
                        Troca âng.
                      </span>
                    )}
                  </div>
                </th>
                <td
                  data-label="Medida (mm)"
                  className="num font-mono font-medium text-lider-ink"
                >
                  {fmtNum(step.medida_corte_mm)} mm
                </td>
                <td data-label="Ângulos" className="whitespace-nowrap">
                  <span className="inline-flex items-center px-1.5 py-0.5 font-mono text-[11px] border border-lider-border bg-lider-canvas text-lider-charcoal rounded-[2px]">
                    {alloc.angulos_corte || step.angulos_corte || "45° / 45°"}
                  </span>
                </td>
                {showGroupCol && (
                  <td data-label="Grupo / Cód. Perfil">
                    <span
                      className={[
                        "inline-flex items-center px-2 py-0.5 text-[11px] font-medium border rounded-[2px]",
                        step.origem_agrupamento === "codigo_perfil"
                          ? "border-lider-wood/40 bg-lider-wood/5 text-lider-wood font-mono"
                          : "border-lider-border bg-lider-canvas text-lider-charcoal",
                      ].join(" ")}
                    >
                      {step.grupo_nome}
                    </span>
                  </td>
                )}
                <td data-label="Origem na Barra">
                  {alloc.eh_sobra ? (
                    <span className="inline-flex items-center px-2 py-0.5 text-[11px] font-medium border border-lider-wood/40 bg-lider-wood/10 text-lider-wood rounded-[2px]">
                      Sobra da Barra #{barNumDisplay}
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-2 py-0.5 text-[11px] font-medium bg-lider-charcoal text-white rounded-[2px]">
                      Barra #{barNumDisplay} (nova)
                    </span>
                  )}
                </td>
                <td data-label="Qtd Cortes" className="num font-medium">
                  {alloc.qtd_cortes}×
                </td>
                <td
                  data-label="Sobra Antes → Depois (mm)"
                  className="num font-mono text-xs text-lider-slate"
                >
                  {fmtNum(alloc.sobra_antes_mm)} →{" "}
                  <strong className="font-medium text-lider-ink">
                    {fmtNum(alloc.sobra_depois_mm)}
                  </strong>
                </td>
                <td data-label="OPs" className="font-mono text-xs text-lider-slate">
                  {alloc.ops || "-"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function OptimizationTab({
  optimization,
  config,
  isOptimizing = false,
  onOptimize,
  onExport,
  exportingKey = null,
  hasData = false,
}) {
  const effectiveConfig = config || optimization?.config || {
    comprimento_barra_mm: 6000,
    espessura_serra_mm: 0,
    desponte_mm: 0,
    separar_por_acabamento: false,
  };

  const [barraMm, setBarraMm] = useState(
    String(effectiveConfig.comprimento_barra_mm ?? 6000)
  );
  const [serraMm, setSerraMm] = useState(
    String(effectiveConfig.espessura_serra_mm ?? 0)
  );
  const [desponteMm, setDesponteMm] = useState(
    String(effectiveConfig.desponte_mm ?? 0)
  );
  const [separarAcabamento, setSepararAcabamento] = useState(
    Boolean(effectiveConfig.separar_por_acabamento)
  );
  const [errors, setErrors] = useState({});

  const [activeScenario, setActiveScenario] = useState("material");
  const [tempoDisplayMode, setTempoDisplayMode] = useState("roteiro");
  const [viewMode, setViewMode] = useState("grupos");
  const [grupoFilter, setGrupoFilter] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [expandedMap, setExpandedMap] = useState({});

  const uid = useId();
  const barraRef = useRef(null);
  const serraRef = useRef(null);
  const desponteRef = useRef(null);

  useEffect(() => {
    const src = config || optimization?.config;
    if (!src) return;
    setBarraMm(String(src.comprimento_barra_mm ?? 6000));
    setSerraMm(String(src.espessura_serra_mm ?? 0));
    setDesponteMm(String(src.desponte_mm ?? 0));
    setSepararAcabamento(Boolean(src.separar_por_acabamento));
    setErrors({});
  }, [config, optimization?.config]);

  const validateFields = (
    bVal = barraMm,
    sVal = serraMm,
    dVal = desponteMm
  ) => {
    const nextErrors = {};
    const bNum = Number(bVal);
    const sNum = Number(sVal);
    const dNum = Number(dVal);

    if (!Number.isFinite(bNum) || bNum < 100) {
      nextErrors.barraMm = "Informe um comprimento >= 100 mm.";
    }
    if (!Number.isFinite(sNum) || sNum < 0) {
      nextErrors.serraMm = "A espessura de serra deve ser >= 0 mm.";
    }
    if (!Number.isFinite(dNum) || dNum < 0 || (Number.isFinite(bNum) && dNum >= bNum)) {
      nextErrors.desponteMm = "Desponte deve ser >= 0 e menor que a barra.";
    }
    return { nextErrors, parsed: { bNum, sNum, dNum } };
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const { nextErrors, parsed } = validateFields();
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      if (nextErrors.barraMm) barraRef.current?.focus();
      else if (nextErrors.serraMm) serraRef.current?.focus();
      else if (nextErrors.desponteMm) desponteRef.current?.focus();
      return;
    }

    onOptimize({
      comprimento_barra_mm: parsed.bNum,
      espessura_serra_mm: parsed.sNum,
      desponte_mm: parsed.dNum,
      separar_por_acabamento: separarAcabamento,
    });
  };

  const activeBarraMm = Number(optimization?.config?.comprimento_barra_mm ?? 6000);
  const activeDesponteMm = Number(optimization?.config?.desponte_mm ?? 0);
  const cenarios = optimization?.cenarios;
  const pecasInviaveisFlat = optimization?.pecas_inviaveis_flat || [];

  const grupoOptions = useMemo(() => {
    const src = cenarios?.material?.grupos || [];
    return src.map((g) => ({ key: g.grupo_key, label: g.grupo_nome }));
  }, [cenarios?.material?.grupos]);

  const materialView = useMemo(
    () =>
      filterScenarioAndComputeMetrics(
        cenarios?.material,
        "material",
        grupoFilter,
        searchTerm,
        activeBarraMm,
        pecasInviaveisFlat
      ),
    [cenarios?.material, grupoFilter, searchTerm, activeBarraMm, pecasInviaveisFlat]
  );

  const tempoView = useMemo(
    () =>
      filterScenarioAndComputeMetrics(
        cenarios?.tempo_execucao,
        "tempo_execucao",
        grupoFilter,
        searchTerm,
        activeBarraMm,
        pecasInviaveisFlat
      ),
    [cenarios?.tempo_execucao, grupoFilter, searchTerm, activeBarraMm, pecasInviaveisFlat]
  );

  const activeView = activeScenario === "material" ? materialView : tempoView;
  const mMat = materialView.metrics;
  const mTmp = tempoView.metrics;
  const activeMetrics = activeView.metrics;

  const hasActiveFilter = Boolean(grupoFilter || searchTerm.trim());

  const diffBarsTmpVsMat = mTmp.totalBarras - mMat.totalBarras;
  const diffAdjTmpVsMat = mMat.totalAjustes - mTmp.totalAjustes;
  const reducaoAdjPct =
    mMat.totalAjustes > 0
      ? Math.round((diffAdjTmpVsMat / mMat.totalAjustes) * 1000) / 10
      : 0;

  // Payload filtrado enviado nos CSVs caso haja filtro aplicado
  const buildFilteredExportOptimization = () => {
    if (!optimization || !hasActiveFilter) return undefined;
    return {
      ...optimization,
      cenarios: {
        material: {
          ...cenarios?.material,
          grupos: materialView.filteredGroups,
          barras_flat: materialView.filteredBarsFlat,
        },
        tempo_execucao: {
          ...cenarios?.tempo_execucao,
          grupos: tempoView.filteredGroups,
          barras_flat: tempoView.filteredBarsFlat,
          roteiro_flat: tempoView.filteredRoteiroFlat,
        },
      },
      pecas_inviaveis_flat: activeView.filteredInviaveis,
    };
  };

  const filteredGroups = activeView.filteredGroups;
  const isGroupOpen = (key, idx) => {
    if (Object.prototype.hasOwnProperty.call(expandedMap, key)) {
      return Boolean(expandedMap[key]);
    }
    return idx === 0;
  };

  const allExpanded =
    filteredGroups.length > 0 &&
    filteredGroups.every((g, idx) => isGroupOpen(g.grupo_key, idx));

  const handleToggleAll = () => {
    const nextOpen = !allExpanded;
    const next = { ...expandedMap };
    filteredGroups.forEach((g) => {
      next[g.grupo_key] = nextOpen;
    });
    setExpandedMap(next);
  };

  const resetFilters = () => {
    setGrupoFilter("");
    setSearchTerm("");
  };

  const inputBaseCls =
    "w-full h-10 px-3 bg-lider-surface border rounded-[2px] font-mono text-sm text-lider-ink tabular-nums focus:outline-none transition-colors";
  const barraMetrosLabel = fmtNum(activeBarraMm / 1000);

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Formulário de Parâmetros Configuráveis (sem perda máxima) */}
      <form
        onSubmit={handleSubmit}
        noValidate
        aria-labelledby="opt-params-title"
        className="border border-lider-border rounded-[2px] bg-lider-canvas/60 p-5 space-y-4"
      >
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-2">
          <div>
            <h3
              id="opt-params-title"
              className="font-display font-normal text-base text-lider-ink"
            >
              Parâmetros da Otimização Linear em Barras
            </h3>
            <p className="text-xs text-lider-slate mt-0.5">
              Agrupamento físico pelo Código do Perfil cadastrado em Regras e Descontos (fallback: Modelo + Tipo). Calcula em paralelo o melhor aproveitamento de material e o menor tempo de execução.
            </p>
          </div>
          {Object.keys(errors).length > 0 && (
            <div
              role="status"
              aria-live="polite"
              className="inline-flex items-center gap-1.5 text-xs text-red-800 bg-red-50 border border-red-700/30 px-2.5 py-1 rounded-[2px]"
            >
              <AlertCircle className="w-3.5 h-3.5 shrink-0" strokeWidth={1.5} />
              <span>Corrija os campos destacados antes de otimizar.</span>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 items-start">
          {/* Comprimento da barra (mm) */}
          <div className="space-y-1">
            <label
              htmlFor={`${uid}-barra`}
              className="block text-[11px] uppercase tracking-[0.06em] text-lider-slate"
            >
              Barra (mm)
            </label>
            <input
              ref={barraRef}
              id={`${uid}-barra`}
              name="comprimento_barra_mm"
              type="text"
              inputMode="decimal"
              value={barraMm}
              onChange={(e) => {
                setBarraMm(e.target.value);
                if (errors.barraMm || errors.desponteMm) {
                  setErrors((prev) => ({
                    ...prev,
                    barraMm: undefined,
                    desponteMm: undefined,
                  }));
                }
              }}
              onBlur={() => {
                const { nextErrors } = validateFields();
                setErrors((prev) => ({
                  ...prev,
                  barraMm: nextErrors.barraMm,
                  desponteMm: nextErrors.desponteMm,
                }));
              }}
              aria-invalid={errors.barraMm ? "true" : undefined}
              aria-describedby={`${uid}-barra-help`}
              className={`${inputBaseCls} ${
                errors.barraMm
                  ? "border-red-700 focus:border-red-700"
                  : "border-lider-border focus:border-lider-charcoal"
              }`}
            />
            <p
              id={`${uid}-barra-help`}
              className={`text-[11px] ${
                errors.barraMm ? "text-red-700" : "text-lider-muted"
              }`}
            >
              {errors.barraMm || `= ${fmtNum((Number(barraMm) || 0) / 1000)} m`}
            </p>
          </div>

          {/* Serra / Kerf (mm) */}
          <div className="space-y-1">
            <label
              htmlFor={`${uid}-serra`}
              className="block text-[11px] uppercase tracking-[0.06em] text-lider-slate"
            >
              Serra / Kerf (mm)
            </label>
            <input
              ref={serraRef}
              id={`${uid}-serra`}
              name="espessura_serra_mm"
              type="text"
              inputMode="decimal"
              value={serraMm}
              onChange={(e) => {
                setSerraMm(e.target.value);
                if (errors.serraMm) {
                  setErrors((prev) => ({ ...prev, serraMm: undefined }));
                }
              }}
              onBlur={() => {
                const { nextErrors } = validateFields();
                setErrors((prev) => ({ ...prev, serraMm: nextErrors.serraMm }));
              }}
              aria-invalid={errors.serraMm ? "true" : undefined}
              aria-describedby={`${uid}-serra-help`}
              className={`${inputBaseCls} ${
                errors.serraMm
                  ? "border-red-700 focus:border-red-700"
                  : "border-lider-border focus:border-lider-charcoal"
              }`}
            />
            <p
              id={`${uid}-serra-help`}
              className={`text-[11px] ${
                errors.serraMm ? "text-red-700" : "text-lider-muted"
              }`}
            >
              {errors.serraMm || "Desconto por corte entre peças"}
            </p>
          </div>

          {/* Desponte (mm) */}
          <div className="space-y-1">
            <label
              htmlFor={`${uid}-desponte`}
              className="block text-[11px] uppercase tracking-[0.06em] text-lider-slate"
            >
              Desponte (mm)
            </label>
            <input
              ref={desponteRef}
              id={`${uid}-desponte`}
              name="desponte_mm"
              type="text"
              inputMode="decimal"
              value={desponteMm}
              onChange={(e) => {
                setDesponteMm(e.target.value);
                if (errors.desponteMm) {
                  setErrors((prev) => ({ ...prev, desponteMm: undefined }));
                }
              }}
              onBlur={() => {
                const { nextErrors } = validateFields();
                setErrors((prev) => ({ ...prev, desponteMm: nextErrors.desponteMm }));
              }}
              aria-invalid={errors.desponteMm ? "true" : undefined}
              aria-describedby={`${uid}-desponte-help`}
              className={`${inputBaseCls} ${
                errors.desponteMm
                  ? "border-red-700 focus:border-red-700"
                  : "border-lider-border focus:border-lider-charcoal"
              }`}
            />
            <p
              id={`${uid}-desponte-help`}
              className={`text-[11px] ${
                errors.desponteMm ? "text-red-700" : "text-lider-muted"
              }`}
            >
              {errors.desponteMm || "Perda fixa nas pontas"}
            </p>
          </div>

          {/* Separar por acabamento */}
          <div className="flex items-center lg:pt-6">
            <input
              id={`${uid}-acab`}
              name="separar_por_acabamento"
              type="checkbox"
              checked={separarAcabamento}
              onChange={(e) => setSepararAcabamento(e.target.checked)}
              className="w-4 h-4 rounded-[2px] border-lider-border text-lider-wood focus:ring-lider-wood cursor-pointer shrink-0"
            />
            <label
              htmlFor={`${uid}-acab`}
              className="ml-2 text-xs text-lider-ink cursor-pointer select-none leading-snug"
            >
              Separar por acabamento
            </label>
          </div>

          {/* Botão Otimizar */}
          <div className="lg:pt-5 flex justify-end">
            <button
              type="submit"
              disabled={!hasData || isOptimizing}
              className="w-full h-10 px-4 bg-lider-charcoal hover:bg-lider-ink disabled:opacity-45 disabled:cursor-not-allowed text-white text-xs font-display uppercase tracking-[0.08em] font-medium rounded-[2px] inline-flex items-center justify-center gap-2 transition-colors"
            >
              {isOptimizing ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" strokeWidth={1.5} />
              ) : (
                <Play className="w-3.5 h-3.5" strokeWidth={1.5} />
              )}
              <span>Otimizar Barras</span>
            </button>
          </div>
        </div>
      </form>

      {!hasData || !cenarios ? (
        <div className="border border-lider-border rounded-[2px] bg-lider-surface px-6 py-14 text-center text-sm text-lider-muted">
          Nenhum dado carregado. Consulte o ERP ou carregue um ou mais arquivos HTML para otimizar as barras de 6 m.
        </div>
      ) : (
        <>
          {/* Seletor Comparativo dos 2 Cenários (100% dinâmico pelo filtro) */}
          <fieldset className="space-y-2">
            <legend className="text-[11px] uppercase tracking-[0.08em] text-lider-slate font-medium">
              Comparativo e Seleção de Cenário {hasActiveFilter ? "· Recorte Filtrado" : ""}
            </legend>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Cenário 1: Aproveitamento de Material */}
              <label
                htmlFor={`${uid}-scen-mat`}
                className={[
                  "cursor-pointer border rounded-[2px] p-4 flex flex-col justify-between gap-3 transition-colors select-none",
                  activeScenario === "material"
                    ? "border-lider-charcoal bg-lider-surface shadow-lider ring-1 ring-lider-charcoal/15"
                    : "border-lider-border bg-lider-canvas/50 hover:bg-lider-surface",
                ].join(" ")}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-2.5 min-w-0">
                    <input
                      type="radio"
                      id={`${uid}-scen-mat`}
                      name="opt_scenario"
                      value="material"
                      checked={activeScenario === "material"}
                      onChange={() => setActiveScenario("material")}
                      className="mt-0.5 text-lider-charcoal focus:ring-lider-charcoal"
                    />
                    <div>
                      <span className="font-display font-medium text-sm text-lider-ink block">
                        Cenário 1 — Aproveitamento de Material
                      </span>
                      <span className="text-xs text-lider-slate">
                        Menor consumo de barras {barraMetrosLabel}m com encadeamento de medidas entre barras.
                      </span>
                    </div>
                  </div>
                  <Scissors className="w-4 h-4 text-lider-wood shrink-0 mt-0.5" strokeWidth={1.5} />
                </div>

                <div className="grid grid-cols-4 gap-2 pt-2 border-t border-lider-border text-xs tabular-nums">
                  <div>
                    <span className="block text-[10px] uppercase text-lider-muted">Barras</span>
                    <strong className="font-medium text-lider-ink text-sm">
                      {mMat.totalBarras}
                    </strong>
                  </div>
                  <div>
                    <span className="block text-[10px] uppercase text-lider-muted">Aproveit.</span>
                    <strong className="font-medium text-lider-wood text-sm">
                      {fmtNum(mMat.aproveitamentoMedioPct)}%
                    </strong>
                  </div>
                  <div>
                    <span className="block text-[10px] uppercase text-lider-muted">Perda</span>
                    <strong className="font-medium text-lider-ink text-sm">
                      {fmtNum(mMat.totalPerdaMetros)} m
                    </strong>
                  </div>
                  <div>
                    <span className="block text-[10px] uppercase text-lider-muted">Ajustes</span>
                    <strong className="font-medium text-lider-ink text-sm">
                      {mMat.totalAjustes}
                    </strong>
                    <span className="block text-[10px] text-lider-muted">
                      {mMat.totalTrocasAngulo} âng.
                    </span>
                  </div>
                </div>
              </label>

              {/* Cenário 2: Tempo de Execução */}
              <label
                htmlFor={`${uid}-scen-tmp`}
                className={[
                  "cursor-pointer border rounded-[2px] p-4 flex flex-col justify-between gap-3 transition-colors select-none",
                  activeScenario === "tempo_execucao"
                    ? "border-lider-wood bg-lider-surface shadow-lider ring-1 ring-lider-wood/20"
                    : "border-lider-border bg-lider-canvas/50 hover:bg-lider-surface",
                ].join(" ")}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-2.5 min-w-0">
                    <input
                      type="radio"
                      id={`${uid}-scen-tmp`}
                      name="opt_scenario"
                      value="tempo_execucao"
                      checked={activeScenario === "tempo_execucao"}
                      onChange={() => setActiveScenario("tempo_execucao")}
                      className="mt-0.5 text-lider-wood focus:ring-lider-wood"
                    />
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-display font-medium text-sm text-lider-ink">
                          Cenário 2 — Tempo de Execução (Maior → Menor)
                        </span>
                        {diffAdjTmpVsMat > 0 && (
                          <span className="inline-flex items-center px-1.5 py-0.5 text-[10px] font-medium border border-lider-wood/40 bg-lider-wood/10 text-lider-wood rounded-[2px]">
                            −{fmtNum(reducaoAdjPct)}% trocas
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-lider-slate">
                        Corte em lote por medida reaproveitando barras semi-cortadas (mínimo de ajustes).
                      </span>
                    </div>
                  </div>
                  <Clock className="w-4 h-4 text-lider-wood shrink-0 mt-0.5" strokeWidth={1.5} />
                </div>

                <div className="grid grid-cols-4 gap-2 pt-2 border-t border-lider-border text-xs tabular-nums">
                  <div>
                    <span className="block text-[10px] uppercase text-lider-muted">Barras</span>
                    <strong className="font-medium text-lider-ink text-sm">
                      {mTmp.totalBarras}
                    </strong>{" "}
                    <span className="text-[11px] text-lider-muted">
                      {diffBarsTmpVsMat === 0
                        ? "(=)"
                        : diffBarsTmpVsMat > 0
                        ? `(+${diffBarsTmpVsMat})`
                        : `(${diffBarsTmpVsMat})`}
                    </span>
                  </div>
                  <div>
                    <span className="block text-[10px] uppercase text-lider-muted">Aproveit.</span>
                    <strong className="font-medium text-lider-wood text-sm">
                      {fmtNum(mTmp.aproveitamentoMedioPct)}%
                    </strong>
                  </div>
                  <div>
                    <span className="block text-[10px] uppercase text-lider-muted">Perda</span>
                    <strong className="font-medium text-lider-ink text-sm">
                      {fmtNum(mTmp.totalPerdaMetros)} m
                    </strong>
                  </div>
                  <div>
                    <span className="block text-[10px] uppercase text-lider-muted">Ajustes</span>
                    <strong className="font-medium text-lider-wood text-sm">
                      {mTmp.totalAjustes}
                    </strong>
                    <span className="block text-[10px] text-lider-muted">
                      {mTmp.totalTrocasAngulo} âng.
                    </span>
                  </div>
                </div>
              </label>
            </div>
          </fieldset>

          {/* Faixa de 5 KPIs Dinâmicos conforme o Filtro e Cenário Ativo */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-5 gap-4">
            <article className="bg-lider-surface border border-lider-border rounded-[2px] shadow-lider p-4 flex flex-col justify-between gap-2">
              <div className="flex items-center justify-between">
                <span className="font-display text-[11px] uppercase tracking-[0.08em] text-lider-muted font-medium">
                  Barras {barraMetrosLabel}m
                </span>
                <Scissors className="w-4 h-4 text-lider-wood" strokeWidth={1.5} />
              </div>
              <div>
                <strong className="block font-display font-normal text-2xl text-lider-ink tabular-nums">
                  {activeMetrics.totalBarras}
                </strong>
                <span className="block text-xs text-lider-slate mt-0.5 tabular-nums">
                  {activeMetrics.totalPecas} peças · {fmtNum(activeMetrics.totalMetrosPecas)} m
                </span>
              </div>
            </article>

            <article className="bg-lider-surface border border-lider-border rounded-[2px] shadow-lider p-4 flex flex-col justify-between gap-2">
              <div className="flex items-center justify-between">
                <span className="font-display text-[11px] uppercase tracking-[0.08em] text-lider-muted font-medium">
                  Aproveit. Médio / Barra
                </span>
                <Layers className="w-4 h-4 text-lider-wood" strokeWidth={1.5} />
              </div>
              <div>
                <strong className="block font-display font-normal text-2xl text-lider-wood tabular-nums">
                  {fmtNum(activeMetrics.aproveitamentoMedioPct)}%
                </strong>
                <span className="block text-xs text-lider-slate mt-0.5">
                  {activeScenario === "material"
                    ? "Cenário Material"
                    : "Cenário Tempo (Lote FFD)"}
                </span>
              </div>
            </article>

            <article className="bg-lider-surface border border-lider-border rounded-[2px] shadow-lider p-4 flex flex-col justify-between gap-2">
              <div className="flex items-center justify-between">
                <span className="font-display text-[11px] uppercase tracking-[0.08em] text-lider-muted font-medium">
                  Perda Total
                </span>
                <AlertCircle className="w-4 h-4 text-lider-terracotta" strokeWidth={1.5} />
              </div>
              <div>
                <strong className="block font-display font-normal text-2xl text-lider-terracotta tabular-nums">
                  {fmtNum(activeMetrics.totalPerdaMm)} mm
                </strong>
                <span className="block text-xs text-lider-slate mt-0.5 tabular-nums">
                  {fmtNum(activeMetrics.totalPerdaMetros)} m · Média{" "}
                  {fmtNum(activeMetrics.perdaMediaBarraMm)} mm/barra
                </span>
              </div>
            </article>

            <article className="bg-lider-surface border border-lider-border rounded-[2px] shadow-lider p-4 flex flex-col justify-between gap-2">
              <div className="flex items-center justify-between">
                <span className="font-display text-[11px] uppercase tracking-[0.08em] text-lider-muted font-medium">
                  Ajustes no Corte
                </span>
                <SlidersHorizontal className="w-4 h-4 text-lider-wood" strokeWidth={1.5} />
              </div>
              <div>
                <strong className="block font-display font-normal text-2xl text-lider-ink tabular-nums">
                  {activeMetrics.totalAjustes}
                </strong>
                <span className="block text-xs text-lider-slate mt-0.5 tabular-nums">
                  {activeScenario === "material"
                    ? `Medida (Tempo: ${mTmp.totalAjustes}) · ${activeMetrics.totalTrocasAngulo} trocas âng.`
                    : diffAdjTmpVsMat > 0
                    ? `${diffAdjTmpVsMat} med. a menos (−${fmtNum(reducaoAdjPct)}%) · ${activeMetrics.totalTrocasAngulo} trocas âng.`
                    : `Trocas medida · ${activeMetrics.totalTrocasAngulo} trocas âng.`}
                </span>
              </div>
            </article>

            <article className="bg-lider-surface border border-lider-border rounded-[2px] shadow-lider p-4 flex flex-col justify-between gap-2">
              <div className="flex items-center justify-between">
                <span className="font-display text-[11px] uppercase tracking-[0.08em] text-lider-muted font-medium">
                  Grupos de Perfil
                </span>
                <Filter
                  className={`w-4 h-4 ${
                    hasActiveFilter ? "text-lider-terracotta" : "text-lider-wood"
                  }`}
                  strokeWidth={1.5}
                />
              </div>
              <div>
                <strong className="block font-display font-normal text-2xl text-lider-ink tabular-nums">
                  {activeMetrics.gruposExibidos}
                  <span className="text-base text-lider-muted">
                    /{activeMetrics.totalGrupos}
                  </span>
                </strong>
                <span className="block text-xs text-lider-slate mt-0.5">
                  {hasActiveFilter ? "KPIs filtrados dinamicamente" : "Todos os perfis"}
                </span>
              </div>
            </article>
          </div>

          {/* Barra de Filtros, Sub-visões e Exportação CSV */}
          <search>
            <div className="flex flex-col xl:flex-row xl:items-end justify-between gap-4">
              <div className="flex flex-wrap items-end gap-3.5">
                <fieldset>
                  <legend className="text-[11px] uppercase tracking-[0.06em] text-lider-slate mb-1.5">
                    Organização
                  </legend>
                  <div className="inline-flex border border-lider-border rounded-[2px] bg-lider-canvas p-0.5">
                    <label
                      htmlFor={`${uid}-view-grupos`}
                      className={[
                        "px-3 py-1.5 text-xs rounded-[2px] cursor-pointer transition-colors select-none",
                        viewMode === "grupos"
                          ? "bg-lider-surface text-lider-ink font-medium shadow-sm"
                          : "text-lider-slate hover:text-lider-ink",
                      ].join(" ")}
                    >
                      <input
                        type="radio"
                        id={`${uid}-view-grupos`}
                        name="opt_view_mode"
                        value="grupos"
                        checked={viewMode === "grupos"}
                        onChange={() => setViewMode("grupos")}
                        className="sr-only"
                      />
                      Por Grupo de Perfil
                    </label>
                    <label
                      htmlFor={`${uid}-view-consolidado`}
                      className={[
                        "px-3 py-1.5 text-xs rounded-[2px] cursor-pointer transition-colors select-none",
                        viewMode === "consolidado"
                          ? "bg-lider-surface text-lider-ink font-medium shadow-sm"
                          : "text-lider-slate hover:text-lider-ink",
                      ].join(" ")}
                    >
                      <input
                        type="radio"
                        id={`${uid}-view-consolidado`}
                        name="opt_view_mode"
                        value="consolidado"
                        checked={viewMode === "consolidado"}
                        onChange={() => setViewMode("consolidado")}
                        className="sr-only"
                      />
                      Visão Consolidada
                    </label>
                  </div>
                </fieldset>

                {activeScenario === "tempo_execucao" && (
                  <fieldset>
                    <legend className="text-[11px] uppercase tracking-[0.06em] text-lider-slate mb-1.5">
                      Exibição do Tempo
                    </legend>
                    <div className="inline-flex border border-lider-border rounded-[2px] bg-lider-canvas p-0.5">
                      <label
                        htmlFor={`${uid}-tmp-roteiro`}
                        className={[
                          "px-3 py-1.5 text-xs rounded-[2px] cursor-pointer transition-colors select-none",
                          tempoDisplayMode === "roteiro"
                            ? "bg-lider-surface text-lider-ink font-medium shadow-sm"
                            : "text-lider-slate hover:text-lider-ink",
                        ].join(" ")}
                      >
                        <input
                          type="radio"
                          id={`${uid}-tmp-roteiro`}
                          name="opt_tempo_mode"
                          value="roteiro"
                          checked={tempoDisplayMode === "roteiro"}
                          onChange={() => setTempoDisplayMode("roteiro")}
                          className="sr-only"
                        />
                        Roteiro por Medida
                      </label>
                      <label
                        htmlFor={`${uid}-tmp-barras`}
                        className={[
                          "px-3 py-1.5 text-xs rounded-[2px] cursor-pointer transition-colors select-none",
                          tempoDisplayMode === "barras"
                            ? "bg-lider-surface text-lider-ink font-medium shadow-sm"
                            : "text-lider-slate hover:text-lider-ink",
                        ].join(" ")}
                      >
                        <input
                          type="radio"
                          id={`${uid}-tmp-barras`}
                          name="opt_tempo_mode"
                          value="barras"
                          checked={tempoDisplayMode === "barras"}
                          onChange={() => setTempoDisplayMode("barras")}
                          className="sr-only"
                        />
                        Mapa Visual 1D
                      </label>
                    </div>
                  </fieldset>
                )}

                <div className="min-w-[180px]">
                  <label
                    htmlFor={`${uid}-filtro-grupo`}
                    className="block text-[11px] uppercase tracking-[0.06em] text-lider-slate mb-1.5"
                  >
                    Filtrar Grupo / Perfil
                  </label>
                  <select
                    id={`${uid}-filtro-grupo`}
                    value={grupoFilter}
                    onChange={(e) => setGrupoFilter(e.target.value)}
                    className="w-full h-10 px-3 bg-lider-surface border border-lider-border rounded-[2px] text-sm text-lider-ink focus:border-lider-charcoal focus:outline-none transition-colors"
                  >
                    <option value="">Todos os Grupos</option>
                    {grupoOptions.map((opt) => (
                      <option key={opt.key} value={opt.key}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="min-w-[210px]">
                  <label
                    htmlFor={`${uid}-busca`}
                    className="block text-[11px] uppercase tracking-[0.06em] text-lider-slate mb-1.5"
                  >
                    Buscar Código / OP / Medida
                  </label>
                  <div className="relative">
                    <Search
                      className="w-3.5 h-3.5 text-lider-muted absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
                      strokeWidth={1.5}
                    />
                    <input
                      type="search"
                      id={`${uid}-busca`}
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      placeholder="5307, OP, 2489..."
                      autoCorrect="off"
                      autoCapitalize="none"
                      spellCheck={false}
                      className="w-full h-10 pl-9 pr-8 bg-lider-surface border border-lider-border rounded-[2px] text-sm text-lider-ink placeholder:text-lider-muted/70 focus:border-lider-charcoal focus:outline-none transition-colors"
                    />
                    {searchTerm && (
                      <button
                        type="button"
                        onClick={() => setSearchTerm("")}
                        aria-label="Limpar busca da otimização"
                        className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1 text-lider-muted hover:text-lider-ink"
                      >
                        <X className="w-3.5 h-3.5" strokeWidth={1.5} />
                      </button>
                    )}
                  </div>
                </div>

                {hasActiveFilter && (
                  <button
                    type="button"
                    onClick={resetFilters}
                    className="h-10 px-3 inline-flex items-center gap-1.5 text-xs border border-lider-border rounded-[2px] text-lider-charcoal hover:bg-lider-canvas transition-colors"
                  >
                    <RotateCcw className="w-3.5 h-3.5" strokeWidth={1.5} />
                    <span>Limpar</span>
                  </button>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-2 shrink-0">
                {viewMode === "grupos" && filteredGroups.length > 0 && (
                  <button
                    type="button"
                    aria-expanded={allExpanded}
                    onClick={handleToggleAll}
                    className="h-9 px-3 text-xs font-medium rounded-[2px] border border-lider-border hover:border-lider-charcoal bg-lider-canvas text-lider-charcoal transition-colors"
                  >
                    {allExpanded ? "Recolher todos" : "Expandir todos"}
                  </button>
                )}
                {onExport && (
                  <>
                    <button
                      type="button"
                      disabled={!hasData || Boolean(exportingKey)}
                      onClick={() =>
                        onExport(
                          "csv-opt-mat",
                          "/api/export/csv",
                          {
                            mode: "otimizacao_material",
                            bar_optimization: buildFilteredExportOptimization(),
                          },
                          "otimizacao_material_6m.csv"
                        )
                      }
                      title={
                        hasActiveFilter
                          ? "Exportar Cenário Material (recorte filtrado)"
                          : "Exportar Cenário Material completo"
                      }
                      className="h-9 px-3 text-xs font-medium rounded-[2px] border border-lider-border hover:border-lider-charcoal bg-transparent hover:bg-lider-canvas text-lider-charcoal inline-flex items-center gap-1.5 transition-colors disabled:opacity-45"
                    >
                      <Download className="w-3.5 h-3.5" strokeWidth={1.5} />
                      <span>CSV Material</span>
                    </button>
                    <button
                      type="button"
                      disabled={!hasData || Boolean(exportingKey)}
                      onClick={() =>
                        onExport(
                          "csv-opt-rot",
                          "/api/export/csv",
                          {
                            mode: "otimizacao_tempo_roteiro",
                            bar_optimization: buildFilteredExportOptimization(),
                          },
                          "otimizacao_tempo_roteiro_6m.csv"
                        )
                      }
                      title={
                        hasActiveFilter
                          ? "Exportar Roteiro por Medida (recorte filtrado)"
                          : "Exportar Roteiro por Medida completo"
                      }
                      className="h-9 px-3 text-xs font-medium rounded-[2px] border border-lider-border hover:border-lider-charcoal bg-transparent hover:bg-lider-canvas text-lider-charcoal inline-flex items-center gap-1.5 transition-colors disabled:opacity-45"
                    >
                      <Download className="w-3.5 h-3.5" strokeWidth={1.5} />
                      <span>CSV Tempo (Roteiro)</span>
                    </button>
                    <button
                      type="button"
                      disabled={!hasData || Boolean(exportingKey)}
                      onClick={() =>
                        onExport(
                          "csv-opt-tmp",
                          "/api/export/csv",
                          {
                            mode: "otimizacao_tempo_barras",
                            bar_optimization: buildFilteredExportOptimization(),
                          },
                          "otimizacao_tempo_barras_6m.csv"
                        )
                      }
                      title={
                        hasActiveFilter
                          ? "Exportar Barras do Cenário Tempo (recorte filtrado)"
                          : "Exportar Barras do Cenário Tempo completo"
                      }
                      className="h-9 px-3 text-xs font-medium rounded-[2px] border border-lider-border hover:border-lider-charcoal bg-transparent hover:bg-lider-canvas text-lider-charcoal inline-flex items-center gap-1.5 transition-colors disabled:opacity-45"
                    >
                      <Download className="w-3.5 h-3.5" strokeWidth={1.5} />
                      <span>CSV Tempo (Barras)</span>
                    </button>
                  </>
                )}
              </div>
            </div>
          </search>

          {/* Aviso de peças maiores que a barra útil */}
          {activeView.filteredInviaveis.length > 0 && (
            <div className="border border-lider-terracotta/40 bg-lider-terracotta/5 rounded-[2px] p-4 space-y-2">
              <div className="flex items-center gap-2 text-xs font-medium text-lider-terracotta">
                <AlertCircle className="w-4 h-4 shrink-0" strokeWidth={1.5} />
                <span>
                  {activeView.filteredInviaveis.length} peça(s) excedem a barra útil (
                  {fmtNum(activeBarraMm - activeDesponteMm)} mm) e não podem ser cortadas neste comprimento:
                </span>
              </div>
              <div className="flex flex-wrap gap-2 text-xs font-mono">
                {activeView.filteredInviaveis.map((p, i) => (
                  <span
                    key={`${p.op}-${p.codigo}-${i}`}
                    className="px-2 py-0.5 bg-lider-surface border border-lider-terracotta/30 rounded-[2px] text-lider-ink"
                  >
                    {p.grupo_nome}: {fmtNum(p.medida_corte_mm)} mm (OP {p.op})
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Legenda dos ângulos quando em Mapa Visual 1D / Material */}
          {(activeScenario === "material" || tempoDisplayMode === "barras") && (
            <AngleLegend />
          )}

          {/* Conteúdo por Organização */}
          {viewMode === "grupos" ? (
            !filteredGroups.length ? (
              <div className="border border-lider-border rounded-[2px] bg-lider-surface px-6 py-12 text-center text-sm text-lider-muted">
                Nenhum grupo ou barra corresponde aos filtros aplicados.
              </div>
            ) : (
              <section
                className="opt-accordion space-y-4"
                aria-label="Grupos de otimização por perfil"
              >
                {filteredGroups.map((g, gIdx) => {
                  const open = isGroupOpen(g.grupo_key, gIdx);
                  return (
                    <details
                      key={g.grupo_key}
                      open={open}
                      onToggle={(e) => {
                        const isOpenNow = e.currentTarget.open;
                        setExpandedMap((prev) => {
                          if (prev[g.grupo_key] === isOpenNow) return prev;
                          return { ...prev, [g.grupo_key]: isOpenNow };
                        });
                      }}
                      className="border border-lider-border rounded-[2px] bg-lider-surface shadow-lider"
                    >
                      <summary className="px-4 sm:px-5 py-4 bg-lider-canvas/60 hover:bg-lider-canvas transition-colors select-none">
                        <div className="flex flex-1 flex-col sm:flex-row sm:items-center justify-between gap-2 min-w-0">
                          <div className="flex flex-wrap items-center gap-2 min-w-0">
                            <span className="font-display font-medium text-sm text-lider-ink">
                              {g.grupo_nome}
                            </span>
                            <span
                              className={[
                                "inline-flex items-center px-2 py-0.5 text-[11px] font-medium border rounded-[2px]",
                                g.origem_agrupamento === "codigo_perfil"
                                  ? "border-lider-wood/40 bg-lider-wood/10 text-lider-wood"
                                  : "border-lider-border bg-lider-surface text-lider-slate",
                              ].join(" ")}
                            >
                              {g.origem_agrupamento === "codigo_perfil"
                                ? "Cód. Perfil"
                                : "Modelo + Tipo"}
                            </span>
                            <span
                              className={[
                                "inline-flex items-center px-2 py-0.5 font-mono text-[11px] border rounded-[2px]",
                                g.perfil_simetrico
                                  ? "border-lider-wood/40 bg-lider-wood/10 text-lider-wood"
                                  : "border-lider-border bg-lider-surface text-lider-slate",
                              ].join(" ")}
                            >
                              {g.perfil_simetrico ? "Simétrico //" : "Assimétrico \\/"}
                            </span>
                            <span className="text-xs text-lider-muted truncate">
                              {(g.modelos || []).join(", ")}
                            </span>
                          </div>

                          <div className="flex flex-wrap items-center gap-2 text-xs tabular-nums shrink-0">
                            <span className="inline-flex items-center px-2 py-0.5 border border-lider-charcoal/25 bg-lider-charcoal text-white rounded-[2px]">
                              {g.qtd_barras} {g.qtd_barras === 1 ? "barra" : "barras"}{" "}
                              {barraMetrosLabel}m
                            </span>
                            <span className="inline-flex items-center px-2 py-0.5 border border-lider-wood/40 bg-lider-wood/5 text-lider-wood rounded-[2px]">
                              {fmtNum(g.aproveitamento_medio_pct)}% / barra
                            </span>
                            <span className="inline-flex items-center px-2 py-0.5 border border-lider-border bg-lider-surface text-lider-slate rounded-[2px]">
                              Perda: {fmtNum(g.total_perda_mm)} mm
                            </span>
                            {g.economia_chanfro_mm > 0 && (
                              <span className="inline-flex items-center px-2 py-0.5 border border-lider-wood/40 bg-lider-wood/10 text-lider-wood rounded-[2px]">
                                Econ. //: {fmtNum(g.economia_chanfro_mm)} mm
                              </span>
                            )}
                            <span className="inline-flex items-center px-2 py-0.5 border border-lider-terracotta/40 bg-lider-terracotta/5 text-lider-terracotta rounded-[2px]">
                              {g.ajustes_corte}{" "}
                              {g.ajustes_corte === 1 ? "ajuste" : "ajustes"} ·{" "}
                              {g.trocas_angulo || 0} âng.
                            </span>
                          </div>
                        </div>
                      </summary>

                      <div className="p-4 sm:p-6 space-y-4 border-t border-lider-border">
                        <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-lider-border">
                          <h4 className="font-display text-xs uppercase tracking-[0.08em] font-medium text-lider-ink">
                            {activeScenario === "material"
                              ? `Sequência Encadeada — Aproveitamento de Material (${g.qtd_barras} barras)`
                              : tempoDisplayMode === "roteiro"
                              ? `Roteiro de Execução por Medida — Maior → Menor (${g.roteiro_medidas?.length ?? 0} passos)`
                              : `Mapa Visual 1D — Corte em Lote FFD (${g.qtd_barras} barras)`}
                          </h4>
                          <span className="text-xs text-lider-slate tabular-nums">
                            {g.total_pecas_alocadas} peças · {fmtNum(g.total_metros_pecas)} m ·{" "}
                            {g.ajustes_corte} troca(s) de medida · {g.trocas_angulo || 0} troca(s) de ângulo
                          </span>
                        </div>

                        {activeScenario === "tempo_execucao" &&
                        tempoDisplayMode === "roteiro" ? (
                          <ExecutionRouteTable
                            steps={g.roteiro_medidas || []}
                            captionId={`${uid}-cap-rot-${gIdx}`}
                          />
                        ) : (
                          <div className="space-y-3">
                            {(g.barras || []).map((bar) => (
                              <BarCard
                                key={`${g.grupo_key}-${activeScenario}-bar-${bar.barra_numero}`}
                                bar={bar}
                                desponteMm={activeDesponteMm}
                                isMaterial={activeScenario === "material"}
                              />
                            ))}
                          </div>
                        )}
                      </div>
                    </details>
                  );
                })}
              </section>
            )
          ) : (
            /* Visão Consolidada */
            <section className="space-y-4" aria-labelledby={`${uid}-cons-title`}>
              <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-lider-border">
                <h4
                  id={`${uid}-cons-title`}
                  className="font-display text-xs uppercase tracking-[0.08em] font-medium text-lider-ink"
                >
                  {activeScenario === "material"
                    ? `Todas as Barras — Cenário Material (${activeView.filteredBarsFlat.length} barras)`
                    : tempoDisplayMode === "roteiro"
                    ? `Roteiro Consolidado por Medida — Maior → Menor (${activeView.filteredRoteiroFlat.length} passos)`
                    : `Todas as Barras — Cenário Tempo de Execução (${activeView.filteredBarsFlat.length} barras)`}
                </h4>
                <span className="text-xs text-lider-slate tabular-nums">
                  {activeMetrics.totalPecas} peças · {fmtNum(activeMetrics.totalMetrosPecas)} m ·{" "}
                  {activeMetrics.totalAjustes} ajuste(s) · {activeMetrics.totalTrocasAngulo} troca(s) de ângulo
                </span>
              </div>

              {activeScenario === "tempo_execucao" && tempoDisplayMode === "roteiro" ? (
                <ExecutionRouteTable
                  steps={activeView.filteredRoteiroFlat}
                  showGroupCol
                  captionId={`${uid}-cap-cons-rot`}
                />
              ) : !activeView.filteredBarsFlat.length ? (
                <div className="border border-lider-border rounded-[2px] bg-lider-surface px-4 py-10 text-center text-xs text-lider-muted">
                  Nenhuma barra corresponde aos filtros aplicados.
                </div>
              ) : (
                <div className="space-y-3">
                  {activeView.filteredBarsFlat.map((bar) => (
                    <BarCard
                      key={`flat-${activeScenario}-${bar.grupo_key}-${bar.barra_numero}`}
                      bar={bar}
                      desponteMm={activeDesponteMm}
                      showGroupBadge
                      isMaterial={activeScenario === "material"}
                    />
                  ))}
                </div>
              )}
            </section>
          )}
        </>
      )}
    </div>
  );
}
