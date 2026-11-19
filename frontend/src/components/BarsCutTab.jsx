import React, { useMemo, useState } from "react";
import { Search, X } from "lucide-react";
import { fmtNum } from "../utils/formatters";

export default function BarsCutTab({ groupedBars = [], detailedBars = [], items = [] }) {
  const [viewMode, setViewMode] = useState("agrupado");
  const [modeloFilter, setModeloFilter] = useState("");
  const [searchTerm, setSearchTerm] = useState("");

  const modelos = useMemo(
    () => Array.from(new Set(items.map((i) => i.modelo).filter(Boolean))).sort(),
    [items]
  );

  const rows = useMemo(() => {
    const source = viewMode === "agrupado" ? groupedBars : detailedBars;
    const q = searchTerm.trim().toLowerCase();
    return source.filter((r) => {
      if (modeloFilter && r.modelo !== modeloFilter) return false;
      if (q) {
        const hay = [
          r.op,
          r.codigo,
          r.modelo,
          r.acabamento_perfil,
          r.funcao_barra,
          r.ops,
        ]
          .join(" ")
          .toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [viewMode, groupedBars, detailedBars, modeloFilter, searchTerm]);

  const totals = useMemo(() => {
    const totalBars = rows.reduce((acc, r) => acc + (Number(r.qtd_barras) || 0), 0);
    const totalMeters =
      viewMode === "agrupado"
        ? rows.reduce((acc, r) => acc + (Number(r.total_metros) || 0), 0)
        : rows.reduce(
            (acc, r) =>
              acc +
              ((Number(r.qtd_barras) || 0) * (Number(r.medida_corte_mm) || 0)) / 1000,
            0
          );
    return { totalBars, totalMeters };
  }, [rows, viewMode]);

  return (
    <div className="p-6 lg:p-8 space-y-5">
      {/* Toolbar */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
        <div className="flex flex-wrap items-end gap-3.5">
          <fieldset>
            <legend className="text-[11px] uppercase tracking-[0.06em] text-lider-slate mb-1.5">
              Modo de Visualização
            </legend>
            <div className="inline-flex border border-lider-border rounded-[2px] bg-lider-canvas p-0.5">
              <label
                htmlFor="corte-agrupado"
                className={[
                  "px-3 py-1.5 text-xs rounded-[2px] cursor-pointer transition-colors select-none",
                  viewMode === "agrupado"
                    ? "bg-lider-surface text-lider-ink font-medium shadow-sm"
                    : "text-lider-slate hover:text-lider-ink",
                ].join(" ")}
              >
                <input
                  type="radio"
                  id="corte-agrupado"
                  name="corte_view"
                  value="agrupado"
                  checked={viewMode === "agrupado"}
                  onChange={() => setViewMode("agrupado")}
                  className="sr-only"
                />
                Lista Agrupada para Serra
              </label>
              <label
                htmlFor="corte-detalhado"
                className={[
                  "px-3 py-1.5 text-xs rounded-[2px] cursor-pointer transition-colors select-none",
                  viewMode === "detalhado"
                    ? "bg-lider-surface text-lider-ink font-medium shadow-sm"
                    : "text-lider-slate hover:text-lider-ink",
                ].join(" ")}
              >
                <input
                  type="radio"
                  id="corte-detalhado"
                  name="corte_view"
                  value="detalhado"
                  checked={viewMode === "detalhado"}
                  onChange={() => setViewMode("detalhado")}
                  className="sr-only"
                />
                Lista Detalhada por OP
              </label>
            </div>
          </fieldset>

          <div className="min-w-[160px]">
            <label
              htmlFor="f-corte-modelo"
              className="block text-[11px] uppercase tracking-[0.06em] text-lider-slate mb-1.5"
            >
              Filtrar Modelo
            </label>
            <select
              id="f-corte-modelo"
              value={modeloFilter}
              onChange={(e) => setModeloFilter(e.target.value)}
              className="w-full h-10 px-3 bg-lider-surface border border-lider-border rounded-[2px] text-sm text-lider-ink focus:border-lider-charcoal focus:outline-none transition-colors"
            >
              <option value="">Todos</option>
              {modelos.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>

          <div className="min-w-[210px]">
            <label
              htmlFor="f-corte-busca"
              className="block text-[11px] uppercase tracking-[0.06em] text-lider-slate mb-1.5"
            >
              Buscar Barra / Perfil
            </label>
            <div className="relative">
              <Search
                className="w-3.5 h-3.5 text-lider-muted absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
                strokeWidth={1.5}
              />
              <input
                type="search"
                id="f-corte-busca"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Acabamento, OP, função..."
                className="w-full h-10 pl-9 pr-8 bg-lider-surface border border-lider-border rounded-[2px] text-sm text-lider-ink placeholder:text-lider-muted/70 focus:border-lider-charcoal focus:outline-none transition-colors"
              />
              {searchTerm && (
                <button
                  type="button"
                  onClick={() => setSearchTerm("")}
                  aria-label="Limpar busca de barras"
                  className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1 text-lider-muted hover:text-lider-ink"
                >
                  <X className="w-3.5 h-3.5" strokeWidth={1.5} />
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-4 text-xs text-lider-slate">
          <span>
            <strong className="font-medium text-lider-ink">{rows.length}</strong> linha(s)
          </span>
          <span>
            <strong className="font-medium text-lider-ink tabular-nums">
              {totals.totalBars}
            </strong>{" "}
            barras
          </span>
          <span>
            <strong className="font-medium text-lider-wood tabular-nums">
              {fmtNum(totals.totalMeters)} m
            </strong>{" "}
            lineares
          </span>
        </div>
      </div>

      {/* Tabela */}
      {!rows.length ? (
        <div className="border border-lider-border rounded-[2px] bg-lider-surface px-6 py-14 text-center text-sm text-lider-muted">
          {(viewMode === "agrupado" ? groupedBars : detailedBars).length
            ? "Nenhuma barra corresponde aos filtros aplicados."
            : "Nenhum plano de corte calculado."}
        </div>
      ) : (
        <div
          tabIndex={0}
          role="region"
          aria-labelledby="caption-corte"
          className="table-wrapper stack-narrow"
        >
          <table className="lider-table">
            <caption id="caption-corte" className="visually-hidden">
              Lista de corte de barras por modelo e medida
            </caption>
            {viewMode === "agrupado" ? (
              <>
                <thead>
                  <tr>
                    <th>Modelo</th>
                    <th>Acabamento Perfil</th>
                    <th>Função da Barra</th>
                    <th>Orientação</th>
                    <th>Puxador?</th>
                    <th>Tipo Corte</th>
                    <th className="num-header">Qtd Barras</th>
                    <th className="num-header">Medida Corte (mm)</th>
                    <th className="num-header">Total (m)</th>
                    <th>OPs</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, idx) => (
                    <tr key={`${r.modelo}-${r.funcao_barra}-${r.medida_corte_mm}-${idx}`}>
                      <th scope="row" data-label="Modelo">
                        <span className="inline-flex items-center px-2 py-0.5 text-[11px] font-medium border border-lider-border bg-lider-canvas text-lider-charcoal rounded-[2px]">
                          {r.modelo}
                        </span>
                      </th>
                      <td data-label="Acabamento Perfil">{r.acabamento_perfil}</td>
                      <td data-label="Função da Barra">{r.funcao_barra}</td>
                      <td data-label="Orientação">{r.orientacao}</td>
                      <td data-label="Puxador?">
                        {r.eh_perfil_puxador ? (
                          <span className="inline-flex items-center px-1.5 py-0.5 text-[11px] font-medium border border-lider-wood/40 bg-lider-wood/5 text-lider-wood rounded-[2px]">
                            Sim
                          </span>
                        ) : (
                          <span className="text-lider-muted">Não</span>
                        )}
                      </td>
                      <td data-label="Tipo Corte">{r.tipo_corte}</td>
                      <td data-label="Qtd Barras" className="num font-medium">
                        {r.qtd_barras}
                      </td>
                      <td data-label="Medida Corte (mm)" className="num font-medium text-lider-ink">
                        {fmtNum(r.medida_corte_mm)}
                      </td>
                      <td data-label="Total (m)" className="num">
                        {fmtNum(r.total_metros)}
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
                    <th>OP</th>
                    <th>Código</th>
                    <th>Entrega</th>
                    <th>Modelo</th>
                    <th>Acabamento</th>
                    <th>Função da Barra</th>
                    <th className="num-header">Qtd</th>
                    <th className="num-header">Nominal (mm)</th>
                    <th className="num-header">Desc. (mm)</th>
                    <th className="num-header">Corte (mm)</th>
                    <th>Obs.</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, idx) => (
                    <tr key={`${r.op}-${r.codigo}-${r.funcao_barra}-${idx}`}>
                      <th scope="row" data-label="OP" className="font-mono text-xs">
                        {r.op}
                      </th>
                      <td data-label="Código">
                        <code className="font-mono text-xs">{r.codigo}</code>
                      </td>
                      <td data-label="Entrega" className="whitespace-nowrap">
                        {r.data_entrega}
                      </td>
                      <td data-label="Modelo">
                        <span className="inline-flex items-center px-2 py-0.5 text-[11px] font-medium border border-lider-border bg-lider-canvas text-lider-charcoal rounded-[2px]">
                          {r.modelo}
                        </span>
                      </td>
                      <td data-label="Acabamento">{r.acabamento_perfil}</td>
                      <td data-label="Função da Barra">{r.funcao_barra}</td>
                      <td data-label="Qtd" className="num font-medium">
                        {r.qtd_barras}
                      </td>
                      <td data-label="Nominal (mm)" className="num">
                        {fmtNum(r.medida_nominal_mm)}
                      </td>
                      <td data-label="Desc. (mm)" className="num text-lider-wood">
                        {fmtNum(r.desconto_mm)}
                      </td>
                      <td data-label="Corte (mm)" className="num font-medium">
                        {fmtNum(r.medida_corte_mm)}
                      </td>
                      <td data-label="Obs." className="text-xs text-lider-slate">
                        {r.observacao_corte || "-"}
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
