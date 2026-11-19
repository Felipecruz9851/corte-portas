


"""API FastAPI para extração construtiva e cálculo de plano de corte de PORTAS."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.bar_optimizer import OptimizationConfig, build_bar_optimization
from app.cutting_engine import (
    CuttingRule,
    _norm_angle,
    build_cutting_plan,
    build_glass_cutting_plan,
    compute_item_cuts,
    compute_item_glasses,
    compute_kpis,
    default_angles_for_tipo_corte,
    load_rules,
    save_rules,
)
from app.description_parser import ExtractedItem, parse_description
from app.erp_client import ERPAuthenticationError, ERPClient, ERPConnectionError
from app.exporter import (
    export_to_csv_bytes,
    export_to_json_bytes,
    export_to_xlsx_bytes,
)
from app.html_parser import parse_op_html
import sys
import os
import uvicorn

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
FRONTEND_DIST_DIR = FRONTEND_DIR / "dist"
FRONTEND_STATIC_DIR = FRONTEND_DIST_DIR / "static"
DEFAULT_RULES_BACKUP = load_rules()

app = FastAPI(
    title="Extrator Construtivo e Plano de Corte - PORTAS",
    version="1.0.0",
)

if FRONTEND_STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_STATIC_DIR)), name="static")
elif FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


class ExtractionStore:
    """Estado da última extração em memória para recálculo instantâneo de regras."""

    def __init__(self) -> None:
        self.meta: Dict[str, Any] = {}
        self.extracted_items: List[ExtractedItem] = []
        self.payload: Optional[Dict[str, Any]] = None
        self.optimization_config: OptimizationConfig = OptimizationConfig()


STORE = ExtractionStore()


class ERPExtractRequest(BaseModel):
    data: Optional[str] = None
    datas: Optional[List[str]] = None
    cod_empresa: str = "11"
    local: str = "PORTAS"
    item_desc: str = "S"
    phpsessid: Optional[str] = None
    usuario: Optional[str] = None
    senha: Optional[str] = None


class HTMLFileItem(BaseModel):
    html: str = ""
    source_name: str = "HTML enviado"


class HTMLExtractRequest(BaseModel):
    html: Optional[str] = None
    source_name: str = "HTML enviado"
    files: Optional[List[HTMLFileItem]] = None


class RuleUpdateModel(BaseModel):
    modelo: str
    descricao: str = ""
    tipo_corte: str = "45°"
    angulo_corte_quadro: Optional[int] = None
    angulo_corte_puxador: Optional[int] = None
    angulo_corte_divisoria: Optional[int] = None
    perfil_simetrico_lateral: bool = False
    perfil_simetrico_puxador: bool = False
    codigo_perfil_lateral: str = ""
    codigo_perfil_puxador: str = ""
    largura_perfil_quadro_mm: float = 0.0
    largura_perfil_puxador_mm: float = 0.0
    desconto_adjacente_puxador_mm: float = 0.0
    desconto_vertical_mm: float = 0.0
    desconto_horizontal_mm: float = 0.0
    desconto_divisoria_mm: float = 0.0
    desconto_vidro_lateral_mm: float = 0.0
    desconto_vidro_puxador_mm: float = 0.0
    observacao: str = ""


class RulesBatchUpdate(BaseModel):
    rules: Dict[str, RuleUpdateModel]


class OptimizeBarsRequest(BaseModel):
    comprimento_barra_mm: float = Field(default=6000.0, gt=0)
    espessura_serra_mm: float = Field(default=0.0, ge=0)
    desponte_mm: float = Field(default=0.0, ge=0)
    separar_por_acabamento: bool = False
    perda_maxima_mm: Optional[float] = Field(default=None, ge=0)
    detailed_bars: Optional[List[Dict[str, Any]]] = None


class ExportRequest(BaseModel):
    mode: str = "items"  # para CSV: 'items', 'corte', 'vidro', 'otimizacao_material', 'otimizacao_tempo_roteiro' ou 'otimizacao_tempo_barras'
    items: Optional[List[Dict[str, Any]]] = None
    detailed_bars: Optional[List[Dict[str, Any]]] = None
    grouped_bars: Optional[List[Dict[str, Any]]] = None
    detailed_glasses: Optional[List[Dict[str, Any]]] = None
    grouped_glasses: Optional[List[Dict[str, Any]]] = None
    bar_optimization: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None
    kpis: Optional[Dict[str, Any]] = None


def _run_pipeline_from_html_list(
    html_pages: List[tuple[str, str]],
    rules: Optional[Dict[str, CuttingRule]] = None,
) -> Dict[str, Any]:
    active_rules = rules or load_rules()
    all_items: List[ExtractedItem] = []
    metas: List[Dict[str, Any]] = []

    for label, html_text in html_pages:
        meta, raw_rows = parse_op_html(html_text)
        meta["origem"] = label
        metas.append(meta)
        for row in raw_rows:
            all_items.append(parse_description(row))

    return _build_response_payload(metas, all_items, active_rules)


def _build_response_payload(
    metas: List[Dict[str, Any]],
    all_items: List[ExtractedItem],
    rules: Dict[str, CuttingRule],
) -> Dict[str, Any]:
    detailed_bars, grouped_bars = build_cutting_plan(all_items, rules)
    detailed_glasses, grouped_glasses = build_glass_cutting_plan(all_items, rules)
    bar_optimization = build_bar_optimization(
        detailed_bars, STORE.optimization_config, rules
    )
    kpis = compute_kpis(all_items, detailed_bars, detailed_glasses)

    items_dicts: List[Dict[str, Any]] = []
    for item in all_items:
        d = item.to_dict()
        d["barras_corte"] = [b.to_dict() for b in compute_item_cuts(item, rules)]
        d["vidros_corte"] = [g.to_dict() for g in compute_item_glasses(item, rules)]
        items_dicts.append(d)

    datas_abertura = sorted(
        {m.get("data_abertura", "") for m in metas if m.get("data_abertura")}
    )
    locais = sorted(
        {m.get("local_producao", "") for m in metas if m.get("local_producao")}
    )

    meta_consolidado = {
        "locais": locais,
        "datas_abertura": datas_abertura,
        "consultas": metas,
        "total_linhas": len(all_items),
    }

    payload = {
        "meta": meta_consolidado,
        "kpis": kpis,
        "items": items_dicts,
        "corte_detalhado": detailed_bars,
        "corte_agrupado": grouped_bars,
        "vidro_detalhado": detailed_glasses,
        "vidro_agrupado": grouped_glasses,
        "otimizacao_barras": bar_optimization,
        "rules": {k: v.to_dict() for k, v in rules.items()},
    }

    STORE.meta = meta_consolidado
    STORE.extracted_items = all_items
    STORE.payload = payload
    return payload


@app.get("/")
def serve_index() -> FileResponse:
    dist_index = FRONTEND_DIST_DIR / "index.html"
    index_path = dist_index if dist_index.exists() else (FRONTEND_DIR / "index.html")
    if not index_path.exists():
        raise HTTPException(404, "Frontend não encontrado.")
    return FileResponse(str(index_path))


@app.get("/logo_lider.png")
def serve_logo() -> FileResponse:
    dist_logo = FRONTEND_DIST_DIR / "logo_lider.png"
    public_logo = FRONTEND_DIR / "public" / "logo_lider.png"
    logo_path = dist_logo if dist_logo.exists() else public_logo
    if not logo_path.exists():
        raise HTTPException(404, "Logo não encontrada.")
    return FileResponse(str(logo_path))


@app.get("/favicon.ico")
def serve_favicon() -> FileResponse:
    dist_favicon = FRONTEND_DIST_DIR / "favicon.ico"
    public_favicon = FRONTEND_DIR / "public" / "favicon.ico"
    favicon_path = dist_favicon if dist_favicon.exists() else public_favicon
    if not favicon_path.exists():
        raise HTTPException(404, "Favicon não encontrado.")
    return FileResponse(str(favicon_path), media_type="image/x-icon")


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/extract/erp")
def extract_from_erp(req: ERPExtractRequest) -> Dict[str, Any]:
    dates_to_fetch = [d.strip() for d in (req.datas or []) if d and d.strip()]
    if not dates_to_fetch and req.data and req.data.strip():
        dates_to_fetch = [req.data.strip()]
    if not dates_to_fetch:
        raise HTTPException(400, "Informe ao menos uma data de abertura (YYYY-MM-DD).")

    client = ERPClient(
        phpsessid=req.phpsessid,
        username=req.usuario,
        password=req.senha,
    )

    html_pages: List[tuple[str, str]] = []
    try:
        for dt in dates_to_fetch:
            html_text = client.fetch_op_abertura(
                data=dt,
                cod_empresa=req.cod_empresa,
                local=req.local,
                item_desc=req.item_desc,
            )
            html_pages.append((f"ERP {req.local} ({dt})", html_text))
    except ERPAuthenticationError as exc:
        raise HTTPException(401, str(exc)) from exc
    except ERPConnectionError as exc:
        raise HTTPException(502, str(exc)) from exc

    return _run_pipeline_from_html_list(html_pages)


@app.post("/api/extract/html")
def extract_from_html(req: HTMLExtractRequest) -> Dict[str, Any]:
    html_pages: List[tuple[str, str]] = []

    if req.files is not None:
        if len(req.files) == 0:
            raise HTTPException(400, "Envie ao menos um arquivo HTML válido.")
        for idx, item in enumerate(req.files):
            label = (item.source_name or "").strip() or f"HTML {idx + 1}"
            if not item.html or len(item.html.strip()) < 10:
                raise HTTPException(
                    400,
                    f"O arquivo '{label}' está vazio ou não contém HTML válido.",
                )
            html_pages.append((label, item.html))
    elif req.html is not None:
        if len(req.html.strip()) < 10:
            raise HTTPException(400, "O conteúdo HTML enviado está vazio ou é inválido.")
        label = (req.source_name or "").strip() or "HTML enviado"
        html_pages.append((label, req.html))
    else:
        raise HTTPException(400, "Envie ao menos um arquivo HTML válido.")

    return _run_pipeline_from_html_list(html_pages)


@app.post("/api/session/clear")
def clear_session() -> Dict[str, str]:
    STORE.meta = {}
    STORE.extracted_items = []
    STORE.payload = None
    return {"status": "cleared"}


@app.get("/api/rules")
def get_rules() -> Dict[str, Any]:
    rules = load_rules()
    return {"rules": {k: v.to_dict() for k, v in rules.items()}}


@app.put("/api/rules")
def update_rules(req: RulesBatchUpdate) -> Dict[str, Any]:
    rules = load_rules()
    for key, model_rule in req.rules.items():
        data = model_rule.model_dump()
        q_def, p_def, d_def = default_angles_for_tipo_corte(data.get("tipo_corte", ""))
        data["angulo_corte_quadro"] = _norm_angle(data.get("angulo_corte_quadro"), q_def)
        data["angulo_corte_puxador"] = _norm_angle(data.get("angulo_corte_puxador"), p_def)
        data["angulo_corte_divisoria"] = _norm_angle(data.get("angulo_corte_divisoria"), d_def)
        data["perfil_simetrico_lateral"] = bool(data.get("perfil_simetrico_lateral", False))
        data["perfil_simetrico_puxador"] = bool(data.get("perfil_simetrico_puxador", False))
        rules[key] = CuttingRule(**data)
    save_rules(rules)

    recalculated = None
    if STORE.extracted_items:
        recalculated = _build_response_payload(
            STORE.meta.get("consultas", []),
            STORE.extracted_items,
            rules,
        )

    return {
        "rules": {k: v.to_dict() for k, v in rules.items()},
        "recalculated": recalculated,
    }


@app.post("/api/rules/reset")
def reset_rules() -> Dict[str, Any]:
    restored = {
        k: CuttingRule(**deepcopy(v.to_dict()))
        for k, v in DEFAULT_RULES_BACKUP.items()
    }
    save_rules(restored)

    recalculated = None
    if STORE.extracted_items:
        recalculated = _build_response_payload(
            STORE.meta.get("consultas", []),
            STORE.extracted_items,
            restored,
        )

    return {
        "rules": {k: v.to_dict() for k, v in restored.items()},
        "recalculated": recalculated,
    }


@app.post("/api/optimize/bars")
def optimize_bars(req: OptimizeBarsRequest) -> Dict[str, Any]:
    if req.desponte_mm >= req.comprimento_barra_mm:
        raise HTTPException(
            400, "O desponte deve ser menor que o comprimento da barra."
        )

    config = OptimizationConfig(
        comprimento_barra_mm=req.comprimento_barra_mm,
        espessura_serra_mm=req.espessura_serra_mm,
        desponte_mm=req.desponte_mm,
        separar_por_acabamento=req.separar_por_acabamento,
    )
    STORE.optimization_config = config

    source_bars = (
        req.detailed_bars
        if req.detailed_bars is not None
        else (STORE.payload.get("corte_detalhado", []) if STORE.payload else [])
    )
    rules = load_rules()
    result = build_bar_optimization(source_bars, config, rules)

    if STORE.payload and req.detailed_bars is None:
        STORE.payload["otimizacao_barras"] = result

    return result


def _resolve_export_data(req: Optional[ExportRequest]) -> Dict[str, Any]:
    if req and req.items is not None:
        return {
            "meta": req.meta or {},
            "kpis": req.kpis or {},
            "items": req.items,
            "corte_detalhado": req.detailed_bars or [],
            "corte_agrupado": req.grouped_bars or [],
            "vidro_detalhado": req.detailed_glasses or [],
            "vidro_agrupado": req.grouped_glasses or [],
            "otimizacao_barras": req.bar_optimization or {},
        }
    if req and req.bar_optimization is not None:
        base = dict(STORE.payload or {})
        base.setdefault("items", [])
        base.setdefault("corte_detalhado", [])
        base.setdefault("corte_agrupado", [])
        base.setdefault("vidro_detalhado", [])
        base.setdefault("vidro_agrupado", [])
        base.setdefault("meta", {})
        base.setdefault("kpis", {})
        base["otimizacao_barras"] = req.bar_optimization
        return base
    if STORE.payload:
        return STORE.payload
    raise HTTPException(
        400,
        "Nenhum dado disponível para exportação. Execute uma extração primeiro.",
    )


@app.post("/api/export/xlsx")
def export_xlsx(req: Optional[ExportRequest] = None) -> Response:
    data = _resolve_export_data(req)
    xlsx_bytes = export_to_xlsx_bytes(
        data["items"],
        data["corte_detalhado"],
        data["corte_agrupado"],
        data.get("vidro_detalhado", []),
        data.get("vidro_agrupado", []),
        data.get("otimizacao_barras", {}),
    )
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="plano_corte_portas.xlsx"'},
    )


@app.post("/api/export/csv")
def export_csv(req: Optional[ExportRequest] = None) -> Response:
    data = _resolve_export_data(req)
    mode = req.mode if req else "items"
    csv_bytes = export_to_csv_bytes(
        data["items"],
        data["corte_agrupado"],
        data.get("vidro_agrupado", []),
        bar_optimization=data.get("otimizacao_barras", {}),
        mode=mode,
    )
    if mode == "corte":
        filename = "corte_serra_portas.csv"
    elif mode == "vidro":
        filename = "corte_vidros_portas.csv"
    elif mode in ("otimizacao_material", "otimizacao_barras"):
        filename = "otimizacao_material_6m.csv"
    elif mode == "otimizacao_tempo_roteiro":
        filename = "otimizacao_tempo_roteiro_6m.csv"
    elif mode in ("otimizacao_tempo_barras", "otimizacao_tempo"):
        filename = "otimizacao_tempo_barras_6m.csv"
    else:
        filename = "itens_portas.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/export/json")
def export_json(req: Optional[ExportRequest] = None) -> Response:
    data = _resolve_export_data(req)
    json_bytes = export_to_json_bytes(
        data["meta"],
        data["kpis"],
        data["items"],
        data["corte_detalhado"],
        data["corte_agrupado"],
        data.get("vidro_detalhado", []),
        data.get("vidro_agrupado", []),
        data.get("otimizacao_barras", {}),
    )
    return Response(
        content=json_bytes,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="extracao_portas.json"'},
    )


def main() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8085"))
    uvicorn.run("main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
