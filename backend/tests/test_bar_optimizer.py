"""Testes automatizados do otimizador de corte em barras de 6m e integração API/exportação."""

from __future__ import annotations

import io
import sys
import time
import unittest
from collections import Counter
from copy import deepcopy
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.bar_optimizer import OptimizationConfig, build_bar_optimization
from app.cutting_engine import (
    RULES_FILE,
    CuttingRule,
    build_cutting_plan,
    load_rules,
)
from app.description_parser import parse_description
from app.html_parser import RawOpRow, parse_op_html
from main import STORE, app

SAMPLE_06_11 = Path(
    r"z:\Planejamento e Controle da Producao\Assistente Móveis\OP's\2026\11- NOVEMBRO\PORTAS\06-11.html"
)
SAMPLE_13_11 = Path(
    r"z:\Planejamento e Controle da Producao\Assistente Móveis\OP's\2026\11- NOVEMBRO\PORTAS\13-11.html"
)


def _make_bar(
    medida_mm: float,
    *,
    modelo: str = "RISK",
    eh_puxador: bool = False,
    tipo_perfil: str | None = None,
    codigo_perfil: str = "",
    acabamento: str = "DAKAR",
    funcao: str = "Vertical Quadro",
    qtd: int = 1,
    op: str = "1001",
    codigo: str = "2PTAG01",
    data_entrega: str = "25/11/2026",
) -> dict:
    tp = tipo_perfil or ("Puxador" if eh_puxador else "Lateral")
    return {
        "op": op,
        "codigo": codigo,
        "pedido": "9001",
        "data_entrega": data_entrega,
        "categoria": "PORTA DE BATER",
        "modelo": modelo,
        "codigo_perfil": codigo_perfil,
        "acabamento_perfil": acabamento,
        "funcao_barra": funcao,
        "orientacao": "VERTICAL",
        "eh_perfil_puxador": eh_puxador,
        "tipo_perfil": tp,
        "qtd_barras": qtd,
        "medida_nominal_mm": medida_mm,
        "desconto_mm": 0.0,
        "medida_corte_mm": medida_mm,
        "tipo_corte": "45°",
        "observacao_corte": "",
        "total_mm": round(medida_mm * qtd, 3),
        "total_metros": round((medida_mm * qtd) / 1000.0, 3),
    }


def _assert_piece_conservation(
    tc: unittest.TestCase, detailed_bars: list[dict], result: dict
) -> None:
    expected = Counter()
    for b in detailed_bars:
        med = round(float(b["medida_corte_mm"]), 3)
        qtd = int(round(float(b["qtd_barras"])))
        if med > 0 and qtd > 0:
            expected[med] += qtd

    actual = Counter()
    for bar in result["barras_otimizadas_flat"]:
        for p in bar["pecas"]:
            actual[round(float(p["medida_corte_mm"]), 3)] += 1
    for p in result["nao_alocados_flat"]:
        actual[round(float(p["medida_corte_mm"]), 3)] += 1

    tc.assertEqual(actual, expected)
    tc.assertEqual(
        result["resumo"]["total_pecas_entrada"],
        result["resumo"]["total_pecas_alocadas"]
        + result["resumo"]["total_pecas_nao_alocadas"],
    )

    # Verifica conservação e consistência matemática do Grupo 2 otimizado + KPIs
    g2_expected = Counter(
        round(float(p["medida_corte_mm"]), 3) for p in result["nao_alocados_flat"]
    )
    g2_actual = Counter()
    for bar in result["barras_grupo2_flat"]:
        tc.assertLessEqual(
            bar["consumido_mm"], bar["comprimento_barra_mm"] + 1e-6
        )
        meds = [p["medida_corte_mm"] for p in bar["pecas"]]
        tc.assertEqual(meds, sorted(meds, reverse=True))
        for p in bar["pecas"]:
            g2_actual[round(float(p["medida_corte_mm"]), 3)] += 1
    for p in result["pecas_inviaveis_flat"]:
        g2_actual[round(float(p["medida_corte_mm"]), 3)] += 1

    tc.assertEqual(g2_actual, g2_expected)
    r = result["resumo"]
    tc.assertEqual(
        r["total_pecas_alocadas_grupo2"] + r["total_pecas_inviaveis"],
        r["total_pecas_nao_alocadas"],
    )
    tc.assertEqual(
        r["total_barras_geral"], r["total_barras_6m"] + r["total_barras_grupo2"]
    )
    tc.assertAlmostEqual(
        r["total_perda_geral_mm"],
        round(r["total_perda_mm"] + r["total_perda_grupo2_mm"], 3),
        places=2,
    )


