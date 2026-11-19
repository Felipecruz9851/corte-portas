"""Testes automatizados para extração HTML, parser construtivo, corte e API."""

from __future__ import annotations

import glob
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient

from app.cutting_engine import (
    CuttingRule,
    build_cutting_plan,
    compute_item_cuts,
    compute_item_glasses,
    load_rules,
)
from app.description_parser import parse_description
from app.html_parser import RawOpRow, parse_op_html
from main import app

SAMPLE_06_11 = Path(
    r"z:\Planejamento e Controle da Producao\Assistente Móveis\OP's\2026\11- NOVEMBRO\PORTAS\06-11.html"
)
SAMPLE_13_11 = Path(
    r"z:\Planejamento e Controle da Producao\Assistente Móveis\OP's\2026\11- NOVEMBRO\PORTAS\13-11.html"
)


class TestExtractionAndCutting(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = load_rules()
        self.client = TestClient(app)

    def test_parse_06_11_and_13_11_files(self) -> None:
        for html_path in (SAMPLE_06_11, SAMPLE_13_11):
            if not html_path.exists():
                self.skipTest(f"Arquivo de amostra não encontrado: {html_path}")

            html_text = html_path.read_text(encoding="utf-8", errors="replace")
            meta, rows = parse_op_html(html_text)
            self.assertEqual(meta["local_producao"], "PORTAS")
            self.assertGreater(len(rows), 0)

            for row in rows:
                ex = parse_description(row)
                self.assertEqual(ex.warnings, [], f"Warnings em {row.codigo}: {ex.warnings}")
                self.assertNotEqual(ex.modelo, "OUTRO")
                if not ex.eh_barra_avulsa:
                    self.assertIsNotNone(ex.largura_mm)
                    self.assertIsNotNone(ex.altura_mm)
                bars = compute_item_cuts(ex, self.rules)
                self.assertGreater(len(bars), 0, f"Sem barras para {row.codigo}")

    def test_specific_cases_from_plan(self) -> None:
        if not SAMPLE_06_11.exists() or not SAMPLE_13_11.exists():
            self.skipTest("Arquivos de amostra 06-11.html ou 13-11.html indisponíveis.")

        _, rows_06 = parse_op_html(
            SAMPLE_06_11.read_text(encoding="utf-8", errors="replace")
        )
        by_code_06 = {r.codigo: parse_description(r) for r in rows_06}

        # 2ESCAAVMFZT5J1: ESCADA ALLU, 2 escadas, 275 x 2236, 4 divisorias
        escada = by_code_06["2ESCAAVMFZT5J1"]
        self.assertEqual(escada.categoria, "LINHA ALLU")
        self.assertEqual(escada.modelo, "ALLU")
        self.assertEqual(escada.qtd_estruturas, 2)
        self.assertEqual(escada.largura_mm, 275.0)
        self.assertEqual(escada.altura_mm, 2236.0)
        self.assertTrue(escada.tem_divisorias)
        self.assertEqual(escada.qtd_divisorias, 4)
        self.assertEqual(escada.divisorias_mm, [150.0, 767.0, 1254.0, 1741.0])

        escada_bars = compute_item_cuts(escada, self.rules)
        bar_map = {b.funcao_barra: (b.qtd_barras, b.medida_corte_mm) for b in escada_bars}
        self.assertEqual(bar_map["Montante Vertical ALLU"], (4, 2236.0))
        self.assertEqual(bar_map["Travessa Quadro ALLU (Sup/Inf)"], (4, 275.0))
        self.assertEqual(bar_map["Divisória Interna ALLU"], (8, 275.0))

        # 2PTNP1FSU59P1 (EXTERNA c/ 2 puxadores) vs 2PTNP1FSU59P3 (INTERNA c/ 1 puxador)
        correr_ext = by_code_06["2PTNP1FSU59P1"]
        self.assertEqual(correr_ext.categoria, "PORTA DE CORRER")
        self.assertEqual(correr_ext.modelo, "RISK")
        self.assertEqual(correr_ext.posicao_folha, "EXTERNA")
        self.assertEqual(correr_ext.qtd_puxadores, 2)
        self.assertEqual(correr_ext.posicao_puxador, "DUPLO (DIREITA E ESQUERDA)")

        correr_int = by_code_06["2PTNP1FSU59P3"]
        self.assertEqual(correr_int.posicao_folha, "INTERNA")
        self.assertEqual(correr_int.qtd_puxadores, 1)
        self.assertEqual(correr_int.posicao_puxador, "LATERAL (DIREITA)")

        _, rows_13 = parse_op_html(
            SAMPLE_13_11.read_text(encoding="utf-8", errors="replace")
        )
        by_code_13 = {r.codigo: parse_description(r) for r in rows_13}

        # 2PTAC48WPP631: PORTA BATER CATCH, 425 x 936, SUPERIOR, DIREITA
        catch = by_code_13["2PTAC48WPP631"]
        self.assertEqual(catch.categoria, "PORTA DE BATER")
        self.assertEqual(catch.modelo, "CATCH")
        self.assertEqual(catch.largura_mm, 425.0)
        self.assertEqual(catch.altura_mm, 936.0)
        self.assertEqual(catch.qtd_puxadores, 1)
        self.assertEqual(catch.posicao_puxador, "SUPERIOR")
        self.assertEqual(catch.lado, "DIREITA")
        self.assertEqual(catch.qtd_divisorias, 0)

        # 2PTAG1ZX6TWE1: PORTA BATER CLEAR S, 611 x 687, SUPERIOR, DIREITA
        clear_s = by_code_13["2PTAG1ZX6TWE1"]
        self.assertEqual(clear_s.categoria, "PORTA DE BATER")
        self.assertEqual(clear_s.modelo, "CLEAR S")
        self.assertEqual(clear_s.largura_mm, 611.0)
        self.assertEqual(clear_s.altura_mm, 687.0)
        self.assertEqual(clear_s.qtd_puxadores, 1)
        self.assertEqual(clear_s.posicao_puxador, "SUPERIOR")
        self.assertEqual(clear_s.lado, "DIREITA")

    def test_november_2026_batch_zero_warnings(self) -> None:
        nov_files = glob.glob(
            r"z:\Planejamento e Controle da Producao\Assistente Móveis\OP's\2026\11- NOVEMBRO\PORTAS\*.html"
        )
        if not nov_files:
            self.skipTest("Arquivos de novembro/2026 não disponíveis.")

        total_rows = 0
        for fpath in nov_files:
            _, rows = parse_op_html(
                Path(fpath).read_text(encoding="utf-8", errors="replace")
            )
            for row in rows:
                total_rows += 1
                ex = parse_description(row)
                self.assertEqual(
                    ex.warnings, [], f"Falha em {Path(fpath).name} / {row.codigo}: {ex.warnings}"
                )
        self.assertGreater(total_rows, 0)

    def test_api_endpoints_extract_rules_and_export(self) -> None:
        if not SAMPLE_13_11.exists():
            self.skipTest("Arquivo 13-11.html indisponível.")

        html_text = SAMPLE_13_11.read_text(encoding="utf-8", errors="replace")

        # 1) GET / e estáticos do frontend
        res_home = self.client.get("/")
        self.assertEqual(res_home.status_code, 200)
        self.assertIn("Extrator Construtivo", res_home.text)

        res_js = self.client.get("/static/app.js")
        self.assertEqual(res_js.status_code, 200)

        # 2) POST /api/extract/html
        res = self.client.post(
            "/api/extract/html",
            json={"html": html_text, "source_name": "13-11.html"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["meta"]["total_linhas"], 37)
        self.assertGreater(data["kpis"]["total_barras_corte"], 0)

        # 3) GET /api/rules, PUT /api/rules e POST /api/rules/reset
        res_rules = self.client.get("/api/rules")
        self.assertEqual(res_rules.status_code, 200)
        rules_payload = res_rules.json()["rules"]
        self.assertIn("ALLU", rules_payload)

        modified = dict(rules_payload)
        modified["CATCH"] = dict(modified["CATCH"], desconto_vertical_mm=4.0)
        res_put = self.client.put("/api/rules", json={"rules": modified})
        self.assertEqual(res_put.status_code, 200)
        catch_bars = [
            b
            for b in res_put.json()["recalculated"]["corte_detalhado"]
            if b["modelo"] == "CATCH" and b["orientacao"] == "VERTICAL"
        ]
        self.assertTrue(all(b["desconto_mm"] == 4.0 for b in catch_bars))

        res_reset = self.client.post("/api/rules/reset")
        self.assertEqual(res_reset.status_code, 200)
        self.assertEqual(res_reset.json()["rules"]["CATCH"]["desconto_vertical_mm"], 0.0)

        # 4) Exportações XLSX, CSV e JSON
        res_xlsx = self.client.post("/api/export/xlsx", json={})
        self.assertEqual(res_xlsx.status_code, 200)
        self.assertIn(
            "spreadsheetml.sheet", res_xlsx.headers.get("content-type", "")
        )
        self.assertGreater(len(res_xlsx.content), 1000)

        res_csv = self.client.post("/api/export/csv", json={"mode": "corte"})
        self.assertEqual(res_csv.status_code, 200)
        self.assertIn("medida_corte_mm", res_csv.text)

        res_csv_vidro = self.client.post("/api/export/csv", json={"mode": "vidro"})
        self.assertEqual(res_csv_vidro.status_code, 200)
        self.assertIn("largura_corte_mm", res_csv_vidro.text)

        res_json = self.client.post("/api/export/json", json={})
        self.assertEqual(res_json.status_code, 200)
        self.assertIn("corte_agrupado", res_json.json())
        self.assertIn("vidro_agrupado", res_json.json())

        # 5) POST /api/extract/erp (com mock HTTP para validar fluxo completo)
        with patch("app.erp_client.ERPClient.fetch_op_abertura", return_value=html_text):
            res_erp = self.client.post(
                "/api/extract/erp",
                json={
                    "data": "2026-11-13",
                    "cod_empresa": "11",
                    "local": "PORTAS",
                    "phpsessid": "dummy",
                },
            )
            self.assertEqual(res_erp.status_code, 200)
            self.assertEqual(res_erp.json()["meta"]["total_linhas"], 37)

    def test_clear_g_adjacent_handle_discount(self) -> None:
        # Puxador lateral (80mm vs quadro 45mm => -35mm nas horizontais adjacentes)
        row_lat = RawOpRow(
            local_producao="PORTAS",
            data_abertura="2026-11-18",
            data_entrega="25/11/2026",
            codigo="2PTAGIIM4F9I1",
            descricao="PORTA BATER CLEAR G C/PUXADOR LATERAL - DIREITA - LARGURA 279 - ALTURA 1366 - PERFIL ALUMINIO - PLACA INCOLOR - FURACAO PAGINA 170",
            quantidade=1.0,
            op="1990001",
            observacao="",
            pedido="200001",
            item_pedido="100",
            ambiente="COZINHA",
            valor_insumos=None,
            valor_mp=None,
        )
        ex_lat = parse_description(row_lat)
        bars_lat = compute_item_cuts(ex_lat, self.rules)
        by_fn_lat = {b.funcao_barra: b for b in bars_lat}
        self.assertEqual(by_fn_lat["Vertical c/ Puxador (DIREITA)"].medida_corte_mm, 1366.0)
        self.assertEqual(by_fn_lat["Vertical Quadro"].medida_corte_mm, 1366.0)
        self.assertEqual(by_fn_lat["Horizontal Quadro"].desconto_mm, 35.0)
        self.assertEqual(by_fn_lat["Horizontal Quadro"].medida_corte_mm, 244.0)

        # Puxador superior (80mm vs quadro 45mm => -35mm nas verticais adjacentes)
        row_sup = RawOpRow(
            local_producao="PORTAS",
            data_abertura="2026-11-18",
            data_entrega="25/11/2026",
            codigo="2PTAGOKZTR611",
            descricao="PORTA BATER CLEAR G C/PUXADOR SUPERIOR - ESQUERDA - LARGURA 250 - ALTURA 400 - PERFIL STEEL - PLACA PERFURADA - FURACAO PAGINA 160",
            quantidade=1.0,
            op="1990002",
            observacao="",
            pedido="200002",
            item_pedido="100",
            ambiente="COZINHA",
            valor_insumos=None,
            valor_mp=None,
        )
        ex_sup = parse_description(row_sup)
        bars_sup = compute_item_cuts(ex_sup, self.rules)
        by_fn_sup = {b.funcao_barra: b for b in bars_sup}
        self.assertEqual(by_fn_sup["Horizontal c/ Puxador"].medida_corte_mm, 250.0)
        self.assertEqual(by_fn_sup["Horizontal Quadro"].medida_corte_mm, 250.0)
        self.assertEqual(by_fn_sup["Vertical Quadro"].desconto_mm, 35.0)
        self.assertEqual(by_fn_sup["Vertical Quadro"].medida_corte_mm, 365.0)

    def test_glass_cutting_discounts_by_handle_position(self) -> None:
        custom_rules = dict(self.rules)
        custom_rules["RISK"] = CuttingRule(
            modelo="RISK",
            descricao="Risk teste vidro",
            tipo_corte="45°",
            desconto_vertical_mm=0.0,
            desconto_horizontal_mm=0.0,
            desconto_divisoria_mm=0.0,
            desconto_vidro_lateral_mm=10.0,
            desconto_vidro_puxador_mm=25.0,
        )

        def make_row(codigo: str, desc: str) -> RawOpRow:
            return RawOpRow(
                local_producao="PORTAS",
                data_abertura="2026-11-18",
                data_entrega="25/11/2026",
                codigo=codigo,
                descricao=desc,
                quantidade=2.0,
                op="1999999",
                observacao="",
                pedido="200000",
                item_pedido="100",
                ambiente="SALA",
                valor_insumos=None,
                valor_mp=None,
            )

        # 1) Sem puxador: 2x Lateral em L e A (2*10 = 20mm em ambos)
        g_sem = compute_item_glasses(
            parse_description(
                make_row(
                    "2PTNP1",
                    "PORTA BATER RISK_DIREITA - SEM PUXADOR - LARGURA 500_ALTURA 1000_PERFIL DAKAR_PLACA ESPELHO PRATA",
                )
            ),
            custom_rules,
        )[0]
        self.assertEqual(g_sem.qtd_pecas, 2)
        self.assertEqual(g_sem.desconto_largura_mm, 20.0)
        self.assertEqual(g_sem.largura_corte_mm, 480.0)
        self.assertEqual(g_sem.desconto_altura_mm, 20.0)
        self.assertEqual(g_sem.altura_corte_mm, 980.0)

        # 2) Puxador Superior: L desconta 2x Lateral (20mm), A desconta 1x Puxador + 1x Lateral (35mm)
        g_sup = compute_item_glasses(
            parse_description(
                make_row(
                    "2PTAG2",
                    "PORTA BATER RISK USINADO SUPERIOR - DIREITA - LARGURA 500 - ALTURA 1000 - PERFIL UMBRA - PLACA ESPELHO PRATA",
                )
            ),
            custom_rules,
        )[0]
        self.assertEqual(g_sup.largura_corte_mm, 480.0)
        self.assertEqual(g_sup.desconto_altura_mm, 35.0)
        self.assertEqual(g_sup.altura_corte_mm, 965.0)

        # 3) Puxador Lateral (1 lado): L desconta 1x Puxador + 1x Lateral (35mm), A desconta 2x Lateral (20mm)
        g_lat = compute_item_glasses(
            parse_description(
                make_row(
                    "2PTNP2",
                    "PORTA BATER RISK_DIREITA_LARGURA 500_ALTURA 1000_PERFIL DAKAR_PLACA ESPELHO PRATA",
                )
            ),
            custom_rules,
        )[0]
        self.assertEqual(g_lat.desconto_largura_mm, 35.0)
        self.assertEqual(g_lat.largura_corte_mm, 465.0)
        self.assertEqual(g_lat.altura_corte_mm, 980.0)

        # 4) Puxador Duplo (2 lados): L desconta 2x Puxador (50mm), A desconta 2x Lateral (20mm)
        g_dup = compute_item_glasses(
            parse_description(
                make_row(
                    "2PTNP3",
                    "PORTA SOFT CLOSING SI OCEAN 80_CORRER RISK_EXTERNA_C/ PUXADOR DIREITO E ESQUERDO_LARGURA 500_ALTURA 1000_PERFIL DAKAR_PLACA ESPELHO PRATA",
                )
            ),
            custom_rules,
        )[0]
        self.assertEqual(g_dup.desconto_largura_mm, 50.0)
        self.assertEqual(g_dup.largura_corte_mm, 450.0)
        self.assertEqual(g_dup.altura_corte_mm, 980.0)

    def test_api_extract_multiple_html_files_and_clear_session(self) -> None:
        html_a = """
        <html><body>
        LOCAL DE PRODUÇÃO = <b>PORTAS</b> DATA DE ABERTURA = <b>2026-11-18</b>
        <table>
          <tr><td><b>Data de Entrega 25/11/2026:</b></td></tr>
          <tr>
            <td>2PTAC1</td>
            <td>PORTA BATER CATCH C/PUXADOR LATERAL - DIREITA - LARGURA 500 - ALTURA 2400 - PERFIL DAKAR - PLACA INCOLOR</td>
            <td>1</td><td>20001</td><td></td><td>6001</td><td>1</td><td>SALA</td>
          </tr>
        </table>
        </body></html>
        """
        html_b = """
        <html><body>
        LOCAL DE PRODUÇÃO = <b>PORTAS</b> DATA DE ABERTURA = <b>2026-11-19</b>
        <table>
          <tr><td><b>Data de Entrega 26/11/2026:</b></td></tr>
          <tr>
            <td>2PTAC2</td>
            <td>PORTA BATER CATCH C/PUXADOR LATERAL - DIREITA - LARGURA 500 - ALTURA 2400 - PERFIL DAKAR - PLACA INCOLOR</td>
            <td>1</td><td>20002</td><td></td><td>6002</td><td>1</td><td>COZINHA</td>
          </tr>
        </table>
        </body></html>
        """

        # 1) Upload múltiplo consolidado via files[]
        res_multi = self.client.post(
            "/api/extract/html",
            json={
                "files": [
                    {"html": html_a, "source_name": "lote_a.html"},
                    {"html": html_b, "source_name": "lote_b.html"},
                ]
            },
        )
        self.assertEqual(res_multi.status_code, 200)
        data_multi = res_multi.json()
        self.assertEqual(data_multi["meta"]["total_linhas"], 2)
        self.assertEqual(len(data_multi["meta"]["consultas"]), 2)
        self.assertEqual(
            [c["origem"] for c in data_multi["meta"]["consultas"]],
            ["lote_a.html", "lote_b.html"],
        )
        self.assertTrue(all(c["total_linhas"] == 1 for c in data_multi["meta"]["consultas"]))
        self.assertEqual(
            data_multi["meta"]["datas_abertura"],
            ["2026-11-18", "2026-11-19"],
        )
        self.assertGreater(data_multi["kpis"]["total_barras_corte"], 0)
        # Duas portas CATCH com lateral 2400mm (1 por HTML) somam 4800mm <= 6000mm
        # + horizontais 500mm => otimização consolida peças dos dois HTMLs em barras 6m
        self.assertEqual(
            data_multi["otimizacao_barras"]["cenarios"]["material"]["resumo"]["total_pecas_entrada"],
            data_multi["kpis"]["total_barras_corte"],
        )
        self.assertEqual(
            data_multi["otimizacao_barras"]["cenarios"]["tempo_execucao"]["resumo"]["total_pecas_entrada"],
            data_multi["kpis"]["total_barras_corte"],
        )

        # 2) Retrocompatibilidade com payload único {html, source_name}
        res_single = self.client.post(
            "/api/extract/html",
            json={"html": html_a, "source_name": "lote_a.html"},
        )
        self.assertEqual(res_single.status_code, 200)
        self.assertEqual(res_single.json()["meta"]["total_linhas"], 1)

        # 3) Validações HTTP 400
        self.assertEqual(self.client.post("/api/extract/html", json={}).status_code, 400)
        self.assertEqual(
            self.client.post("/api/extract/html", json={"files": []}).status_code, 400
        )
        res_empty_file = self.client.post(
            "/api/extract/html",
            json={"files": [{"html": "   ", "source_name": "vazio.html"}]},
        )
        self.assertEqual(res_empty_file.status_code, 400)
        self.assertIn("vazio.html", res_empty_file.json()["detail"])

        # 4) Limpeza da sessão via POST /api/session/clear
        res_clear = self.client.post("/api/session/clear")
        self.assertEqual(res_clear.status_code, 200)
        self.assertEqual(res_clear.json(), {"status": "cleared"})
        self.assertEqual(self.client.post("/api/export/json", json={}).status_code, 400)

    def test_cut_angles_per_end_mixed_and_dividers(self) -> None:
        rules_backup = RULES_FILE_PATH = Path(BACKEND_DIR / "app" / "data" / "regras_corte.json").read_text(encoding="utf-8")
        try:
            mixed_rules = dict(self.rules)
            mixed_rules["CATCH"] = CuttingRule(
                modelo="CATCH",
                descricao="Catch misto",
                tipo_corte="45° / 90° (Misto)",
                desconto_vertical_mm=0.0,
                desconto_horizontal_mm=0.0,
                desconto_divisoria_mm=0.0,
                angulo_corte_quadro=45,
                angulo_corte_puxador=90,
                angulo_corte_divisoria=90,
                perfil_simetrico_lateral=True,
                perfil_simetrico_puxador=False,
                largura_perfil_quadro_mm=45.0,
                largura_perfil_puxador_mm=80.0,
            )

            def make_row(codigo: str, desc: str) -> RawOpRow:
                return RawOpRow(
                    local_producao="PORTAS",
                    data_abertura="2026-11-19",
                    data_entrega="26/11/2026",
                    codigo=codigo,
                    descricao=desc,
                    quantidade=1.0,
                    op="200100",
                    observacao="",
                    pedido="300100",
                    item_pedido="1",
                    ambiente="SALA",
                    valor_insumos=None,
                    valor_mp=None,
                )

            # 0 puxadores -> Quadro 45° / 45°
            bars_0 = compute_item_cuts(
                parse_description(
                    make_row(
                        "2PTAC0",
                        "PORTA BATER CATCH S/PUXADOR - DIREITA - LARGURA 500 - ALTURA 2000 - PERFIL DAKAR - PLACA INCOLOR",
                    )
                ),
                mixed_rules,
            )
            self.assertEqual({(b.angulo_esq, b.angulo_dir) for b in bars_0}, {(45, 45)})

            # 1 puxador lateral + travessa -> Puxador 90°/90°, Quadro Vert 45°/45°, Quadro Horiz 45°/90°, Divisória 90°/90°
            bars_lat = compute_item_cuts(
                parse_description(
                    make_row(
                        "2PTAC1",
                        "PORTA BATER CATCH C/PUXADOR LATERAL - DIREITA - LARGURA 500 - ALTURA 2000 - PERFIL DAKAR - PLACA INCOLOR - TRAVESSA A 1000MM",
                    )
                ),
                mixed_rules,
            )
            by_fn_lat = {b.funcao_barra: (b.angulo_esq, b.angulo_dir, b.angulos_corte) for b in bars_lat}
            self.assertEqual(by_fn_lat["Vertical c/ Puxador (DIREITA)"], (90, 90, "90° / 90°"))
            self.assertEqual(by_fn_lat["Vertical Quadro"], (45, 45, "45° / 45°"))
            self.assertEqual(by_fn_lat["Horizontal Quadro"], (45, 90, "45° / 90°"))
            self.assertEqual(by_fn_lat["Travessa Divisória Interna"], (90, 90, "90° / 90°"))
            sim_by_fn = {
                b.funcao_barra: (b.perfil_simetrico, b.largura_perfil_mm)
                for b in bars_lat
            }
            self.assertEqual(sim_by_fn["Vertical Quadro"], (True, 45.0))
            self.assertEqual(sim_by_fn["Horizontal Quadro"], (True, 45.0))
            self.assertEqual(sim_by_fn["Vertical c/ Puxador (DIREITA)"], (False, 80.0))

            # 1 puxador superior -> Horiz Pux 90°/90°, Horiz Quadro 45°/45°, Vert Quadro 45°/90°
            bars_sup = compute_item_cuts(
                parse_description(
                    make_row(
                        "2PTAC2",
                        "PORTA BATER CATCH C/PUXADOR SUPERIOR - DIREITA - LARGURA 500 - ALTURA 1000 - PERFIL DAKAR - PLACA INCOLOR",
                    )
                ),
                mixed_rules,
            )
            by_fn_sup = {b.funcao_barra: (b.angulo_esq, b.angulo_dir) for b in bars_sup}
            self.assertEqual(by_fn_sup["Horizontal c/ Puxador"], (90, 90))
            self.assertEqual(by_fn_sup["Horizontal Quadro"], (45, 45))
            self.assertEqual(by_fn_sup["Vertical Quadro"], (45, 90))

            # 2 puxadores -> Vert Pux 90°/90°, Horiz Quadro 90°/90°
            bars_dup = compute_item_cuts(
                parse_description(
                    make_row(
                        "2PTAC3",
                        "PORTA CORRER CATCH C/ PUXADOR DIREITO E ESQUERDO - LARGURA 800 - ALTURA 2200 - PERFIL DAKAR - PLACA INCOLOR",
                    )
                ),
                mixed_rules,
            )
            self.assertEqual({(b.angulo_esq, b.angulo_dir) for b in bars_dup}, {(90, 90)})

            # Barra linear avulsa -> sempre 90° / 90°
            bars_av = compute_item_cuts(
                parse_description(
                    make_row(
                        "2BARRA1",
                        "BARRA ALLU - ENVIAR SOMENTE A BARRA CORTADA COM LARGURA DE 1200 MM",
                    )
                ),
                mixed_rules,
            )
            self.assertEqual((bars_av[0].angulo_esq, bars_av[0].angulo_dir), (90, 90))

            # Round-trip PUT /api/rules preservando novos campos angulo_corte_*
            rules_api = self.client.get("/api/rules").json()["rules"]
            rules_api["CATCH"]["tipo_corte"] = "45° / 90° (Misto)"
            rules_api["CATCH"]["angulo_corte_quadro"] = 45
            rules_api["CATCH"]["angulo_corte_puxador"] = 90
            rules_api["CATCH"]["angulo_corte_divisoria"] = 90
            rules_api["CATCH"]["perfil_simetrico_lateral"] = True
            rules_api["CATCH"]["perfil_simetrico_puxador"] = False
            res_put = self.client.put("/api/rules", json={"rules": rules_api})
            self.assertEqual(res_put.status_code, 200)
            catch_saved = res_put.json()["rules"]["CATCH"]
            self.assertEqual(catch_saved["angulo_corte_quadro"], 45)
            self.assertEqual(catch_saved["angulo_corte_puxador"], 90)
            self.assertEqual(catch_saved["angulo_corte_divisoria"], 90)
            self.assertIs(catch_saved["perfil_simetrico_lateral"], True)
            self.assertIs(catch_saved["perfil_simetrico_puxador"], False)
        finally:
            Path(BACKEND_DIR / "app" / "data" / "regras_corte.json").write_text(
                rules_backup, encoding="utf-8"
            )


if __name__ == "__main__":
    unittest.main()
