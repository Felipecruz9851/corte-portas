"""Motor de cálculo de plano de corte de barras e perfis por modelo."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List

from app.description_parser import ExtractedItem

RULES_FILE = Path(__file__).parent / "data" / "regras_corte.json"


@dataclass
class CuttingRule:
    modelo: str
    descricao: str
    tipo_corte: str
    desconto_vertical_mm: float
    desconto_horizontal_mm: float
    desconto_divisoria_mm: float
    largura_perfil_quadro_mm: float = 0.0
    largura_perfil_puxador_mm: float = 0.0
    desconto_adjacente_puxador_mm: float = 0.0
    desconto_vidro_lateral_mm: float = 0.0
    desconto_vidro_puxador_mm: float = 0.0
    observacao: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CutGlass:
    """Representa uma peça/lote de vidro/placa a cortar para uma OP."""

    op: str
    codigo: str
    pedido: str
    data_entrega: str
    categoria: str
    modelo: str
    acabamento_placa: str
    posicao_puxador: str
    qtd_pecas: int
    largura_nominal_mm: float
    desconto_largura_mm: float
    largura_corte_mm: float
    regra_largura: str
    altura_nominal_mm: float
    desconto_altura_mm: float
    altura_corte_mm: float
    regra_altura: str

    @property
    def area_m2(self) -> float:
        return round(
            (self.qtd_pecas * self.largura_corte_mm * self.altura_corte_mm) / 1_000_000.0,
            4,
        )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["area_m2"] = self.area_m2
        return data


@dataclass
class CutBar:
    """Representa um grupo de barras idênticas a cortar para uma OP."""

    op: str
    codigo: str
    pedido: str
    data_entrega: str
    categoria: str
    modelo: str
    codigo_perfil: str
    acabamento_perfil: str
    funcao_barra: str
    orientacao: str
    eh_perfil_puxador: bool
    qtd_barras: int
    medida_nominal_mm: float
    desconto_mm: float
    medida_corte_mm: float
    tipo_corte: str
    observacao_corte: str = ""

    @property
    def total_mm(self) -> float:
        return round(self.qtd_barras * self.medida_corte_mm, 3)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["total_mm"] = self.total_mm
        data["total_metros"] = round(self.total_mm / 1000.0, 3)
        return data


def load_rules(path: Path = RULES_FILE) -> Dict[str, CuttingRule]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    rules: Dict[str, CuttingRule] = {}
    for key, val in raw.items():
        rules[key] = CuttingRule(**val)
    return rules


def save_rules(rules: Dict[str, CuttingRule], path: Path = RULES_FILE) -> None:
    payload = {k: v.to_dict() for k, v in rules.items()}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _safe_cut(nominal: float, discount: float) -> float:
    return round(max(0.0, nominal - discount), 3)


def _qty_int(item: ExtractedItem) -> int:
    try:
        q = int(round(item.quantidade))
        return max(1, q)
    except Exception:
        return 1


def compute_item_cuts(
    item: ExtractedItem, rules: Dict[str, CuttingRule]
) -> List[CutBar]:
    """Decompõe um item construtivo nas barras individuais de corte."""
    rule = rules.get(item.modelo) or rules["OUTRO"]
    op_qty = _qty_int(item)
    bars: List[CutBar] = []

    def add_bar(
        funcao: str,
        orientacao: str,
        eh_puxador: bool,
        qtd: int,
        nominal: float,
        desconto: float,
        obs: str = "",
    ) -> None:
        if qtd <= 0 or nominal <= 0:
            return
        bars.append(
            CutBar(
                op=item.op,
                codigo=item.codigo,
                pedido=item.pedido,
                data_entrega=item.data_entrega,
                categoria=item.categoria,
                modelo=item.modelo,
                codigo_perfil=item.codigo_perfil,
                acabamento_perfil=item.acabamento_perfil or "PADRAO",
                funcao_barra=funcao,
                orientacao=orientacao,
                eh_perfil_puxador=eh_puxador,
                qtd_barras=qtd,
                medida_nominal_mm=round(nominal, 3),
                desconto_mm=round(desconto, 3),
                medida_corte_mm=_safe_cut(nominal, desconto),
                tipo_corte=rule.tipo_corte,
                observacao_corte=obs,
            )
        )

    # 1) Barra linear avulsa
    if item.eh_barra_avulsa:
        med = item.medida_linear_mm or item.largura_mm or item.altura_mm or 0.0
        add_bar(
            funcao="Barra Linear Avulsa",
            orientacao="LINEAR",
            eh_puxador=False,
            qtd=op_qty * item.qtd_estruturas,
            nominal=med,
            desconto=0.0,
            obs="Corte avulso conforme descrição",
        )
        return bars

    # 2) Cristaleira Provence Urda (cortes explícitos de Mini Kendo + Baguete)
    if item.categoria == "CRISTALEIRA":
        med_h = item.corte_h_mm or item.largura_mm or 0.0
        med_v = item.corte_v_mm or item.altura_mm or 0.0
        add_bar(
            funcao="Horizontal Quadro (Mini Kendo + Baguete)",
            orientacao="HORIZONTAL",
            eh_puxador=False,
            qtd=2 * op_qty,
            nominal=med_h,
            desconto=rule.desconto_horizontal_mm,
        )
        add_bar(
            funcao="Vertical Quadro (Mini Kendo + Baguete)",
            orientacao="VERTICAL",
            eh_puxador=False,
            qtd=2 * op_qty,
            nominal=med_v,
            desconto=rule.desconto_vertical_mm,
        )
        return bars

    largura = item.largura_mm or 0.0
    altura = item.altura_mm or 0.0

    # 3) Linha ALLU: um quadro nas dimensões + divisórias internas
    if item.categoria == "LINHA ALLU":
        fator = op_qty * item.qtd_estruturas
        add_bar(
            funcao="Montante Vertical ALLU",
            orientacao="VERTICAL",
            eh_puxador=False,
            qtd=2 * fator,
            nominal=altura,
            desconto=rule.desconto_vertical_mm,
            obs=f"{item.qtd_estruturas} escada(s) x {op_qty} OP",
        )
        qtd_horiz_quadro = 1 if item.eh_formato_u else 2
        add_bar(
            funcao=(
                "Travessa Quadro ALLU (Formato U)"
                if item.eh_formato_u
                else "Travessa Quadro ALLU (Sup/Inf)"
            ),
            orientacao="HORIZONTAL",
            eh_puxador=False,
            qtd=qtd_horiz_quadro * fator,
            nominal=largura,
            desconto=rule.desconto_horizontal_mm,
        )
        if item.qtd_divisorias > 0:
            pos_str = ", ".join(f"{d:g}mm" for d in item.divisorias_mm)
            add_bar(
                funcao="Divisória Interna ALLU",
                orientacao="HORIZONTAL",
                eh_puxador=False,
                qtd=item.qtd_divisorias * fator,
                nominal=largura,
                desconto=rule.desconto_divisoria_mm,
                obs=f"Posições: {pos_str}" if pos_str else "",
            )
        return bars

    # 4) Portas, Frentes de Báscula, Gavetas, Passagem, Visor
    fator = op_qty
    adj_desc = rule.desconto_adjacente_puxador_mm
    div_adj_desc = 0.0

    def _join_obs(*parts: str) -> str:
        return " · ".join(p for p in parts if p)

    if item.qtd_puxadores == 0:
        add_bar(
            funcao="Vertical Quadro",
            orientacao="VERTICAL",
            eh_puxador=False,
            qtd=2 * fator,
            nominal=altura,
            desconto=rule.desconto_vertical_mm,
        )
        add_bar(
            funcao="Horizontal Quadro",
            orientacao="HORIZONTAL",
            eh_puxador=False,
            qtd=2 * fator,
            nominal=largura,
            desconto=rule.desconto_horizontal_mm,
        )
    elif item.qtd_puxadores == 2:
        add_bar(
            funcao="Vertical c/ Puxador (Dir/Esq)",
            orientacao="VERTICAL",
            eh_puxador=True,
            qtd=2 * fator,
            nominal=altura,
            desconto=rule.desconto_vertical_mm,
            obs=item.tipo_puxador,
        )
        horiz_desc = rule.desconto_horizontal_mm + (2.0 * adj_desc)
        div_adj_desc = 2.0 * adj_desc
        add_bar(
            funcao="Horizontal Quadro",
            orientacao="HORIZONTAL",
            eh_puxador=False,
            qtd=2 * fator,
            nominal=largura,
            desconto=horiz_desc,
            obs=f"-{2 * adj_desc:g}mm Adj. 2 Puxadores" if adj_desc > 0 else "",
        )
    elif item.posicao_puxador in ("SUPERIOR", "HORIZONTAL (BASCULA/GAVETA)"):
        add_bar(
            funcao="Horizontal c/ Puxador",
            orientacao="HORIZONTAL",
            eh_puxador=True,
            qtd=1 * fator,
            nominal=largura,
            desconto=rule.desconto_horizontal_mm,
            obs=item.tipo_puxador,
        )
        add_bar(
            funcao="Horizontal Quadro",
            orientacao="HORIZONTAL",
            eh_puxador=False,
            qtd=1 * fator,
            nominal=largura,
            desconto=rule.desconto_horizontal_mm,
        )
        vert_desc = rule.desconto_vertical_mm + adj_desc
        add_bar(
            funcao="Vertical Quadro",
            orientacao="VERTICAL",
            eh_puxador=False,
            qtd=2 * fator,
            nominal=altura,
            desconto=vert_desc,
            obs=f"-{adj_desc:g}mm Adj. Puxador Sup." if adj_desc > 0 else "",
        )
    else:
        # 1 puxador lateral (DIREITA ou ESQUERDA)
        add_bar(
            funcao=f"Vertical c/ Puxador ({item.lado})",
            orientacao="VERTICAL",
            eh_puxador=True,
            qtd=1 * fator,
            nominal=altura,
            desconto=rule.desconto_vertical_mm,
            obs=item.tipo_puxador,
        )
        add_bar(
            funcao="Vertical Quadro",
            orientacao="VERTICAL",
            eh_puxador=False,
            qtd=1 * fator,
            nominal=altura,
            desconto=rule.desconto_vertical_mm,
        )
        horiz_desc = rule.desconto_horizontal_mm + adj_desc
        div_adj_desc = adj_desc
        add_bar(
            funcao="Horizontal Quadro",
            orientacao="HORIZONTAL",
            eh_puxador=False,
            qtd=2 * fator,
            nominal=largura,
            desconto=horiz_desc,
            obs=f"-{adj_desc:g}mm Adj. Puxador Lat." if adj_desc > 0 else "",
        )

    if item.qtd_divisorias > 0:
        pos_str = ", ".join(f"{d:g}mm" for d in item.divisorias_mm)
        div_total_desc = rule.desconto_divisoria_mm + div_adj_desc
        adj_note = f"-{div_adj_desc:g}mm Adj. Puxador" if div_adj_desc > 0 else ""
        pos_note = f"Posições: {pos_str}" if pos_str else item.detalhe_divisorias
        add_bar(
            funcao="Travessa Divisória Interna",
            orientacao="HORIZONTAL",
            eh_puxador=False,
            qtd=item.qtd_divisorias * fator,
            nominal=largura,
            desconto=div_total_desc,
            obs=_join_obs(pos_note, adj_note),
        )

    return bars


def build_cutting_plan(
    items: List[ExtractedItem], rules: Dict[str, CuttingRule]
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Gera a lista detalhada de corte por OP e o resumo agrupado para serra."""
    detailed_bars: List[CutBar] = []
    for item in items:
        detailed_bars.extend(compute_item_cuts(item, rules))

    grouped: Dict[tuple, Dict[str, Any]] = {}
    for bar in detailed_bars:
        key = (
            bar.modelo,
            bar.acabamento_perfil,
            bar.funcao_barra,
            bar.orientacao,
            bar.eh_perfil_puxador,
            bar.medida_corte_mm,
            bar.tipo_corte,
        )
        if key not in grouped:
            grouped[key] = {
                "modelo": bar.modelo,
                "acabamento_perfil": bar.acabamento_perfil,
                "funcao_barra": bar.funcao_barra,
                "orientacao": bar.orientacao,
                "eh_perfil_puxador": bar.eh_perfil_puxador,
                "medida_corte_mm": bar.medida_corte_mm,
                "tipo_corte": bar.tipo_corte,
                "qtd_barras": 0,
                "total_mm": 0.0,
                "ops": set(),
            }
        entry = grouped[key]
        entry["qtd_barras"] += bar.qtd_barras
        entry["total_mm"] = round(entry["total_mm"] + bar.total_mm, 3)
        entry["ops"].add(bar.op)

    summary_list: List[Dict[str, Any]] = []
    for entry in grouped.values():
        ops_sorted = sorted(entry["ops"])
        summary_list.append(
            {
                "modelo": entry["modelo"],
                "acabamento_perfil": entry["acabamento_perfil"],
                "funcao_barra": entry["funcao_barra"],
                "orientacao": entry["orientacao"],
                "eh_perfil_puxador": entry["eh_perfil_puxador"],
                "medida_corte_mm": entry["medida_corte_mm"],
                "tipo_corte": entry["tipo_corte"],
                "qtd_barras": entry["qtd_barras"],
                "total_mm": entry["total_mm"],
                "total_metros": round(entry["total_mm"] / 1000.0, 3),
                "qtd_ops": len(ops_sorted),
                "ops": ", ".join(ops_sorted[:10])
                + (f" (+{len(ops_sorted) - 10})" if len(ops_sorted) > 10 else ""),
            }
        )

    summary_list.sort(
        key=lambda x: (
            x["modelo"],
            x["acabamento_perfil"],
            x["funcao_barra"],
            -x["medida_corte_mm"],
        )
    )

    return [b.to_dict() for b in detailed_bars], summary_list


