---
modulo: "description_parser.py + cutting_engine.py"
tipo: "dominio"
data_atualizacao: 2026-11-18
tags: [regras-negocio, calculo, parametros, portas]
---

# Regra: Extração Construtiva e Cálculo de Corte de Perfis

**Contexto:** Converte descrições textuais heterogêneas do PCP (`PORTAS`) em especificações estruturadas de construção e lista de barras de corte com descontos por modelo.

## Lógica e Parâmetros

- **Variáveis de Entrada Obrigatórias:**
  - `RawOpRow` (`codigo`, `descricao`, `quantidade`, `op`, `pedido`, `data_entrega`, `ambiente`) extraído por `./backend/app/html_parser.py`.
  - `regras_corte.json`: `codigo_perfil_lateral`, `codigo_perfil_puxador`, `desconto_vertical_mm`, `desconto_horizontal_mm`, `desconto_divisoria_mm`, `largura_perfil_quadro_mm`, `largura_perfil_puxador_mm`, `desconto_adjacente_puxador_mm`, `desconto_vidro_lateral_mm`, `desconto_vidro_puxador_mm` e `tipo_corte` por modelo.
- **Condicionais Críticas:**
  - **ALLU (`ESCADA`, `NICHO`, `LATERAL`, `PE`, `ILHA`):** Um quadro externo fechado (`2` verticais na altura + `2` horizontais na largura, ou `1` horizontal se `ALLU EM U`) somado às divisórias internas na largura (`qtd_divisorias`), multiplicado por `quantidade * qtd_estruturas`.
  - **`CLEAR_S_PUXADOR` vs `S/PUXADOR`:** `CLEAR_S_PUXADOR` identifica o modelo `CLEAR S` com puxador; ausência de puxador ocorre apenas com `S/PUXADOR`, `SEM PUXADOR`, `SEM PUXADRO`, `_SEM PUX` ou `SEM USINAGEM`.
  - **Portas e Frentes:** Separa barras com perfil puxador (`SUPERIOR`, `HORIZONTAL`, `LATERAL (DIREITA/ESQUERDA)` ou `DUPLO`) das demais barras do quadro, e adiciona travessas internas quando há `TRAVESSA`/`DIVISAO` ou `VAO`.
  - **Desconto em Peças Adjacentes ao Puxador (ex.: `CLEAR G`):** Quando o perfil puxador é mais largo que o perfil quadro (ex.: `80 mm - 45 mm = 35 mm`), o valor `desconto_adjacente_puxador_mm` é somado automaticamente às barras perpendiculares ao puxador:
    - Puxador `SUPERIOR` / `HORIZONTAL`: desconta `1x` nas `2` barras **Verticais Quadro**.
    - Puxador `LATERAL` (1 lado): desconta `1x` nas `2` barras **Horizontais Quadro** (e nas travessas divisórias internas).
    - Puxador `DUPLO` (2 lados): desconta `2x` nas `2` barras **Horizontais Quadro** (e nas travessas divisórias internas).
  - **Corte de Vidros / Placas:** Soma os descontos por lado (`desconto_vidro_lateral_mm` para cada lado sem puxador e `desconto_vidro_puxador_mm` para cada lado com puxador) em cada eixo:
    - `SEM PUXADOR`: Largura `- 2 * Lateral`, Altura `- 2 * Lateral`.
    - `SUPERIOR` / `HORIZONTAL`: Largura `- 2 * Lateral`, Altura `- (Puxador + Lateral)`.
    - `LATERAL` (1 lado): Largura `- (Puxador + Lateral)`, Altura `- 2 * Lateral`.
    - `DUPLO` (2 lados): Largura `- 2 * Puxador`, Altura `- 2 * Lateral`.
  - **Cristaleira Provence Urda:** Utiliza os comprimentos explícitos do perfil `MINI KENDO + BAGUETE` informados na descrição.
- **Saída Esperada:**
  - Lista de `ExtractedItem` (medidas, modelo, puxadores, divisórias, acabamentos, furação), `CutBar` por OP e resumo agrupado para serra.

## Dependências

**⬅️ Consumido por:** [[02-Backend-API/API-Extracao-ERP-Portas]], [[03-Dominio-Calculos/Otimizacao-Barras-6m]]
