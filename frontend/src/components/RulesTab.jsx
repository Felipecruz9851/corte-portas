import React, { useEffect, useMemo, useState } from "react";
import { Loader2, RotateCcw, Save } from "lucide-react";

export default function RulesTab({
  rules = {},
  isSaving = false,
  onSaveRules,
  onResetRules,
}) {
  const [draftRules, setDraftRules] = useState({});
  const [isDirty, setIsDirty] = useState(false);

  useEffect(() => {
    setDraftRules(structuredClone(rules));
    setIsDirty(false);
  }, [rules]);

  const sortedKeys = useMemo(() => Object.keys(draftRules).sort(), [draftRules]);

  const handleFieldChange = (key, field, rawValue) => {
    setIsDirty(true);
    setDraftRules((prev) => {
      const current = { ...prev[key] };
      if (field === "tipo_corte") {
        current[field] = rawValue;
      } else {
        current[field] = rawValue === "" ? "" : Number(rawValue);
      }

      if (
        field === "largura_perfil_quadro_mm" ||
        field === "largura_perfil_puxador_mm"
      ) {
        const quadro = Number(current.largura_perfil_quadro_mm) || 0;
        const pux = Number(current.largura_perfil_puxador_mm) || 0;
        if (quadro > 0 || pux > 0) {
          current.desconto_adjacente_puxador_mm = Math.max(0, pux - quadro);
        }
      }

      return { ...prev, [key]: current };
    });
  };

  const handleSaveClick = () => {
    const normalized = {};
    for (const key of sortedKeys) {
      const r = draftRules[key];
      normalized[key] = {
        ...r,
        largura_perfil_quadro_mm: Number(r.largura_perfil_quadro_mm) || 0,
        largura_perfil_puxador_mm: Number(r.largura_perfil_puxador_mm) || 0,
        desconto_adjacente_puxador_mm: Number(r.desconto_adjacente_puxador_mm) || 0,
        desconto_vertical_mm: Number(r.desconto_vertical_mm) || 0,
        desconto_horizontal_mm: Number(r.desconto_horizontal_mm) || 0,
        desconto_divisoria_mm: Number(r.desconto_divisoria_mm) || 0,
        desconto_vidro_lateral_mm: Number(r.desconto_vidro_lateral_mm) || 0,
        desconto_vidro_puxador_mm: Number(r.desconto_vidro_puxador_mm) || 0,
      };
    }
    onSaveRules(normalized);
  };

  return (
    <div className="p-6 lg:p-8 space-y-5">
      {/* Cabeçalho das Regras */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="max-w-3xl space-y-1">
          <div className="flex flex-wrap items-center gap-2.5">
            <h3 className="font-display font-normal text-base text-lider-ink">
              Regras de Corte e Descontos por Modelo (mm)
            </h3>
            {isDirty && (
              <span className="inline-flex items-center px-2 py-0.5 text-[11px] font-medium border border-lider-terracotta/50 bg-lider-terracotta/10 text-lider-terracotta rounded-[2px]">
                Alterações pendentes
              </span>
            )}
          </div>
          <p className="text-xs text-lider-slate leading-relaxed">
            Perfis: quando o puxador for mais largo que o quadro (ex.: Clear G = 80 vs 45 mm), desconta a diferença (35 mm) das barras adjacentes ao puxador. Vidros: informe o desconto por lado sem puxador (Lateral) e por lado com puxador (Puxador).
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 shrink-0">
          <button
            type="button"
            disabled={isSaving}
            onClick={onResetRules}
            className="h-10 px-4 bg-transparent hover:bg-lider-canvas border border-lider-border hover:border-lider-charcoal text-lider-charcoal text-xs font-medium rounded-[2px] inline-flex items-center gap-2 transition-colors disabled:opacity-45"
          >
            <RotateCcw className="w-3.5 h-3.5" strokeWidth={1.5} />
            Restaurar Padrão
          </button>
          <button
            type="button"
            disabled={isSaving}
            onClick={handleSaveClick}
            className="h-10 px-5 bg-lider-charcoal hover:bg-lider-ink text-white text-xs font-display uppercase tracking-[0.08em] font-medium rounded-[2px] inline-flex items-center gap-2 transition-colors disabled:opacity-45"
          >
            {isSaving ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" strokeWidth={1.5} />
            ) : (
              <Save className="w-3.5 h-3.5" strokeWidth={1.5} />
            )}
            Salvar e Recalcular
          </button>
        </div>
      </div>

      {/* Tabela Editável */}
      <div
        tabIndex={0}
        role="region"
        aria-labelledby="caption-regras"
        className="table-wrapper"
      >
        <table className="lider-table">
          <caption id="caption-regras" className="visually-hidden">
            Regras e descontos de corte por modelo
          </caption>
          <thead>
            <tr>
              <th>Modelo</th>
              <th>Descrição</th>
              <th>Tipo de Corte</th>
              <th className="num-header">Larg. Quadro (mm)</th>
              <th className="num-header">Larg. Puxador (mm)</th>
              <th className="num-header">Desc. Adj. Puxador (mm)</th>
              <th className="num-header">Desc. Fixo Vert. (mm)</th>
              <th className="num-header">Desc. Fixo Horiz. (mm)</th>
              <th className="num-header">Desc. Fixo Div. (mm)</th>
              <th className="num-header">Vidro: Lateral (mm/lado)</th>
              <th className="num-header">Vidro: Puxador (mm/lado)</th>
              <th>Observação</th>
            </tr>
          </thead>
          <tbody>
            {!sortedKeys.length ? (
              <tr>
                <td colSpan={12} className="empty-cell text-center py-12 text-lider-muted">
                  Carregando regras de corte...
                </td>
              </tr>
            ) : (
              sortedKeys.map((key) => {
                const r = draftRules[key];
                const inputCls =
                  "w-24 h-8 px-2 bg-lider-surface border border-lider-border rounded-[2px] text-right font-mono text-xs text-lider-ink tabular-nums focus:border-lider-wood focus:outline-none transition-colors";
                return (
                  <tr key={key}>
                    <th scope="row">
                      <span className="inline-flex items-center px-2 py-0.5 text-[11px] font-medium border border-lider-border bg-lider-canvas text-lider-charcoal rounded-[2px]">
                        {r.modelo}
                      </span>
                    </th>
                    <td className="min-w-[160px] text-xs text-lider-slate">
                      {r.descricao}
                    </td>
                    <td>
                      <select
                        value={r.tipo_corte}
                        onChange={(e) =>
                          handleFieldChange(key, "tipo_corte", e.target.value)
                        }
                        aria-label={`Tipo de corte para ${r.modelo}`}
                        className="h-8 px-2 bg-lider-surface border border-lider-border rounded-[2px] text-xs text-lider-ink focus:border-lider-wood focus:outline-none"
                      >
                        <option value="45°">45°</option>
                        <option value="90° (Topo)">90° (Topo)</option>
                        <option value="90° (Explícito)">90° (Explícito)</option>
                      </select>
                    </td>
                    <td className="num">
                      <input
                        type="number"
                        step="0.5"
                        min="0"
                        value={r.largura_perfil_quadro_mm ?? 0}
                        onChange={(e) =>
                          handleFieldChange(
                            key,
                            "largura_perfil_quadro_mm",
                            e.target.value
                          )
                        }
                        aria-label={`Largura do perfil quadro em mm para ${r.modelo}`}
                        className={inputCls}
                      />
                    </td>
                    <td className="num">
                      <input
                        type="number"
                        step="0.5"
                        min="0"
                        value={r.largura_perfil_puxador_mm ?? 0}
                        onChange={(e) =>
                          handleFieldChange(
                            key,
                            "largura_perfil_puxador_mm",
                            e.target.value
                          )
                        }
                        aria-label={`Largura do perfil puxador em mm para ${r.modelo}`}
                        className={inputCls}
                      />
                    </td>
                    <td className="num">
                      <input
                        type="number"
                        step="0.5"
                        min="0"
                        value={r.desconto_adjacente_puxador_mm ?? 0}
                        onChange={(e) =>
                          handleFieldChange(
                            key,
                            "desconto_adjacente_puxador_mm",
                            e.target.value
                          )
                        }
                        aria-label={`Desconto adjacente ao puxador em mm para ${r.modelo}`}
                        className={inputCls}
                      />
                    </td>
                    <td className="num">
                      <input
                        type="number"
                        step="0.5"
                        value={r.desconto_vertical_mm ?? 0}
                        onChange={(e) =>
                          handleFieldChange(key, "desconto_vertical_mm", e.target.value)
                        }
                        aria-label={`Desconto fixo vertical em mm para ${r.modelo}`}
                        className={inputCls}
                      />
                    </td>
                    <td className="num">
                      <input
                        type="number"
                        step="0.5"
                        value={r.desconto_horizontal_mm ?? 0}
                        onChange={(e) =>
                          handleFieldChange(
                            key,
                            "desconto_horizontal_mm",
                            e.target.value
                          )
                        }
                        aria-label={`Desconto fixo horizontal em mm para ${r.modelo}`}
                        className={inputCls}
                      />
                    </td>
                    <td className="num">
                      <input
                        type="number"
                        step="0.5"
                        value={r.desconto_divisoria_mm ?? 0}
                        onChange={(e) =>
                          handleFieldChange(
                            key,
                            "desconto_divisoria_mm",
                            e.target.value
                          )
                        }
                        aria-label={`Desconto fixo divisória em mm para ${r.modelo}`}
                        className={inputCls}
                      />
                    </td>
                    <td className="num">
                      <input
                        type="number"
                        step="0.5"
                        min="0"
                        value={r.desconto_vidro_lateral_mm ?? 0}
                        onChange={(e) =>
                          handleFieldChange(
                            key,
                            "desconto_vidro_lateral_mm",
                            e.target.value
                          )
                        }
                        aria-label={`Desconto vidro lateral em mm por lado para ${r.modelo}`}
                        className={inputCls}
                      />
                    </td>
                    <td className="num">
                      <input
                        type="number"
                        step="0.5"
                        min="0"
                        value={r.desconto_vidro_puxador_mm ?? 0}
                        onChange={(e) =>
                          handleFieldChange(
                            key,
                            "desconto_vidro_puxador_mm",
                            e.target.value
                          )
                        }
                        aria-label={`Desconto vidro lado puxador em mm por lado para ${r.modelo}`}
                        className={inputCls}
                      />
                    </td>
                    <td className="min-w-[200px] text-xs text-lider-muted">
                      {r.observacao || ""}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
