import React, { useMemo, useState } from "react";
import { Search, X } from "lucide-react";
import { fmtNum } from "../utils/formatters";

export default function GlassCutTab({
  groupedGlasses = [],
  detailedGlasses = [],
  items = [],
}) {
  const [viewMode, setViewMode] = useState("agrupado");
  const [modeloFilter, setModeloFilter] = useState("");
  const [searchTerm, setSearchTerm] = useState("");

  const modelos = useMemo(
    () => Array.from(new Set(items.map((i) => i.modelo).filter(Boolean))).sort(),
    [items]
  );

  const rows = useMemo(() => {
    const source = viewMode === "agrupado" ? groupedGlasses : detailedGlasses;
    const q = searchTerm.trim().toLowerCase();
    return source.filter((r) => {
      if (modeloFilter && r.modelo !== modeloFilter) return false;
      if (q) {
        const hay = [r.op, r.codigo, r.modelo, r.acabamento_placa, r.ops]
          .join(" ")
          .toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [viewMode, groupedGlasses, detailedGlasses, modeloFilter, searchTerm]);

  const totals = useMemo(() => {
    const totalPecas = rows.reduce((acc, r) => acc + (Number(r.qtd_pecas) || 0), 0);
    const totalArea = rows.reduce((acc, r) => acc + (Number(r.area_m2) || 0), 0);
    return { totalPecas, totalArea };
  }, [rows]);

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
                htmlFor="vidro-agrupado"
                className={[
                  "px-3 py-1.5 text-xs rounded-[2px] cursor-pointer transition-colors select-none",
                  viewMode === "agrupado"
                    ? "bg-lider-surface text-lider-ink font-medium shadow-sm"
                    : "text-lider-slate hover:text-lider-ink",
                ].join(" ")}
              >
                <input
                  type="radio"
                  id="vidro-agrupado"
                  name="vidro_view"
                  value="agrupado"
                  checked={viewMode === "agrupado"}
                  onChange={() => setViewMode("agrupado")}
                  className="sr-only"
                />
                Lista Agrupada por Medida
              </label>
              <label
                htmlFor="vidro-detalhado"
                className={[
                  "px-3 py-1.5 text-xs rounded-[2px] cursor-pointer transition-colors select-none",
                  viewMode === "detalhado"
                    ? "bg-lider-surface text-lider-ink font-medium shadow-sm"
                    : "text-lider-slate hover:text-lider-ink",
                ].join(" ")}
              >
                <input
                  type="radio"
                  id="vidro-detalhado"
                  name="vidro_view"
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
              htmlFor="f-vidro-modelo"
              className="block text-[11px] uppercase tracking-[0.06em] text-lider-slate mb-1.5"
            >
              Filtrar Modelo
            </label>
            <select
              id="f-vidro-modelo"
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
              htmlFor="f-vidro-busca"
              className="block text-[11px] uppercase tracking-[0.06em] text-lider-slate mb-1.5"
            >
              Buscar Placa / Vidro
            </label>
            <div className="relative">
              <Search
                className="w-3.5 h-3.5 text-lider-muted absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
                strokeWidth={1.5}
              />
              <input
                type="search"
                id="f-vidro-busca"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Espelho, incolor, OP..."
                className="w-full h-10 pl-9 pr-8 bg-lider-surface border border-lider-border rounded-[2px] text-sm text-lider-ink placeholder:text-lider-muted/70 focus:border-lider-charcoal focus:outline-none transition-colors"
              />
              {searchTerm && (
                <button
                  type="button"
                  onClick={() => setSearchTerm("")}
                  aria-label="Limpar busca de vidros"
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
              {totals.totalPecas}
            </strong>{" "}
            peças
          </span>
          <span>
            <strong className="font-medium text-lider-wood tabular-nums">
              {fmtNum(totals.totalArea)} m²
            </strong>{" "}
            área total
          </span>
        </div>
      </div>

      {/* Tabela */}
      {!rows.length ? (
        <div className="border border-lider-border rounded-[2px] bg-lider-surface px-6 py-14 text-center text-sm text-lider-muted">
          {(viewMode === "agrupado" ? groupedGlasses : detailedGlasses).length
            ? "Nenhum vidro corresponde aos filtros aplicados."
            : "Nenhum plano de corte de vidros calculado."}
        </div>
      ) : (
        <div
          tabIndex={0}
          role="region"
          aria-labelledby="caption-vidros"
          className="table-wrapper stack-narrow"
        >
          <table className="lider-table">
            <caption id="caption-vidros" className="visually-hidden">
              Lista de corte de vidros e placas por modelo
            </caption>
            {viewMode === "agrupado" ? (
              <>
                <thead>
                  <tr>
                    <th>Modelo</th>
                    <th>Acabamento / Placa</th>
                    <th className="num-header">Qtd Peças</th>
                    <th className="num-header">Largura Corte (mm)</th>
                    <th className="num-header">Altura Corte (mm)</th>
                    <th>Regra Largura</th>
                    <th>Regra Altura</th>
                    <th className="num-header">Área (m²)</th>
                    <th>OPs</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, idx) => (
                    <tr
                      key={`${r.modelo}-${r.acabamento_placa}-${r.largura_corte_mm}-${r.altura_corte_mm}-${idx}`}
                    >
                      <th scope="row" data-label="Modelo">
                        <span className="inline-flex items-center px-2 py-0.5 text-[11px] font-medium border border-lider-border bg-lider-canvas text-lider-charcoal rounded-[2px]">
                          {r.modelo}
                        </span>
                      </th>
                      <td data-label="Acabamento / Placa">{r.acabamento_placa}</td>
                      <td data-label="Qtd Peças" className="num font-medium">
                        {r.qtd_pecas}
                      </td>
                      <td data-label="Largura Corte (mm)" className="num font-medium">
                        {fmtNum(r.largura_corte_mm)}
                      </td>
                      <td data-label="Altura Corte (mm)" className="num font-medium">
                        {fmtNum(r.altura_corte_mm)}
                      </td>
                      <td data-label="Regra Largura" className="text-xs text-lider-slate">
                        {r.regra_largura}
                      </td>
                      <td data-label="Regra Altura" className="text-xs text-lider-slate">
                        {r.regra_altura}
                      </td>
                      <td data-label="Área (m²)" className="num">
                        {fmtNum(r.area_m2)}
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
                    <th>Acabamento / Placa</th>
                    <th>Posição Puxador</th>
                    <th className="num-header">Qtd</th>
                    <th className="num-header">Larg. Nom.</th>
                    <th className="num-header">Desc. L</th>
                    <th className="num-header">Larg. Corte (mm)</th>
                    <th className="num-header">Alt. Nom.</th>
                    <th className="num-header">Desc. A</th>
                    <th className="num-header">Alt. Corte (mm)</th>
                    <th className="num-header">Área (m²)</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, idx) => (
                    <tr key={`${r.op}-${r.codigo}-${idx}`}>
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
                      <td data-label="Acabamento / Placa">{r.acabamento_placa}</td>
                      <td data-label="Posição Puxador" className="text-xs">
                        {r.posicao_puxador}
                      </td>
                      <td data-label="Qtd" className="num font-medium">
                        {r.qtd_pecas}
                      </td>
                      <td data-label="Larg. Nom." className="num">
                        {fmtNum(r.largura_nominal_mm)}
                      </td>
                      <td data-label="Desc. L" className="num text-lider-wood">
                        {fmtNum(r.desconto_largura_mm)}
                      </td>
                      <td data-label="Larg. Corte (mm)" className="num font-medium">
                        {fmtNum(r.largura_corte_mm)}
                      </td>
                      <td data-label="Alt. Nom." className="num">
                        {fmtNum(r.altura_nominal_mm)}
                      </td>
                      <td data-label="Desc. A" className="num text-lider-wood">
                        {fmtNum(r.desconto_altura_mm)}
                      </td>
                      <td data-label="Alt. Corte (mm)" className="num font-medium">
                        {fmtNum(r.altura_corte_mm)}
                      </td>
                      <td data-label="Área (m²)" className="num">
                        {fmtNum(r.area_m2)}
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
