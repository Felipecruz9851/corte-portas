---
modulo: "backend/main.py + backend/app/exporter.py"
tipo: "backend"
linguagem: "python"
data_atualizacao: 2026-11-25
tags: [codigo, backend, python, fastapi]
---

# Módulo: API FastAPI e Exportador

**Responsabilidade:** Expõe os endpoints HTTP REST para consulta ao vivo do ERP, parsing de HTML, gerenciamento de regras de corte em JSON e exportação em Excel multi-abas (`.xlsx`), CSV e JSON, além de servir o build de produção do frontend Vite (`./frontend/dist/`).

## Principais Funções / Métodos
* `serve_index()`, `serve_logo()`, `serve_favicon()` e montagem de `/static`: Servem `./frontend/dist/index.html`, `./frontend/dist/logo_lider.png`, `./frontend/dist/favicon.ico` e `./frontend/dist/static/` (`app.js`, `styles.css`), com fallback para `./frontend/`.
* `extract_from_erp()` (`POST /api/extract/erp`): Consulta uma ou mais datas em `http://192.168.0.6/pcp/op_abertura.php` e retorna itens extraídos, barras, vidros, `otimizacao_barras` e KPIs.
* `extract_from_html()` (`POST /api/extract/html`): Executa o mesmo pipeline consolidado (incluindo `otimizacao_barras`) aceitando tanto lote de múltiplos arquivos (`files: [{ html, source_name }]`) quanto o payload único retrocompatível (`{ html, source_name }`), validando conteúdo vazio com HTTP `400`.
* `clear_session()` (`POST /api/session/clear`): Limpa o estado em memória da última extração em `STORE` (`meta`, `extracted_items`, `payload`), preservando `optimization_config`.
* `optimize_bars()` (`POST /api/optimize/bars`): Recalcula em memória os **dois cenários paralelos** de otimização linear (`cenarios.material` e `cenarios.tempo_execucao`), além de `comparativo` (incluindo `reducao_trocas_angulo_tempo_vs_material`, `pico_sobras_tempo`, `total_retomadas_tempo` e `barras_complexas_material`) e `pecas_inviaveis_flat`, aceitando os parâmetros `priorizar_mesma_medida` (boolean, modo serra manual no Cenário Material) e `limite_sobras_simultaneas` (inteiro `>= 1` ou `null`, limite do cavalete no Cenário Tempo), com orientação automática de peças mistas `45° / 90°` e contagem de trocas de ângulo (`total_trocas_angulo`, `trocas_angulo_barra`, `troca_angulo`).
* `get_rules()`, `update_rules()`, `reset_rules()`: Lê, atualiza e reseta `./backend/app/data/regras_corte.json` (incluindo `angulo_corte_quadro`, `angulo_corte_puxador`, `angulo_corte_divisoria`, `perfil_simetrico_lateral`, `perfil_simetrico_puxador`, `codigo_perfil_lateral`, `codigo_perfil_puxador` e normalização de `observacao`) recalculando os cortes e a otimização em memória.
* `export_xlsx()`, `export_csv()`, `export_json()`: Exportam planilhas formatadas via `./backend/app/exporter.py`, gerando as 4 abas de otimização no `.xlsx` completo (`plano_corte_portas.xlsx`: `Otimizacao_Material`, `Otimizacao_Tempo_Roteiro`, `Otimizacao_Tempo_Barras` e `Otimizacao_Comparativo`) ou o `.xlsx` dedicado do roteiro (`roteiro_corte_otimizado.xlsx` via `export_roteiro_to_xlsx_bytes` quando `POST /api/export/xlsx` recebe `mode="otimizacao_tempo_roteiro"`). A aba `Otimizacao_Tempo_Roteiro` (e o CSV `otimizacao_tempo_roteiro`) segue layout 1:1 com o frontend em 11 colunas (`Passo`, `Modelo`, `Cód. Perfil`, `Ângulos`, `Origem na Barra`, `Qtd Cortes`, `Medida (mm)`, `Sobra Antes → Depois (mm)`, `Ação / Cavalete`, `OPs`, `Observação`), com estilização Lider Design (`_style_roteiro_sheet`) e impressão A4 paisagem; as demais abas de otimização preservam colunas de ângulos, simetria, economia de chanfro e complexidade (`Medidas_Distintas`, `Material_Barras_4_Mais_Medidas`, `Tempo_Retomadas_Sobras`, `Tempo_Pico_Sobras_Cavalete`, `Angulos_Barra`, `Trocas_Angulo_Barra`, `Material_Trocas_Angulo`, `Tempo_Trocas_Angulo`, `Perfil_Simetrico`, `Cortes_Paralelos`, `Cortes_V`, `Economia_Chanfro_mm`, `Material_Economia_Chanfro_mm`, `Tempo_Economia_Chanfro_mm`) e os modos CSV `otimizacao_material`, `otimizacao_tempo_roteiro` e `otimizacao_tempo_barras`.

## Dependências (Grafo)
**⬅️ Quem chama este módulo (Entrada):**
* [[01-Frontend-UI/Interface-Web-Corte-Portas]]

**➡️ Quem este módulo chama (Saída/Uso):**
* [[04-Infra-Dados/Integracao-HTTP-ERP]]
* [[03-Dominio-Calculos/Regras-Extracao-e-Corte-Perfis]]
* [[03-Dominio-Calculos/Otimizacao-Barras-6m]]
* **Bibliotecas Externas:** `fastapi`, `pydantic`, `pandas`, `openpyxl`.
