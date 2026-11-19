import React, { useCallback, useEffect, useRef, useState } from "react";
import { Layers, Ruler, SlidersHorizontal, Square } from "lucide-react";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import MetricsCards from "./components/MetricsCards";
import ItemsTab from "./components/ItemsTab";
import BarsCutTab from "./components/BarsCutTab";
import GlassCutTab from "./components/GlassCutTab";
import RulesTab from "./components/RulesTab";
import PieceDetailDialog from "./components/PieceDetailDialog";
import { downloadExportFile, fetchJson } from "./utils/api";
import { getTodayIso } from "./utils/formatters";

const TABS = [
  { id: "tab-itens", panelId: "panel-itens", label: "Construção das Peças", icon: Layers },
  { id: "tab-corte", panelId: "panel-corte", label: "Plano de Corte de Barras", icon: Ruler },
  { id: "tab-vidros", panelId: "panel-vidros", label: "Plano de Corte de Vidros", icon: Square },
  { id: "tab-regras", panelId: "panel-regras", label: "Regras e Descontos (mm)", icon: SlidersHorizontal },
];

export default function App() {
  const [payload, setPayload] = useState(null);
  const [rules, setRules] = useState({});
  const [activeTab, setActiveTab] = useState("tab-itens");

  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [isDesktopCollapsed, setIsDesktopCollapsed] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [isSavingRules, setIsSavingRules] = useState(false);
  const [exportingKey, setExportingKey] = useState(null);
  const [status, setStatus] = useState({
    message: "Pronto para consultar o ERP ou carregar um arquivo HTML de OP.",
    kind: "",
  });

  const [erpForm, setErpForm] = useState({
    data: getTodayIso(),
    datasExtra: "",
    codEmpresa: "11",
    local: "PORTAS",
    authMode: "cookie",
    phpsessid: "ms1hfp1mhvr4608vaf2j37jlqn",
    usuario: "",
    senha: "",
  });

  const [modalState, setModalState] = useState({ item: null, list: [] });
  const tabRefs = useRef({});
  const panelRefs = useRef({});

  const applyPayload = useCallback((nextPayload) => {
    setPayload(nextPayload);
    if (nextPayload?.rules) {
      setRules(nextPayload.rules);
    }
  }, []);

  // Carrega regras iniciais ao montar
  useEffect(() => {
    let active = true;
    fetchJson("/api/rules")
      .then((res) => {
        if (active && res?.rules) {
          setRules(res.rules);
        }
      })
      .catch((err) => {
        if (active) {
          setStatus({
            message: `Erro ao carregar regras iniciais: ${err.message}`,
            kind: "err",
          });
        }
      });
    return () => {
      active = false;
    };
  }, []);

  // Suporte a find-in-page (beforematch) nos painéis com hidden="until-found"
  useEffect(() => {
    const cleanups = [];
    TABS.forEach((tab) => {
      const panelEl = panelRefs.current[tab.panelId];
      if (!panelEl) return;
      const handler = () => setActiveTab(tab.id);
      panelEl.addEventListener("beforematch", handler);
      cleanups.push(() => panelEl.removeEventListener("beforematch", handler));
    });
    return () => cleanups.forEach((fn) => fn());
  }, []);

  const selectTab = useCallback((tabId, shouldFocus = false) => {
    setActiveTab(tabId);
    const el = tabRefs.current[tabId];
    if (el) {
      if (shouldFocus) el.focus();
      el.scrollIntoView({ block: "nearest", inline: "nearest" });
    }
  }, []);

  const handleTabKeyDown = (e, idx) => {
    if (e.key === "ArrowRight") {
      e.preventDefault();
      const next = TABS[(idx + 1) % TABS.length];
      selectTab(next.id, true);
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      const prev = TABS[(idx - 1 + TABS.length) % TABS.length];
      selectTab(prev.id, true);
    }
  };

  const handleErpSubmit = async (e) => {
    e.preventDefault();
    const dataPrincipal = erpForm.data.trim();
    const extras = erpForm.datasExtra
      .split(/[,;\s]+/)
      .map((s) => s.trim())
      .filter(Boolean);
    const datas = Array.from(new Set([dataPrincipal, ...extras].filter(Boolean)));

    const body = {
      datas,
      cod_empresa: erpForm.codEmpresa.trim() || "11",
      local: erpForm.local.trim() || "PORTAS",
      item_desc: "S",
    };

    if (erpForm.authMode === "cookie") {
      body.phpsessid = erpForm.phpsessid.trim();
    } else {
      body.usuario = erpForm.usuario.trim();
      body.senha = erpForm.senha;
    }

    setIsLoading(true);
    setStatus({ message: `Consultando ERP (${datas.join(", ")})...`, kind: "" });
    try {
      const data = await fetchJson("/api/extract/erp", {
        method: "POST",
        body: JSON.stringify(body),
      });
      applyPayload(data);
      setStatus({
        message: `Extração concluída: ${data.kpis.total_linhas_op} linhas e ${data.kpis.total_barras_corte} barras calculadas.`,
        kind: "ok",
      });
      setIsMobileSidebarOpen(false);
    } catch (err) {
      setStatus({ message: err.message, kind: "err" });
    } finally {
      setIsLoading(false);
    }
  };

  const handleUploadHtmlFile = async (file) => {
    setIsLoading(true);
    setStatus({ message: `Processando ${file.name}...`, kind: "" });
    try {
      const html = await file.text();
      const data = await fetchJson("/api/extract/html", {
        method: "POST",
        body: JSON.stringify({ html, source_name: file.name }),
      });
      applyPayload(data);
      setStatus({
        message: `Arquivo ${file.name} processado: ${data.kpis.total_linhas_op} linhas e ${data.kpis.total_barras_corte} barras.`,
        kind: "ok",
      });
      setIsMobileSidebarOpen(false);
    } catch (err) {
      setStatus({ message: err.message, kind: "err" });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveRules = async (updatedRules) => {
    setIsSavingRules(true);
    setStatus({ message: "Salvando regras e recalculando barras...", kind: "" });
    try {
      const res = await fetchJson("/api/rules", {
        method: "PUT",
        body: JSON.stringify({ rules: updatedRules }),
      });
      setRules(res.rules);
      if (res.recalculated) {
        applyPayload(res.recalculated);
      }
      setStatus({
        message: "Regras salvas e plano de corte recalculado.",
        kind: "ok",
      });
    } catch (err) {
      setStatus({ message: err.message, kind: "err" });
    } finally {
      setIsSavingRules(false);
    }
  };

  const handleResetRules = async () => {
    setIsSavingRules(true);
    setStatus({ message: "Restaurando regras padrão...", kind: "" });
    try {
      const res = await fetchJson("/api/rules/reset", { method: "POST" });
      setRules(res.rules);
      if (res.recalculated) {
        applyPayload(res.recalculated);
      }
      setStatus({
        message: "Regras restauradas para os padrões configurados.",
        kind: "ok",
      });
    } catch (err) {
      setStatus({ message: err.message, kind: "err" });
    } finally {
      setIsSavingRules(false);
    }
  };

  const handleExport = async (key, endpoint, body, filename) => {
    setExportingKey(key);
    try {
      await downloadExportFile(endpoint, body, filename);
    } catch (err) {
      setStatus({ message: err.message, kind: "err" });
    } finally {
      setExportingKey(null);
    }
  };

  const items = payload?.items || [];
  const hasData = items.length > 0;

  return (
    <div className="min-h-screen flex bg-lider-canvas text-lider-ink">
      {/* Sidebar fixa à esquerda (desktop) / drawer (mobile) */}
      <Sidebar
        isOpen={isMobileSidebarOpen}
        isDesktopCollapsed={isDesktopCollapsed}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
        onToggleCollapse={() => setIsDesktopCollapsed((c) => !c)}
        erpForm={erpForm}
        onChangeErpForm={setErpForm}
        onSubmitErp={handleErpSubmit}
        onUploadHtmlFile={handleUploadHtmlFile}
        isLoading={isLoading}
        status={status}
        meta={payload?.meta}
      />

      {/* Coluna principal */}
      <div className="flex-1 min-w-0 flex flex-col">
        <Header
          isDesktopCollapsed={isDesktopCollapsed}
          onOpenMobileSidebar={() => setIsMobileSidebarOpen(true)}
          onToggleDesktopSidebar={() => setIsDesktopCollapsed((c) => !c)}
          hasData={hasData}
          meta={payload?.meta}
          exportingKey={exportingKey}
          onExport={handleExport}
        />

        <main className="flex-1 px-4 sm:px-6 lg:px-10 py-6 lg:py-10 space-y-8 max-w-[1680px] w-full mx-auto">
          {/* Cartões de métricas */}
          <MetricsCards kpis={payload?.kpis} meta={payload?.meta} />

          {/* Painel de Resultados e Configurações em Abas */}
          <section
            aria-label="Resultados e configurações"
            className="bg-lider-surface border border-lider-border rounded-[2px] shadow-lider"
          >
            {/* Tablist */}
            <div
              className="tablist-scroller border-b border-lider-border bg-lider-canvas/70 px-4 sm:px-6"
              focusgroup="tablist nomemory"
              role="tablist"
              aria-label="Visões do sistema"
            >
              {TABS.map((tab, idx) => {
                const selected = activeTab === tab.id;
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    ref={(el) => {
                      tabRefs.current[tab.id] = el;
                    }}
                    type="button"
                    role="tab"
                    id={tab.id}
                    aria-selected={selected}
                    focusgroupstart={selected ? "" : undefined}
                    onClick={() => selectTab(tab.id)}
                    onKeyDown={(e) => handleTabKeyDown(e, idx)}
                    className={[
                      "px-4 sm:px-5 py-4 text-xs sm:text-[13px] font-display tracking-[0.04em] inline-flex items-center gap-2 whitespace-nowrap transition-colors",
                      selected
                        ? "text-lider-ink font-medium"
                        : "text-lider-slate hover:text-lider-ink font-normal",
                    ].join(" ")}
                  >
                    <Icon
                      className={`w-3.5 h-3.5 ${
                        selected ? "text-lider-wood" : "text-lider-muted"
                      }`}
                      strokeWidth={1.5}
                    />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Tabpanels (sem estilos de box no próprio elemento tabpanel para compatibilidade com hidden="until-found") */}
            <div>
              <div
                ref={(el) => {
                  panelRefs.current["panel-itens"] = el;
                }}
                role="tabpanel"
                id="panel-itens"
                aria-labelledby="tab-itens"
                tabIndex={activeTab === "tab-itens" ? 0 : undefined}
                hidden={activeTab === "tab-itens" ? undefined : "until-found"}
              >
                <ItemsTab
                  items={items}
                  onSelectItem={(item, visibleList) =>
                    setModalState({ item, list: visibleList })
                  }
                />
              </div>

              <div
                ref={(el) => {
                  panelRefs.current["panel-corte"] = el;
                }}
                role="tabpanel"
                id="panel-corte"
                aria-labelledby="tab-corte"
                tabIndex={activeTab === "tab-corte" ? 0 : undefined}
                hidden={activeTab === "tab-corte" ? undefined : "until-found"}
              >
                <BarsCutTab
                  groupedBars={payload?.corte_agrupado || []}
                  detailedBars={payload?.corte_detalhado || []}
                  items={items}
                />
              </div>

              <div
                ref={(el) => {
                  panelRefs.current["panel-vidros"] = el;
                }}
                role="tabpanel"
                id="panel-vidros"
                aria-labelledby="tab-vidros"
                tabIndex={activeTab === "tab-vidros" ? 0 : undefined}
                hidden={activeTab === "tab-vidros" ? undefined : "until-found"}
              >
                <GlassCutTab
                  groupedGlasses={payload?.vidro_agrupado || []}
                  detailedGlasses={payload?.vidro_detalhado || []}
                  items={items}
                />
              </div>

              <div
                ref={(el) => {
                  panelRefs.current["panel-regras"] = el;
                }}
                role="tabpanel"
                id="panel-regras"
                aria-labelledby="tab-regras"
                tabIndex={activeTab === "tab-regras" ? 0 : undefined}
                hidden={activeTab === "tab-regras" ? undefined : "until-found"}
              >
                <RulesTab
                  rules={rules}
                  isSaving={isSavingRules}
                  onSaveRules={handleSaveRules}
                  onResetRules={handleResetRules}
                />
              </div>
            </div>
          </section>
        </main>
      </div>

      {/* Modal 2D de Detalhes */}
      <PieceDetailDialog
        item={modalState.item}
        items={modalState.list}
        onSelectItem={(nextItem) =>
          setModalState((prev) => ({ ...prev, item: nextItem }))
        }
        onClose={() => setModalState({ item: null, list: [] })}
      />
    </div>
  );
}
