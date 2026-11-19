import React from "react";
import {
  FileSpreadsheet,
  FileText,
  Braces,
  Menu,
  PanelLeftOpen,
  Scissors,
  Square,
  Loader2,
} from "lucide-react";

export default function Header({
  isDesktopCollapsed,
  onOpenMobileSidebar,
  onToggleDesktopSidebar,
  hasData,
  meta,
  exportingKey,
  onExport,
}) {
  const exportButtons = [
    {
      key: "xlsx",
      label: "Excel (.xlsx)",
      icon: FileSpreadsheet,
      endpoint: "/api/export/xlsx",
      body: {},
      filename: "plano_corte_portas.xlsx",
      accent: true,
    },
    {
      key: "csv-items",
      label: "CSV Itens",
      icon: FileText,
      endpoint: "/api/export/csv",
      body: { mode: "items" },
      filename: "itens_portas.csv",
    },
    {
      key: "csv-corte",
      label: "CSV Serra",
      icon: Scissors,
      endpoint: "/api/export/csv",
      body: { mode: "corte" },
      filename: "corte_serra_portas.csv",
    },
    {
      key: "csv-vidro",
      label: "CSV Vidros",
      icon: Square,
      endpoint: "/api/export/csv",
      body: { mode: "vidro" },
      filename: "corte_vidros_portas.csv",
    },
    {
      key: "json",
      label: "JSON",
      icon: Braces,
      endpoint: "/api/export/json",
      body: {},
      filename: "extracao_portas.json",
    },
  ];

  const datas = (meta?.datas_abertura || []).join(", ");
  const consultasCount = meta?.consultas?.length || 0;
  const subtitleParts = ["Consulta carregada"];
  if (consultasCount > 1) {
    subtitleParts.push(`${consultasCount} arquivos/lotes`);
  }
  if (datas) {
    subtitleParts.push(`Abertura ${datas}`);
  }
  subtitleParts.push(`${meta?.total_linhas ?? 0} registro(s)`);

  return (
    <header className="sticky top-0 z-30 bg-lider-surface/95 backdrop-blur-sm border-b border-lider-border">
      <div className="px-4 sm:px-6 lg:px-10 py-3.5 flex flex-col xl:flex-row xl:items-center xl:justify-between gap-3.5">
        {/* Topo Esquerdo: Controle de Sidebar + Logo (quando sidebar fechada) + Título Editorial */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-2.5 sm:gap-3.5 min-w-0">
          <div className="flex items-center gap-3 shrink-0">
            {/* Menu mobile/tablet */}
            <button
              type="button"
              onClick={onOpenMobileSidebar}
              className="lg:hidden inline-flex items-center justify-center p-2 border border-lider-border rounded-[2px] text-lider-charcoal hover:bg-lider-canvas transition-colors shrink-0"
              aria-label="Abrir menu lateral"
            >
              <Menu className="w-4 h-4" strokeWidth={1.5} />
            </button>

            {/* Expandir sidebar desktop quando recolhida */}
            {isDesktopCollapsed && (
              <button
                type="button"
                onClick={onToggleDesktopSidebar}
                className="hidden lg:inline-flex items-center justify-center p-2 border border-lider-border rounded-[2px] text-lider-charcoal hover:bg-lider-canvas transition-colors shrink-0"
                title="Exibir barra lateral"
                aria-label="Exibir barra lateral"
              >
                <PanelLeftOpen className="w-4 h-4" strokeWidth={1.5} />
              </button>
            )}

            {/* Logo visível no topo esquerdo quando mobile/tablet ou sidebar desktop recolhida */}
            <div
              className={[
                "items-center shrink-0 sm:pr-3 sm:border-r sm:border-lider-border",
                isDesktopCollapsed ? "flex" : "flex lg:hidden",
              ].join(" ")}
            >
              <img
                src="/logo_lider.png"
                alt="Lider Design"
                className="h-6 sm:h-7 w-auto object-contain"
              />
            </div>
          </div>

          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="font-display font-normal text-base sm:text-lg tracking-tight text-lider-ink">
                Extrator Construtivo &amp; Plano de Corte
              </h1>
              <span className="inline-flex items-center px-2 py-0.5 text-[10px] font-display uppercase tracking-[0.1em] border border-lider-wood/40 text-lider-wood bg-lider-wood/5 rounded-[2px]">
                PORTAS
              </span>
            </div>
            <p className="text-xs text-lider-slate mt-0.5 leading-snug">
              {hasData
                ? subtitleParts.join(" · ")
                : "Medidas, Modelos, Puxadores, Divisórias, Perfis de Alumínio e Vidros"}
            </p>
          </div>
        </div>

        {/* Barra de Exportação Global */}
        <div
          className="flex flex-wrap xl:flex-nowrap items-center gap-1.5 shrink-0"
          aria-label="Exportação de dados"
        >
          {exportButtons.map((btn) => {
            const Icon = btn.icon;
            const isBusy = exportingKey === btn.key;
            return (
              <button
                key={btn.key}
                type="button"
                disabled={!hasData || Boolean(exportingKey)}
                onClick={() => onExport(btn.key, btn.endpoint, btn.body, btn.filename)}
                className={[
                  "h-9 px-2.5 text-xs font-medium rounded-[2px] whitespace-nowrap inline-flex items-center gap-1.5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed",
                  btn.accent
                    ? "bg-lider-charcoal text-white hover:bg-lider-ink border border-lider-charcoal"
                    : "bg-transparent text-lider-charcoal border border-lider-border hover:border-lider-charcoal hover:bg-lider-canvas",
                ].join(" ")}
              >
                {isBusy ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" strokeWidth={1.5} />
                ) : (
                  <Icon className="w-3.5 h-3.5" strokeWidth={1.5} />
                )}
                <span>{btn.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
}
