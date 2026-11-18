"""Parser estruturado do HTML retornado por /pcp/op_abertura.php."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import List, Optional


ROW_PATTERN = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL | re.IGNORECASE)
CELL_PATTERN = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL | re.IGNORECASE)
TAG_STRIP_PATTERN = re.compile(r"<[^>]+>")
WHITESPACE_PATTERN = re.compile(r"\s+")

LOCAL_PATTERN = re.compile(
    r"LOCAL\s+DE\s+PRODU(?:Ç|C)[ÃA]O\s*=\s*<b>(.*?)</b>",
    re.IGNORECASE | re.DOTALL,
)
DATA_ABERTURA_PATTERN = re.compile(
    r"DATA\s+DE\s+ABERTURA\s*=\s*<b>(.*?)</b>",
    re.IGNORECASE | re.DOTALL,
)
DELIVERY_SPLIT_PATTERN = re.compile(
    r"<b>\s*Data\s+de\s+Entrega\s+([^:<]+?):?\s*</b>",
    re.IGNORECASE,
)
SUMMARY_DIA_PATTERN = re.compile(r"Dia\s+\d{2}/\d{2}/\d{4}", re.IGNORECASE)
PREFIX_SUMMARY_TOKEN = re.compile(r"^\d+-[A-Z0-9]+,$", re.IGNORECASE)


@dataclass
class RawOpRow:
    """Representa uma linha bruta de item extraída do HTML do PCP."""

    local_producao: str
    data_abertura: str
    data_entrega: str
    codigo: str
    descricao: str
    quantidade: float
    op: str
    observacao: str
    pedido: str
    item_pedido: str
    ambiente: str
    valor_insumos: Optional[float]
    valor_mp: Optional[float]


def _clean_cell(raw_html: str) -> str:
    text = TAG_STRIP_PATTERN.sub(" ", raw_html)
    text = html.unescape(text)
    return WHITESPACE_PATTERN.sub(" ", text).strip()


def _parse_br_float(value: str) -> Optional[float]:
    cleaned = (value or "").strip()
    if not cleaned:
        return None
    normalized = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return None


def _is_non_item_row(cells: List[str]) -> bool:
    if not cells or not any(cells):
        return True

    first = cells[0].strip()
    first_upper = first.upper()

    if "LOCAL DE PRODU" in first_upper or "DATA DE ABERTURA" in first_upper:
        return True

    if SUMMARY_DIA_PATTERN.search(first):
        return True

    if (
        first_upper.startswith("HORAS:")
        or first_upper.startswith("INSUMOS:")
        or first_upper.startswith("MP:")
    ):
        return True

    # Tabela de contagem de prefixos no rodapé (ex.: '1-2PEALUI,', '3-2PTAC48,')
    non_empty = [c for c in cells if c]
    if non_empty and all(
        c.endswith(",") or bool(PREFIX_SUMMARY_TOKEN.match(c)) for c in non_empty
    ):
        return True

    # Um registro de item válido tem pelo menos código, descrição, quantidade e OP
    if len(cells) < 4:
        return True

    return False


def parse_op_html(html_content: str) -> tuple[dict[str, str], list[RawOpRow]]:
    """Extrai metadados de cabeçalho e todas as linhas de OP do HTML do PCP."""
    local_match = LOCAL_PATTERN.search(html_content)
    data_match = DATA_ABERTURA_PATTERN.search(html_content)

    local_producao = _clean_cell(local_match.group(1)) if local_match else ""
    data_abertura = _clean_cell(data_match.group(1)) if data_match else ""

    parts = DELIVERY_SPLIT_PATTERN.split(html_content)
    sections: list[tuple[str, str]] = []
    if len(parts) == 1:
        sections.append(("", parts[0]))
    else:
        sections.append(("", parts[0]))
        for idx in range(1, len(parts), 2):
            delivery_date = _clean_cell(parts[idx])
            section_html = parts[idx + 1] if idx + 1 < len(parts) else ""
            sections.append((delivery_date, section_html))

    rows: list[RawOpRow] = []

    for delivery_date, section_html in sections:
        for tr_match in ROW_PATTERN.finditer(section_html):
            tr_html = tr_match.group(1)
            raw_cells = CELL_PATTERN.findall(tr_html)
            cells = [_clean_cell(td) for td in raw_cells]

            if _is_non_item_row(cells):
                continue

            codigo = cells[0] if len(cells) > 0 else ""
            descricao = cells[1] if len(cells) > 1 else ""
            qtd_raw = cells[2] if len(cells) > 2 else "0"
            op = cells[3] if len(cells) > 3 else ""
            observacao = cells[4] if len(cells) > 4 else ""
            pedido = cells[5] if len(cells) > 5 else ""
            item_pedido = cells[6] if len(cells) > 6 else ""
            ambiente = cells[7] if len(cells) > 7 else ""
            insumos_raw = cells[8] if len(cells) > 8 else ""
            mp_raw = cells[9] if len(cells) > 9 else ""

            if not codigo or not descricao:
                continue

            quantidade = _parse_br_float(qtd_raw)
            if quantidade is None:
                quantidade = 1.0

            rows.append(
                RawOpRow(
                    local_producao=local_producao,
                    data_abertura=data_abertura,
                    data_entrega=delivery_date,
                    codigo=codigo,
                    descricao=descricao,
                    quantidade=quantidade,
                    op=op,
                    observacao=observacao,
                    pedido=pedido,
                    item_pedido=item_pedido,
                    ambiente=ambiente,
                    valor_insumos=_parse_br_float(insumos_raw),
                    valor_mp=_parse_br_float(mp_raw),
                )
            )

    meta = {
        "local_producao": local_producao,
        "data_abertura": data_abertura,
        "total_linhas": len(rows),
    }
    return meta, rows
