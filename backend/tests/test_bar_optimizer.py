"""Testes automatizados do otimizador de barras de 6 m (Material vs Tempo de Execução)."""

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
from app.html_parser import parse_op_html
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
    tipo_corte: str = "45°",
    angulo_esq: int = 45,
    angulo_dir: int = 45,
    perfil_simetrico: bool = False,
    largura_perfil_mm: float = 0.0,
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
        "tipo_corte": tipo_corte,
        "angulo_esq": angulo_esq,
        "angulo_dir": angulo_dir,
        "angulos_corte": f"{angulo_esq}° / {angulo_dir}°",
        "perfil_simetrico": perfil_simetrico,
        "largura_perfil_mm": largura_perfil_mm,
        "observacao_corte": "",
        "total_mm": round(medida_mm * qtd, 3),
        "total_metros": round((medida_mm * qtd) / 1000.0, 3),
    }


def _assert_scenarios_conservation(
    tc: unittest.TestCase, detailed_bars: list[dict], result: dict
) -> None:
    expected = Counter()
    for b in detailed_bars:
        med = round(float(b["medida_corte_mm"]), 3)
        qtd = int(round(float(b["qtd_barras"])))
        if med > 0 and qtd > 0:
            expected[med] += qtd

    inviaveis_cnt = Counter(
        round(float(p["medida_corte_mm"]), 3) for p in result["pecas_inviaveis_flat"]
    )

    for scen_id in ("material", "tempo_execucao"):
        scen = result["cenarios"][scen_id]
        actual = Counter(inviaveis_cnt)
        for bar in scen["barras_flat"]:
            tc.assertLessEqual(bar["consumido_mm"], bar["comprimento_barra_mm"] + 1e-6)
            for p in bar["pecas"]:
                actual[round(float(p["medida_corte_mm"]), 3)] += 1

        tc.assertEqual(actual, expected, f"Falha de conservação em {scen_id}")
        r = scen["resumo"]
        tc.assertEqual(
            r["total_pecas_entrada"],
            r["total_pecas_alocadas"] + r["total_pecas_inviaveis"],
        )

    # Verifica conservação também no roteiro_flat do cenário tempo_execucao
    roteiro_cnt = Counter(inviaveis_cnt)
    for step in result["cenarios"]["tempo_execucao"]["roteiro_flat"]:
        med = round(float(step["medida_corte_mm"]), 3)
        for alloc in step["alocacoes"]:
            roteiro_cnt[med] += alloc["qtd_cortes"]
    tc.assertEqual(roteiro_cnt, expected, "Falha de conservação no roteiro_flat")


