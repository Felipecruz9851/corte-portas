"""Motor de extração estruturada das descrições de OPs do local PORTAS."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from app.html_parser import RawOpRow


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _norm_upper(text: str) -> str:
    return re.sub(r"\s+", " ", _strip_accents(text or "")).strip().upper()


@dataclass
class ExtractedItem:
    """Representação construtiva completa de um item de OP de PORTAS."""

    # Dados da OP / HTML
    local_producao: str
    data_abertura: str
    data_entrega: str
    op: str
    codigo: str
    descricao: str
    quantidade: float
    observacao: str
    pedido: str
    item_pedido: str
    ambiente: str
    valor_insumos: Optional[float]
    valor_mp: Optional[float]

    # Classificação construtiva
    categoria: str
    subcategoria: str
    modelo: str
    subtipo_modelo: str
    codigo_perfil: str
    sistema: str
    eh_especial: bool

    # Dimensões (mm)
    largura_mm: Optional[float]
    altura_mm: Optional[float]
    medida_linear_mm: Optional[float]
    corte_h_mm: Optional[float]
    corte_v_mm: Optional[float]
    vidro_largura_mm: Optional[float]
    vidro_profundidade_mm: Optional[float]
    qtd_estruturas: int
    eh_formato_u: bool
    eh_barra_avulsa: bool

    # Posição / Lado / Folha
    lado: str
    posicao_folha: str

    # Puxadores
    tem_puxador: bool
    qtd_puxadores: int
    posicao_puxador: str
    tipo_puxador: str

    # Divisórias / Travessas
    tem_divisorias: bool
    qtd_divisorias: int
    divisorias_mm: List[float] = field(default_factory=list)
    detalhe_divisorias: str = ""

    # Acabamentos e Furação
    acabamento_perfil: str = ""
    acabamento_placa: str = ""
    furacao: str = ""
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _extract_categoria_subcategoria(upper: str) -> tuple[str, str]:
    if any(
        k in upper
        for k in (
            "ESCADA ALLU",
            "LATERAL NICHO ALLU",
            "NICHO ALLU",
            "ILHA ALLU",
            "PE ALLU",
            "BARRA ALLU",
            "ALLU EM U",
            "PERFIL ALLU",
        )
    ):
        if "ESCADA ALLU" in upper:
            return "LINHA ALLU", "ESCADA ALLU"
        if "LATERAL NICHO ALLU" in upper:
            return "LINHA ALLU", "LATERAL NICHO ALLU"
        if "NICHO ALLU" in upper:
            return "LINHA ALLU", "NICHO ALLU"
        if "ILHA ALLU" in upper:
            return "LINHA ALLU", "ILHA ALLU"
        if "PE ALLU" in upper:
            return "LINHA ALLU", "PE ALLU"
        if "ALLU EM U" in upper:
            return "LINHA ALLU", "ALLU EM U"
        return "LINHA ALLU", "BARRA ALLU"

    if "PROVENCE URDA" in upper or "CRISTALEIRA" in upper:
        return "CRISTALEIRA", "FRENTE PROVENCE URDA"

    if "TAMPO GAVETEIRO VISOR" in upper:
        return "PRATELEIRA / TAMPO VISOR", "TAMPO GAVETEIRO VISOR"
    if "PRATELEIRA VISOR" in upper:
        return "PRATELEIRA / TAMPO VISOR", "PRATELEIRA VISOR"

    if "FRENTE GAVETA" in upper:
        return "FRENTE GAVETA", "FRENTE GAVETA"

    if "FRENTE INFERIOR BASCULA" in upper:
        return "FRENTE BASCULA", "BASCULA INFERIOR (HF)"
    if "FRENTE SUPERIOR BASCULA" in upper:
        return "FRENTE BASCULA", "BASCULA SUPERIOR (HF)"
    if "FRENTE BASCULA INVERSA" in upper:
        return "FRENTE BASCULA", "BASCULA INVERSA"
    if "FRENTE BASCULA" in upper:
        return "FRENTE BASCULA", "BASCULA COMUM"

    if any(
        k in upper
        for k in (
            "PORTA CASCATA",
            "NOVA PORTA CASCATA",
            "PASSAGEM SUSPENSA",
            "FECHAMENTO PISO E TETO",
            "FECHAMENTO SUSPENSA",
        )
    ):
        if "CASCATA" in upper:
            return "PORTA PASSAGEM / DIVISORIA", "PORTA CASCATA"
        if "PASSAGEM SUSPENSA" in upper:
            return "PORTA PASSAGEM / DIVISORIA", "PORTA PASSAGEM SUSPENSA"
        if "FECHAMENTO PISO E TETO" in upper:
            return "PORTA PASSAGEM / DIVISORIA", "PORTA FECHAMENTO PISO E TETO"
        return "PORTA PASSAGEM / DIVISORIA", "PORTA FECHAMENTO SUSPENSA"

    if "PORTA BATER" in upper:
        return "PORTA DE BATER", "PORTA BATER"

    if "CORRER" in upper or "SOFT CLOSING" in upper or "SISTEMA AVANTE" in upper:
        if "ESPELHEIRA" in upper:
            return "PORTA DE CORRER", "PORTA CORRER ESPELHEIRA"
        return "PORTA DE CORRER", "PORTA CORRER"

    return "OUTRO", "OUTRO"


def _extract_modelo(upper: str, categoria: str, codigo: str = "") -> tuple[str, str, str]:
    codigo_perfil = ""
    code_match = re.search(r"(\d{4}/\d{4})", upper)
    if code_match:
        codigo_perfil = code_match.group(1)
    else:
        paren_code = re.search(r"BAGUETE\s*\(([^)]+)\)", upper)
        if paren_code:
            codigo_perfil = paren_code.group(1).strip()
        else:
            single_code = re.search(r"PERFIL\s+(\d{4})\b", upper)
            if single_code:
                codigo_perfil = single_code.group(1)

    if categoria == "LINHA ALLU":
        return "ALLU", "QUADRO/ESCADA ALLU", codigo_perfil or "ALLU"

    if "MINI KENDO" in upper or "PROVENCE URDA" in upper:
        return "MINI KENDO + BAGUETE", "PROVENCE URDA", codigo_perfil or "3PERUNO6BG215B"

    if "CATCH" in upper:
        return "CATCH", "PERLARE CATCH", codigo_perfil or "5307/5317"

    if re.search(r"PERFIL\s+5307\s+S/PUXADOR", upper):
        return "PERFIL 5307", "PERLARE S/PUXADOR", codigo_perfil or "5307"

    if "DJEI" in upper:
        sub = "VISOR" if "VISOR" in upper else "DJEI"
        return "DJEI", sub, codigo_perfil or "5307/6817"

    if "CLEAR_S" in upper or "CLEAR S/" in upper or "CLEAR S " in upper:
        return "CLEAR S", "CLEAR_S", codigo_perfil

    if "CLEAR G" in upper:
        return "CLEAR G", "CLEAR G", codigo_perfil

    if "RISK" in upper:
        if "INCLINADO" in upper:
            sub = "RISK INCLINADO"
        elif "SEM USINAGEM" in upper:
            sub = "RISK SEM USINAGEM"
        elif "USINADO" in upper:
            sub = "RISK USINADO"
        else:
            sub = "RISK"
        return "RISK", sub, codigo_perfil

    if "GROOVE" in upper:
        return "GROOVE", "GROOVE", codigo_perfil

    if "CORRER SINGULAR" in upper:
        return "SINGULAR", "CASCATA SINGULAR", codigo_perfil

    if "CORRER INTEIRA" in upper:
        return "INTEIRA", "CORRER INTEIRA", codigo_perfil

    if "5307/5317" in upper:
        return "CATCH", "PERLARE CATCH", "5307/5317"
    if "5307/6817" in upper:
        return "DJEI", "DJEI", "5307/6817"

    if codigo.upper().startswith("2PTAG"):
        return "RISK", "RISK SEM PUXADOR", codigo_perfil

    return "OUTRO", "", codigo_perfil


def _extract_qtd_estruturas(upper: str, categoria: str) -> int:
    if categoria != "LINHA ALLU":
        return 1
    mapping = {
        "PRODUZIR UMA ESCADA": 1,
        "PRODUZIR DUAS ESCADAS": 2,
        "PRODUZIR TRES ESCADAS": 3,
        "PRODUZIR QUATRO ESCADAS": 4,
    }
    for token, qtd in mapping.items():
        if token in upper:
            return qtd
    return 1


def _extract_dimensions(
    upper: str, categoria: str
) -> tuple[
    Optional[float],
    Optional[float],
    Optional[float],
    Optional[float],
    Optional[float],
    Optional[float],
    Optional[float],
    bool,
]:
    """Retorna (largura, altura, linear, corte_h, corte_v, vidro_l, vidro_p, eh_barra_avulsa)."""
    largura: Optional[float] = None
    altura: Optional[float] = None
    linear: Optional[float] = None
    corte_h: Optional[float] = None
    corte_v: Optional[float] = None
    vidro_l: Optional[float] = None
    vidro_p: Optional[float] = None
    eh_barra_avulsa = False

    # Caso 1: Barra avulsa (sem altura/largura de quadro)
    if (
        "SOMENTE A BARRA" in upper
        or "CORTAR BARRA COM" in upper
        or "APENAS A BARRA" in upper
        or "APENAR A BARRA" in upper
    ):
        eh_barra_avulsa = True
        m_bar = re.search(
            r"(?:LARGURA\s+DE|CORTAR\s+BARRA\s+COM|MEDIDA)\s+(\d+(?:\.\d+)?)\s*(?:MM)?",
            upper,
        )
        if m_bar:
            linear = float(m_bar.group(1))
            largura = linear
        return largura, altura, linear, corte_h, corte_v, vidro_l, vidro_p, eh_barra_avulsa

    # Caso 2: Cristaleira Provence Urda (placa + cortes explícitos de perfil)
    if categoria == "CRISTALEIRA":
        m_placa = re.search(
            r"PLACA\s+LARGURA\s+(\d+(?:\.\d+)?)\s*X\s*ALTURA\s+(\d+(?:\.\d+)?)\s*MM",
            upper,
        )
        if m_placa:
            largura = float(m_placa.group(1))
            altura = float(m_placa.group(2))

        m_cortes = re.search(
            r"02\s+UNIDADES\s+MEDIDA\s+(\d+(?:\.\d+)?)\s*MM\s+E\s+02\s+UNIDADES\s+MEDIDA\s+(\d+(?:\.\d+)?)\s*MM",
            upper,
        )
        if m_cortes:
            corte_h = float(m_cortes.group(1))
            corte_v = float(m_cortes.group(2))
            if largura is None:
                largura = corte_h
            if altura is None:
                altura = corte_v
        return largura, altura, linear, corte_h, corte_v, vidro_l, vidro_p, eh_barra_avulsa

    # Caso 3: Tampo / Prateleira Visor (MEDIDA L X P e vidro LARGURA X PROFUNDIDADE)
    if categoria == "PRATELEIRA / TAMPO VISOR":
        m_med = re.search(
            r"MEDI\s*DA\s+(\d+(?:\.\d+)?)\s*X\s*(\d+(?:\.\d+)?)", upper
        )
        if m_med:
            largura = float(m_med.group(1))
            altura = float(m_med.group(2))
        else:
            m_lp = re.search(
                r"LARGURA\s+(\d+(?:\.\d+)?)\s*X\s*(?:PROFUNDIDADE|PORFUNDIDADE|ALTURA)\s+(\d+(?:\.\d+)?)",
                upper,
            )
            if m_lp:
                largura = float(m_lp.group(1))
                altura = float(m_lp.group(2))

        m_vidro = re.search(
            r"VIDRO\s+[^-]*?LARGURA\s+(\d+(?:\.\d+)?)\s*X\s*(?:PROFUNDIDADE|PORFUNDIDADE)\s+(\d+(?:\.\d+)?)",
            upper,
        )
        if m_vidro:
            vidro_l = float(m_vidro.group(1))
            vidro_p = float(m_vidro.group(2))
        return largura, altura, linear, corte_h, corte_v, vidro_l, vidro_p, eh_barra_avulsa

    # Caso 4: Padrão geral LARGURA ... ALTURA ...
    m_larg = re.search(r"LARGURA(?:\s+DE)?\s+(\d+(?:\.\d+)?)", upper)
    m_alt = re.search(r"(?:ALTURA|PROFUNDIDADE|PORFUNDIDADE)(?:\s+DE)?\s+(\d+(?:\.\d+)?)", upper)
    if m_larg:
        largura = float(m_larg.group(1))
    if m_alt:
        altura = float(m_alt.group(1))

    if "PERFIL LINEAR" in upper:
        eh_barra_avulsa = True
        linear = altura or largura

    return largura, altura, linear, corte_h, corte_v, vidro_l, vidro_p, eh_barra_avulsa


def _extract_lado_e_folha(upper: str) -> tuple[str, str]:
    posicao_folha = "N/A"
    if "_EXTERNA_" in upper or " EXTERNA " in upper or upper.endswith(" EXTERNA"):
        posicao_folha = "EXTERNA"
    elif "_INTERNA_" in upper or " INTERNA " in upper or "_INTERNA " in upper:
        posicao_folha = "INTERNA"

    # Verifica ambos os lados
    if any(
        tok in upper
        for tok in (
            "DIREITO E ESQUERDO",
            "DIREITA E ESQUERDA",
            "LATERAL DIREITA E LATERAL ESQUERDA",
            "DOS DOIS LADOS",
        )
    ):
        return "AMBOS", posicao_folha

    # Lado único (evita confundir "ESQUERDA" dentro de acabamento)
    struct_part = re.split(r"[-_](?:PERFIL|ACABAMENTO|PLACA)\b", upper)[0]
    has_dir = bool(re.search(r"(?:^|[\s_-])DIREIT[AO](?:$|[\s_-])", struct_part))
    has_esq = bool(re.search(r"(?:^|[\s_-])ESQUERD[AO](?:$|[\s_-])|_ESQ\b|- ESQ\b", struct_part))

    if has_dir and has_esq:
        return "AMBOS", posicao_folha
    if has_dir:
        return "DIREITA", posicao_folha
    if has_esq:
        return "ESQUERDA", posicao_folha

    return "N/A", posicao_folha


def _extract_puxadores(
    upper: str, categoria: str, lado: str
) -> tuple[bool, int, str, str]:
    """Retorna (tem_puxador, qtd_puxadores, posicao_puxador, tipo_puxador)."""
    if categoria in ("LINHA ALLU", "CRISTALEIRA", "PRATELEIRA / TAMPO VISOR"):
        return False, 0, "SEM PUXADOR", ""

    # Casos explícitos sem puxador / sem usinagem
    if any(
        tok in upper
        for tok in (
            "S/PUXADOR",
            "S/ PUXADOR",
            "SEM PUXADOR",
            "SEM PUXADRO",
            "_SEM PUX",
            "SEM PUX",
            "SEM USINAGEM",
        )
    ):
        return False, 0, "SEM PUXADOR", ""

    # Tipo de puxador (quando especificado)
    tipo_puxador = ""
    m_smart = re.search(r"PUX\.?\s*SMART\s*(\d+\s*MM)?", upper)
    if m_smart:
        size = (m_smart.group(1) or "").strip()
        tipo_puxador = f"PUX.SMART {size}".strip()
    elif "PUXADOR SLIM" in upper:
        tipo_puxador = "PUXADOR SLIM"
    elif "USINADO" in upper:
        tipo_puxador = "USINADO NO PERFIL"
    elif "INCLINADO" in upper:
        tipo_puxador = "USINADO INCLINADO"
    elif "5307/5317" in upper:
        tipo_puxador = "PERFIL CATCH (5317)"
    elif "5307/6817" in upper:
        tipo_puxador = "PERFIL DJEI (6817)"
    elif "GROOVE" in upper:
        tipo_puxador = "PERFIL GROOVE"
    elif "CLEAR_S" in upper or "CLEAR G" in upper:
        tipo_puxador = "PUXADOR CLEAR"
    elif "RISK" in upper:
        tipo_puxador = "USINADO RISK"

    # Caso 2 puxadores (dois lados)
    if any(
        tok in upper
        for tok in (
            "DIREITO E ESQUERDO",
            "DIREITA E ESQUERDA",
            "LATERAL DIREITA E LATERAL ESQUERDA",
            "DOS DOIS LADOS",
        )
    ):
        return True, 2, "DUPLO (DIREITA E ESQUERDA)", tipo_puxador or "DUPLO"

    # Posição explícita: SUPERIOR
    if "PUXADOR SUPERIOR" in upper or "USINADO SUPERIOR" in upper:
        if categoria == "FRENTE GAVETA":
            return True, 1, "SUPERIOR", tipo_puxador
        return True, 1, "SUPERIOR", tipo_puxador

    # Posição explícita: LATERAL
    if "PUXADOR LATERAL" in upper or "USINADO LATERAL" in upper or "INCLINADO LATERAL" in upper:
        pos = f"LATERAL ({lado})" if lado in ("DIREITA", "ESQUERDA") else "LATERAL"
        return True, 1, pos, tipo_puxador

    # Frentes de Báscula e Gaveta com puxador
    if categoria in ("FRENTE BASCULA", "FRENTE GAVETA"):
        if (
            "C/PUXADOR" in upper
            or "C/ PUXADOR" in upper
            or "_PUXADOR" in upper
            or "USINADO" in upper
            or "CATCH" in upper
            or "DJEI" in upper
        ):
            return True, 1, "HORIZONTAL (BASCULA/GAVETA)", tipo_puxador
        return False, 0, "SEM PUXADOR", ""

    # Portas de bater / correr / passagem que informam o lado do puxador implicitamente
    if categoria in ("PORTA DE BATER", "PORTA DE CORRER", "PORTA PASSAGEM / DIVISORIA"):
        if (
            "C/PUXADOR" in upper
            or "C/ PUXADOR" in upper
            or "_PUXADOR" in upper
            or "COM PUX" in upper
            or "PUXADOR SLIM" in upper
            or "RISK" in upper
            or "DJEI" in upper
            or "GROOVE" in upper
            or "CORRER INTEIRA" in upper
        ):
            if lado in ("DIREITA", "ESQUERDA"):
                return True, 1, f"LATERAL ({lado})", tipo_puxador
            return True, 1, "LATERAL", tipo_puxador

    return False, 0, "SEM PUXADOR", ""


def _extract_divisorias(upper: str) -> tuple[bool, int, List[float], str]:
    """Retorna (tem_divisorias, qtd_divisorias, divisorias_mm, detalhe)."""
    # 1) Padrão Linha ALLU: DIVISORIA 1 - 150MM - DIVISORIA 2 - 767MM ...
    allu_divs = re.findall(r"DIVISORIA\s*\d+\s*-\s*(\d+(?:\.\d+)?)\s*MM", upper)
    if allu_divs:
        vals = [float(v) for v in allu_divs]
        detalhe = ", ".join(f"{v:g}mm" for v in vals)
        return True, len(vals), vals, f"{len(vals)} divisória(s): {detalhe}"

    # 2) Padrão Portas com travessa/divisão interna (ex: TRAVESSA A 1065MM DE BAIXO / DIVISAO A 790 MM)
    porta_divs = re.findall(
        r"(?:DIVISAO|TRAVESSA(?:\s+DE\s+DIVISAO)?)\s+A\s+(\d+(?:\.\d+)?)\s*MM",
        upper,
    )
    if porta_divs:
        vals = [float(v) for v in porta_divs]
        detalhe = ", ".join(f"{v:g}mm da base" for v in vals)
        return True, len(vals), vals, f"{len(vals)} travessa(s): {detalhe}"

    # 3) Padrão Porta Cascata Singular com vãos (VAO INFERIOR / CENTRAL / SUPERIOR)
    vaos = re.findall(r"VAO\s+(INFERIOR|CENTRAL|SUPERIOR)\s+(\d+(?:\.\d+)?)", upper)
    if len(vaos) >= 2:
        # Calcula posição acumulada das divisórias entre os vãos a partir de baixo
        vao_map = {name: float(val) for name, val in vaos}
        ordered = [vao_map[k] for k in ("INFERIOR", "CENTRAL", "SUPERIOR") if k in vao_map]
        if len(ordered) >= 2:
            posicoes: List[float] = []
            acc = 0.0
            for v in ordered[:-1]:
                acc += v
                posicoes.append(acc)
            detalhe_vaos = " / ".join(f"{name}: {float(val):g}mm" for name, val in vaos)
            return True, len(ordered) - 1, posicoes, f"Vãos ({detalhe_vaos})"

    return False, 0, [], ""


def _extract_acabamentos_e_furacao(desc: str, upper: str, categoria: str) -> tuple[str, str, str, str]:
    """Retorna (acabamento_perfil, acabamento_placa, furacao, sistema)."""
    acabamento_perfil = ""
    acabamento_placa = ""
    furacao = ""
    sistema = ""

    # Sistema (BLUM, DELTA, HF, SI OCEAN 80, AVANTE)
    m_oc = re.search(r"(SI\s+OCEAN\s*\d+|SISTEMA\s+AVANTE)", upper)
    if m_oc:
        sistema = m_oc.group(1).strip()
    m_sis = re.search(r"SISTEMA\s+([A-Z0-9\s-]+?)(?:\s*-\s*FURACAO|\s*-\s*SEM|\s*$)", upper)
    if m_sis:
        sis_val = m_sis.group(1).strip(" -")
        if sis_val:
            sistema = f"{sistema} / {sis_val}".strip(" /") if sistema else sis_val
    elif "SEM ARTICULADOR" in upper:
        sistema = "SEM ARTICULADOR"
    elif "TANDEMBOX" in upper or "BLUM" in upper:
        m_blum = re.search(r"(BLUM\s+[A-Z0-9\s-]+?)(?:\s*-\s*FURACAO|\s*$)", upper)
        sistema = m_blum.group(1).strip(" -") if m_blum else "BLUM"
    elif "TELESCOPICA" in upper:
        m_tel = re.search(r"(TELESCOPICA(?:\s+[A-Z]+)?)", upper)
        if m_tel:
            sistema = m_tel.group(1).strip()

    # Furação
    if "SEM FURACAO" in upper:
        furacao = "SEM FURACAO"
    elif "SEM DOBRADICA" in upper:
        m_fur = re.search(r"FURACAO\s+([A-Z0-9\s/-]+?)(?:\s*$)", upper)
        furacao = m_fur.group(1).strip(" )") if m_fur else "SEM DOBRADICA"
    else:
        m_fur = re.search(r"FURACAO\s+([^_]+?)(?:\s*-\s*TRAVESSA|\s*$)", upper)
        if m_fur:
            furacao = m_fur.group(1).strip(" )-")

    # Acabamentos
    if categoria == "LINHA ALLU":
        m_acab = re.search(r"ACABAMENTO\s+(.+?)(?:\s*-\s*FAZER\s+FURO|\s*$)", upper)
        if m_acab:
            acabamento_perfil = m_acab.group(1).strip(" -")
        return acabamento_perfil, acabamento_placa, furacao, sistema

    if categoria == "CRISTALEIRA":
        m_pl = re.search(r"ACABAMENTO\s+PLACA\s+(.+?)$", upper)
        if m_pl:
            acabamento_placa = m_pl.group(1).strip(" -")
        acabamento_perfil = "PROVENCE URDA"
        return acabamento_perfil, acabamento_placa, furacao, sistema

    if categoria == "PRATELEIRA / TAMPO VISOR":
        m_acab = re.search(r"ACABAMENTO\s+(?:PERFIL\s+)?(.+?)\s*-\s*VIDRO\s+(.+?)(?:\s+LARGURA|\s*$)", upper)
        if m_acab:
            acabamento_perfil = m_acab.group(1).strip(" -")
            acabamento_placa = m_acab.group(2).strip(" -")
        return acabamento_perfil, acabamento_placa, furacao, sistema

    # Padrão com PERFIL ... e PLACA/ESPELHO/VIDRO/TRANSLUCIDO ...
    # Separa primeiro no bloco de PERFIL
    m_perf = re.search(
        r"(?:^|[-_\s])PERFIL\s*(.+?)(?=(?:\s*[-_]\s*(?:PLACA|ESPELHO|VIDRO|TRANSLUCIDO|PLACAEXTERNA|PLACA\s+EXTERNA)|_PLACA|-\s*ESPELHO|-\s*VIDRO|-\s*TRANSLUCIDO|$))",
        upper,
    )
    if m_perf:
        cand = m_perf.group(1).strip(" -_")
        # Evita capturar "PERFIL 5307 S/PUXADOR..." do início do nome se houver outro "PERFIL " depois
        if "S/PUXADOR" in cand or "DJEI" in cand or "RISK" in cand:
            m_perf2 = re.search(
                r"[-_]\s*PERFIL\s*(.+?)(?=(?:\s*[-_]\s*(?:PLACA|ESPELHO|VIDRO|TRANSLUCIDO)|_PLACA|-\s*ESPELHO|-\s*VIDRO|-\s*TRANSLUCIDO|$))",
                upper,
            )
            if m_perf2:
                cand = m_perf2.group(1).strip(" -_")
        acabamento_perfil = cand

    m_placa = re.search(
        r"(?:PLACA\s*EXTERNA|PLACAS?\s+|[-_]\s*(?=ESPELHO\b|VIDRO\b|TRANSLUCIDO\b))(.+?)(?=(?:\s*[-_]\s*(?:FURACAO|SISTEMA|SEM\s+ARTICULADOR|SEM\s+FURACAO|BLUM|TANDEMBOX|TELESCOPICA|VAO\s+|COM\s+PUX|SEM\s+PUX|PUXADOR\s+SLIM)|_FURACAO|_VAO|_SEM\s+PUX|$))",
        upper,
    )
    if m_placa:
        acabamento_placa = m_placa.group(1).strip(" -_")
    elif "PLACA" in upper:
        m_pl2 = re.search(r"PLACA\s*(.+?)(?:_FURACAO|- FURACAO|$)", upper)
        if m_pl2:
            acabamento_placa = m_pl2.group(1).strip(" -_")

    # Limpa caso tenha sobrado "- - SISTEMA" ou código de placa do tipo PLACAGRUPO
    acabamento_placa = re.sub(r"\s*-\s*3[A-Z0-9]+\s*$", "", acabamento_placa).strip(" -")

    return acabamento_perfil, acabamento_placa, furacao, sistema


def parse_description(row: RawOpRow) -> ExtractedItem:
    """Extrai todas as informações construtivas de uma linha de OP."""
    desc = row.descricao
    upper = _norm_upper(desc)

    categoria, subcategoria = _extract_categoria_subcategoria(upper)
    modelo, subtipo_modelo, codigo_perfil = _extract_modelo(upper, categoria, row.codigo)
    qtd_estruturas = _extract_qtd_estruturas(upper, categoria)

    (
        largura_mm,
        altura_mm,
        medida_linear_mm,
        corte_h_mm,
        corte_v_mm,
        vidro_largura_mm,
        vidro_profundidade_mm,
        eh_barra_avulsa,
    ) = _extract_dimensions(upper, categoria)

    eh_formato_u = "ALLU EM U" in upper or "FORMATO DE U" in upper
    eh_especial = bool(re.search(r"\b(?:ESPECIAL|ESPCIAL|ESP)\b|^ESP-", upper))

    lado, posicao_folha = _extract_lado_e_folha(upper)
    tem_puxador, qtd_puxadores, posicao_puxador, tipo_puxador = _extract_puxadores(
        upper, categoria, lado
    )
    tem_divisorias, qtd_divisorias, divisorias_mm, detalhe_divisorias = _extract_divisorias(
        upper
    )
    acabamento_perfil, acabamento_placa, furacao, sistema = _extract_acabamentos_e_furacao(
        desc, upper, categoria
    )

    warnings: List[str] = []
    if not eh_barra_avulsa and (largura_mm is None or altura_mm is None):
        warnings.append("Dimensão largura/altura não identificada na descrição.")
    if eh_barra_avulsa and medida_linear_mm is None:
        warnings.append("Comprimento linear da barra não identificado na descrição.")
    if modelo == "OUTRO":
        warnings.append("Modelo de perfil não reconhecido automaticamente.")

    return ExtractedItem(
        local_producao=row.local_producao,
        data_abertura=row.data_abertura,
        data_entrega=row.data_entrega,
        op=row.op,
        codigo=row.codigo,
        descricao=row.descricao,
        quantidade=row.quantidade,
        observacao=row.observacao,
        pedido=row.pedido,
        item_pedido=row.item_pedido,
        ambiente=row.ambiente,
        valor_insumos=row.valor_insumos,
        valor_mp=row.valor_mp,
        categoria=categoria,
        subcategoria=subcategoria,
        modelo=modelo,
        subtipo_modelo=subtipo_modelo,
        codigo_perfil=codigo_perfil,
        sistema=sistema,
        eh_especial=eh_especial,
        largura_mm=largura_mm,
        altura_mm=altura_mm,
        medida_linear_mm=medida_linear_mm,
        corte_h_mm=corte_h_mm,
        corte_v_mm=corte_v_mm,
        vidro_largura_mm=vidro_largura_mm,
        vidro_profundidade_mm=vidro_profundidade_mm,
        qtd_estruturas=qtd_estruturas,
        eh_formato_u=eh_formato_u,
        eh_barra_avulsa=eh_barra_avulsa,
        lado=lado,
        posicao_folha=posicao_folha,
        tem_puxador=tem_puxador,
        qtd_puxadores=qtd_puxadores,
        posicao_puxador=posicao_puxador,
        tipo_puxador=tipo_puxador,
        tem_divisorias=tem_divisorias,
        qtd_divisorias=qtd_divisorias,
        divisorias_mm=divisorias_mm,
        detalhe_divisorias=detalhe_divisorias,
        acabamento_perfil=acabamento_perfil,
        acabamento_placa=acabamento_placa,
        furacao=furacao,
        warnings=warnings,
    )
