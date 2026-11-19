import React, { useEffect, useRef } from "react";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { fmtNum } from "../utils/formatters";

function PieceDiagramSvg({ item }) {
  const w = Number(item.largura_mm) || 400;
  const h = Number(item.altura_mm) || (item.eh_barra_avulsa ? 60 : 800);

  const maxW = 220;
  const maxH = 260;
  const scale = Math.min(maxW / w, maxH / h);
  const drawW = Math.max(44, Math.round(w * scale));
  const drawH = Math.max(26, Math.round(h * scale));

  const padX = 72;
  const padY = 44;
  const svgW = drawW + padX * 2;
  const svgH = drawH + padY * 2;

  const puxColor = "#8B5A2B";
  const divColor = "#A0522D";
  const frameColor = "#222222";

  const handleLines = [];
  if (item.tem_puxador) {
    if (
      item.posicao_puxador === "SUPERIOR" ||
      item.posicao_puxador === "HORIZONTAL (BASCULA/GAVETA)"
    ) {
      handleLines.push({ x1: padX, y1: padY, x2: padX + drawW, y2: padY });
    } else if (item.posicao_puxador === "DUPLO (DIREITA E ESQUERDA)") {
      handleLines.push(
        { x1: padX, y1: padY, x2: padX, y2: padY + drawH },
        { x1: padX + drawW, y1: padY, x2: padX + drawW, y2: padY + drawH }
      );
    } else if (item.lado === "DIREITA") {
      handleLines.push({
        x1: padX + drawW,
        y1: padY,
        x2: padX + drawW,
        y2: padY + drawH,
      });
    } else {
      handleLines.push({ x1: padX, y1: padY, x2: padX, y2: padY + drawH });
    }
  }

  const dividers = (item.divisorias_mm || [])
    .map((posMm) => {
      const y = padY + drawH - (posMm / h) * drawH;
      if (y < padY || y > padY + drawH) return null;
      return { posMm, y };
    })
    .filter(Boolean);

  return (
    <div className="space-y-3">
      <div className="border border-lider-border rounded-[2px] bg-lider-canvas p-4 flex items-center justify-center min-h-[320px]">
        <svg
          viewBox={`0 0 ${svgW} ${svgH}`}
          className="w-full max-w-[380px] h-auto text-lider-ink"
          role="img"
          aria-label={`Diagrama 2D proporcional da peça ${item.codigo} com ${fmtNum(w)} por ${fmtNum(h)} milímetros`}
        >
          {/* Fundo sutil da placa */}
          <rect
            x={padX}
            y={padY}
            width={drawW}
            height={drawH}
            fill="#FFFFFF"
            stroke={frameColor}
            strokeWidth="3.5"
          />

          {/* Divisórias internas */}
          {dividers.map((d, i) => (
            <g key={i}>
              <line
                x1={padX}
                y1={d.y}
                x2={padX + drawW}
                y2={d.y}
                stroke={divColor}
                strokeWidth="2.5"
                strokeDasharray="4 2"
              />
              <text
                x={padX + drawW + 8}
                y={d.y + 4}
                fontSize="10.5"
                fontFamily="JetBrains Mono, monospace"
                fill={divColor}
              >
                {fmtNum(d.posMm)}mm
              </text>
            </g>
          ))}

          {/* Puxadores */}
          {handleLines.map((line, i) => (
            <line
              key={i}
              x1={line.x1}
              y1={line.y1}
              x2={line.x2}
              y2={line.y2}
              stroke={puxColor}
              strokeWidth="7"
              strokeLinecap="square"
            />
          ))}

          {/* Cotas */}
          <text
            x={padX + drawW / 2}
            y={padY - 14}
            textAnchor="middle"
            fontSize="11.5"
            fontFamily="JetBrains Mono, monospace"
            fontWeight="500"
            fill={frameColor}
          >
            L: {fmtNum(w)} mm
          </text>
          <text
            x={padX - 10}
            y={padY + drawH / 2 + 4}
            textAnchor="end"
            fontSize="11.5"
            fontFamily="JetBrains Mono, monospace"
            fontWeight="500"
            fill={frameColor}
          >
            A: {fmtNum(h)} mm
          </text>
        </svg>
      </div>

      {/* Legenda arquitetônica */}
      <div className="flex flex-wrap items-center gap-4 text-[11px] text-lider-slate">
        <span className="inline-flex items-center gap-1.5">
          <span className="w-3 h-1 bg-lider-charcoal inline-block" /> Quadro ({item.modelo})
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-3 h-1.5 bg-lider-wood inline-block" /> Perfil Puxador
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-lider-terracotta inline-block" /> Divisória Interna
        </span>
      </div>
    </div>
  );
}