def compute_item_glasses(
    item: ExtractedItem, rules: Dict[str, CuttingRule]
) -> List[CutGlass]:
    """Calcula a(s) medida(s) de corte do vidro/placa com base nos descontos por lado."""
    if item.categoria == "LINHA ALLU" or item.eh_barra_avulsa:
        return []

    largura_nom = item.largura_mm or 0.0
    altura_nom = item.altura_mm or 0.0
    if largura_nom <= 0 or altura_nom <= 0:
        return []

    rule = rules.get(item.modelo) or rules["OUTRO"]
    op_qty = _qty_int(item)
    lat = rule.desconto_vidro_lateral_mm
    pux = rule.desconto_vidro_puxador_mm
    acabamento = item.acabamento_placa or "NAO ESPECIFICADO"

    # Caso especial: Prateleira / Tampo Visor sem desconto configurado usa vidro explícito se houver
    if (
        item.categoria == "PRATELEIRA / TAMPO VISOR"
        and lat == 0.0
        and pux == 0.0
        and item.vidro_largura_mm
        and item.vidro_profundidade_mm
    ):
        desc_l = round(max(0.0, largura_nom - item.vidro_largura_mm), 3)
        desc_a = round(max(0.0, altura_nom - item.vidro_profundidade_mm), 3)
        return [
            CutGlass(
                op=item.op,
                codigo=item.codigo,
                pedido=item.pedido,
                data_entrega=item.data_entrega,
                categoria=item.categoria,
                modelo=item.modelo,
                acabamento_placa=acabamento,
                posicao_puxador=item.posicao_puxador,
                qtd_pecas=op_qty,
                largura_nominal_mm=round(largura_nom, 3),
                desconto_largura_mm=desc_l,
                largura_corte_mm=round(item.vidro_largura_mm, 3),
                regra_largura="Explícito na descrição",
                altura_nominal_mm=round(altura_nom, 3),
                desconto_altura_mm=desc_a,
                altura_corte_mm=round(item.vidro_profundidade_mm, 3),
                regra_altura="Explícito na descrição",
            )
        ]

    if item.qtd_puxadores == 0:
        desc_l = round(2.0 * lat, 3)
        desc_a = round(2.0 * lat, 3)
        regra_l = "2x Lateral"
        regra_a = "2x Lateral"
    elif item.posicao_puxador in ("SUPERIOR", "HORIZONTAL (BASCULA/GAVETA)"):
        desc_l = round(2.0 * lat, 3)
        desc_a = round(pux + lat, 3)
        regra_l = "2x Lateral"
        regra_a = "1x Puxador + 1x Lateral"
    elif item.qtd_puxadores == 2:
        desc_l = round(2.0 * pux, 3)
        desc_a = round(2.0 * lat, 3)
        regra_l = "2x Puxador"
        regra_a = "2x Lateral"
    else:
        # 1 puxador lateral (DIREITA ou ESQUERDA)
        desc_l = round(pux + lat, 3)
        desc_a = round(2.0 * lat, 3)
        regra_l = "1x Puxador + 1x Lateral"
        regra_a = "2x Lateral"

    return [
        CutGlass(
            op=item.op,
            codigo=item.codigo,
            pedido=item.pedido,
            data_entrega=item.data_entrega,
            categoria=item.categoria,
            modelo=item.modelo,
            acabamento_placa=acabamento,
            posicao_puxador=item.posicao_puxador,
            qtd_pecas=op_qty,
            largura_nominal_mm=round(largura_nom, 3),
            desconto_largura_mm=desc_l,
            largura_corte_mm=_safe_cut(largura_nom, desc_l),
            regra_largura=regra_l,
            altura_nominal_mm=round(altura_nom, 3),
            desconto_altura_mm=desc_a,
            altura_corte_mm=_safe_cut(altura_nom, desc_a),
            regra_altura=regra_a,
        )
    ]


