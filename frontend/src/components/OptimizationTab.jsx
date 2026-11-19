import React, { useEffect, useId, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  ChevronDown,
  ChevronRight,
  Download,
  Layers,
  Loader2,
  Play,
  Scissors,
  Search,
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

function BarCard({
  bar,
  desponteMm = 0,
  showGroupBadge = false,
  badgePrefix = "#",
  badgeTone = "charcoal",
}) {
  const [showPieces, setShowPieces] = useState(false);
  const barLen = Number(bar.comprimento_barra_mm) || 6000;
  const pieces = bar.pecas || [];
  const despontePct = desponteMm > 0 ? Math.min(100, (desponteMm / barLen) * 100) : 0;
  const perdaPct = Math.max(0, ((Number(bar.perda_mm) || 0) / barLen) * 100);
  const kerfTotalPct = Math.max(
    0,
    (((Number(bar.perda_serra_desponte_mm) || 0) - desponteMm) / barLen) * 100
  );

  const badgeCls =
    badgeTone === "terracotta"
      ? "bg-lider-terracotta text-white"
      : "bg-lider-charcoal text-white";

  return (
    <div className="border border-lider-border rounded-[2px] bg-lider-surface p-4 space-y-3">
      {/* Cabeçalho da Barra */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-2.5">
        <div className="flex flex-wrap items-center gap-2 min-w-0">
          <span
            className={`inline-flex items-center px-2 py-0.5 font-mono text-xs font-medium rounded-[2px] ${badgeCls}`}
          >
            {badgePrefix}
            {showGroupBadge ? bar.barra_global_numero || bar.barra_numero : bar.barra_numero}
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
          <span className="font-mono text-xs sm:text-[13px] font-medium text-lider-ink">
            {bar.padrao_corte}
          </span>
          <span className="text-xs text-lider-muted">
            ({bar.qtd_pecas} {bar.qtd_pecas === 1 ? "peça" : "peças"})
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs tabular-nums shrink-0">
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

      {/* Diagrama 1D proporcional da barra */}
      <div
        className="w-full h-8 border border-lider-border rounded-[2px] bg-lider-canvas flex overflow-hidden select-none"
        role="img"
        aria-label={`Barra ${bar.barra_numero}: ${bar.padrao_corte}, perda ${fmtNum(
          bar.perda_mm
        )} mm (${fmtNum(bar.aproveitamento_pct)}% aproveitamento)`}
      >
        {despontePct > 0 && (
          <div
            style={{ width: `${despontePct}%` }}
            title={`Desponte: ${fmtNum(desponteMm)} mm`}
            className="h-full bg-lider-muted/40 border-r border-white/80 shrink-0"
          />
        )}
        {pieces.map((p, idx) => {
          const pct = ((Number(p.medida_corte_mm) || 0) / barLen) * 100;
          const bg = SEGMENT_COLORS[idx % SEGMENT_COLORS.length];
          return (
            <div
              key={`${p.op}-${p.codigo}-${idx}`}
              style={{ width: `${pct}%`, backgroundColor: bg }}
              title={`${fmtNum(p.medida_corte_mm)} mm · ${p.modelo} (${p.funcao_barra}) · OP ${p.op} · ${p.acabamento_perfil}`}
              className="h-full border-r border-white/85 flex items-center justify-center overflow-hidden px-1 text-[11px] font-mono text-white shrink-0"
            >
              {pct >= 5.5 && (
                <span className="truncate">{fmtNum(p.medida_corte_mm)}</span>
              )}
            </div>
          );
        })}
        {kerfTotalPct > 0.2 && (
          <div
            style={{ width: `${kerfTotalPct}%` }}
            title={`Serra (kerf): ${fmtNum(
              (Number(bar.perda_serra_desponte_mm) || 0) - desponteMm
            )} mm`}
            className="h-full bg-lider-muted/25 shrink-0"
          />
        )}
        {perdaPct > 0 && (
          <div
            style={{ width: `${perdaPct}%` }}
            title={`Sobra / Perda na barra: ${fmtNum(bar.perda_mm)} mm (${fmtNum(
              bar.perda_cm
            )} cm)`}
            className="h-full loss-hatch flex items-center justify-center overflow-hidden px-1 text-[10px] font-mono text-lider-terracotta flex-1 min-w-0"
          >
            {perdaPct >= 3.5 && (
              <span className="truncate">-{fmtNum(bar.perda_mm)}</span>
            )}
          </div>
        )}
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
          <span>{showPieces ? "Ocultar peças" : "Ver peças da barra"}</span>
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
              Peças alocadas na barra {bar.barra_numero}
            </caption>
            <thead>
              <tr>
                <th>OP</th>
                <th>Código</th>
                <th>Entrega</th>
                <th>Modelo</th>
                <th>Tipo</th>
                <th>Função</th>
                <th>Acabamento</th>
                <th className="num-header">Medida Corte (mm)</th>
              </tr>
            </thead>
            <tbody>
              {pieces.map((p, idx) => (
                <tr key={`${p.op}-${p.codigo}-${idx}`}>
                  <th scope="row" data-label="OP" className="font-mono text-xs">
                    {p.op}
                  </th>
                  <td data-label="Código">
                    <code className="font-mono text-xs">{p.codigo}</code>
                  </td>
                  <td data-label="Entrega" className="whitespace-nowrap">
                    {p.data_entrega || "-"}
                  </td>
                  <td data-label="Modelo">{p.modelo}</td>
                  <td data-label="Tipo">{p.tipo_perfil}</td>
                  <td data-label="Função">{p.funcao_barra}</td>
                  <td data-label="Acabamento" className="text-xs text-lider-slate">
                    {p.acabamento_perfil}
                  </td>
                  <td data-label="Medida Corte (mm)" className="num font-medium">
                    {fmtNum(p.medida_corte_mm)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function UnplacedTable({
  groupedRows = [],
  detailedRows = [],
  mode = "agrupado",
  onChangeMode,
  showGroupCol = false,
  hideModeToggle = false,
  captionId,
}) {
  const rows = mode === "agrupado" ? groupedRows : detailedRows;

  return (
    <div className="space-y-3">
      {!hideModeToggle && (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="inline-flex border border-lider-border rounded-[2px] bg-lider-canvas p-0.5">
            <button
              type="button"
              onClick={() => onChangeMode("agrupado")}
              className={[
                "px-2.5 py-1 text-xs rounded-[2px] transition-colors",
                mode === "agrupado"
                  ? "bg-lider-surface text-lider-ink font-medium shadow-sm"
                  : "text-lider-slate hover:text-lider-ink",
              ].join(" ")}
            >
              Agrupado por Medida
            </button>
            <button
              type="button"
              onClick={() => onChangeMode("detalhado")}
              className={[
                "px-2.5 py-1 text-xs rounded-[2px] transition-colors",
                mode === "detalhado"
                  ? "bg-lider-surface text-lider-ink font-medium shadow-sm"
                  : "text-lider-slate hover:text-lider-ink",
              ].join(" ")}
            >
              Detalhado por OP
            </button>
          </div>
          <span className="text-xs text-lider-muted">
            Ordenado estritamente do maior para o menor comprimento
          </span>
        </div>
      )}

      {!rows.length ? (
        <div className="border border-lider-border rounded-[2px] bg-lider-canvas/60 px-4 py-5 text-center text-xs text-lider-slate">
          Todas as peças deste filtro foram alocadas nas barras dentro da perda configurada.
        </div>
      ) : (
        <div
          tabIndex={0}
          role="region"
          aria-labelledby={captionId}
          className="table-wrapper stack-narrow"
        >
          <table className="lider-table">
            <caption id={captionId} className="visually-hidden">
              Peças não alocadas ordenadas do maior para o menor comprimento
            </caption>
            {mode === "agrupado" ? (
              <>
                <thead>
                  <tr>
                    <th className="num-header">Medida Corte (mm)</th>
                    {showGroupCol && <th>Grupo / Cód. Perfil</th>}
                    <th>Modelo</th>
                    <th>Tipo</th>
                    <th>Função da Barra</th>
                    <th>Acabamento</th>
                    <th>Corte</th>
                    <th className="num-header">Qtd</th>
                    <th className="num-header">Total (m)</th>
                    <th>Motivo</th>
                    <th>OPs</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, idx) => (
                    <tr
                      key={`${r.grupo_key}-${r.modelo}-${r.medida_corte_mm}-${r.funcao_barra}-${idx}`}
                    >
                      <th
                        scope="row"
                        data-label="Medida Corte (mm)"
                        className="font-mono font-medium text-lider-ink"
                      >
                        {fmtNum(r.medida_corte_mm)} mm
                      </th>
                      {showGroupCol && (
                        <td data-label="Grupo / Cód. Perfil">
                          <span
                            className={[
                              "inline-flex items-center px-2 py-0.5 text-[11px] font-medium border rounded-[2px]",
                              r.origem_agrupamento === "codigo_perfil"
                                ? "border-lider-wood/40 bg-lider-wood/5 text-lider-wood font-mono"
                                : "border-lider-border bg-lider-canvas text-lider-charcoal",
                            ].join(" ")}
                          >
                            {r.grupo_nome}
                          </span>
                        </td>
                      )}
                      <td data-label="Modelo">{r.modelo}</td>
                      <td data-label="Tipo">{r.tipo_perfil}</td>
                      <td data-label="Função da Barra">{r.funcao_barra}</td>
                      <td data-label="Acabamento" className="text-xs text-lider-slate">
                        {r.acabamento_perfil}
                      </td>
                      <td data-label="Corte">{r.tipo_corte}</td>
                      <td data-label="Qtd" className="num font-medium">
                        {r.qtd_pecas}
                      </td>
                      <td data-label="Total (m)" className="num">
                        {fmtNum(r.total_metros)}
                      </td>
                      <td data-label="Motivo" className="text-xs text-lider-terracotta">
                        {r.motivo}
                      </td>
                      <td data-label="OPs" className="font-mono text-xs text-lider-slate">
                        {r.ops}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </>
            ) : (
              <>
                <thead>
                  <tr>
                    <th className="num-header">Medida Corte (mm)</th>
                    {showGroupCol && <th>Grupo / Cód. Perfil</th>}
                    <th>OP</th>
                    <th>Código</th>
                    <th>Entrega</th>
                    <th>Modelo</th>
                    <th>Tipo</th>
                    <th>Função da Barra</th>
                    <th>Acabamento</th>
                    <th>Motivo</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, idx) => (
                    <tr
                      key={`${r.grupo_key}-${r.op}-${r.codigo}-${r.medida_corte_mm}-${idx}`}
                    >
                      <th
                        scope="row"
                        data-label="Medida Corte (mm)"
                        className="font-mono font-medium text-lider-ink"
                      >
                        {fmtNum(r.medida_corte_mm)} mm
                      </th>
                      {showGroupCol && (
                        <td data-label="Grupo / Cód. Perfil">
                          <span
                            className={[
                              "inline-flex items-center px-2 py-0.5 text-[11px] font-medium border rounded-[2px]",
                              r.origem_agrupamento === "codigo_perfil"
                                ? "border-lider-wood/40 bg-lider-wood/5 text-lider-wood font-mono"
                                : "border-lider-border bg-lider-canvas text-lider-charcoal",
                            ].join(" ")}
                          >
                            {r.grupo_nome}
                          </span>
                        </td>
                      )}
                      <td data-label="OP" className="font-mono text-xs">
                        {r.op}
                      </td>
                      <td data-label="Código">
                        <code className="font-mono text-xs">{r.codigo}</code>
                      </td>
                      <td data-label="Entrega" className="whitespace-nowrap">
                        {r.data_entrega || "-"}
                      </td>
                      <td data-label="Modelo">{r.modelo}</td>
                      <td data-label="Tipo">{r.tipo_perfil}</td>
                      <td data-label="Função da Barra">{r.funcao_barra}</td>
                      <td data-label="Acabamento" className="text-xs text-lider-slate">
                        {r.acabamento_perfil}
                      </td>
                      <td data-label="Motivo" className="text-xs text-lider-terracotta">
                        {r.motivo}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </>
            )}
          </table>
        </div>
      )}
    </div>
  );
}

function Group2Section({
  bars = [],
  groupedUnplaced = [],
  detailedUnplaced = [],
  stats,
  desponteMm = 0,
  activeBarraMm = 6000,
  showGroupCol = false,
  captionId,
  group2View = "barras",
  onChangeGroup2View,
}) {
  const barraMetrosLabel = fmtNum(activeBarraMm / 1000);
  return (
    <div className="space-y-3">
      {/* Faixa compacta de KPIs do Grupo 2 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 bg-lider-canvas/60 border border-lider-border rounded-[2px] p-3 text-xs tabular-nums">
        <div>
          <span className="block text-[11px] uppercase tracking-[0.06em] text-lider-muted">
            Barras {barraMetrosLabel}m (G2)
          </span>
          <strong className="font-display font-medium text-sm text-lider-ink">
            {stats.qtdBarras}
          </strong>
        </div>
        <div>
          <span className="block text-[11px] uppercase tracking-[0.06em] text-lider-muted">
            Aproveit. Médio / Barra
          </span>
          <strong className="font-display font-medium text-sm text-lider-wood">
            {fmtNum(stats.aproveitamentoPct)}%
          </strong>
        </div>
        <div>
          <span className="block text-[11px] uppercase tracking-[0.06em] text-lider-muted">
            Perda Total (G2)
          </span>
          <strong className="font-display font-medium text-sm text-lider-terracotta">
            {fmtNum(stats.perdaTotalMm)} mm ({fmtNum(stats.perdaTotalMetros)} m)
          </strong>
        </div>
        <div>
          <span className="block text-[11px] uppercase tracking-[0.06em] text-lider-muted">
            Perda Média / Barra
          </span>
          <strong className="font-display font-medium text-sm text-lider-ink">
            {fmtNum(stats.perdaMediaMm)} mm
          </strong>
        </div>
      </div>

      {stats.pecasInviaveis > 0 && (
        <div className="border border-lider-terracotta/40 bg-lider-terracotta/5 rounded-[2px] px-3 py-2 text-xs text-lider-terracotta">
          {stats.pecasInviaveis} peça(s) excedem a barra útil ({fmtNum(activeBarraMm - desponteMm)} mm) e constam apenas na listagem abaixo.
        </div>
      )}

      {/* Seletor de 3 modos para Grupo 2 */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="inline-flex flex-wrap border border-lider-border rounded-[2px] bg-lider-canvas p-0.5">
          <button
            type="button"
            onClick={() => onChangeGroup2View("barras")}
            className={[
              "px-2.5 py-1 text-xs rounded-[2px] transition-colors",
              group2View === "barras"
                ? "bg-lider-surface text-lider-ink font-medium shadow-sm"
                : "text-lider-slate hover:text-lider-ink",
            ].join(" ")}
          >
            Barras Otimizadas {barraMetrosLabel}m ({bars.length})
          </button>
          <button
            type="button"
            onClick={() => onChangeGroup2View("agrupado")}
            className={[
              "px-2.5 py-1 text-xs rounded-[2px] transition-colors",
              group2View === "agrupado"
                ? "bg-lider-surface text-lider-ink font-medium shadow-sm"
                : "text-lider-slate hover:text-lider-ink",
            ].join(" ")}
          >
            Peças Agrupadas (Maior → Menor)
          </button>
          <button
            type="button"
            onClick={() => onChangeGroup2View("detalhado")}
            className={[
              "px-2.5 py-1 text-xs rounded-[2px] transition-colors",
              group2View === "detalhado"
                ? "bg-lider-surface text-lider-ink font-medium shadow-sm"
                : "text-lider-slate hover:text-lider-ink",
            ].join(" ")}
          >
            Detalhado por OP (Maior → Menor)
          </button>
        </div>

        <span className="text-xs text-lider-muted">
          {group2View === "barras"
            ? "Otimizado no menor número possível de barras com aproveitamento da sobra"
            : "Ordenado estritamente do maior para o menor comprimento"}
        </span>
      </div>

      {group2View === "barras" ? (
        !bars.length ? (
          <div className="border border-lider-border rounded-[2px] bg-lider-canvas/60 px-4 py-5 text-center text-xs text-lider-slate">
            Nenhuma peça viável restante para otimizar neste filtro do Grupo 2.
          </div>
        ) : (
          <div className="space-y-3">
            {bars.map((bar, idx) => (
              <BarCard
                key={`${bar.grupo_key}-g2-${bar.barra_global_numero || bar.barra_numero}-${idx}`}
                bar={bar}
                desponteMm={desponteMm}
                showGroupBadge={showGroupCol}
                badgePrefix="G2 #"
                badgeTone="terracotta"
              />
            ))}
          </div>
        )
      ) : (
        <UnplacedTable
          groupedRows={groupedUnplaced}
          detailedRows={detailedUnplaced}
          mode={group2View}
          onChangeMode={onChangeGroup2View}
          showGroupCol={showGroupCol}
          hideModeToggle
          captionId={captionId}
        />
      )}
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
    perda_maxima_mm: 200,
    espessura_serra_mm: 0,
    desponte_mm: 0,
    separar_por_acabamento: false,
  };

  const [barraMm, setBarraMm] = useState(
    String(effectiveConfig.comprimento_barra_mm ?? 6000)
  );
  const [perdaCm, setPerdaCm] = useState(
    String(
      effectiveConfig.perda_maxima_mm !== undefined
        ? Number(effectiveConfig.perda_maxima_mm) / 10
        : 20
    )
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

  const [viewMode, setViewMode] = useState("grupos");
  const [group2View, setGroup2View] = useState("barras");
  const [grupoFilter, setGrupoFilter] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [expandedMap, setExpandedMap] = useState({});

  const uid = useId();
  const barraRef = useRef(null);
  const perdaRef = useRef(null);
  const serraRef = useRef(null);
  const desponteRef = useRef(null);

  useEffect(() => {
    const src = config || optimization?.config;
    if (!src) return;
    setBarraMm(String(src.comprimento_barra_mm ?? 6000));
    setPerdaCm(String(Number(src.perda_maxima_mm ?? 200) / 10));
    setSerraMm(String(src.espessura_serra_mm ?? 0));
    setDesponteMm(String(src.desponte_mm ?? 0));
    setSepararAcabamento(Boolean(src.separar_por_acabamento));
    setErrors({});
  }, [config, optimization?.config]);

  const validateFields = (
    bVal = barraMm,
    pVal = perdaCm,
    sVal = serraMm,
    dVal = desponteMm
  ) => {
    const nextErrors = {};
    const bNum = Number(bVal);
    const pNum = Number(pVal);
    const sNum = Number(sVal);
    const dNum = Number(dVal);

    if (!Number.isFinite(bNum) || bNum < 100) {
      nextErrors.barraMm = "Informe um comprimento >= 100 mm.";
    }
    if (!Number.isFinite(pNum) || pNum < 0) {
      nextErrors.perdaCm = "A perda máxima deve ser >= 0 cm.";
    }
    if (!Number.isFinite(sNum) || sNum < 0) {
      nextErrors.serraMm = "A espessura de serra deve ser >= 0 mm.";
    }
    if (!Number.isFinite(dNum) || dNum < 0 || (Number.isFinite(bNum) && dNum >= bNum)) {
      nextErrors.desponteMm = "Desponte deve ser >= 0 e menor que a barra.";
    }
    return { nextErrors, parsed: { bNum, pNum, sNum, dNum } };
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const { nextErrors, parsed } = validateFields();
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      if (nextErrors.barraMm) barraRef.current?.focus();
      else if (nextErrors.perdaCm) perdaRef.current?.focus();
      else if (nextErrors.serraMm) serraRef.current?.focus();
      else if (nextErrors.desponteMm) desponteRef.current?.focus();
      return;
    }

    onOptimize({
      comprimento_barra_mm: parsed.bNum,
      perda_maxima_mm: Math.round(parsed.pNum * 10 * 1000) / 1000,
      espessura_serra_mm: parsed.sNum,
      desponte_mm: parsed.dNum,
      separar_por_acabamento: separarAcabamento,
    });
  };

  const grupos = optimization?.grupos || [];
  const resumo = optimization?.resumo;
  const activeBarraMm = Number(optimization?.config?.comprimento_barra_mm ?? 6000);
  const activePerdaCm = Number(optimization?.config?.perda_maxima_cm ?? 20);
  const activeDesponteMm = Number(optimization?.config?.desponte_mm ?? 0);

  const grupoOptions = useMemo(
    () => grupos.map((g) => ({ key: g.grupo_key, label: g.grupo_nome })),
    [grupos]
  );

  const filteredGroups = useMemo(() => {
    const q = searchTerm.trim().toLowerCase();
    return grupos.filter((g) => {
      if (grupoFilter && g.grupo_key !== grupoFilter) return false;
      if (!q) return true;
      const hay = [
        g.grupo_nome,
        g.codigo_perfil,
        ...(g.modelos || []),
        ...(g.tipos_perfil || []),
        ...(g.acabamentos || []),
      ]
        .join(" ")
        .toLowerCase();
      if (hay.includes(q)) return true;
      return (g.barras_fechadas || []).some((b) =>
        (b.ops || "").toLowerCase().includes(q)
      ) || (g.nao_alocados || []).some((p) => (p.op || "").toLowerCase().includes(q));
    });
  }, [grupos, grupoFilter, searchTerm]);

  const filteredFlatBars = useMemo(() => {
    const src = optimization?.barras_otimizadas_flat || [];
    const q = searchTerm.trim().toLowerCase();
    return src.filter((b) => {
      if (grupoFilter && b.grupo_key !== grupoFilter) return false;
      if (!q) return true;
      return [b.grupo_nome, b.codigo_perfil, b.padrao_corte, b.ops]
        .join(" ")
        .toLowerCase()
        .includes(q);
    });
  }, [optimization?.barras_otimizadas_flat, grupoFilter, searchTerm]);

  const filteredFlatBarsG2 = useMemo(() => {
    const src = optimization?.barras_grupo2_flat || [];
    const q = searchTerm.trim().toLowerCase();
    return src.filter((b) => {
      if (grupoFilter && b.grupo_key !== grupoFilter) return false;
      if (!q) return true;
      return [b.grupo_nome, b.codigo_perfil, b.padrao_corte, b.ops]
        .join(" ")
        .toLowerCase()
        .includes(q);
    });
  }, [optimization?.barras_grupo2_flat, grupoFilter, searchTerm]);

  const filteredFlatUnplacedGrouped = useMemo(() => {
    const src = optimization?.nao_alocados_agrupados_flat || [];
    const q = searchTerm.trim().toLowerCase();
    return src.filter((r) => {
      if (grupoFilter && r.grupo_key !== grupoFilter) return false;
      if (!q) return true;
      return [
        r.grupo_nome,
        r.codigo_perfil,
        r.modelo,
        r.tipo_perfil,
        r.funcao_barra,
        r.acabamento_perfil,
        r.ops,
      ]
        .join(" ")
        .toLowerCase()
        .includes(q);
    });
  }, [optimization?.nao_alocados_agrupados_flat, grupoFilter, searchTerm]);

  const filteredFlatUnplacedDetailed = useMemo(() => {
    const src = optimization?.nao_alocados_flat || [];
    const q = searchTerm.trim().toLowerCase();
    return src.filter((r) => {
      if (grupoFilter && r.grupo_key !== grupoFilter) return false;
      if (!q) return true;
      return [
        r.grupo_nome,
        r.codigo_perfil,
        r.op,
        r.codigo,
        r.modelo,
        r.tipo_perfil,
        r.funcao_barra,
        r.acabamento_perfil,
      ]
        .join(" ")
        .toLowerCase()
        .includes(q);
    });
  }, [optimization?.nao_alocados_flat, grupoFilter, searchTerm]);

  // Por padrão expande o primeiro grupo (ou grupos filtrados únicos)
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

  const inputBaseCls =
    "w-full h-10 px-3 bg-lider-surface border rounded-[2px] font-mono text-sm text-lider-ink tabular-nums focus:outline-none transition-colors";

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Formulário de Parâmetros Configuráveis */}
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
              Agrupamento pelo Código do Perfil cadastrado em Regras e Descontos; quando vazio, agrupa por Modelo + Tipo (Puxador ou Lateral).
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

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4 items-start">
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

          {/* Perda Máxima (cm) */}
          <div className="space-y-1">
            <label
              htmlFor={`${uid}-perda`}
              className="block text-[11px] uppercase tracking-[0.06em] text-lider-slate"
            >
              Perda Máxima (cm)
            </label>
            <input
              ref={perdaRef}
              id={`${uid}-perda`}
              name="perda_maxima_cm"
              type="text"
              inputMode="decimal"
              value={perdaCm}
              onChange={(e) => {
                setPerdaCm(e.target.value);
                if (errors.perdaCm) {
                  setErrors((prev) => ({ ...prev, perdaCm: undefined }));
                }
              }}
              onBlur={() => {
                const { nextErrors } = validateFields();
                setErrors((prev) => ({ ...prev, perdaCm: nextErrors.perdaCm }));
              }}
              aria-invalid={errors.perdaCm ? "true" : undefined}
              aria-describedby={`${uid}-perda-help`}
              className={`${inputBaseCls} ${
                errors.perdaCm
                  ? "border-red-700 focus:border-red-700"
                  : "border-lider-border focus:border-lider-charcoal"
              }`}
            />
            <p
              id={`${uid}-perda-help`}
              className={`text-[11px] ${
                errors.perdaCm ? "text-red-700" : "text-lider-muted"
              }`}
            >
              {errors.perdaCm || `= ${fmtNum((Number(perdaCm) || 0) * 10)} mm`}
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

      {!hasData || !optimization ? (
        <div className="border border-lider-border rounded-[2px] bg-lider-surface px-6 py-14 text-center text-sm text-lider-muted">
          Nenhum dado carregado. Consulte o ERP ou carregue um arquivo HTML para otimizar as barras de 6 m.
        </div>
      ) : (
        <>
          {/* Faixa de KPIs da Otimização (6 cards) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-6 gap-4">
            <article className="bg-lider-surface border border-lider-border rounded-[2px] shadow-lider p-4 flex flex-col justify-between gap-2">
              <div className="flex items-center justify-between">
                <span className="font-display text-[11px] uppercase tracking-[0.08em] text-lider-muted font-medium">
                  Grupo 1 — Barras {fmtNum(activeBarraMm / 1000)}m
                </span>
                <Scissors className="w-4 h-4 text-lider-wood" strokeWidth={1.5} />
              </div>
              <div>
                <strong className="block font-display font-normal text-2xl text-lider-ink tabular-nums">
                  {resumo?.total_barras_6m ?? 0}
                </strong>
                <span className="block text-xs text-lider-slate mt-0.5 tabular-nums">
                  {resumo?.total_pecas_alocadas ?? 0} peças ·{" "}
                  {fmtNum(resumo?.total_metros_alocados ?? 0)} m
                </span>
              </div>
            </article>

            <article className="bg-lider-surface border border-lider-border rounded-[2px] shadow-lider p-4 flex flex-col justify-between gap-2">
              <div className="flex items-center justify-between">
                <span className="font-display text-[11px] uppercase tracking-[0.08em] text-lider-muted font-medium">
                  Grupo 1 — Aproveit. / Perda
                </span>
                <Layers className="w-4 h-4 text-lider-wood" strokeWidth={1.5} />
              </div>
              <div>
                <strong className="block font-display font-normal text-xl text-lider-ink tabular-nums">
                  {fmtNum(resumo?.aproveitamento_medio_pct ?? 0)}% / barra
                </strong>
                <span className="block text-xs text-lider-slate mt-0.5 tabular-nums">
                  Perda total: {fmtNum(resumo?.total_perda_mm ?? 0)} mm (
                  {fmtNum(resumo?.total_perda_metros ?? 0)} m)
                </span>
              </div>
            </article>

            <article className="bg-lider-surface border border-lider-border rounded-[2px] shadow-lider p-4 flex flex-col justify-between gap-2">
              <div className="flex items-center justify-between">
                <span className="font-display text-[11px] uppercase tracking-[0.08em] text-lider-muted font-medium">
                  Grupo 2 — Barras {fmtNum(activeBarraMm / 1000)}m (Otim.)
                </span>
                <Scissors className="w-4 h-4 text-lider-terracotta" strokeWidth={1.5} />
              </div>
              <div>
                <strong className="block font-display font-normal text-2xl text-lider-terracotta tabular-nums">
                  {resumo?.total_barras_grupo2 ?? 0}
                </strong>
                <span className="block text-xs text-lider-slate mt-0.5 tabular-nums">
                  {resumo?.total_pecas_alocadas_grupo2 ?? 0} peças ·{" "}
                  {fmtNum(resumo?.total_metros_alocados_grupo2 ?? 0)} m
                </span>
              </div>
            </article>

            <article className="bg-lider-surface border border-lider-border rounded-[2px] shadow-lider p-4 flex flex-col justify-between gap-2">
              <div className="flex items-center justify-between">
                <span className="font-display text-[11px] uppercase tracking-[0.08em] text-lider-muted font-medium">
                  Grupo 2 — Aproveit. / Perda
                </span>
                <AlertCircle className="w-4 h-4 text-lider-terracotta" strokeWidth={1.5} />
              </div>
              <div>
                <strong className="block font-display font-normal text-xl text-lider-ink tabular-nums">
                  {fmtNum(resumo?.aproveitamento_medio_grupo2_pct ?? 0)}% / barra
                </strong>
                <span className="block text-xs text-lider-slate mt-0.5 tabular-nums">
                  Perda total: {fmtNum(resumo?.total_perda_grupo2_mm ?? 0)} mm (
                  {fmtNum(resumo?.total_perda_grupo2_metros ?? 0)} m)
                </span>
              </div>
            </article>

            <article className="bg-lider-surface border border-lider-border rounded-[2px] shadow-lider p-4 flex flex-col justify-between gap-2">
              <div className="flex items-center justify-between">
                <span className="font-display text-[11px] uppercase tracking-[0.08em] text-lider-muted font-medium">
                  Geral — Total Barras {fmtNum(activeBarraMm / 1000)}m
                </span>
                <Layers className="w-4 h-4 text-lider-charcoal" strokeWidth={1.5} />
              </div>
              <div>
                <strong className="block font-display font-normal text-2xl text-lider-ink tabular-nums">
                  {resumo?.total_barras_geral ?? 0}
                </strong>
                <span className="block text-xs text-lider-slate mt-0.5 tabular-nums">
                  {resumo?.total_pecas_entrada ?? 0} peças ·{" "}
                  {resumo?.total_grupos ?? 0} grupo(s)
                </span>
              </div>
            </article>

            <article className="bg-lider-surface border border-lider-border rounded-[2px] shadow-lider p-4 flex flex-col justify-between gap-2">
              <div className="flex items-center justify-between">
                <span className="font-display text-[11px] uppercase tracking-[0.08em] text-lider-muted font-medium">
                  Geral — Aproveit. / Perda Total
                </span>
                <Layers className="w-4 h-4 text-lider-wood" strokeWidth={1.5} />
              </div>
              <div>
                <strong className="block font-display font-normal text-xl text-lider-wood tabular-nums">
                  {fmtNum(resumo?.aproveitamento_medio_geral_pct ?? 0)}% / barra
                </strong>
                <span className="block text-xs text-lider-slate mt-0.5 tabular-nums">
                  Perda total: {fmtNum(resumo?.total_perda_geral_mm ?? 0)} mm (
                  {fmtNum(resumo?.total_perda_geral_metros ?? 0)} m)
                </span>
              </div>
            </article>
          </div>

          {/* Barra de Filtros, Visão e Exportação CSV */}
          <search>
            <div className="flex flex-col xl:flex-row xl:items-end justify-between gap-4">
              <div className="flex flex-wrap items-end gap-3.5">
                <fieldset>
                  <legend className="text-[11px] uppercase tracking-[0.06em] text-lider-slate mb-1.5">
                    Modo de Exibição
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
                      Visão Consolidada (2 Grupos)
                    </label>
                  </div>
                </fieldset>

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
                    Buscar Código / OP / Modelo
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
                      placeholder="5307, RISK, OP..."
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
                          "csv-opt-barras",
                          "/api/export/csv",
                          { mode: "otimizacao_barras" },
                          "otimizacao_barras_6m.csv"
                        )
                      }
                      className="h-9 px-3 text-xs font-medium rounded-[2px] border border-lider-border hover:border-lider-charcoal bg-transparent hover:bg-lider-canvas text-lider-charcoal inline-flex items-center gap-1.5 transition-colors disabled:opacity-45"
                    >
                      <Download className="w-3.5 h-3.5" strokeWidth={1.5} />
                      <span>CSV Barras G1</span>
                    </button>
                    <button
                      type="button"
                      disabled={!hasData || Boolean(exportingKey)}
                      onClick={() =>
                        onExport(
                          "csv-opt-g2",
                          "/api/export/csv",
                          { mode: "otimizacao_grupo2" },
                          "otimizacao_grupo2_barras_6m.csv"
                        )
                      }
                      className="h-9 px-3 text-xs font-medium rounded-[2px] border border-lider-border hover:border-lider-charcoal bg-transparent hover:bg-lider-canvas text-lider-charcoal inline-flex items-center gap-1.5 transition-colors disabled:opacity-45"
                    >
                      <Download className="w-3.5 h-3.5" strokeWidth={1.5} />
                      <span>CSV Barras G2</span>
                    </button>
                    <button
                      type="button"
                      disabled={!hasData || Boolean(exportingKey)}
                      onClick={() =>
                        onExport(
                          "csv-opt-sobras",
                          "/api/export/csv",
                          { mode: "otimizacao_sobras" },
                          "otimizacao_nao_alocados.csv"
                        )
                      }
                      className="h-9 px-3 text-xs font-medium rounded-[2px] border border-lider-border hover:border-lider-charcoal bg-transparent hover:bg-lider-canvas text-lider-charcoal inline-flex items-center gap-1.5 transition-colors disabled:opacity-45"
                    >
                      <Download className="w-3.5 h-3.5" strokeWidth={1.5} />
                      <span>CSV Peças G2</span>
                    </button>
                  </>
                )}
              </div>
            </div>
          </search>

          {/* Conteúdo por Modo */}
          {viewMode === "grupos" ? (
            !filteredGroups.length ? (
              <div className="border border-lider-border rounded-[2px] bg-lider-surface px-6 py-12 text-center text-sm text-lider-muted">
                Nenhum grupo corresponde aos filtros aplicados.
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
                            <span className="text-xs text-lider-muted truncate">
                              {(g.modelos || []).join(", ")}
                            </span>
                          </div>

                          <div className="flex flex-wrap items-center gap-2 text-xs tabular-nums shrink-0">
                            <span className="inline-flex items-center px-2 py-0.5 border border-lider-charcoal/25 bg-lider-charcoal text-white rounded-[2px]">
                              G1: {g.qtd_barras_6m} {g.qtd_barras_6m === 1 ? "barra" : "barras"}
                            </span>
                            <span className="inline-flex items-center px-2 py-0.5 border border-lider-terracotta/40 bg-lider-terracotta/5 text-lider-terracotta rounded-[2px]">
                              G2: {g.qtd_barras_grupo2 ?? 0}{" "}
                              {(g.qtd_barras_grupo2 ?? 0) === 1 ? "barra" : "barras"} (
                              {g.total_pecas_nao_alocadas} pçs)
                            </span>
                            <span className="inline-flex items-center px-2 py-0.5 border border-lider-wood/40 bg-lider-wood/5 text-lider-wood rounded-[2px]">
                              {fmtNum(g.aproveitamento_medio_geral_pct ?? g.aproveitamento_medio_pct)}% / barra
                            </span>
                            <span className="inline-flex items-center px-2 py-0.5 border border-lider-border bg-lider-surface text-lider-slate rounded-[2px]">
                              Perda: {fmtNum(g.total_perda_geral_mm ?? g.total_perda_mm)} mm
                            </span>
                          </div>
                        </div>
                      </summary>

                      <div className="p-4 sm:p-6 space-y-6 border-t border-lider-border">
                        {/* Grupo 1: Barras de 6m fechadas */}
                        <div className="space-y-3">
                          <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-lider-border">
                            <h4 className="font-display text-xs uppercase tracking-[0.08em] font-medium text-lider-ink">
                              Grupo 1 — Organizados na Barra de {fmtNum(activeBarraMm / 1000)}m (Perda ≤ {fmtNum(activePerdaCm)} cm)
                            </h4>
                            <span className="text-xs text-lider-slate tabular-nums">
                              {g.qtd_barras_6m} barra(s) · {g.total_pecas_alocadas} peças ·{" "}
                              {fmtNum(g.aproveitamento_medio_pct)}% / barra · Perda:{" "}
                              {fmtNum(g.total_perda_mm)} mm
                            </span>
                          </div>

                          {!g.barras_fechadas?.length ? (
                            <div className="border border-lider-border rounded-[2px] bg-lider-canvas/60 px-4 py-5 text-center text-xs text-lider-slate">
                              Nenhuma combinação fechou barra dentro do limite de perda de{" "}
                              {fmtNum(activePerdaCm)} cm neste grupo.
                            </div>
                          ) : (
                            <div className="space-y-3">
                              {g.barras_fechadas.map((bar) => (
                                <BarCard
                                  key={`${g.grupo_key}-bar-${bar.barra_numero}`}
                                  bar={bar}
                                  desponteMm={activeDesponteMm}
                                />
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Grupo 2: Otimizado + Listagem (Maior -> Menor) */}
                        <div className="space-y-3">
                          <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-lider-border">
                            <h4 className="font-display text-xs uppercase tracking-[0.08em] font-medium text-lider-terracotta">
                              Grupo 2 — Restantes (Otimizado em Barras {fmtNum(activeBarraMm / 1000)}m e Lista Maior → Menor)
                            </h4>
                            <span className="text-xs text-lider-slate tabular-nums">
                              {g.qtd_barras_grupo2 ?? 0} barra(s) ·{" "}
                              {g.total_pecas_nao_alocadas} peça(s) ·{" "}
                              {fmtNum(g.total_metros_nao_alocados)} m
                            </span>
                          </div>

                          <Group2Section
                            bars={g.barras_grupo2 || []}
                            groupedUnplaced={g.nao_alocados_agrupados || []}
                            detailedUnplaced={g.nao_alocados || []}
                            stats={{
                              qtdBarras: g.qtd_barras_grupo2 ?? 0,
                              aproveitamentoPct: g.aproveitamento_medio_grupo2_pct ?? 0,
                              perdaTotalMm: g.total_perda_grupo2_mm ?? 0,
                              perdaTotalMetros: g.total_perda_grupo2_metros ?? 0,
                              perdaMediaMm: g.perda_media_barra_grupo2_mm ?? 0,
                              pecasInviaveis: g.total_pecas_inviaveis ?? 0,
                            }}
                            desponteMm={activeDesponteMm}
                            activeBarraMm={activeBarraMm}
                            captionId={`${uid}-cap-fora-${gIdx}`}
                            group2View={group2View}
                            onChangeGroup2View={setGroup2View}
                          />
                        </div>
                      </div>
                    </details>
                  );
                })}
              </section>
            )
          ) : (
            /* Visão Consolidada (2 Grupos) */
            <div className="space-y-8">
              <section className="space-y-3" aria-labelledby={`${uid}-cons-g1`}>
                <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-lider-border">
                  <h4
                    id={`${uid}-cons-g1`}
                    className="font-display text-xs uppercase tracking-[0.08em] font-medium text-lider-ink"
                  >
                    Grupo 1 — Todas as Barras de {fmtNum(activeBarraMm / 1000)}m (Perda ≤{" "}
                    {fmtNum(activePerdaCm)} cm)
                  </h4>
                  <span className="text-xs text-lider-slate tabular-nums">
                    {filteredFlatBars.length} barra(s) exibida(s)
                  </span>
                </div>

                {!filteredFlatBars.length ? (
                  <div className="border border-lider-border rounded-[2px] bg-lider-surface px-4 py-8 text-center text-xs text-lider-muted">
                    Nenhuma barra de {fmtNum(activeBarraMm / 1000)}m fechada para os filtros aplicados.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {filteredFlatBars.map((bar) => (
                      <BarCard
                        key={`flat-bar-${bar.barra_global_numero}`}
                        bar={bar}
                        desponteMm={activeDesponteMm}
                        showGroupBadge
                      />
                    ))}
                  </div>
                )}
              </section>

              <section className="space-y-3" aria-labelledby={`${uid}-cons-g2`}>
                <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-lider-border">
                  <h4
                    id={`${uid}-cons-g2`}
                    className="font-display text-xs uppercase tracking-[0.08em] font-medium text-lider-terracotta"
                  >
                    Grupo 2 — Barras Otimizadas e Peças Não Alocadas (Maior → Menor)
                  </h4>
                  <span className="text-xs text-lider-slate tabular-nums">
                    {filteredFlatBarsG2.length} barra(s) ·{" "}
                    {filteredFlatUnplacedDetailed.length} peça(s) exibida(s)
                  </span>
                </div>

                <Group2Section
                  bars={filteredFlatBarsG2}
                  groupedUnplaced={filteredFlatUnplacedGrouped}
                  detailedUnplaced={filteredFlatUnplacedDetailed}
                  stats={(() => {
                    const qtdBarras = filteredFlatBarsG2.length;
                    const somaMm = filteredFlatBarsG2.reduce(
                      (acc, b) => acc + (Number(b.soma_pecas_mm) || 0),
                      0
                    );
                    const perdaTotalMm = filteredFlatBarsG2.reduce(
                      (acc, b) => acc + (Number(b.perda_mm) || 0),
                      0
                    );
                    const pecasInviaveis = filteredFlatUnplacedDetailed.filter((p) =>
                      String(p.motivo || "").includes("Maior que a barra")
                    ).length;
                    return {
                      qtdBarras,
                      aproveitamentoPct:
                        qtdBarras > 0 && activeBarraMm > 0
                          ? (somaMm / (qtdBarras * activeBarraMm)) * 100
                          : 0,
                      perdaTotalMm,
                      perdaTotalMetros: perdaTotalMm / 1000,
                      perdaMediaMm: qtdBarras > 0 ? perdaTotalMm / qtdBarras : 0,
                      pecasInviaveis,
                    };
                  })()}
                  desponteMm={activeDesponteMm}
                  activeBarraMm={activeBarraMm}
                  showGroupCol
                  captionId={`${uid}-cap-cons-fora`}
                  group2View={group2View}
                  onChangeGroup2View={setGroup2View}
                />
              </section>
            </div>
          )}
        </>
      )}
    </div>
  );
}
