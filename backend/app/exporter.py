"""Exportação de itens construtivos e plano de corte para XLSX, CSV e JSON."""

from __future__ import annotations

import io
import json
from typing import Any, Dict, List

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


def _flatten_items_for_table(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for it in items:
        divs = it.get("divisorias_mm") or []
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


def export_to_xlsx_bytes(
    items: List[Dict[str, Any]],
    detailed_bars: List[Dict[str, Any]],
    grouped_bars: List[Dict[str, Any]],
) -> bytes:
    """Gera pasta de trabalho Excel multi-abas formatada em memória."""
    df_items = pd.DataFrame(_flatten_items_for_table(items))
    df_bars = pd.DataFrame(detailed_bars)
    df_grouped = pd.DataFrame(grouped_bars)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_items.to_excel(writer, sheet_name="Itens_Construcao", index=False)
        df_bars.to_excel(writer, sheet_name="Lista_Corte_Barras", index=False)
        df_grouped.to_excel(writer, sheet_name="Resumo_Corte_Serra", index=False)

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
    mode: str = "items",
) -> bytes:
    """Exporta itens ou resumo de corte em CSV (; UTF-8 BOM para Excel PT-BR)."""
    if mode == "corte":
        df = pd.DataFrame(grouped_bars)
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
) -> bytes:
    payload = {
        "meta": meta,
        "kpis": kpis,
        "items": items,
        "corte_detalhado": detailed_bars,
        "corte_agrupado": grouped_bars,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
