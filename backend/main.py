"""API FastAPI para extração construtiva e cálculo de plano de corte de PORTAS."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.cutting_engine import (
    CuttingRule,
    build_cutting_plan,
    build_glass_cutting_plan,
    compute_item_cuts,
    compute_item_glasses,
    compute_kpis,
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

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
DEFAULT_RULES_BACKUP = load_rules()

app = FastAPI(
    title="Extrator Construtivo e Plano de Corte - PORTAS",
    version="1.0.0",
)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


class ExtractionStore:
    """Estado da última extração em memória para recálculo instantâneo de regras."""

    def __init__(self) -> None:
        self.meta: Dict[str, Any] = {}
        self.extracted_items: List[ExtractedItem] = []
        self.payload: Optional[Dict[str, Any]] = None


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


class HTMLExtractRequest(BaseModel):
    html: str = Field(..., min_length=10)
    source_name: str = "HTML enviado"


class RuleUpdateModel(BaseModel):
    modelo: str
    descricao: str = ""
    tipo_corte: str = "45°"
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


class ExportRequest(BaseModel):
    mode: str = "items"  # para CSV: 'items', 'corte' ou 'vidro'
    items: Optional[List[Dict[str, Any]]] = None
    detailed_bars: Optional[List[Dict[str, Any]]] = None
    grouped_bars: Optional[List[Dict[str, Any]]] = None
    detailed_glasses: Optional[List[Dict[str, Any]]] = None
    grouped_glasses: Optional[List[Dict[str, Any]]] = None
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
        "rules": {k: v.to_dict() for k, v in rules.items()},
    }

    STORE.meta = meta_consolidado
    STORE.extracted_items = all_items
    STORE.payload = payload
    return payload


@app.get("/")
def serve_index() -> FileResponse:
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(404, "Frontend não encontrado.")
    return FileResponse(str(index_path))


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
    return _run_pipeline_from_html_list([(req.source_name, req.html)])


@app.get("/api/rules")
def get_rules() -> Dict[str, Any]:
    rules = load_rules()
    return {"rules": {k: v.to_dict() for k, v in rules.items()}}


@app.put("/api/rules")
def update_rules(req: RulesBatchUpdate) -> Dict[str, Any]:
    rules = load_rules()
    for key, model_rule in req.rules.items():
        rules[key] = CuttingRule(**model_rule.model_dump())
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
        }
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
        mode=mode,
    )
    if mode == "corte":
        filename = "corte_serra_portas.csv"
    elif mode == "vidro":
        filename = "corte_vidros_portas.csv"
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
    )
    return Response(
        content=json_bytes,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="extracao_portas.json"'},
    )