export default function PieceDetailDialog({
  item,
  items = [],
  onSelectItem,
  onClose,
}) {
  const dialogRef = useRef(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (item && !dialog.open) {
      dialog.showModal();
    } else if (!item && dialog.open) {
      dialog.close();
    }
  }, [item]);

  // Fallback para navegadores sem suporte a closedby="any"
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog || "closedBy" in HTMLDialogElement.prototype) return;

    const handleBackdropClick = (event) => {
      if (event.target !== dialog) return;
      const rect = dialog.getBoundingClientRect();
      const inside =
        rect.top <= event.clientY &&
        event.clientY <= rect.top + rect.height &&
        rect.left <= event.clientX &&
        event.clientX <= rect.left + rect.width;
      if (!inside) {
        dialog.close();
      }
    };

    dialog.addEventListener("click", handleBackdropClick);
    return () => dialog.removeEventListener("click", handleBackdropClick);
  }, []);

  const currentIdx = item ? items.indexOf(item) : -1;
  const hasPrev = currentIdx > 0;
  const hasNext = currentIdx >= 0 && currentIdx < items.length - 1;

  const specs = item
    ? [
        [
          "Modelo / Perfil",
          `${item.modelo} ${item.codigo_perfil ? `(${item.codigo_perfil})` : ""}`,
        ],
        [
          "Quantidade OP",
          `${fmtNum(item.quantidade)} · Estruturas/Escadas: ${item.qtd_estruturas}`,
        ],
        ["Medidas", `${fmtNum(item.largura_mm)} × ${fmtNum(item.altura_mm)} mm`],
        ["Lado / Folha", `${item.lado} · ${item.posicao_folha}`],
        [
          "Puxadores",
          `${item.qtd_puxadores}x · ${item.posicao_puxador} ${
            item.tipo_puxador ? `(${item.tipo_puxador})` : ""
          }`,
        ],
        [
          "Divisórias",
          item.tem_divisorias ? item.detalhe_divisorias : "Sem divisórias",
        ],
        ["Acabamento Perfil", item.acabamento_perfil || "-"],
        ["Acabamento Placa", item.acabamento_placa || "-"],
        ["Sistema / Furação", `${item.sistema || "-"} · ${item.furacao || "-"}`],
      ]
    : [];

  return (
    <dialog
      ref={dialogRef}
      id="detail-dialog"
      closedby="any"
      aria-labelledby="dialog-title"
      onClose={onClose}
      className="lider-dialog"
    >
      {item && (
        <div>
          {/* Cabeçalho fixo do modal */}
          <div className="sticky top-0 z-10 bg-lider-surface border-b border-lider-border px-6 py-4 flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
              <h2
                id="dialog-title"
                className="font-display font-normal text-lg text-lider-ink"
              >
                {item.codigo} · OP {item.op}
              </h2>
              <p className="text-xs text-lider-slate mt-0.5">
                {item.categoria} ({item.modelo}) · Pedido {item.pedido} · Entrega{" "}
                {item.data_entrega}
              </p>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              {items.length > 1 && (
                <div className="inline-flex items-center gap-1 mr-1">
                  <button
                    type="button"
                    disabled={!hasPrev}
                    onClick={() => hasPrev && onSelectItem(items[currentIdx - 1])}
                    aria-label="Peça anterior"
                    className="h-8 px-2.5 border border-lider-border rounded-[2px] text-xs text-lider-charcoal hover:bg-lider-canvas disabled:opacity-35 disabled:cursor-not-allowed inline-flex items-center gap-1"
                  >
                    <ChevronLeft className="w-3.5 h-3.5" strokeWidth={1.5} />
                    Anterior
                  </button>
                  <button
                    type="button"
                    disabled={!hasNext}
                    onClick={() => hasNext && onSelectItem(items[currentIdx + 1])}
                    aria-label="Próxima peça"
                    className="h-8 px-2.5 border border-lider-border rounded-[2px] text-xs text-lider-charcoal hover:bg-lider-canvas disabled:opacity-35 disabled:cursor-not-allowed inline-flex items-center gap-1"
                  >
                    Próxima
                    <ChevronRight className="w-3.5 h-3.5" strokeWidth={1.5} />
                  </button>
                </div>
              )}

              <form method="dialog">
                <button
                  type="submit"
                  aria-label="Fechar janela"
                  className="h-8 px-3 border border-lider-border rounded-[2px] text-xs font-medium text-lider-charcoal hover:border-lider-charcoal hover:bg-lider-canvas inline-flex items-center gap-1.5 transition-colors"
                >
                  <span>Fechar</span>
                  <X className="w-3.5 h-3.5" strokeWidth={1.5} />
                </button>
              </form>
            </div>
          </div>

          {/* Corpo do modal */}
          <div className="p-6 lg:p-8 grid grid-cols-1 lg:grid-cols-[minmax(280px,380px)_1fr] gap-8">
            {/* Esquema 2D */}
            <div>
              <h3 className="font-display text-xs uppercase tracking-[0.1em] text-lider-muted font-medium mb-3">
                Esquema 2D Proporcional
              </h3>
              <PieceDiagramSvg item={item} />
            </div>

            {/* Especificações e listas de corte */}
            <div className="space-y-6 min-w-0">
              <div>
                <h3 className="font-display text-xs uppercase tracking-[0.1em] text-lider-muted font-medium mb-3">
                  Especificação Extraída
                </h3>
                <dl className="grid grid-cols-1 sm:grid-cols-[150px_1fr] gap-x-4 gap-y-2 text-xs border border-lider-border rounded-[2px] p-4 bg-lider-canvas/50">
                  {specs.map(([k, v]) => (
                    <React.Fragment key={k}>
                      <dt className="text-lider-muted font-medium">{k}</dt>
                      <dd className="text-lider-ink m-0">{v}</dd>
                    </React.Fragment>
                  ))}
                </dl>
              </div>

              <div>
                <h3 className="font-display text-xs uppercase tracking-[0.1em] text-lider-muted font-medium mb-2.5">
                  Barras para Corte
                </h3>
                <div className="border border-lider-border rounded-[2px] overflow-x-auto">
                  <table className="lider-table">
                    <thead>
                      <tr>
                        <th>Função</th>
                        <th className="num-header">Qtd</th>
                        <th className="num-header">Nominal</th>
                        <th className="num-header">Desc.</th>
                        <th className="num-header">Corte (mm)</th>
                        <th>Obs.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(item.barras_corte || []).map((b, i) => (
                        <tr key={i}>
                          <td>{b.funcao_barra}</td>
                          <td className="num font-medium">{b.qtd_barras}</td>
                          <td className="num">{fmtNum(b.medida_nominal_mm)}</td>
                          <td className="num text-lider-wood">
                            {fmtNum(b.desconto_mm)}
                          </td>
                          <td className="num font-medium">
                            {fmtNum(b.medida_corte_mm)}
                          </td>
                          <td className="text-xs text-lider-slate">
                            {b.observacao_corte || "-"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <h3 className="font-display text-xs uppercase tracking-[0.1em] text-lider-muted font-medium mb-2.5">
                  Vidro / Placa para Corte
                </h3>
                <div className="border border-lider-border rounded-[2px] overflow-x-auto">
                  <table className="lider-table">
                    <thead>
                      <tr>
                        <th>Acabamento</th>
                        <th className="num-header">Qtd</th>
                        <th className="num-header">Larg. Corte</th>
                        <th className="num-header">Alt. Corte</th>
                        <th>Descontos (L / A)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(item.vidros_corte || []).length ? (
                        item.vidros_corte.map((g, i) => (
                          <tr key={i}>
                            <td>{g.acabamento_placa}</td>
                            <td className="num font-medium">{g.qtd_pecas}</td>
                            <td className="num font-medium">
                              {fmtNum(g.largura_corte_mm)} mm
                            </td>
                            <td className="num font-medium">
                              {fmtNum(g.altura_corte_mm)} mm
                            </td>
                            <td className="text-xs text-lider-slate">
                              L: -{fmtNum(g.desconto_largura_mm)} ({g.regra_largura}) · A: -
                              {fmtNum(g.desconto_altura_mm)} ({g.regra_altura})
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={5} className="text-center py-4 text-lider-muted">
                            Item sem placa/vidro para corte.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              <details className="border border-lider-border rounded-[2px] px-4 py-3 bg-lider-canvas/60 text-xs">
                <summary className="cursor-pointer font-medium text-lider-charcoal select-none">
                  Descrição original completa no ERP
                </summary>
                <p className="mt-2.5 text-lider-slate leading-relaxed font-mono text-[11px]">
                  {item.descricao}
                </p>
              </details>
            </div>
          </div>
        </div>
      )}
    </dialog>
  );
}