class TestBarOptimizer(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = load_rules()
        self.client = TestClient(app)

    def test_material_global_vs_old_split_and_exact_packing(self) -> None:
        cfg = OptimizationConfig(comprimento_barra_mm=6000.0)

        # Caso que caía em 3 barras no antigo split G1+G2, mas fecha exatamente em 2 barras
        split_trap = [_make_bar(m) for m in (2900, 2900, 2500, 2500, 600, 600)]
        res_split = build_bar_optimization(split_trap, cfg, self.rules)
        _assert_scenarios_conservation(self, split_trap, res_split)
        mat_r = res_split["cenarios"]["material"]["resumo"]
        self.assertEqual(mat_r["total_barras"], 2)
        self.assertEqual(mat_r["total_perda_mm"], 0.0)
        self.assertEqual(mat_r["aproveitamento_medio_pct"], 100.0)

        # Caso onde FFD falha (precisa de redução/exact fill para fechar em 2 barras)
        ffd_trap = [_make_bar(m) for m in (2500, 2400, 2100, 2000, 1500, 1400)]
        res_ffd = build_bar_optimization(ffd_trap, cfg, self.rules)
        _assert_scenarios_conservation(self, ffd_trap, res_ffd)
        self.assertEqual(res_ffd["cenarios"]["material"]["resumo"]["total_barras"], 2)
        self.assertEqual(res_ffd["cenarios"]["material"]["resumo"]["total_perda_mm"], 100.0)

        # Caso de redução 3-para-2 ([2500, 2400, 1900, 1800, 1400, 1300])
        red_3_2 = [_make_bar(m) for m in (2500, 2400, 1900, 1800, 1400, 1300)]
        res_3_2 = build_bar_optimization(red_3_2, cfg, self.rules)
        _assert_scenarios_conservation(self, red_3_2, res_3_2)
        r32 = res_3_2["cenarios"]["material"]["resumo"]
        self.assertEqual(r32["total_barras"], 2)
        self.assertAlmostEqual(r32["total_perda_mm"], 700.0, places=3)
        self.assertAlmostEqual(r32["aproveitamento_medio_pct"], 94.17, places=2)

    def test_material_chaining_reduces_adjustments_and_zero_for_uniform(self) -> None:
        # 2 barras com [2489, 2489, 956]: barra 1 termina em 956 e barra 2 inicia em 956 -> 2 trocas
        bars = [
            _make_bar(2489.0, op="1", qtd=4),
            _make_bar(956.0, op="2", qtd=2),
        ]
        res = build_bar_optimization(bars, OptimizationConfig(), self.rules)
        _assert_scenarios_conservation(self, bars, res)
        mat = res["cenarios"]["material"]
        self.assertEqual(mat["resumo"]["total_barras"], 2)
        self.assertEqual(mat["resumo"]["total_ajustes_corte"], 2)
        b1, b2 = mat["barras_flat"]
        self.assertFalse(b1["troca_entrada"])
        self.assertFalse(b2["troca_entrada"])
        self.assertEqual(b1["pecas"][-1]["medida_corte_mm"], b2["pecas"][0]["medida_corte_mm"])

        # Peças idênticas -> 0 trocas de medida em ambos os cenários
        uniform = [_make_bar(936.0, qtd=10)]
        res_u = build_bar_optimization(uniform, OptimizationConfig(), self.rules)
        self.assertEqual(res_u["cenarios"]["material"]["resumo"]["total_ajustes_corte"], 0)
        self.assertEqual(res_u["cenarios"]["tempo_execucao"]["resumo"]["total_ajustes_corte"], 0)

    def test_tempo_execucao_ffd_route_and_min_adjustments(self) -> None:
        bars = [
            _make_bar(700.0, op="4", qtd=2),
            _make_bar(2800.0, op="1", qtd=2),
            _make_bar(1500.0, op="3", qtd=2),
            _make_bar(2400.0, op="2", qtd=1),
        ]
        res = build_bar_optimization(bars, OptimizationConfig(), self.rules)
        _assert_scenarios_conservation(self, bars, res)

        tmp = res["cenarios"]["tempo_execucao"]
        grp = tmp["grupos"][0]
        roteiro = grp["roteiro_medidas"]

        # Passos estritamente ordenados da maior medida para a menor
        meds = [s["medida_corte_mm"] for s in roteiro]
        self.assertEqual(meds, [2800.0, 2400.0, 1500.0, 700.0])
        self.assertEqual(grp["ajustes_corte"], 3)  # 4 medidas distintas - 1

        # Passo 1 (2800 x2 = 5600) abre Barra nova #1
        self.assertFalse(roteiro[0]["troca_medida"])
        self.assertEqual(roteiro[0]["alocacoes"][0]["origem_barra"], "Barra nova")
        self.assertFalse(roteiro[0]["alocacoes"][0]["eh_sobra"])
        # Passo 2 (2400) abre Barra nova #2
        self.assertTrue(roteiro[1]["troca_medida"])
        # Passo 3 (1500 x2 = 3000) cabe na Sobra da Barra #2 (sobra era 3600 -> fica 600)
        alloc_1500 = roteiro[2]["alocacoes"][0]
        self.assertTrue(alloc_1500["eh_sobra"])
        self.assertEqual(alloc_1500["origem_barra"], "Sobra da Barra #2")
        self.assertEqual(alloc_1500["sobra_antes_mm"], 3600.0)
        self.assertEqual(alloc_1500["sobra_depois_mm"], 600.0)

    def test_grouping_codigo_perfil_fallback_and_params(self) -> None:
        custom_rules = {k: CuttingRule(**deepcopy(v.to_dict())) for k, v in self.rules.items()}
        custom_rules["CATCH"].codigo_perfil_lateral = "5307"
        custom_rules["DJEI"].codigo_perfil_lateral = "5307"
        custom_rules["CATCH"].codigo_perfil_puxador = ""
        custom_rules["DJEI"].codigo_perfil_puxador = ""

        bars = [
            _make_bar(3000.0, modelo="CATCH", eh_puxador=False),
            _make_bar(2950.0, modelo="DJEI", eh_puxador=False),
            _make_bar(1200.0, modelo="CATCH", eh_puxador=True),
            _make_bar(6150.0, modelo="RISK", eh_puxador=False),  # > 6000mm
        ]

        res = build_bar_optimization(bars, OptimizationConfig(), custom_rules)
        _assert_scenarios_conservation(self, bars, res)

        by_name = {g["grupo_nome"]: g for g in res["cenarios"]["material"]["grupos"]}
        self.assertIn("5307", by_name)
        self.assertEqual(by_name["5307"]["origem_agrupamento"], "codigo_perfil")
        self.assertEqual(by_name["5307"]["qtd_barras"], 1)
        self.assertIn("CATCH — Puxador", by_name)
        self.assertEqual(by_name["CATCH — Puxador"]["origem_agrupamento"], "modelo_tipo")
        self.assertEqual(len(res["pecas_inviaveis_flat"]), 1)
        self.assertEqual(res["pecas_inviaveis_flat"][0]["medida_corte_mm"], 6150.0)

        # Kerf = 3 mm impede duas de 3000 mm na mesma barra de 6000 mm
        kerf_bars = [_make_bar(3000.0, modelo="CATCH", qtd=2)]
        res_kerf = build_bar_optimization(
            kerf_bars,
            OptimizationConfig(comprimento_barra_mm=6000.0, espessura_serra_mm=3.0),
            self.rules,
        )
        self.assertEqual(res_kerf["cenarios"]["material"]["resumo"]["total_barras"], 2)

        # Desponte = 100 mm torna 5950 mm inviável
        res_desp = build_bar_optimization(
            [_make_bar(5950.0, modelo="RISK")],
            OptimizationConfig(comprimento_barra_mm=6000.0, desponte_mm=100.0),
            self.rules,
        )
        self.assertEqual(res_desp["cenarios"]["material"]["resumo"]["total_barras"], 0)
        self.assertEqual(len(res_desp["pecas_inviaveis_flat"]), 1)

        # Separar por acabamento
        acab_bars = [
            _make_bar(3000.0, modelo="RISK", acabamento="DAKAR"),
            _make_bar(3000.0, modelo="RISK", acabamento="STEEL"),
        ]
        res_split = build_bar_optimization(
            acab_bars,
            OptimizationConfig(separar_por_acabamento=True),
            self.rules,
        )
        self.assertEqual(res_split["cenarios"]["material"]["resumo"]["total_grupos"], 2)
        self.assertEqual(res_split["cenarios"]["material"]["resumo"]["total_barras"], 2)

    def test_real_samples_conservation_comparison_and_speed(self) -> None:
        cfg = OptimizationConfig(comprimento_barra_mm=6000.0)
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
            _assert_scenarios_conservation(self, det, res)

            mat_r = res["cenarios"]["material"]["resumo"]
            tmp_r = res["cenarios"]["tempo_execucao"]["resumo"]
            self.assertLessEqual(mat_r["total_barras"], tmp_r["total_barras"])
            self.assertLessEqual(tmp_r["total_ajustes_corte"], mat_r["total_ajustes_corte"])
            self.assertEqual(
                res["comparativo"]["reducao_ajustes_tempo_vs_material"],
                mat_r["total_ajustes_corte"] - tmp_r["total_ajustes_corte"],
            )

    def test_api_two_scenarios_and_exports(self) -> None:
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
            self.assertIn("cenarios", data["otimizacao_barras"])
            self.assertIn("comparativo", data["otimizacao_barras"])

            # Atualiza código do perfil lateral via PUT /api/rules para unificar CATCH e DJEI
            rules_data = self.client.get("/api/rules").json()["rules"]
            rules_data["CATCH"]["codigo_perfil_lateral"] = "PERFIL-5307"
            rules_data["DJEI"]["codigo_perfil_lateral"] = "PERFIL-5307"
            res_put = self.client.put("/api/rules", json={"rules": rules_data})
            self.assertEqual(res_put.status_code, 200)
            recalc = res_put.json()["recalculated"]
            opt_groups = {
                g["grupo_nome"]: g
                for g in recalc["otimizacao_barras"]["cenarios"]["material"]["grupos"]
            }
            self.assertIn("PERFIL-5307", opt_groups)
            self.assertEqual(opt_groups["PERFIL-5307"]["origem_agrupamento"], "codigo_perfil")

            # POST /api/optimize/bars valida desponte >= barra e aceita campo legado opcional
            res_bad = self.client.post(
                "/api/optimize/bars",
                json={"comprimento_barra_mm": 6000.0, "desponte_mm": 6000.0},
            )
            self.assertEqual(res_bad.status_code, 400)

            res_opt = self.client.post(
                "/api/optimize/bars",
                json={
                    "comprimento_barra_mm": 6000.0,
                    "espessura_serra_mm": 2.0,
                    "desponte_mm": 0.0,
                    "separar_por_acabamento": False,
                    "perda_maxima_mm": 200.0,
                },
            )
            self.assertEqual(res_opt.status_code, 200)
            opt_json = res_opt.json()
            self.assertIn("total_ajustes_corte", opt_json["cenarios"]["material"]["resumo"])
            self.assertIn("roteiro_flat", opt_json["cenarios"]["tempo_execucao"])

            # Exportação XLSX contém as 4 novas abas de otimização
            res_xlsx = self.client.post("/api/export/xlsx", json={})
            self.assertEqual(res_xlsx.status_code, 200)
            wb = load_workbook(io.BytesIO(res_xlsx.content))
            for sheet in (
                "Otimizacao_Material",
                "Otimizacao_Tempo_Roteiro",
                "Otimizacao_Tempo_Barras",
                "Otimizacao_Comparativo",
            ):
                self.assertIn(sheet, wb.sheetnames)

            # CSVs para Material, Roteiro e Barras (incluindo envio de bar_optimization filtrado)
            res_csv_mat = self.client.post(
                "/api/export/csv", json={"mode": "otimizacao_material"}
            )
            self.assertEqual(res_csv_mat.status_code, 200)
            self.assertIn("Sequencia_Corte", res_csv_mat.text)
            self.assertIn("Ajustes_Barra", res_csv_mat.text)

            res_csv_rot = self.client.post(
                "/api/export/csv", json={"mode": "otimizacao_tempo_roteiro"}
            )
            self.assertEqual(res_csv_rot.status_code, 200)
            self.assertIn("Origem_Barra", res_csv_rot.text)

            res_csv_tmp = self.client.post(
                "/api/export/csv",
                json={"mode": "otimizacao_tempo_barras", "bar_optimization": opt_json},
            )
            self.assertEqual(res_csv_tmp.status_code, 200)
            self.assertIn("Sequencia_Corte", res_csv_tmp.text)

            res_json = self.client.post("/api/export/json", json={})
            self.assertEqual(res_json.status_code, 200)
            json_body = res_json.json()
            self.assertIn("cenarios", json_body["otimizacao_barras"])
            self.assertIn("comparativo", json_body["otimizacao_barras"])
        finally:
            RULES_FILE.write_text(rules_backup, encoding="utf-8")
            STORE.optimization_config = OptimizationConfig()

    def test_angles_orientation_chaining_and_angle_change_count(self) -> None:
        # 1) 4 peças assimétricas 45° / 90° em uma barra: alterna (45/90)->(90/45)->(45/90)->(90/45) => 4 trocas (vs 7 sem orientação)
        mixed_bars = [_make_bar(1000.0, op="10", qtd=4, angulo_esq=45, angulo_dir=90)]
        res_mixed = build_bar_optimization(mixed_bars, OptimizationConfig(), self.rules)
        _assert_scenarios_conservation(self, mixed_bars, res_mixed)

        for scen_id in ("material", "tempo_execucao"):
            scen = res_mixed["cenarios"][scen_id]
            self.assertEqual(scen["resumo"]["total_barras"], 1)
            self.assertEqual(scen["resumo"]["total_trocas_angulo"], 4)
            pcs = scen["barras_flat"][0]["pecas"]
            pairs = [(p["angulo_esq"], p["angulo_dir"]) for p in pcs]
            self.assertEqual(pairs, [(45, 90), (90, 45), (45, 90), (90, 45)])

        # 2) Sequência mista [90/90, 45/90, 45/45] => 45/45 -> 45/90 -> 90/90 = apenas 1 troca total
        seq_bars = [
            _make_bar(1500.0, op="1", codigo="C1", angulo_esq=90, angulo_dir=90),
            _make_bar(1500.0, op="2", codigo="C2", angulo_esq=45, angulo_dir=90),
            _make_bar(1500.0, op="3", codigo="C3", angulo_esq=45, angulo_dir=45),
        ]
        res_seq = build_bar_optimization(seq_bars, OptimizationConfig(), self.rules)
        _assert_scenarios_conservation(self, seq_bars, res_seq)
        self.assertEqual(res_seq["cenarios"]["material"]["resumo"]["total_trocas_angulo"], 1)
        self.assertEqual(res_seq["cenarios"]["tempo_execucao"]["resumo"]["total_trocas_angulo"], 1)

        # 3) Integração com exports XLSX e CSV incluindo colunas de ângulos e trocas
        res_opt = self.client.post(
            "/api/optimize/bars",
            json={
                "comprimento_barra_mm": 6000.0,
                "detailed_bars": seq_bars,
            },
        )
        self.assertEqual(res_opt.status_code, 200)
        opt_payload = res_opt.json()

        res_csv_mat = self.client.post(
            "/api/export/csv",
            json={"mode": "otimizacao_material", "bar_optimization": opt_payload},
        )
        self.assertEqual(res_csv_mat.status_code, 200)
        self.assertIn("Angulos_Barra", res_csv_mat.text)
        self.assertIn("Trocas_Angulo_Barra", res_csv_mat.text)

        res_csv_rot = self.client.post(
            "/api/export/csv",
            json={"mode": "otimizacao_tempo_roteiro", "bar_optimization": opt_payload},
        )
        self.assertEqual(res_csv_rot.status_code, 200)
        self.assertIn("Angulos_Corte", res_csv_rot.text)
        self.assertIn("Troca_Angulo", res_csv_rot.text)

        res_xlsx = self.client.post(
            "/api/export/xlsx",
            json={"bar_optimization": opt_payload},
        )
        self.assertEqual(res_xlsx.status_code, 200)
        wb = load_workbook(io.BytesIO(res_xlsx.content))
        mat_headers = [c.value for c in wb["Otimizacao_Material"][1]]
        rot_headers = [c.value for c in wb["Otimizacao_Tempo_Roteiro"][1]]
        cmp_headers = [c.value for c in wb["Otimizacao_Comparativo"][1]]
        self.assertIn("Angulos_Barra", mat_headers)
        self.assertIn("Trocas_Angulo_Barra", mat_headers)
        self.assertIn("Angulos_Corte", rot_headers)
        self.assertIn("Troca_Angulo", rot_headers)
        self.assertIn("Material_Trocas_Angulo", cmp_headers)
        self.assertIn("Tempo_Trocas_Angulo", cmp_headers)

    def test_symmetric_profile_parallel_nesting_vs_v_cut(self) -> None:
        cfg = OptimizationConfig(comprimento_barra_mm=6000.0)

        # 6 peças de 1030mm (45°/45°, largura 45mm) em barra de 6000mm:
        # - Assimétrico (\/): soma = 6180mm -> exige 2 barras
        asym_bars = [
            _make_bar(
                1030.0,
                qtd=6,
                angulo_esq=45,
                angulo_dir=45,
                perfil_simetrico=False,
                largura_perfil_mm=45.0,
            )
        ]
        res_asym = build_bar_optimization(asym_bars, cfg, self.rules)
        _assert_scenarios_conservation(self, asym_bars, res_asym)
        for scen_id in ("material", "tempo_execucao"):
            scen = res_asym["cenarios"][scen_id]
            self.assertEqual(scen["resumo"]["total_barras"], 2)
            self.assertEqual(scen["resumo"]["total_economia_chanfro_mm"], 0.0)
            self.assertEqual(scen["resumo"]["total_cortes_paralelos"], 0)
            self.assertGreater(scen["resumo"]["total_cortes_v"], 0)
            for bar in scen["barras_flat"]:
                self.assertFalse(bar["perfil_simetrico"])
                self.assertEqual(bar["cortes_paralelos_qtd"], 0)
                self.assertEqual(bar["economia_chanfro_mm"], 0.0)
                self.assertTrue(all(not p["invertida"] for p in bar["pecas"]))
                self.assertEqual(bar["pecas"][0]["juncao_entrada"], "")
                if len(bar["pecas"]) > 1:
                    self.assertTrue(all(p["juncao_entrada"] == "\\/" for p in bar["pecas"][1:]))

        # - Simétrico (// com giro 180°): 5 encaixes * 45mm = 225mm recuperados -> 5955mm -> 1 barra!
        sym_bars = [
            _make_bar(
                1030.0,
                qtd=6,
                angulo_esq=45,
                angulo_dir=45,
                perfil_simetrico=True,
                largura_perfil_mm=45.0,
            )
        ]
        res_sym = build_bar_optimization(sym_bars, cfg, self.rules)
        _assert_scenarios_conservation(self, sym_bars, res_sym)
        for scen_id in ("material", "tempo_execucao"):
            scen = res_sym["cenarios"][scen_id]
            self.assertEqual(scen["resumo"]["total_barras"], 1)
            self.assertAlmostEqual(scen["resumo"]["total_economia_chanfro_mm"], 225.0, places=3)
            self.assertEqual(scen["resumo"]["total_cortes_paralelos"], 5)
            self.assertEqual(scen["resumo"]["total_cortes_v"], 0)
            bar = scen["barras_flat"][0]
            self.assertTrue(bar["perfil_simetrico"])
            self.assertAlmostEqual(bar["consumido_mm"], 5955.0, places=3)
            self.assertAlmostEqual(bar["perda_mm"], 45.0, places=3)
            self.assertAlmostEqual(bar["aproveitamento_pct"], 99.25, places=2)
            self.assertAlmostEqual(bar["economia_chanfro_mm"], 225.0, places=3)
            self.assertEqual(bar["cortes_paralelos_qtd"], 5)
            self.assertEqual(bar["cortes_v_qtd"], 0)
            self.assertEqual(
                [p["invertida"] for p in bar["pecas"]],
                [False, True, False, True, False, True],
            )
            self.assertEqual(bar["pecas"][0]["juncao_entrada"], "")
            self.assertTrue(all(p["juncao_entrada"] == "//" for p in bar["pecas"][1:]))

        # Simétrico com largura 0mm: alterna orientação e marca "//", porém com economia 0.0 mm
        sym_zero_w = [
            _make_bar(
                1000.0,
                qtd=3,
                angulo_esq=45,
                angulo_dir=45,
                perfil_simetrico=True,
                largura_perfil_mm=0.0,
            )
        ]
        res_zero_w = build_bar_optimization(sym_zero_w, cfg, self.rules)
        _assert_scenarios_conservation(self, sym_zero_w, res_zero_w)
        bar_zw = res_zero_w["cenarios"]["material"]["barras_flat"][0]
        self.assertEqual([p["invertida"] for p in bar_zw["pecas"]], [False, True, False])
        self.assertEqual([p["juncao_entrada"] for p in bar_zw["pecas"]], ["", "//", "//"])
        self.assertEqual(bar_zw["cortes_paralelos_qtd"], 2)
        self.assertEqual(bar_zw["economia_chanfro_mm"], 0.0)

        # Exports CSV e XLSX com as colunas de simetria e economia de chanfro
        res_csv_mat = self.client.post(
            "/api/export/csv",
            json={"mode": "otimizacao_material", "bar_optimization": res_sym},
        )
        self.assertEqual(res_csv_mat.status_code, 200)
        for col in ("Perfil_Simetrico", "Cortes_Paralelos", "Cortes_V", "Economia_Chanfro_mm"):
            self.assertIn(col, res_csv_mat.text)

        res_csv_rot = self.client.post(
            "/api/export/csv",
            json={"mode": "otimizacao_tempo_roteiro", "bar_optimization": res_sym},
        )
        self.assertEqual(res_csv_rot.status_code, 200)
        self.assertIn("Perfil_Simetrico", res_csv_rot.text)

        res_xlsx = self.client.post(
            "/api/export/xlsx",
            json={"bar_optimization": res_sym},
        )
        self.assertEqual(res_xlsx.status_code, 200)
        wb = load_workbook(io.BytesIO(res_xlsx.content))
        mat_headers = [c.value for c in wb["Otimizacao_Material"][1]]
        rot_headers = [c.value for c in wb["Otimizacao_Tempo_Roteiro"][1]]
        cmp_headers = [c.value for c in wb["Otimizacao_Comparativo"][1]]
        for col in ("Perfil_Simetrico", "Cortes_Paralelos", "Cortes_V", "Economia_Chanfro_mm"):
            self.assertIn(col, mat_headers)
        self.assertIn("Perfil_Simetrico", rot_headers)
        self.assertIn("Material_Economia_Chanfro_mm", cmp_headers)
        self.assertIn("Tempo_Economia_Chanfro_mm", cmp_headers)


if __name__ == "__main__":
    unittest.main()
