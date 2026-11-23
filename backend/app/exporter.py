"""Exportação de itens construtivos, corte de perfis e corte de vidros para XLSX, CSV e JSON."""

from __future__ import annotations

import io
import json
from typing import Any, Dict, List, Optional

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


def _flatten_items_for_table(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for it in items:
        divs = it.get("divisorias_mm") or []
        vidros = it.get("vidros_corte") or []
        v0 = vidros[0] if vidros else {}
        rows.append(
            {
                "OP": it.get("op"),
                "Codigo": it.get("codigo"),
                "Pedido": it.get("pedido"),
                "Item_Pedido": it.get("item_pedido"),
                "Data_Abertura": it.get("data_abertura"),
                "Data_Entrega": it.get("data_entrega"),
                "Ambiente": it.get("ambiente"),
                "Categoria": it.get("categoria"),
                "Subcategoria": it.get("subcategoria"),
                "Modelo": it.get("modelo"),
                "Subtipo_Modelo": it.get("subtipo_modelo"),
                "Codigo_Perfil": it.get("codigo_perfil"),
                "Quantidade_OP": it.get("quantidade"),
                "Estruturas_Escadas": it.get("qtd_estruturas"),
                "Largura_mm": it.get("largura_mm"),
                "Altura_mm": it.get("altura_mm"),
                "Linear_mm": it.get("medida_linear_mm"),
                "Vidro_Largura_Corte_mm": v0.get("largura_corte_mm"),
                "Vidro_Altura_Corte_mm": v0.get("altura_corte_mm"),
                "Lado": it.get("lado"),
                "Folha": it.get("posicao_folha"),
                "Tem_Puxador": "Sim" if it.get("tem_puxador") else "Não",
                "Qtd_Puxadores": it.get("qtd_puxadores"),
                "Posicao_Puxador": it.get("posicao_puxador"),
                "Tipo_Puxador": it.get("tipo_puxador"),
                "Tem_Divisorias": "Sim" if it.get("tem_divisorias") else "Não",
                "Qtd_Divisorias": it.get("qtd_divisorias"),
                "Posicoes_Divisorias_mm": ", ".join(f"{d:g}" for d in divs),
                "Detalhe_Divisorias": it.get("detalhe_divisorias"),
                "Acabamento_Perfil": it.get("acabamento_perfil"),
                "Acabamento_Placa": it.get("acabamento_placa"),
                "Sistema": it.get("sistema"),
                "Furacao": it.get("furacao"),
                "Especial": "Sim" if it.get("eh_especial") else "Não",
                "Descricao_Original": it.get("descricao"),
            }
        )
    return rows


def _flatten_scenario_bars(
    bar_opt: Optional[Dict[str, Any]],
    scenario_id: str,
) -> List[Dict[str, Any]]:
    barras = (
        (bar_opt or {})
        .get("cenarios", {})
        .get(scenario_id, {})
        .get("barras_flat")
        or []
    )
    rows: List[Dict[str, Any]] = []
    for b in barras:
        rows.append(
            {
                "Barra_Global": b.get("barra_global_numero"),
                "Grupo": b.get("grupo_nome"),
                "Origem_Agrupamento": b.get("origem_agrupamento"),
                "Codigo_Perfil": b.get("codigo_perfil") or "",
                "Barra_Grupo": b.get("barra_numero"),
                "Comprimento_Barra_mm": b.get("comprimento_barra_mm"),
                "Qtd_Pecas": b.get("qtd_pecas"),
                "Medidas_Distintas": b.get("medidas_distintas_barra", 0),
                "Soma_Pecas_mm": b.get("soma_pecas_mm"),
                "Perda_Serra_Desponte_mm": b.get("perda_serra_desponte_mm"),
                "Perda_mm": b.get("perda_mm"),
                "Perda_cm": b.get("perda_cm"),
                "Aproveitamento_pct": b.get("aproveitamento_pct"),
                "Troca_Entrada": "Sim" if b.get("troca_entrada") else "Não",
                "Ajustes_Internos": b.get("ajustes_internos", 0),
                "Ajustes_Barra": b.get("ajustes_barra", 0),
                "Angulos_Barra": b.get("angulos_resumo") or "",
                "Trocas_Angulo_Barra": b.get("trocas_angulo_barra", 0),
                "Perfil_Simetrico": "Sim (//)" if b.get("perfil_simetrico") else "Não (\\/)",
                "Cortes_Paralelos": b.get("cortes_paralelos_qtd", 0),
                "Cortes_V": b.get("cortes_v_qtd", 0),
                "Economia_Chanfro_mm": b.get("economia_chanfro_mm", 0.0),
                "Sequencia_Corte": b.get("sequencia_corte") or b.get("padrao_corte"),
                "OPs": b.get("ops"),
            }
        )
    return rows


def _flatten_tempo_roteiro(
    bar_opt: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    steps = (
        (bar_opt or {})
        .get("cenarios", {})
        .get("tempo_execucao", {})
        .get("roteiro_flat")
        or []
    )
    rows: List[Dict[str, Any]] = []
    for step in steps:
        for alloc in step.get("alocacoes") or []:
            alloc_pcs = alloc.get("pecas") or []
            alloc_sim = bool(alloc_pcs) and all(
                bool(p.get("perfil_simetrico")) for p in alloc_pcs
            )
            rows.append(
                {
                    "Grupo": step.get("grupo_nome"),
                    "Codigo_Perfil": step.get("codigo_perfil") or "",
                    "Perfil_Simetrico": "Sim (//)" if alloc_sim else "Não (\\/)",
                    "Passo": step.get("passo"),
                    "Tipo_Passo": "Drenagem cavalete" if step.get("eh_drenagem") else "Lote principal",
                    "Troca_Medida": "Sim" if step.get("troca_medida") else "Não",
                    "Troca_Angulo": "Sim" if step.get("troca_angulo") else "Não",
                    "Trocas_Angulo_Passo": step.get("trocas_angulo_passo", 0),
                    "Medida_Corte_mm": step.get("medida_corte_mm"),
                    "Angulos_Corte": alloc.get("angulos_corte") or step.get("angulos_corte") or "",
                    "Origem_Barra": alloc.get("origem_barra"),
                    "Vaga_Cavalete": alloc.get("vaga_cavalete") or "",
                    "Acao_Cavalete": alloc.get("acao_cavalete") or "",
                    "Ocupacao_Cavalete": step.get("cavalete_ocupacao", 0),
                    "Barra_Grupo": alloc.get("barra_numero"),
                    "Barra_Global": alloc.get("barra_global_numero"),
                    "Qtd_Cortes": alloc.get("qtd_cortes"),
                    "Sobra_Antes_mm": alloc.get("sobra_antes_mm"),
                    "Sobra_Depois_mm": alloc.get("sobra_depois_mm"),
                    "OPs": alloc.get("ops"),
                }
            )
    return rows


def _flatten_scenario_comparison(
    bar_opt: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    cenarios = (bar_opt or {}).get("cenarios") or {}
    mat_groups = cenarios.get("material", {}).get("grupos") or []
    tmp_groups_by_key = {
        g["grupo_key"]: g for g in (cenarios.get("tempo_execucao", {}).get("grupos") or [])
    }
    rows: List[Dict[str, Any]] = []
    for gm in mat_groups:
        gt = tmp_groups_by_key.get(gm["grupo_key"], {})
        mat_bars = gm.get("qtd_barras", 0)
        tmp_bars = gt.get("qtd_barras", 0)
        mat_adj = gm.get("ajustes_corte", 0)
        tmp_adj = gt.get("ajustes_corte", 0)
        mat_ang = gm.get("trocas_angulo", 0)
        tmp_ang = gt.get("trocas_angulo", 0)
        rows.append(
            {
                "Grupo": gm.get("grupo_nome"),
                "Origem_Agrupamento": gm.get("origem_agrupamento"),
                "Codigo_Perfil": gm.get("codigo_perfil") or "",
                "Qtd_Pecas": gm.get("total_pecas_alocadas", 0),
                "Material_Barras": mat_bars,
                "Material_Aproveitamento_pct": gm.get("aproveitamento_medio_pct", 0.0),
                "Material_Perda_mm": gm.get("total_perda_mm", 0.0),
                "Material_Ajustes": mat_adj,
                "Material_Trocas_Angulo": mat_ang,
                "Material_Economia_Chanfro_mm": gm.get("economia_chanfro_mm", 0.0),
                "Material_Barras_4_Mais_Medidas": gm.get("barras_complexas_qtd", 0),
                "Tempo_Barras": tmp_bars,
                "Tempo_Aproveitamento_pct": gt.get("aproveitamento_medio_pct", 0.0),
                "Tempo_Perda_mm": gt.get("total_perda_mm", 0.0),
                "Tempo_Ajustes": tmp_adj,
                "Tempo_Trocas_Angulo": tmp_ang,
                "Tempo_Economia_Chanfro_mm": gt.get("economia_chanfro_mm", 0.0),
                "Tempo_Retomadas_Sobras": gt.get("retomadas_sobras", 0),
                "Tempo_Pico_Sobras_Cavalete": gt.get("pico_sobras_simultaneas", 0),
                "Diff_Barras": tmp_bars - mat_bars,
                "Reducao_Ajustes": mat_adj - tmp_adj,
                "Reducao_Trocas_Angulo": mat_ang - tmp_ang,
            }
        )
    return rows


def export_to_xlsx_bytes(
    items: List[Dict[str, Any]],
    detailed_bars: List[Dict[str, Any]],
    grouped_bars: List[Dict[str, Any]],
    detailed_glasses: Optional[List[Dict[str, Any]]] = None,
    grouped_glasses: Optional[List[Dict[str, Any]]] = None,
    bar_optimization: Optional[Dict[str, Any]] = None,
) -> bytes:
    """Gera pasta de trabalho Excel multi-abas formatada em memória."""
    df_items = pd.DataFrame(_flatten_items_for_table(items))
    df_bars = pd.DataFrame(detailed_bars)
    df_grouped = pd.DataFrame(grouped_bars)
    df_glass_det = pd.DataFrame(detailed_glasses or [])
    df_glass_grp = pd.DataFrame(grouped_glasses or [])
    df_opt_mat = pd.DataFrame(_flatten_scenario_bars(bar_optimization, "material"))
    df_opt_rot = pd.DataFrame(_flatten_tempo_roteiro(bar_optimization))
    df_opt_tmp = pd.DataFrame(_flatten_scenario_bars(bar_optimization, "tempo_execucao"))
    df_opt_cmp = pd.DataFrame(_flatten_scenario_comparison(bar_optimization))

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_items.to_excel(writer, sheet_name="Itens_Construcao", index=False)
        df_bars.to_excel(writer, sheet_name="Lista_Corte_Barras", index=False)
        df_grouped.to_excel(writer, sheet_name="Resumo_Corte_Serra", index=False)
        df_glass_det.to_excel(writer, sheet_name="Lista_Corte_Vidros", index=False)
        df_glass_grp.to_excel(writer, sheet_name="Resumo_Corte_Vidros", index=False)
        df_opt_mat.to_excel(writer, sheet_name="Otimizacao_Material", index=False)
        df_opt_rot.to_excel(writer, sheet_name="Otimizacao_Tempo_Roteiro", index=False)
        df_opt_tmp.to_excel(writer, sheet_name="Otimizacao_Tempo_Barras", index=False)
        df_opt_cmp.to_excel(writer, sheet_name="Otimizacao_Comparativo", index=False)

        wb = writer.book
        header_fill = PatternFill(
            start_color="1E293B", end_color="1E293B", fill_type="solid"
        )
        header_font = Font(color="FFFFFF", bold=True, size=10)

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            ws.freeze_panes = "A2"
            if ws.max_row >= 1:
                ws.auto_filter.ref = ws.dimensions
                for cell in ws[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal="center", vertical="center")
            for col_idx, column_cells in enumerate(ws.columns, start=1):
                max_len = max(
                    (len(str(c.value)) if c.value is not None else 0)
                    for c in column_cells
                )
                ws.column_dimensions[get_column_letter(col_idx)].width = min(
                    max(max_len + 3, 12), 52
                )

    buffer.seek(0)
    return buffer.getvalue()


def export_to_csv_bytes(
    items: List[Dict[str, Any]],
    grouped_bars: List[Dict[str, Any]],
    grouped_glasses: Optional[List[Dict[str, Any]]] = None,
    bar_optimization: Optional[Dict[str, Any]] = None,
    mode: str = "items",
) -> bytes:
    """Exporta itens, resumo de corte, vidros ou cenários de otimização em CSV (; UTF-8 BOM)."""
    if mode == "corte":
        df = pd.DataFrame(grouped_bars)
    elif mode == "vidro":
        df = pd.DataFrame(grouped_glasses or [])
    elif mode in ("otimizacao_material", "otimizacao_barras"):
        df = pd.DataFrame(_flatten_scenario_bars(bar_optimization, "material"))
    elif mode == "otimizacao_tempo_roteiro":
        df = pd.DataFrame(_flatten_tempo_roteiro(bar_optimization))
    elif mode in ("otimizacao_tempo_barras", "otimizacao_tempo"):
        df = pd.DataFrame(_flatten_scenario_bars(bar_optimization, "tempo_execucao"))
    else:
        df = pd.DataFrame(_flatten_items_for_table(items))

    csv_text = df.to_csv(index=False, sep=";")
    return ("\ufeff" + csv_text).encode("utf-8")


def export_to_json_bytes(
    meta: Dict[str, Any],
    kpis: Dict[str, Any],
    items: List[Dict[str, Any]],
    detailed_bars: List[Dict[str, Any]],
    grouped_bars: List[Dict[str, Any]],
    detailed_glasses: Optional[List[Dict[str, Any]]] = None,
    grouped_glasses: Optional[List[Dict[str, Any]]] = None,
    bar_optimization: Optional[Dict[str, Any]] = None,
) -> bytes:
    payload = {
        "meta": meta,
        "kpis": kpis,
        "items": items,
        "corte_detalhado": detailed_bars,
        "corte_agrupado": grouped_bars,
        "vidro_detalhado": detailed_glasses or [],
        "vidro_agrupado": grouped_glasses or [],
        "otimizacao_barras": bar_optimization or {},
    }
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