class TestBarOptimizer(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = load_rules()
        self.client = TestClient(app)

    def test_tricky_ffd_trap_and_greedy_trap(self) -> None:
        cfg = OptimizationConfig(comprimento_barra_mm=6000.0, perda_maxima_mm=200.0)

        # Caso onde FFD falha (agrupa 2500+2400 e deixa 2100+2000+1500+1400 sem fechar)
        ffd_bars = [_make_bar(m) for m in (2500, 2400, 2100, 2000, 1500, 1400)]
        res_ffd = build_bar_optimization(ffd_bars, cfg, self.rules)
        _assert_piece_conservation(self, ffd_bars, res_ffd)
        self.assertEqual(res_ffd["resumo"]["total_barras_6m"], 2)
        self.assertEqual(res_ffd["resumo"]["total_pecas_nao_alocadas"], 0)

        # Caso onde guloso de menor perda (3600+2400=6000) deixa 2300+2300+1100=5700 < 5800
        greedy_bars = [_make_bar(m) for m in (3600, 2400, 2300, 2300, 1100)]
        res_greedy = build_bar_optimization(greedy_bars, cfg, self.rules)
        _assert_piece_conservation(self, greedy_bars, res_greedy)
        self.assertEqual(res_greedy["resumo"]["total_barras_6m"], 2)
        self.assertEqual(res_greedy["resumo"]["total_pecas_nao_alocadas"], 0)

    def test_grouping_by_codigo_perfil_and_fallback_modelo_tipo(self) -> None:
        custom_rules = {k: CuttingRule(**deepcopy(v.to_dict())) for k, v in self.rules.items()}
        # Cadastra código 5307 apenas para Lateral de CATCH e DJEI; Puxador fica sem código
        custom_rules["CATCH"].codigo_perfil_lateral = "5307"
        custom_rules["DJEI"].codigo_perfil_lateral = "5307"
        custom_rules["CATCH"].codigo_perfil_puxador = ""
        custom_rules["DJEI"].codigo_perfil_puxador = ""

        # CATCH Lateral (3000) + DJEI Lateral (2950) devem se unir no grupo 5307 (5950 <= 6000)
        bars = [
            _make_bar(3000.0, modelo="CATCH", eh_puxador=False, codigo_perfil=""),
            _make_bar(2950.0, modelo="DJEI", eh_puxador=False, codigo_perfil=""),
            _make_bar(1200.0, modelo="CATCH", eh_puxador=True, codigo_perfil=""),
            _make_bar(900.0, modelo="DJEI", eh_puxador=True, codigo_perfil=""),
        ]
        res = build_bar_optimization(bars, OptimizationConfig(), custom_rules)
        _assert_piece_conservation(self, bars, res)

        by_name = {g["grupo_nome"]: g for g in res["grupos"]}
        self.assertIn("5307", by_name)
        self.assertEqual(by_name["5307"]["origem_agrupamento"], "codigo_perfil")
        self.assertEqual(by_name["5307"]["qtd_barras_6m"], 1)
        self.assertEqual(by_name["5307"]["total_pecas_alocadas"], 2)
        self.assertEqual(sorted(by_name["5307"]["modelos"]), ["CATCH", "DJEI"])

        # Fallback para Modelo + Tipo quando não há código cadastrado
        self.assertIn("CATCH — Puxador", by_name)
        self.assertEqual(by_name["CATCH — Puxador"]["origem_agrupamento"], "modelo_tipo")
        self.assertIn("DJEI — Puxador", by_name)
        self.assertEqual(by_name["DJEI — Puxador"]["origem_agrupamento"], "modelo_tipo")

    def test_descending_ordering_and_configurable_parameters(self) -> None:
        bars = [
            _make_bar(400.0, modelo="RISK", eh_puxador=False, op="1"),
            _make_bar(1850.0, modelo="RISK", eh_puxador=False, op="2"),
            _make_bar(950.0, modelo="RISK", eh_puxador=False, op="3"),
            _make_bar(3000.0, modelo="CATCH", eh_puxador=False, op="4", qtd=2),
            _make_bar(6200.0, modelo="ALLU", eh_puxador=False, op="5"),  # > 6000mm
            _make_bar(833.333, modelo="RISK", eh_puxador=False, op="6"),
        ]

        # 1) Kerf = 0 -> duas de 3000 fecham uma barra de 6m com perda 0
        res_no_kerf = build_bar_optimization(
            bars,
            OptimizationConfig(
                comprimento_barra_mm=6000.0,
                perda_maxima_mm=200.0,
                espessura_serra_mm=0.0,
            ),
            self.rules,
        )
        _assert_piece_conservation(self, bars, res_no_kerf)
        catch_grp = next(g for g in res_no_kerf["grupos"] if g["grupo_nome"] == "CATCH — Lateral")
        self.assertEqual(catch_grp["qtd_barras_6m"], 1)
        self.assertEqual(catch_grp["barras_fechadas"][0]["perda_mm"], 0.0)

        # Verifica ordenação estrita maior -> menor no Grupo 2 (global e por grupo)
        flat_meds = [p["medida_corte_mm"] for p in res_no_kerf["nao_alocados_flat"]]
        self.assertEqual(flat_meds, sorted(flat_meds, reverse=True))
        grp_meds = [
            p["medida_corte_mm"] for p in res_no_kerf["nao_alocados_agrupados_flat"]
        ]
        self.assertEqual(grp_meds, sorted(grp_meds, reverse=True))
        self.assertEqual(flat_meds[0], 6200.0)

        # 2) Kerf = 3 mm -> 3000 + 3000 + 3 = 6003 > 6000 -> CATCH não fecha barra
        res_kerf = build_bar_optimization(
            bars,
            OptimizationConfig(
                comprimento_barra_mm=6000.0,
                perda_maxima_mm=200.0,
                espessura_serra_mm=3.0,
            ),
            self.rules,
        )
        _assert_piece_conservation(self, bars, res_kerf)
        catch_grp_k = next(g for g in res_kerf["grupos"] if g["grupo_nome"] == "CATCH — Lateral")
        self.assertEqual(catch_grp_k["qtd_barras_6m"], 0)
        self.assertEqual(catch_grp_k["total_pecas_nao_alocadas"], 2)

        # 3) Perda máxima configurável (ex.: 2100 mm permite fechar grupo RISK de 4033.333mm)
        res_loose = build_bar_optimization(
            bars,
            OptimizationConfig(
                comprimento_barra_mm=6000.0,
                perda_maxima_mm=2100.0,
            ),
            self.rules,
        )
        _assert_piece_conservation(self, bars, res_loose)
        risk_grp = next(g for g in res_loose["grupos"] if g["grupo_nome"] == "RISK — Lateral")
        self.assertEqual(risk_grp["qtd_barras_6m"], 1)
        # Peças internas da barra ordenadas do maior para o menor
        inner_meds = [p["medida_corte_mm"] for p in risk_grp["barras_fechadas"][0]["pecas"]]
        self.assertEqual(inner_meds, sorted(inner_meds, reverse=True))

        # 4) Separar por acabamento vs unificado
        acab_bars = [
            _make_bar(3000.0, modelo="RISK", acabamento="DAKAR"),
            _make_bar(3000.0, modelo="RISK", acabamento="STEEL"),
        ]
        res_unified = build_bar_optimization(
            acab_bars, OptimizationConfig(separar_por_acabamento=False), self.rules
        )
        self.assertEqual(res_unified["resumo"]["total_barras_6m"], 1)
        res_split = build_bar_optimization(
            acab_bars, OptimizationConfig(separar_por_acabamento=True), self.rules
        )
        self.assertEqual(res_split["resumo"]["total_barras_6m"], 0)
        self.assertEqual(res_split["resumo"]["total_grupos"], 2)

        # 5) Desponte reduz comprimento útil
        res_desp = build_bar_optimization(
            [_make_bar(5950.0, modelo="RISK")],
            OptimizationConfig(comprimento_barra_mm=6000.0, perda_maxima_mm=200.0, desponte_mm=100.0),
            self.rules,
        )
        self.assertEqual(res_desp["resumo"]["total_barras_6m"], 0)
        self.assertIn("Maior que a barra útil", res_desp["nao_alocados_flat"][0]["motivo"])

    def test_group2_min_bars_3_to_2_and_kpis(self) -> None:
        # [2500, 2400, 1900, 1800, 1400, 1300] (soma 11300mm): com perda_max=100mm (w_min=5900),
        # nenhuma combinação fecha Grupo 1, mas Grupo 2 deve empacotar exatamente em 2 barras (5800 + 5500)
        bars = [_make_bar(m, op=str(i + 1)) for i, m in enumerate((2500, 2400, 1900, 1800, 1400, 1300))]
        cfg = OptimizationConfig(comprimento_barra_mm=6000.0, perda_maxima_mm=100.0)
        res = build_bar_optimization(bars, cfg, self.rules)
        _assert_piece_conservation(self, bars, res)

        r = res["resumo"]
        self.assertEqual(r["total_barras_6m"], 0)
        self.assertEqual(r["total_pecas_nao_alocadas"], 6)
        self.assertEqual(r["total_barras_grupo2"], 2)
        self.assertEqual(r["total_pecas_alocadas_grupo2"], 6)
        self.assertAlmostEqual(r["total_perda_grupo2_mm"], 700.0, places=3)
        self.assertAlmostEqual(r["aproveitamento_medio_grupo2_pct"], 94.17, places=2)
        self.assertEqual(r["total_barras_geral"], 2)
        self.assertAlmostEqual(r["total_perda_geral_mm"], 700.0, places=3)
        self.assertAlmostEqual(r["aproveitamento_medio_geral_pct"], 94.17, places=2)

        # Verifica peça > barra útil separada em inviáveis sem perder conservação
        bars_with_oversized = bars + [_make_bar(6250.0, op="99")]
        res_ov = build_bar_optimization(bars_with_oversized, cfg, self.rules)
        _assert_piece_conservation(self, bars_with_oversized, res_ov)
        self.assertEqual(res_ov["resumo"]["total_pecas_inviaveis"], 1)
        self.assertEqual(res_ov["resumo"]["total_barras_grupo2"], 2)
        self.assertEqual(res_ov["nao_alocados_flat"][0]["medida_corte_mm"], 6250.0)

    def test_real_samples_conservation_and_bounds(self) -> None:
        cfg = OptimizationConfig(comprimento_barra_mm=6000.0, perda_maxima_mm=200.0)
        for sample in (SAMPLE_06_11, SAMPLE_13_11):
            if not sample.exists():
                continue
            _, rows = parse_op_html(sample.read_text(encoding="utf-8", errors="replace"))
            items = [parse_description(r) for r in rows]
            det, _ = build_cutting_plan(items, self.rules)
            t0 = time.perf_counter()
            res = build_bar_optimization(det, cfg, self.rules)
            elapsed = time.perf_counter() - t0
            self.assertLess(elapsed, 2.0, f"Tempo excessivo em {sample.name}: {elapsed:.2f}s")
            _assert_piece_conservation(self, det, res)
            for bar in res["barras_otimizadas_flat"]:
                self.assertLessEqual(bar["perda_mm"], 200.0 + 1e-6)
                self.assertGreaterEqual(bar["perda_mm"], 0.0)
                meds = [p["medida_corte_mm"] for p in bar["pecas"]]
                self.assertEqual(meds, sorted(meds, reverse=True))
            flat_out = [p["medida_corte_mm"] for p in res["nao_alocados_flat"]]
            self.assertEqual(flat_out, sorted(flat_out, reverse=True))

    def test_api_optimize_rules_and_exports(self) -> None:
        rules_backup = RULES_FILE.read_text(encoding="utf-8")
        try:
            html_sample = """
            <html><body>
            LOCAL DE PRODUÇÃO = <b>PORTAS</b> DATA DE ABERTURA = <b>2026-11-19</b>
            <table>
              <tr><td><b>Data de Entrega 26/11/2026:</b></td></tr>
              <tr>
                <td>2PTAC1</td>
                <td>PORTA BATER CATCH C/PUXADOR LATERAL - DIREITA - LARGURA 500 - ALTURA 2450 - PERFIL DAKAR - PLACA INCOLOR</td>
                <td>2</td><td>10001</td><td></td><td>5001</td><td>1</td><td>SALA</td>
              </tr>
              <tr>
                <td>2PTAD1</td>
                <td>PORTA BATER DJEI C/PUXADOR LATERAL - DIREITA - LARGURA 500 - ALTURA 2450 - PERFIL DAKAR - PLACA INCOLOR</td>
                <td>1</td><td>10002</td><td></td><td>5002</td><td>1</td><td>SALA</td>
              </tr>
              <tr>
                <td>2PTAC2</td>
                <td>PORTA BATER CATCH C/PUXADOR SUPERIOR - DIREITA - LARGURA 1100 - ALTURA 700 - PERFIL DAKAR - PLACA INCOLOR</td>
                <td>1</td><td>10003</td><td></td><td>5003</td><td>1</td><td>COZINHA</td>
              </tr>
            </table>
            </body></html>
            """

            res_ext = self.client.post(
                "/api/extract/html",
                json={"html": html_sample, "source_name": "synthetic.html"},
            )
            self.assertEqual(res_ext.status_code, 200)
            data = res_ext.json()
            self.assertIn("otimizacao_barras", data)
            self.assertEqual(data["otimizacao_barras"]["config"]["perda_maxima_mm"], 200.0)

            # Atualiza código do perfil lateral via PUT /api/rules para unificar CATCH e DJEI
            rules_data = self.client.get("/api/rules").json()["rules"]
            rules_data["CATCH"]["codigo_perfil_lateral"] = "PERFIL-5307"
            rules_data["DJEI"]["codigo_perfil_lateral"] = "PERFIL-5307"
            res_put = self.client.put("/api/rules", json={"rules": rules_data})
            self.assertEqual(res_put.status_code, 200)
            recalc = res_put.json()["recalculated"]
            opt_groups = {
                g["grupo_nome"]: g for g in recalc["otimizacao_barras"]["grupos"]
            }
            self.assertIn("PERFIL-5307", opt_groups)
            self.assertEqual(opt_groups["PERFIL-5307"]["origem_agrupamento"], "codigo_perfil")
            # 3x 2450 (2 CATCH + 1 DJEI) + 1x 1100 = 2450 + 2450 + 1100 = 6000!
            self.assertGreaterEqual(opt_groups["PERFIL-5307"]["qtd_barras_6m"], 1)

            # POST /api/optimize/bars com parâmetros customizados e validação de erro
            res_bad = self.client.post(
                "/api/optimize/bars",
                json={"comprimento_barra_mm": 6000.0, "desponte_mm": 6000.0},
            )
            self.assertEqual(res_bad.status_code, 400)

            res_opt = self.client.post(
                "/api/optimize/bars",
                json={
                    "comprimento_barra_mm": 6000.0,
                    "perda_maxima_mm": 150.0,
                    "espessura_serra_mm": 0.0,
                    "desponte_mm": 0.0,
                    "separar_por_acabamento": False,
                },
            )
            self.assertEqual(res_opt.status_code, 200)
            opt_json = res_opt.json()
            self.assertEqual(opt_json["config"]["perda_maxima_mm"], 150.0)
            for kpi_key in (
                "aproveitamento_medio_pct",
                "total_perda_mm",
                "aproveitamento_medio_grupo2_pct",
                "total_perda_grupo2_mm",
                "aproveitamento_medio_geral_pct",
                "total_perda_geral_mm",
            ):
                self.assertIn(kpi_key, opt_json["resumo"])

            # Exportações XLSX, CSV e JSON incluem dados da otimização (G1 e G2)
            res_xlsx = self.client.post("/api/export/xlsx", json={})
            self.assertEqual(res_xlsx.status_code, 200)
            wb = load_workbook(io.BytesIO(res_xlsx.content))
            self.assertIn("Otimizacao_Barras_6m", wb.sheetnames)
            self.assertIn("Otimizacao_Grupo2_Barras", wb.sheetnames)
            self.assertIn("Otimizacao_Nao_Alocados", wb.sheetnames)

            res_csv_b = self.client.post(
                "/api/export/csv", json={"mode": "otimizacao_barras"}
            )
            self.assertEqual(res_csv_b.status_code, 200)
            self.assertIn("Padrao_Corte", res_csv_b.text)

            res_csv_g2 = self.client.post(
                "/api/export/csv", json={"mode": "otimizacao_grupo2"}
            )
            self.assertEqual(res_csv_g2.status_code, 200)
            self.assertIn("Padrao_Corte", res_csv_g2.text)

            res_csv_s = self.client.post(
                "/api/export/csv", json={"mode": "otimizacao_sobras"}
            )
            self.assertEqual(res_csv_s.status_code, 200)
            self.assertIn("Medida_Corte_mm", res_csv_s.text)

            res_json = self.client.post("/api/export/json", json={})
            self.assertEqual(res_json.status_code, 200)
            json_body = res_json.json()
            self.assertIn("otimizacao_barras", json_body)
            self.assertIn("aproveitamento_medio_geral_pct", json_body["otimizacao_barras"]["resumo"])
        finally:
            RULES_FILE.write_text(rules_backup, encoding="utf-8")
            STORE.optimization_config = OptimizationConfig()


if __name__ == "__main__":
    unittest.main()