def build_glass_cutting_plan(
    items: List[ExtractedItem], rules: Dict[str, CuttingRule]
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Gera a lista detalhada de corte de vidros por OP e o resumo agrupado."""
    detailed_glasses: List[CutGlass] = []
    for item in items:
        detailed_glasses.extend(compute_item_glasses(item, rules))

    grouped: Dict[tuple, Dict[str, Any]] = {}
    for g in detailed_glasses:
        key = (
            g.modelo,
            g.acabamento_placa,
            g.largura_corte_mm,
            g.altura_corte_mm,
            g.regra_largura,
            g.regra_altura,
        )
        if key not in grouped:
            grouped[key] = {
                "modelo": g.modelo,
                "acabamento_placa": g.acabamento_placa,
                "largura_corte_mm": g.largura_corte_mm,
                "altura_corte_mm": g.altura_corte_mm,
                "regra_largura": g.regra_largura,
                "regra_altura": g.regra_altura,
                "qtd_pecas": 0,
                "area_m2": 0.0,
                "ops": set(),
            }
        entry = grouped[key]
        entry["qtd_pecas"] += g.qtd_pecas
        entry["area_m2"] = round(entry["area_m2"] + g.area_m2, 4)
        entry["ops"].add(g.op)

    summary_list: List[Dict[str, Any]] = []
    for entry in grouped.values():
        ops_sorted = sorted(entry["ops"])
        summary_list.append(
            {
                "modelo": entry["modelo"],
                "acabamento_placa": entry["acabamento_placa"],
                "largura_corte_mm": entry["largura_corte_mm"],
                "altura_corte_mm": entry["altura_corte_mm"],
                "regra_largura": entry["regra_largura"],
                "regra_altura": entry["regra_altura"],
                "qtd_pecas": entry["qtd_pecas"],
                "area_m2": entry["area_m2"],
                "qtd_ops": len(ops_sorted),
                "ops": ", ".join(ops_sorted[:10])
                + (f" (+{len(ops_sorted) - 10})" if len(ops_sorted) > 10 else ""),
            }
        )

    summary_list.sort(
        key=lambda x: (
            x["modelo"],
            x["acabamento_placa"],
            -x["altura_corte_mm"],
            -x["largura_corte_mm"],
        )
    )

    return [g.to_dict() for g in detailed_glasses], summary_list


def compute_kpis(
    items: List[ExtractedItem],
    detailed_bars: List[Dict[str, Any]],
    detailed_glasses: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """Calcula indicadores consolidados da consulta."""
    total_itens = len(items)
    total_pecas_op = sum(_qty_int(i) for i in items)
    total_estruturas = sum(_qty_int(i) * i.qtd_estruturas for i in items)
    total_barras = sum(b["qtd_barras"] for b in detailed_bars)
    total_metros = round(sum(b["total_mm"] for b in detailed_bars) / 1000.0, 2)
    glasses = detailed_glasses or []
    total_pecas_vidro = sum(g["qtd_pecas"] for g in glasses)
    total_area_vidro_m2 = round(sum(g["area_m2"] for g in glasses), 2)
    itens_com_divisoria = sum(1 for i in items if i.tem_divisorias)
    itens_com_puxador = sum(1 for i in items if i.tem_puxador)
    total_puxadores = sum(_qty_int(i) * i.qtd_puxadores for i in items)
    itens_especiais = sum(1 for i in items if i.eh_especial)

    por_modelo: Dict[str, int] = defaultdict(int)
    por_posicao_puxador: Dict[str, int] = defaultdict(int)
    for it in items:
        por_modelo[it.modelo] += _qty_int(it)
        por_posicao_puxador[it.posicao_puxador] += _qty_int(it)

    return {
        "total_linhas_op": total_itens,
        "total_pecas_op": total_pecas_op,
        "total_estruturas": total_estruturas,
        "total_barras_corte": total_barras,
        "total_metros_lineares": total_metros,
        "total_pecas_vidro": total_pecas_vidro,
        "total_area_vidro_m2": total_area_vidro_m2,
        "itens_com_divisoria": itens_com_divisoria,
        "itens_com_puxador": itens_com_puxador,
        "total_puxadores": total_puxadores,
        "itens_especiais": itens_especiais,
        "por_modelo": dict(sorted(por_modelo.items(), key=lambda kv: -kv[1])),
        "por_posicao_puxador": dict(
            sorted(por_posicao_puxador.items(), key=lambda kv: -kv[1])
        ),
    }
