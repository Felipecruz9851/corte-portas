import React, { useId, useState } from "react";
import {
  Calendar,
  Database,
  Eye,
  EyeOff,
  FileText,
  FileUp,
  Loader2,
  PanelLeftClose,
  Plus,
  RefreshCw,
  Trash2,
  Upload,
  X,
  CheckCircle2,
  AlertCircle,
  Info,
} from "lucide-react";

function splitFilename(filename) {
  const name = String(filename || "");
  const dotIdx = name.lastIndexOf(".");
  if (dotIdx <= 0 || dotIdx === name.length - 1) {
    return { stem: name, ext: "" };
  }
  return {
    stem: name.slice(0, dotIdx),
    ext: name.slice(dotIdx),
  };
}

export default function Sidebar({
  isOpen,
  isDesktopCollapsed,
  onCloseMobile,
  onToggleCollapse,
  erpForm,
  onChangeErpForm,
  onSubmitErp,
  loadedHtmlFiles = [],
  onUploadHtmlFiles,
  onRemoveHtmlFile,
  onClearHtmlFiles,
  isLoading,
  status,
  meta,
}) {
  const [showPassword, setShowPassword] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isAppendDragOver, setIsAppendDragOver] = useState(false);
  const replaceInputId = useId();
  const appendInputId = useId();
  const dropzoneHelpId = useId();

  const handleFieldChange = (field) => (e) => {
    onChangeErpForm((prev) => ({ ...prev, [field]: e.target.value }));
  };

  const handleFileChange = (append) => (e) => {
    const files = Array.from(e.target.files || []);
    e.target.value = "";
    if (files.length > 0 && onUploadHtmlFiles) {
      onUploadHtmlFiles(files, { append });
    }
  };

  const handleDrop = (append) => (e) => {
    e.preventDefault();
    if (append) {
      setIsAppendDragOver(false);
    } else {
      setIsDragOver(false);
    }
    const files = Array.from(e.dataTransfer?.files || []);
    if (files.length > 0 && onUploadHtmlFiles) {
      onUploadHtmlFiles(files, { append });
    }
  };

  const statusTone =
    status.kind === "ok"
      ? "border-lider-wood/40 bg-lider-wood/5 text-lider-ink"
      : status.kind === "err"
      ? "border-red-700/40 bg-red-50/70 text-red-900"
      : "border-lider-border bg-lider-canvas text-lider-slate";

  const StatusIcon =
    status.kind === "ok"
      ? CheckCircle2
      : status.kind === "err"
      ? AlertCircle
      : Info;

  return (
    <>
      {/* Backdrop para drawer mobile/tablet */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-lider-ink/35 backdrop-blur-[1px] lg:hidden"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      )}

      <aside
        aria-label="Painel de consulta e parâmetros"
        className={[
          "fixed inset-y-0 left-0 z-50 flex flex-col bg-lider-surface border-r border-lider-border transition-transform duration-200 ease-out",
          "w-[310px] sm:w-[330px]",
          isOpen ? "translate-x-0" : "-translate-x-full",
          isDesktopCollapsed
            ? "lg:-translate-x-full"
            : "lg:translate-x-0 lg:static lg:z-auto lg:shrink-0",
        ].join(" ")}
      >
        {/* Marca no topo esquerdo */}
        <div className="flex items-center justify-between gap-3 px-6 py-5 border-b border-lider-border">
          <div className="flex flex-col gap-1.5 min-w-0">
            <img
              src="/logo_lider.png"
              alt="Lider Design"
              className="h-7 w-auto object-contain object-left select-none"
            />
            <span className="text-[11px] font-display uppercase tracking-[0.14em] text-lider-muted">
              PCP · Engenharia de Portas
            </span>
          </div>

          <button
            type="button"
            onClick={onCloseMobile}
            className="lg:hidden inline-flex items-center justify-center p-1.5 text-lider-slate hover:text-lider-ink rounded-[2px] border border-transparent hover:border-lider-border transition-colors"
            aria-label="Fechar painel lateral"
          >
            <X className="w-4 h-4" strokeWidth={1.5} />
          </button>

          <button
            type="button"
            onClick={onToggleCollapse}
            className="hidden lg:inline-flex items-center justify-center p-1.5 text-lider-slate hover:text-lider-ink rounded-[2px] border border-transparent hover:border-lider-border transition-colors"
            title="Recolher barra lateral"
            aria-label="Recolher barra lateral"
          >
            <PanelLeftClose className="w-4 h-4" strokeWidth={1.5} />
          </button>
        </div>

        {/* Conteúdo rolável da sidebar */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          {/* Status operacional */}
          <div
            className={`border rounded-[2px] px-3.5 py-3 text-xs leading-relaxed flex items-start gap-2.5 ${statusTone}`}
            role="status"
            aria-live="polite"
          >
            {isLoading ? (
              <Loader2
                className="w-4 h-4 shrink-0 mt-0.5 animate-spin text-lider-wood"
                strokeWidth={1.5}
              />
            ) : (
              <StatusIcon
                className={`w-4 h-4 shrink-0 mt-0.5 ${
                  status.kind === "ok"
                    ? "text-lider-wood"
                    : status.kind === "err"
                    ? "text-red-700"
                    : "text-lider-muted"
                }`}
                strokeWidth={1.5}
              />
            )}
            <span className="min-w-0 break-words">{status.message}</span>
          </div>

          {/* Formulário ERP */}
          <form onSubmit={onSubmitErp} className="space-y-4">
            <div className="flex items-center gap-2 pb-1 border-b border-lider-border/70">
              <Database className="w-3.5 h-3.5 text-lider-wood" strokeWidth={1.5} />
              <h2 className="font-display text-xs uppercase tracking-[0.12em] font-medium text-lider-ink">
                Consulta ao Vivo ERP
              </h2>
            </div>

            <div className="space-y-3.5">
              <div>
                <label
                  htmlFor="erp-data"
                  className="block text-[11px] uppercase tracking-[0.06em] text-lider-slate mb-1.5"
                >
                  Data de Abertura *
                </label>
                <div className="relative">
                  <input
                    type="date"
                    id="erp-data"
                    name="data"
                    required
                    value={erpForm.data}
                    onChange={handleFieldChange("data")}
                    className="w-full h-10 px-3 bg-lider-surface border border-lider-border rounded-[2px] text-sm text-lider-ink focus:border-lider-charcoal focus:outline-none transition-colors"
                  />
                </div>
              </div>

              <div>
                <label
                  htmlFor="erp-datas-extra"
                  className="block text-[11px] uppercase tracking-[0.06em] text-lider-slate mb-1.5"
                >
                  Datas Adicionais (opcional)
                </label>
                <input
                  type="text"
                  id="erp-datas-extra"
                  name="datas_extra"
                  value={erpForm.datasExtra}
                  onChange={handleFieldChange("datasExtra")}
                  placeholder="Ex: 2026-11-06, 2026-11-13"
                  autoCorrect="off"
                  autoCapitalize="none"
                  spellCheck={false}
                  className="w-full h-10 px-3 bg-lider-surface border border-lider-border rounded-[2px] text-sm text-lider-ink placeholder:text-lider-muted/70 focus:border-lider-charcoal focus:outline-none transition-colors"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label
                    htmlFor="erp-empresa"
                    className="block text-[11px] uppercase tracking-[0.06em] text-lider-slate mb-1.5"
                  >
                    Empresa
                  </label>
                  <input
                    type="text"
                    id="erp-empresa"
                    name="cod_empresa"
                    inputMode="numeric"
                    required
                    value={erpForm.codEmpresa}
                    onChange={handleFieldChange("codEmpresa")}
                    autoCorrect="off"
                    spellCheck={false}
                    className="w-full h-10 px-3 bg-lider-surface border border-lider-border rounded-[2px] text-sm text-lider-ink focus:border-lider-charcoal focus:outline-none transition-colors"
                  />
                </div>
                <div>
                  <label
                    htmlFor="erp-local"
                    className="block text-[11px] uppercase tracking-[0.06em] text-lider-slate mb-1.5"
                  >
                    Local
                  </label>
                  <input
                    type="text"
                    id="erp-local"
                    name="local"
                    required
                    value={erpForm.local}
                    onChange={handleFieldChange("local")}
                    autoCorrect="off"
                    spellCheck={false}
                    className="w-full h-10 px-3 bg-lider-surface border border-lider-border rounded-[2px] text-sm text-lider-ink focus:border-lider-charcoal focus:outline-none transition-colors"
                  />
                </div>
              </div>

              {/* Modo de Autenticação */}
              <fieldset className="pt-1">
                <legend className="text-[11px] uppercase tracking-[0.06em] text-lider-slate mb-2">
                  Autenticação ERP
                </legend>
                <div className="grid grid-cols-2 border border-lider-border rounded-[2px] bg-lider-canvas p-0.5">
                  <label
                    htmlFor="auth-cookie"
                    className={[
                      "justify-center text-xs py-2 px-2 rounded-[2px] cursor-pointer transition-colors select-none",
                      erpForm.authMode === "cookie"
                        ? "bg-lider-surface text-lider-ink font-medium shadow-sm"
                        : "text-lider-slate hover:text-lider-ink",
                    ].join(" ")}
                  >
                    <input
                      type="radio"
                      id="auth-cookie"
                      name="auth_mode"
                      value="cookie"
                      checked={erpForm.authMode === "cookie"}
                      onChange={handleFieldChange("authMode")}
                      className="sr-only"
                    />
                    PHPSESSID
                  </label>
                  <label
                    htmlFor="auth-creds"
                    className={[
                      "justify-center text-xs py-2 px-2 rounded-[2px] cursor-pointer transition-colors select-none",
                      erpForm.authMode === "creds"
                        ? "bg-lider-surface text-lider-ink font-medium shadow-sm"
                        : "text-lider-slate hover:text-lider-ink",
                    ].join(" ")}
                  >
                    <input
                      type="radio"
                      id="auth-creds"
                      name="auth_mode"
                      value="creds"
                      checked={erpForm.authMode === "creds"}
                      onChange={handleFieldChange("authMode")}
                      className="sr-only"
                    />
                    Usuário/Senha
                  </label>
                </div>
              </fieldset>

              {erpForm.authMode === "cookie" ? (
                <div>
                  <label
                    htmlFor="erp-phpsessid"
                    className="block text-[11px] uppercase tracking-[0.06em] text-lider-slate mb-1.5"
                  >
                    Cookie PHPSESSID
                  </label>
                  <input
                    type="text"
                    id="erp-phpsessid"
                    name="phpsessid"
                    value={erpForm.phpsessid}
                    onChange={handleFieldChange("phpsessid")}
                    autoComplete="off"
                    autoCorrect="off"
                    autoCapitalize="none"
                    spellCheck={false}
                    className="w-full h-10 px-3 bg-lider-surface border border-lider-border rounded-[2px] font-mono text-xs text-lider-ink focus:border-lider-charcoal focus:outline-none transition-colors"
                  />
                </div>
              ) : (
                <div className="space-y-3">
                  <div>
                    <label
                      htmlFor="erp-usuario"
                      className="block text-[11px] uppercase tracking-[0.06em] text-lider-slate mb-1.5"
                    >
                      Usuário ERP
                    </label>
                    <input
                      type="text"
                      id="erp-usuario"
                      name="usuario"
                      value={erpForm.usuario}
                      onChange={handleFieldChange("usuario")}
                      autoComplete="username"
                      autoCorrect="off"
                      autoCapitalize="none"
                      spellCheck={false}
                      className="w-full h-10 px-3 bg-lider-surface border border-lider-border rounded-[2px] text-sm text-lider-ink focus:border-lider-charcoal focus:outline-none transition-colors"
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="erp-senha"
                      className="block text-[11px] uppercase tracking-[0.06em] text-lider-slate mb-1.5"
                    >
                      Senha ERP
                    </label>
                    <div className="relative">
                      <input
                        type={showPassword ? "text" : "password"}
                        id="erp-senha"
                        name="senha"
                        value={erpForm.senha}
                        onChange={handleFieldChange("senha")}
                        autoComplete="current-password"
                        className="w-full h-10 pl-3 pr-10 bg-lider-surface border border-lider-border rounded-[2px] text-sm text-lider-ink focus:border-lider-charcoal focus:outline-none transition-colors"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword((v) => !v)}
                        aria-label={showPassword ? "Ocultar senha" : "Exibir senha"}
                        className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1.5 text-lider-muted hover:text-lider-ink"
                      >
                        {showPassword ? (
                          <EyeOff className="w-4 h-4" strokeWidth={1.5} />
                        ) : (
                          <Eye className="w-4 h-4" strokeWidth={1.5} />
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full h-11 px-4 bg-lider-charcoal hover:bg-lider-ink disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-display uppercase tracking-[0.1em] font-medium rounded-[2px] inline-flex items-center justify-center gap-2 transition-colors"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" strokeWidth={1.5} />
              ) : (
                <RefreshCw className="w-4 h-4" strokeWidth={1.5} />
              )}
              Consultar ERP ao Vivo
            </button>
          </form>

          {/* Importação local de HTML */}
          <div className="space-y-3 pt-2 border-t border-lider-border">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <FileUp className="w-3.5 h-3.5 text-lider-wood" strokeWidth={1.5} />
                <h2 className="font-display text-xs uppercase tracking-[0.12em] font-medium text-lider-ink">
                  Arquivos Locais (.html)
                </h2>
              </div>
              {loadedHtmlFiles.length > 0 && (
                <span className="font-mono text-[11px] text-lider-wood">
                  {loadedHtmlFiles.length} {loadedHtmlFiles.length === 1 ? "ativo" : "ativos"}
                </span>
              )}
            </div>

            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragOver(true);
              }}
              onDragLeave={(e) => {
                if (!e.currentTarget.contains(e.relatedTarget)) {
                  setIsDragOver(false);
                }
              }}
              onDrop={handleDrop(false)}
              className={[
                "border border-dashed rounded-[2px] p-4 text-center transition-colors",
                isDragOver
                  ? "border-lider-wood bg-lider-wood/5"
                  : "border-lider-border bg-lider-canvas/60",
              ].join(" ")}
            >
              <p id={dropzoneHelpId} className="text-xs text-lider-slate mb-3">
                Arraste um ou mais arquivos HTML do ERP ou selecione manualmente.
              </p>
              <div className="relative">
                <input
                  id={replaceInputId}
                  name="html_files"
                  type="file"
                  accept=".html,.htm,text/html"
                  multiple
                  disabled={isLoading}
                  aria-describedby={dropzoneHelpId}
                  onChange={handleFileChange(false)}
                  className="visually-hidden peer"
                />
                <label
                  htmlFor={replaceInputId}
                  className="w-full h-10 px-3 bg-transparent hover:bg-lider-surface border border-lider-charcoal/40 hover:border-lider-charcoal text-lider-ink text-xs font-medium rounded-[2px] inline-flex items-center justify-center gap-2 transition-colors cursor-pointer peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-lider-wood peer-focus-visible:outline-offset-2 peer-disabled:opacity-50 peer-disabled:cursor-not-allowed peer-disabled:pointer-events-none"
                >
                  <Upload className="w-3.5 h-3.5 shrink-0" strokeWidth={1.5} />
                  <span>Carregar HTML(s) local</span>
                </label>
              </div>
            </div>

            {loadedHtmlFiles.length > 0 && (
              <div className="space-y-2.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[11px] uppercase tracking-[0.06em] text-lider-slate">
                    Arquivos carregados ({loadedHtmlFiles.length})
                  </span>
                  <button
                    type="button"
                    disabled={isLoading}
                    onClick={onClearHtmlFiles}
                    className="inline-flex items-center gap-1 px-2 py-1 text-[11px] text-lider-slate hover:text-red-800 border border-transparent hover:border-lider-border rounded-[2px] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Trash2 className="w-3 h-3" strokeWidth={1.5} />
                    <span>Limpar</span>
                  </button>
                </div>

                <ul
                  aria-label="Arquivos HTML carregados na sessão"
                  className="max-h-44 overflow-y-auto divide-y divide-lider-border border border-lider-border rounded-[2px] bg-lider-surface"
                >
                  {loadedHtmlFiles.map((file, idx) => {
                    const { stem, ext } = splitFilename(file.name);
                    const consultaMeta =
                      meta?.consultas?.[idx]?.origem === file.name
                        ? meta.consultas[idx]
                        : null;
                    return (
                      <li
                        key={file.key}
                        className="flex items-center justify-between gap-2 px-2.5 py-1.5"
                      >
                        <div className="flex items-center gap-2 min-w-0 flex-1">
                          <FileText
                            className="w-3.5 h-3.5 text-lider-wood shrink-0"
                            strokeWidth={1.5}
                          />
                          <span
                            className="file-name-truncate font-mono text-[11px] text-lider-ink"
                            title={file.name}
                          >
                            <span>{stem}</span>{ext}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5 shrink-0">
                          {consultaMeta && (
                            <span className="text-[10px] font-mono text-lider-muted tabular-nums">
                              {consultaMeta.total_linhas} lin.
                            </span>
                          )}
                          <button
                            type="button"
                            disabled={isLoading}
                            onClick={() => onRemoveHtmlFile(file.key)}
                            aria-label={`Remover ${file.name}`}
                            title={`Remover ${file.name}`}
                            className="inline-flex items-center justify-center p-1 text-lider-muted hover:text-red-800 rounded-[2px] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            <X className="w-3.5 h-3.5" strokeWidth={1.5} />
                          </button>
                        </div>
                      </li>
                    );
                  })}
                </ul>

                <div
                  onDragOver={(e) => {
                    e.preventDefault();
                    setIsAppendDragOver(true);
                  }}
                  onDragLeave={(e) => {
                    if (!e.currentTarget.contains(e.relatedTarget)) {
                      setIsAppendDragOver(false);
                    }
                  }}
                  onDrop={handleDrop(true)}
                  className={[
                    "relative rounded-[2px] transition-colors",
                    isAppendDragOver ? "bg-lider-wood/10" : "",
                  ].join(" ")}
                >
                  <input
                    id={appendInputId}
                    name="html_files_append"
                    type="file"
                    accept=".html,.htm,text/html"
                    multiple
                    disabled={isLoading}
                    onChange={handleFileChange(true)}
                    className="visually-hidden peer"
                  />
                  <label
                    htmlFor={appendInputId}
                    className={[
                      "w-full h-9 px-3 border border-dashed rounded-[2px] text-[11px] font-medium inline-flex items-center justify-center gap-1.5 transition-colors cursor-pointer",
                      "peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-lider-wood peer-focus-visible:outline-offset-2",
                      "peer-disabled:opacity-50 peer-disabled:cursor-not-allowed peer-disabled:pointer-events-none",
                      isAppendDragOver
                        ? "border-lider-wood text-lider-ink bg-lider-wood/5"
                        : "border-lider-border text-lider-slate hover:text-lider-ink hover:border-lider-charcoal/50 bg-lider-canvas/40",
                    ].join(" ")}
                  >
                    <Plus className="w-3.5 h-3.5 shrink-0" strokeWidth={1.5} />
                    <span>Adicionar mais HTML(s) ao lote</span>
                  </label>
                </div>
              </div>
            )}
          </div>

          {/* Resumo da extração atual */}
          {meta && (
            <div className="pt-2 border-t border-lider-border space-y-2.5 text-xs">
              <div className="flex items-center gap-2">
                <Calendar className="w-3.5 h-3.5 text-lider-wood" strokeWidth={1.5} />
                <span className="font-display uppercase tracking-[0.1em] text-[11px] text-lider-ink font-medium">
                  Resumo da Sessão
                </span>
              </div>
              <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-lider-slate">
                <dt className="text-lider-muted">Locais:</dt>
                <dd className="text-lider-ink text-right truncate">
                  {(meta.locais || []).join(", ") || "-"}
                </dd>
                <dt className="text-lider-muted">Abertura:</dt>
                <dd className="text-lider-ink text-right truncate">
                  {(meta.datas_abertura || []).join(", ") || "-"}
                </dd>
                {(meta.consultas || []).length > 1 && (
                  <>
                    <dt className="text-lider-muted">Origens:</dt>
                    <dd className="text-lider-ink text-right font-mono">
                      {loadedHtmlFiles.length > 0
                        ? `${meta.consultas.length} arquivos`
                        : `${meta.consultas.length} consultas`}
                    </dd>
                  </>
                )}
                <dt className="text-lider-muted">Linhas OP:</dt>
                <dd className="text-lider-ink text-right font-mono">
                  {meta.total_linhas ?? 0}
                </dd>
              </dl>
            </div>
          )}
        </div>

        {/* Rodapé discreto da sidebar */}
        <div className="px-6 py-3.5 border-t border-lider-border bg-lider-canvas/60 text-[11px] text-lider-muted">
          ERP: <code className="font-mono text-lider-slate">192.168.0.6/pcp/op_abertura.php</code>
        </div>
      </aside>
    </>
  );
}
