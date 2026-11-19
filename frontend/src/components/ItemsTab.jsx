import React, { useMemo, useState } from "react";
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  RotateCcw,
  Search,
  X,
} from "lucide-react";
import { fmtNum } from "../utils/formatters";

export default function ItemsTab({ items, onSelectItem }) {
  const [searchTerm, setSearchTerm] = useState("");
  const [modeloFilter, setModeloFilter] = useState("");
  const [puxadorFilter, setPuxadorFilter] = useState("");
  const [divisoriaFilter, setDivisoriaFilter] = useState("");
  const [entregaFilter, setEntregaFilter] = useState("");
  const [sortConfig, setSortConfig] = useState({ key: null, direction: "asc" });

  const filterOptions = useMemo(() => {
    const modelos = Array.from(new Set(items.map((i) => i.modelo).filter(Boolean))).sort();
    const puxadores = Array.from(
      new Set(items.map((i) => i.posicao_puxador).filter(Boolean))
    ).sort();
    const entregas = Array.from(
      new Set(items.map((i) => i.data_entrega).filter(Boolean))
    ).sort();
    return { modelos, puxadores, entregas };
  }, [items]);

  const hasActiveFilters = Boolean(
    searchTerm || modeloFilter || puxadorFilter || divisoriaFilter || entregaFilter
  );

  const filteredAndSorted = useMemo(() => {
    const q = searchTerm.trim().toLowerCase();
    const filtered = items.filter((it) => {
      if (modeloFilter && it.modelo !== modeloFilter) return false;
      if (puxadorFilter && it.posicao_puxador !== puxadorFilter) return false;
      if (divisoriaFilter === "sim" && !it.tem_divisorias) return false;
      if (divisoriaFilter === "nao" && it.tem_divisorias) return false;
      if (entregaFilter && it.data_entrega !== entregaFilter) return false;
      if (q) {
        const hay = [
          it.op,
          it.codigo,
          it.pedido,
          it.modelo,
          it.categoria,
          it.subcategoria,
          it.acabamento_perfil,
          it.acabamento_placa,
          it.descricao,
        ]
          .join(" ")
          .toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    if (!sortConfig.key) return filtered;

    const dir = sortConfig.direction === "asc" ? 1 : -1;
    const numericFields = new Set([
      "quantidade",
      "qtd_estruturas",
      "largura_mm",
      "altura_mm",
    ]);

    return [...filtered].sort((a, b) => {
      const va = a[sortConfig.key];
      const vb = b[sortConfig.key];
      if (numericFields.has(sortConfig.key)) {
        return ((Number(va) || 0) - (Number(vb) || 0)) * dir;
      }
      return String(va ?? "").localeCompare(String(vb ?? ""), "pt-BR", {
        numeric: true,
      }) * dir;
    });
  }, [
    items,
    searchTerm,
    modeloFilter,
    puxadorFilter,
    divisoriaFilter,
    entregaFilter,
    sortConfig,
  ]);

  const handleSort = (key) => {
    setSortConfig((prev) => {
      if (prev.key !== key) return { key, direction: "asc" };
      if (prev.direction === "asc") return { key, direction: "desc" };
      return { key: null, direction: "asc" };
    });
  };

  const resetFilters = () => {
    setSearchTerm("");
    setModeloFilter("");
    setPuxadorFilter("");
    setDivisoriaFilter("");
    setEntregaFilter("");
  };

  const renderSortIcon = (key) => {
    if (sortConfig.key !== key) {
      return <ArrowUpDown className="w-3 h-3 opacity-40" strokeWidth={1.5} />;
    }
    return sortConfig.direction === "asc" ? (
      <ArrowUp className="w-3 h-3 text-lider-wood" strokeWidth={1.75} />
    ) : (
      <ArrowDown className="w-3 h-3 text-lider-wood" strokeWidth={1.75} />
    );
  };

  return (
    <div className="p-6 lg:p-8 space-y-5">
      {/* Barra de Busca e Filtros */}
      <search>
        <form
          onSubmit={(e) => e.preventDefault()}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5 items-end"
        >
          <div className="sm:col-span-2 lg:col-span-1">
            <label
              htmlFor="f-busca"
              className="block text-[11px] uppercase tracking-[0.06em] text-lider-slate mb-1.5"
            >
              Buscar (OP, código, pedido)
            </label>
            <div className="relative">
              <Search
                className="w-3.5 h-3.5 text-lider-muted absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
                strokeWidth={1.5}
              />
              <input
                type="search"
                id="f-busca"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Ex: 1943702, CATCH..."
                className="w-full h-10 pl-9 pr-8 bg-lider-surface border border-lider-border rounded-[2px] text-sm text-lider-ink placeholder:text-lider-muted/70 focus:border-lider-charcoal focus:outline-none transition-colors"
              />
              {searchTerm && (
                <button
                  type="button"
                  onClick={() => setSearchTerm("")}
                  aria-label="Limpar busca"
                  className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1 text-lider-muted hover:text-lider-ink"
                >
                  <X className="w-3.5 h-3.5" strokeWidth={1.5} />
                </button>
              )}
            </div>
          </div>

          <div>
            <label
              htmlFor="f-modelo"
              className="block text-[11px] uppercase tracking-[0.06em] text-lider-slate mb-1.5"
            >
              Modelo
            </label>
            <select
              id="f-modelo"
              value={modeloFilter}
              onChange={(e) => setModeloFilter(e.target.value)}
              className="w-full h-10 px-3 bg-lider-surface border border-lider-border rounded-[2px] text-sm text-lider-ink focus:border-lider-charcoal focus:outline-none transition-colors"
            >
              <option value="">Todos</option>
              {filterOptions.modelos.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="f-puxador"
              className="block text-[11px] uppercase tracking-[0.06em] text-lider-slate mb-1.5"
            >
              Posição Puxador
            </label>
            <select
              id="f-puxador"
              value={puxadorFilter}
              onChange={(e) => setPuxadorFilter(e.target.value)}
              className="w-full h-10 px-3 bg-lider-surface border border-lider-border rounded-[2px] text-sm text-lider-ink focus:border-lider-charcoal focus:outline-none transition-colors"
            >
              <option value="">Todas</option>
              {filterOptions.puxadores.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="f-divisoria"
              className="block text-[11px] uppercase tracking-[0.06em] text-lider-slate mb-1.5"
            >
              Divisórias
            </label>
            <select
              id="f-divisoria"
              value={divisoriaFilter}
              onChange={(e) => setDivisoriaFilter(e.target.value)}
              className="w-full h-10 px-3 bg-lider-surface border border-lider-border rounded-[2px] text-sm text-lider-ink focus:border-lider-charcoal focus:outline-none transition-colors"
            >
              <option value="">Todas</option>
              <option value="sim">Com Divisórias</option>
              <option value="nao">Sem Divisórias</option>
            </select>
          </div>

          <div>
            <label
              htmlFor="f-entrega"
              className="block text-[11px] uppercase tracking-[0.06em] text-lider-slate mb-1.5"
            >
              Entrega
            </label>
            <select
              id="f-entrega"
              value={entregaFilter}
              onChange={(e) => setEntregaFilter(e.target.value)}
              className="w-full h-10 px-3 bg-lider-surface border border-lider-border rounded-[2px] text-sm text-lider-ink focus:border-lider-charcoal focus:outline-none transition-colors"
            >
              <option value="">Todas</option>
              {filterOptions.entregas.map((e) => (
                <option key={e} value={e}>
                  {e}
                </option>
              ))}
            </select>
          </div>
        </form>
      </search>

      {/* Metadados da tabela */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-lider-slate">
        <div className="flex flex-wrap items-center gap-3">
          <span className="font-medium text-lider-ink">
            {filteredAndSorted.length} item(ns) exibido(s)
          </span>
          {hasActiveFilters && (
            <button
              type="button"
              onClick={resetFilters}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 border border-lider-border rounded-[2px] text-lider-charcoal hover:bg-lider-canvas transition-colors"
            >
              <RotateCcw className="w-3 h-3" strokeWidth={1.5} />
              Limpar filtros
            </button>
          )}
        </div>
        <span className="text-lider-muted">
          Clique em qualquer linha para abrir o desenho 2D e corte detalhado da peça.
        </span>
      </div>

      {/* Tabela Responsiva */}
      {!filteredAndSorted.length ? (
        <div className="border border-lider-border rounded-[2px] bg-lider-surface px-6 py-14 text-center text-sm text-lider-muted">
          {!items.length
            ? "Nenhum dado carregado. Consulte o ERP no painel lateral ou carregue um arquivo HTML."
            : "Nenhum item corresponde aos filtros selecionados."}
        </div>
      ) : (
        <div
          tabIndex={0}
          role="region"
          aria-labelledby="caption-itens"
          className="table-wrapper stack-narrow"
        >
          <table className="lider-table">
            <caption id="caption-itens" className="visually-hidden">
              Dados construtivos extraídos das OPs
            </caption>
            <thead>
              <tr>
                <th>
                  <button
                    type="button"
                    onClick={() => handleSort("op")}
                    className="inline-flex items-center gap-1 hover:text-lider-ink"
                  >
                    OP {renderSortIcon("op")}
                  </button>
                </th>
                <th>
                  <button
                    type="button"
                    onClick={() => handleSort("codigo")}
                    className="inline-flex items-center gap-1 hover:text-lider-ink"
                  >
                    Código {renderSortIcon("codigo")}
                  </button>
                </th>
                <th>
                  <button
                    type="button"
                    onClick={() => handleSort("pedido")}
                    className="inline-flex items-center gap-1 hover:text-lider-ink"
                  >
                    Pedido {renderSortIcon("pedido")}
                  </button>
                </th>
                <th>
                  <button
                    type="button"
                    onClick={() => handleSort("data_entrega")}
                    className="inline-flex items-center gap-1 hover:text-lider-ink"
                  >
                    Entrega {renderSortIcon("data_entrega")}
                  </button>
                </th>
                <th>Categoria</th>
                <th>
                  <button
                    type="button"
                    onClick={() => handleSort("modelo")}
                    className="inline-flex items-center gap-1 hover:text-lider-ink"
                  >
                    Modelo {renderSortIcon("modelo")}
                  </button>
                </th>
                <th className="num-header">
                  <button
                    type="button"
                    onClick={() => handleSort("quantidade")}
                    className="inline-flex items-center justify-end gap-1 hover:text-lider-ink ml-auto"
                  >
                    Qtd {renderSortIcon("quantidade")}
                  </button>
                </th>
                <th className="num-header">Quadros</th>
                <th className="num-header">
                  <button
                    type="button"
                    onClick={() => handleSort("largura_mm")}
                    className="inline-flex items-center justify-end gap-1 hover:text-lider-ink ml-auto"
                  >
                    Largura (mm) {renderSortIcon("largura_mm")}
                  </button>
                </th>
                <th className="num-header">
                  <button
                    type="button"
                    onClick={() => handleSort("altura_mm")}
                    className="inline-flex items-center justify-end gap-1 hover:text-lider-ink ml-auto"
                  >
                    Altura (mm) {renderSortIcon("altura_mm")}
                  </button>
                </th>
                <th>Puxadores</th>
                <th>Divisórias</th>
                <th>Perfil</th>
                <th>Placa / Vidro</th>
                <th>Furação</th>
              </tr>
            </thead>
            <tbody>
              {filteredAndSorted.map((it, idx) => (
                <tr
                  key={`${it.op}-${it.codigo}-${idx}`}
                  tabIndex={0}
                  onClick={() => onSelectItem(it, filteredAndSorted)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onSelectItem(it, filteredAndSorted);
                    }
                  }}
                  className="clickable-row focus:outline-none focus:bg-[#f3f1ee]"
                >
                  <th scope="row" data-label="OP" className="font-mono text-xs">
                    {it.op}
                  </th>
                  <td data-label="Código">
                    <code className="font-mono text-xs text-lider-charcoal">
                      {it.codigo}
                    </code>
                  </td>
                  <td data-label="Pedido">{it.pedido}</td>
                  <td data-label="Entrega" className="whitespace-nowrap">
                    {it.data_entrega}
                  </td>
                  <td data-label="Categoria">{it.subcategoria || it.categoria}</td>
                  <td data-label="Modelo">
                    <span className="inline-flex items-center px-2 py-0.5 text-[11px] font-medium border border-lider-border bg-lider-canvas text-lider-charcoal rounded-[2px] whitespace-nowrap">
                      {it.modelo}
                    </span>
                  </td>
                  <td data-label="Qtd" className="num">
                    {fmtNum(it.quantidade)}
                  </td>
                  <td data-label="Quadros" className="num">
                    {it.qtd_estruturas}
                  </td>
                  <td data-label="Largura (mm)" className="num font-medium">
                    {fmtNum(it.largura_mm)}
                  </td>
                  <td data-label="Altura (mm)" className="num font-medium">
                    {fmtNum(it.altura_mm)}
                  </td>
                  <td data-label="Puxadores" className="whitespace-nowrap">
                    {it.tem_puxador ? (
                      <span className="inline-flex items-center gap-1.5">
                        <span className="inline-flex items-center px-1.5 py-0.5 text-[11px] font-medium border border-lider-wood/40 bg-lider-wood/5 text-lider-wood rounded-[2px]">
                          {it.qtd_puxadores}x
                        </span>
                        <span className="text-xs">{it.posicao_puxador}</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-1.5 py-0.5 text-[11px] border border-lider-border bg-lider-canvas text-lider-muted rounded-[2px]">
                        0 · SEM PUXADOR
                      </span>
                    )}
                  </td>
                  <td data-label="Divisórias" className="whitespace-nowrap">
                    {it.tem_divisorias ? (
                      <span className="inline-flex items-center gap-1.5">
                        <span className="inline-flex items-center px-1.5 py-0.5 text-[11px] font-medium border border-lider-terracotta/40 bg-lider-terracotta/5 text-lider-terracotta rounded-[2px]">
                          {it.qtd_divisorias}x
                        </span>
                        <span className="text-xs">
                          {(it.divisorias_mm || []).map((d) => `${fmtNum(d)}mm`).join(", ")}
                        </span>
                      </span>
                    ) : (
                      <span className="text-lider-muted">Não</span>
                    )}
                  </td>
                  <td data-label="Perfil">{it.acabamento_perfil || "-"}</td>
                  <td data-label="Placa / Vidro">{it.acabamento_placa || "-"}</td>
                  <td data-label="Furação">{it.furacao || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
