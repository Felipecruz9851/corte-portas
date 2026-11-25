---
modulo: "catalogo-modelos-portas"
tipo: "dominio"
data_atualizacao: 2026-11-25
tags: [regras-negocio, catalogo, modelos, portas, particularidades]
---

# Catálogo de Modelos, Categorias e Particularidades (`PORTAS`)

**Objetivo:** Servir como referência técnica detalhada de cada um dos **12 modelos** cadastrados em `./backend/app/data/regras_corte.json` e das **8 categorias construtivas** reconhecidas por `./backend/app/description_parser.py`, incluindo critérios de detecção, exemplos reais do ERP, contas passo a passo e armadilhas conhecidas.

---

## 1. Matriz Comparativa dos 12 Modelos

Snapshot fiel da configuração vigente em `./backend/app/data/regras_corte.json` (`2026-11-25`):

| Modelo | Tipo Corte | Desc. V / H / Div (mm) | Larg. Quadro / Pux. / Adj. (mm) | Vidro Lat. / Pux. (mm/lado) | Cód. Perfil (Lat / Pux) | Puxador? | Particularidade Principal |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`ALLU`** | `90° (Explícito)` | `0 / 24 / 24` | `12 / 12 / 0` | `0 / 0` | vazio / vazio | Não (`0`) | Quadro + divisórias, multiplicador `qtd_estruturas`, Formato U, Barra Avulsa, sem vidro. |
| **`CATCH`** | `45°` | `0 / 0 / 0` | `0 / 0 / 0` | `0 / 0` | vazio / vazio | Sim (`5307/5317`) | Compartilha perfil lateral `5307` com `DJEI` e `PERFIL 5307`. |
| **`PERFIL 5307`** | `45°` | `0 / 0 / 0` | `0 / 0 / 0` | `0 / 0` | vazio / vazio | Não (`S/PUXADOR`) | Sempre sem puxador; detectado apenas por `PERFIL 5307 S/PUXADOR`. |
| **`DJEI`** | `45°` | `0 / 0 / 0` | `0 / 0 / 0` | **`5 / 20`** | vazio / vazio | Sim (exceto Visor / `S/PUXADOR`) | Atende portas (`5307/6817`) e Tampo/Prateleira Visor; desconto de vidro já calibrado (`5/20`) desativa fallback explícito do Visor. |
| **`CLEAR S`** | `45°` | `0 / 0 / 0` | `0 / 0 / 0` | `0 / 0` | vazio / vazio | Condicional | Armadilha `CLEAR_S_PUXADOR` (com puxador) vs `CLEAR S/PUXADOR` (sem puxador). |
| **`CLEAR G`** | `45°` | `0 / 0 / 0` | **`45 / 80 / 35`** | `0 / 0` | vazio / vazio | Sim | Perfil assimétrico: `-35 mm` automático nas barras perpendiculares ao puxador (`-70 mm` se duplo). |
| **`RISK`** | `45° / 90° (Misto)` | `0 / 0 / 0` | `0 / 0 / 0` | `0 / 0` | `RISK` / `RISK` | Implícito (exceto `SEM USINAGEM`/`SEM PUXADOR`) | **Quadro fechado + puxador adicional (`puxador_adicional_quadro_fechado = true`):** 4 peças no quadro (`45° / 45°`) + 1 peça de puxador (`90° / 90°`) = **5 peças/porta** (`4` se sem puxador; `6` se duplo). 4 subtipos (`USINADO`, `INCLINADO`, `SEM USINAGEM`, `RISK`) e fallback `2PTAG`. |
| **`GROOVE`** | `45°` | `0 / 0 / 0` | `0 / 0 / 0` | `0 / 0` | vazio / vazio | Implícito em portas | Espelheira / Sistema Avante. |
| **`INTEIRA`** | `45°` | `0 / 0 / 0` | `0 / 0 / 0` | `0 / 0` | vazio / vazio | Implícito em portas | Detectado por `CORRER INTEIRA`; frequente em Passagem Suspensa / Cascata com `PUX.SMART`. |
| **`SINGULAR`** | `45°` | `0 / 0 / 0` | `0 / 0 / 0` | `0 / 0` | vazio / vazio | Condicional | Detectado por `CORRER SINGULAR`; divisórias geradas por `VAO INFERIOR/CENTRAL/SUPERIOR`. |
| **`MINI KENDO + BAGUETE`** | `90° (Explícito)` | `0 / 0 / 0` | `0 / 0 / 0` | `0 / 0` | vazio / vazio | Não (`0`) | Cristaleira Provence Urda (`3PERUNO6BG215B`); usa medidas explícitas `02 UNIDADES MEDIDA H MM E 02 UNIDADES MEDIDA V MM`. |
| **`OUTRO`** | `45°` | `0 / 0 / 0` | `0 / 0 / 0` | `0 / 0` | vazio / vazio | Condicional | Regra sentinela obrigatória; emite warning de modelo não reconhecido. |

---

## 2. Fichas Técnicas Individuais dos 12 Modelos

### 2.1. `ALLU` (Linha ALLU — Escada, Nicho, Lateral, Pé, Ilha)
- **Critério de Detecção:** qualquer item classificado por `_extract_categoria_subcategoria()` como `LINHA ALLU` (`ESCADA ALLU`, `LATERAL NICHO ALLU`, `NICHO ALLU`, `ILHA ALLU`, `PE ALLU`, `BARRA ALLU`, `ALLU EM U`, `PERFIL ALLU`). É o 1º modelo testado em `_extract_modelo()`.
- **Exemplos Reais de Descrição ERP:**
  - `2NICHAZTWOY9D1`: `NICHO ALLU - PRODUZIR DUAS ESCADAS - LARGURA 348 - ALTURA 752 - DIVISORIA 1 - 376.5MM - ACABAMENTO LACA METALIZADA FOSCASTEEL - METALIZADA FOSCA`
  - `2LATALW6EGLJW1`: `LATERAL NICHO ALLU - PRODUZIR UMA ESCADA - LARGURA 150 - ALTURA 1000 - ACABAMENTO LACA PADRAO CARBONO - FOSCA`
  - `2PEALU2RFV1VF1`: `PE ALLU - PRODUZIR UMA ESCADA - LARGURA 600 - ALTURA 643 - ACABAMENTO LACA PADRAO BRANCA - FOSCA`
- **Cálculo Passo a Passo (com `desconto_vertical_mm=0`, `desconto_horizontal_mm=24`, `desconto_divisoria_mm=24`):**
  - Para o item `2NICHAZTWOY9D1` (`quantidade=1`, `PRODUZIR DUAS ESCADAS` → `qtd_estruturas=2`, `fator = 1 * 2 = 2`):
    - `Montante Vertical ALLU`: `2 * 2 = 4` barras de `752 - 0 = 752.0 mm`
    - `Travessa Quadro ALLU (Sup/Inf)`: `2 * 2 = 4` barras de `348 - 24 = 324.0 mm` (ou `1 * 2 = 2` barras se `ALLU EM U` / `FORMATO DE U`)
    - `Divisória Interna ALLU`: `1 * 2 = 2` barras de `348 - 24 = 324.0 mm`
  - Se for barra avulsa (`SOMENTE A BARRA`, `CORTAR BARRA COM`, `APENAS A BARRA`, `APENAR A BARRA`, `PERFIL LINEAR`): gera `op_qty * qtd_estruturas` barras `Barra Linear Avulsa` com `desconto_mm = 0.0`.
  - **Vidros:** nunca gera corte de vidro/placa.
- **Particularidades e Manutenção:**
  - O multiplicador `_extract_qtd_estruturas()` reconhece apenas `UMA` (`1`), `DUAS` (`2`), `TRES` (`3`) e `QUATRO ESCADAS` (`4`); quantidades maiores caem no fallback `1` se não forem adicionadas ao dicionário.
  - Há um débito técnico no teste `test_specific_cases_from_plan` (`./backend/tests/test_extraction.py`), escrito antes de calibrarem os `24.0 mm` de desconto horizontal/divisória na regra `ALLU`.

### 2.2. `CATCH` (Perfil Catch / Perlare `5307/5317`)
- **Critério de Detecção:** presença de `"CATCH"` em `upper` (3º teste) ou fallback `"5307/5317"` em `upper` (12º teste). Subtipo fixo `"PERLARE CATCH"`.
- **Exemplo Real de Descrição ERP:**
  - `2PTAC70NECX91`: `PORTA BATER CATCH C/PUXADOR SUPERIOR - PERLARE - 5307/5317 - DIREITA - LARGURA DE 524 - ALTURA 1206 - PERFIL LACA PADRAO\QUINOA - ESPELHO PRATA - FURACAO PAGINA 151)`
- **Comportamento no Corte:** segue o ramo geral de portas/básculas (`compute_item_cuts` e `compute_item_glasses`). Em `2PTAC70NECX91` (`SUPERIOR`), gera `1x Horizontal c/ Puxador (524 mm)`, `1x Horizontal Quadro (524 mm)` e `2x Vertical Quadro (1206 mm)` com os descontos vigentes (`0.0 mm`).
- **Particularidades e Manutenção:**
  - Fisicamente compartilha o perfil lateral `5307` com `DJEI` e `PERFIL 5307`. Preencha `codigo_perfil_lateral = "5307"` nos 3 modelos na aba **Regras e Descontos (mm)** para que a otimização de barras de 6 m una automaticamente todas as barras laterais desses 3 modelos.

### 2.3. `PERFIL 5307` (Perlare sem puxador)
- **Critério de Detecção:** regex exata `PERFIL\s+5307\s+S/PUXADOR` em `upper` (4º teste). Subtipo `"PERLARE S/PUXADOR"`.
- **Exemplo Real de Descrição ERP:**
  - `2PTSPSUN53QL1`: `PORTA BATER PERFIL 5307 S/PUXADOR - PERLARE - 5307 - DIREITA - LARGURA DE 489 - ALTURA 1596 - PERFIL LACA METALIZADA\HUST - TRANSLUCIDO\LISO REFLETENTE BRONZE - FURACAO PAGINA 171`
- **Comportamento no Corte:** sempre cai no caso `qtd_puxadores == 0` (por conter `S/PUXADOR`), gerando `2x Vertical Quadro`, `2x Horizontal Quadro` (ambos `Lateral`) e vidro `2x Lateral` em ambos os eixos.
- **Particularidades e Manutenção:**
  - Para capturar o acabamento real quando a descrição inicia com `PERFIL 5307 S/PUXADOR...`, `_extract_acabamentos_e_furacao()` verifica se o primeiro bloco contém `S/PUXADOR` e salta para o segundo bloco `[-_] PERFIL ...`.
  - Cuidado para não trocar a regex por `"5307"` genérico, pois `CATCH` (`5307/5317`) e `DJEI` (`5307/6817`) também contêm `5307`.

### 2.4. `DJEI` (`5307/6817` e Linha Visor)
- **Critério de Detecção:** presença de `"DJEI"` em `upper` (5º teste, subtipo `"VISOR"` se `"VISOR"` presente, senão `"DJEI"`) ou fallback `"5307/6817"` (13º teste).
- **Exemplos Reais de Descrição ERP:**
  - Porta/Báscula: `FRENTE INFERIOR BASCULA DJEI C/PUXADOR - 5307/6817 - LARGURA DE 1061 - ALTURA 425 ...` (`2PTAJRH10AMZ1`) e `FRENTE SUPERIOR BASCULA DJEI S/PUXADOR - 5307/5307 - LARGURA DE 1061 - ALTURA 425 ...` (`2PTAJRH10AMZ4`)
  - Prateleira Visor: `2PRVIXSSF8ZV1` (`PRATELEIRA VISOR - PERFIL DJEI SEM PUXADOR - LARGURA 700 X PROFUNDIDADE 500 - ACABAMENTO PERFIL QUINOA - METALIZADA FOSCA - VIDRO INCOLOR LOW IRON`)
- **Comportamento no Corte:**
  - Em portas/básculas: `DJEI` entra na lista de puxador implícito caso não tenha `S/PUXADOR` / `SEM PUXADOR`.
  - Em `PRATELEIRA / TAMPO VISOR`: a categoria força `qtd_puxadores = 0`, gerando `2x Vertical Quadro` (na profundidade, guardada em `altura_mm`) e `2x Horizontal Quadro` (na largura).
  - **Vidros (atenção especial!):** em `./backend/app/data/regras_corte.json`, `DJEI` já está calibrado com `desconto_vidro_lateral_mm = 5.0` e `desconto_vidro_puxador_mm = 20.0`. Por exemplo, em `2PRVIXSSF8ZV1` (`700 x 500`, sem puxador), o vidro recebe `2x Lateral` = `-10.0 mm` em ambos os eixos → **`690.0 × 490.0 mm`**. Como os descontos de vidro são `> 0`, o fallback `"Explícito na descrição"` do Visor **não** é acionado.
- **Particularidades e Manutenção:**
  - `DJEI` é o único modelo que atende simultaneamente frentes móveis (com/sem puxador) e prateleiras/tampos Visor. Se no futuro o Visor precisar de descontos de perfil/vidro diferentes da porta `DJEI`, será necessário criar uma regra separada (ex.: `"DJEI VISOR"`) no JSON e em `_extract_modelo()` **acima** do `if "DJEI" in upper:`.

### 2.5. `CLEAR S`
- **Critério de Detecção:** `"CLEAR_S" in upper or "CLEAR S/" in upper or "CLEAR S " in upper` (6º teste). Subtipo `"CLEAR_S"`.
- **Exemplo Real de Descrição ERP:**
  - `2PTAG1H03Z651`: `FRENTE GAVETA CLEAR_S_PUXADOR - LARGURA 496 - ALTURA 160 - PERFIL LACA FOSCA CINZA COBALTO - FOSCA - PLACA PERFURADA DIAM. 6 MM LACA FOSCA CINZA COBALTO - FOSCA - TELESCOPICA BAIXA - FURACAO PAGINA 80`
- **Comportamento no Corte:** segue o ramo geral de quadro + puxador + vidro.
- **Particularidades e Manutenção:**
  - **Pegadinha clássica:** o ERP gera `CLEAR_S_PUXADOR` (com underscore) para peças **com** puxador e `CLEAR S/PUXADOR` (com barra) para peças **sem** puxador. O parser já diferencia os dois casos porque a lista negativa busca `"S/PUXADOR"` (com barra) e não `"S_PUXADOR"`. Nunca simplifique `"S/PUXADOR"` para substring sem barra!

### 2.6. `CLEAR G` (Perfil Assimétrico — Puxador 80 mm vs Quadro 45 mm)
- **Critério de Detecção:** `"CLEAR G"` em `upper` (7º teste). Subtipo `"CLEAR G"`.
- **Exemplos Reais de Teste (`./backend/tests/test_extraction.py`):**
  - Lateral (`2PTAGIIM4F9I1`): `PORTA BATER CLEAR G C/PUXADOR LATERAL - DIREITA - LARGURA 279 - ALTURA 1366 - PERFIL ALUMINIO - PLACA INCOLOR - FURACAO PAGINA 170`
  - Superior (`2PTAGOKZTR611`): `PORTA BATER CLEAR G C/PUXADOR SUPERIOR - ESQUERDA - LARGURA 250 - ALTURA 400 - PERFIL STEEL - PLACA PERFURADA - FURACAO PAGINA 160`
- **Cálculo Passo a Passo (`largura_perfil_quadro_mm=45.0`, `largura_perfil_puxador_mm=80.0`, `desconto_adjacente_puxador_mm=35.0`):**
  - Em `2PTAGIIM4F9I1` (`LATERAL (DIREITA)`, `279 × 1366 mm`):
    - `Vertical c/ Puxador (DIREITA)` (`Puxador`): `1x 1366.0 mm` (`desc = 0`)
    - `Vertical Quadro` (`Lateral`): `1x 1366.0 mm` (`desc = 0`)
    - `Horizontal Quadro` (`Lateral`): `2x 279 - 35 = 244.0 mm` (`desc = 35.0`, obs `"-35mm Adj. Puxador Lat."`)
  - Em `2PTAGOKZTR611` (`SUPERIOR`, `250 × 400 mm`):
    - `Horizontal c/ Puxador` (`Puxador`): `1x 250.0 mm` (`desc = 0`)
    - `Horizontal Quadro` (`Lateral`): `1x 250.0 mm` (`desc = 0`)
    - `Vertical Quadro` (`Lateral`): `2x 400 - 35 = 365.0 mm` (`desc = 35.0`, obs `"-35mm Adj. Puxador Sup."`)
  - Caso houvesse **2 puxadores laterais**, as barras horizontais e divisórias internas receberiam `2 × 35 = 70.0 mm` de desconto.
- **Particularidades e Manutenção:**
  - Lembre-se de que `cutting_engine.py` aplica `desconto_adjacente_puxador_mm` diretamente — manter coerência com `pux - quadro` caso edite o JSON à mão.

### 2.7. `RISK` (`USINADO`, `INCLINADO`, `SEM USINAGEM`, `RISK`)
- **Critério de Detecção:** `"RISK"` em `upper` (8º teste; subtipo por precedência: `"INCLINADO"` → `"RISK INCLINADO"`, `"SEM USINAGEM"` → `"RISK SEM USINAGEM"`, `"USINADO"` → `"RISK USINADO"`, senão `"RISK"`) **OU** fallback pelo prefixo de código `codigo.upper().startswith("2PTAG")` (14º teste, subtipo `"RISK SEM PUXADOR"`).
- **Exemplos Reais de Descrição ERP:**
  - Porta Bater 1 Puxador (`2PTNP412ZDM41`): `PORTA BATER RISK_DIREITA_LARGURA 434_ALTURA 2309_PERFIL PADRAO PRETA - FOSCA_ PLACA INCOLOR LOW IRON_FURACAO PAGINA 172`
  - Porta Correr Externa 2 Puxadores (`2PTNP7POYS1N3`): `PORTA SOFT CLOSING SI OCEAN 80_CORRER RISK_EXTERNA_C/ PUXADOR DIREITO E ESQUERDO_LARGURA 1219.333_ALTURA 2640_PERFIL PADRAO QUINOA - FOSCA_PLACA REFLETENTE BRONZE`
- **Comportamento no Corte (`puxador_adicional_quadro_fechado = true`, `tipo_corte = "45° / 90° (Misto)"`, `angulo_corte_quadro = 45`, `angulo_corte_puxador = 90`, `codigo_perfil_lateral = "RISK"`, `codigo_perfil_puxador = "RISK"`):**
  - Em portas (`PORTA DE BATER`, `PORTA DE CORRER`, `PORTA PASSAGEM / DIVISORIA`), `"RISK"` aciona puxador **implícito** mesmo sem a palavra `PUXADOR` (ex.: `2PTNP412ZDM41` acima recebe `1x LATERAL (DIREITA)`). Só vira `0` puxadores se houver token negativo (`SEM USINAGEM`, `S/PUXADOR`, `SEM PUXADOR`, etc.).
  - **Quadro fechado + puxador adicional:** todos os itens `RISK` (Bater, Correr, Báscula, Gaveta) emitem sempre o quadro fechado de **4 peças** em `45° / 45°` (`2x Vertical Quadro` na altura + `2x Horizontal Quadro` na largura), somado às peças adicionais de puxador em `90° / 90°` com mesmo código `RISK` (otimizando junto nas mesmas barras de 6 m):
    - `0` puxadores (`SEM PUXADOR` / `SEM USINAGEM`): **4 peças** (`2x Vertical Quadro` + `2x Horizontal Quadro`).
    - `1` puxador: **5 peças** (`4` do quadro + `1x Puxador Vertical (<Lado>)` na altura, ou `1x Puxador Horizontal` na largura em `SUPERIOR` / `HORIZONTAL (BASCULA/GAVETA)`).
    - `2` puxadores (`DUPLO (DIREITA E ESQUERDA)`): **6 peças** (`4` do quadro + `2x Puxador Vertical (Dir/Esq)` na altura).
  - **Vidro / Placa:** como o quadro é fechado nos 4 lados, `compute_item_glasses()` aplica sempre **`2x Lateral`** em Largura e Altura (inclusive com 1 ou 2 puxadores).
  - Suporta medidas decimais (como `1219.333 mm` em `2PTNP7POYS1N3`), preservadas até a 3ª casa decimal em `cutting_engine.py` e convertidas para micrômetros exatos (`1219333 µm`) em `bar_optimizer.py`.
- **Particularidades e Manutenção:**
  - Caso entre algum novo código `2PTAG...` no ERP que **não** seja `RISK`, lembre-se da regra de fallback da linha 226 em `description_parser.py` — a nova regra do modelo precisará estar no topo (antes dos fallbacks).

### 2.8. `GROOVE` (Espelheira / Sistema Avante)
- **Critério de Detecção:** `"GROOVE"` em `upper` (9º teste). Subtipo `"GROOVE"`.
- **Comportamento no Corte:**
  - Segue o ramo geral de portas + puxador + vidro.
  - Em portas (`PORTA DE BATER`, `PORTA DE CORRER`, `PORTA PASSAGEM / DIVISORIA`), `"GROOVE"` também ativa puxador **implícito** salvo presença de token negativo explícito.

### 2.9. `INTEIRA` (Porta Correr / Cascata / Passagem / Fechamento Inteira)
- **Critério de Detecção:** `"CORRER INTEIRA"` em `upper` (11º teste). Subtipo `"CORRER INTEIRA"`.
- **Exemplo Real de Descrição ERP:**
  - `2PTPPN1AJHBT1`: `NOVA PORTA DE PASSAGEM SUSPENSA_COM RODIZIO_CORRER INTEIRA ACABAMENTO DOIS LADOS_DIREITA_LARGURA 849_ALTURA 2138_PERFIL PADROES FOSCA ROSA CHA - FOSCA_PLACA EXTERNA ESPELHO PRATA_PLACA INTERNA GRUPO 3\ 0059 - SEPIA _COM PUX.SMART 1000MM PADRAO S101 - FOSCA (SEPIA E OAK)`
- **Comportamento no Corte:**
  - `"CORRER INTEIRA"` também está na lista de puxador implícito para portas (`qtd = 1`, `LATERAL (DIREITA)` no exemplo, com `tipo_puxador = "PUX.SMART 1000MM"`).
  - Por ser `NOVA PORTA DE PASSAGEM SUSPENSA`, é classificada em `PORTA PASSAGEM / DIVISORIA` (antes de `PORTA DE CORRER`), embora contenha `CORRER INTEIRA`.

### 2.10. `SINGULAR` (Porta Cascata Correr Singular com Vãos)
- **Critério de Detecção:** `"CORRER SINGULAR"` em `upper` (10º teste). Subtipo `"CASCATA SINGULAR"`.
- **Comportamento no Corte:**
  - Frequentemente acompanha o padrão de vãos `VAO INFERIOR <X>_VAO CENTRAL <Y>_VAO SUPERIOR <Z>` capturado pelo 3º ramo de `_extract_divisorias()`.
  - Com `N` vãos (`>= 2`), gera `N - 1` barras `Travessa Divisória Interna` na `largura` (descontando `desconto_divisoria_mm + div_adj_desc`).
  - **Limitação de vidro:** mesmo possuindo vãos/travessas, `compute_item_glasses()` calcula atualmente **1 única chapa inteira** pelas dimensões externas descontadas.

### 2.11. `MINI KENDO + BAGUETE` (Cristaleira Provence Urda)
- **Critério de Detecção:** `"MINI KENDO"` ou `"PROVENCE URDA"` em `upper` (2º teste). Subtipo `"PROVENCE URDA"`, código textual fallback `"3PERUNO6BG215B"`.
- **Exemplo Real de Descrição ERP:**
  - `2PTURED0S2FE1`: `CORTE PERFIS + PLACA DE VIDRO FRENTE PROVENCE URDA CRISTALEIRA - PLACA LARGURA 251 X ALTURA 743 MM - PERFIL MINI KENDO +BAGUETE(3PERUNO6BG215B) 02 UNIDADES MEDIDA 244 MM E 02 UNIDADES MEDIDA 743 MM - ACABAMENTO PLACA TRANSLUCIDO\TEXTURIZADO CANELADO`
- **Cálculo Passo a Passo (`2PTURED0S2FE1`):**
  - `_extract_dimensions()` (Caso 2 — `CRISTALEIRA`) extrai `largura_mm = 251.0`, `altura_mm = 743.0`, `corte_h_mm = 244.0`, `corte_v_mm = 743.0`.
  - `_extract_puxadores()` força `0` puxadores (`SEM PUXADOR`).
  - `compute_item_cuts()` (ramo `CRISTALEIRA`) usa `corte_h_mm` e `corte_v_mm` diretamente:
    - `2x Horizontal Quadro (Mini Kendo + Baguete)`: `244.0 - desconto_horizontal_mm`
    - `2x Vertical Quadro (Mini Kendo + Baguete)`: `743.0 - desconto_vertical_mm`
  - `compute_item_glasses()`: usa `largura_mm (251.0)` e `altura_mm (743.0)` com `2x Lateral` (`0.0 mm` no padrão).
- **Particularidades:** observe que neste modelo a medida de corte explícita da horizontal (`244 mm`) já difere da medida nominal da placa (`251 mm`), razão pela qual `desconto_horizontal_mm` e `desconto_vertical_mm` vêm zerados no JSON.

### 2.12. `OUTRO` (Regra Sentinela de Fallback)
- **Critério de Detecção:** qualquer item que não casou com os 11 modelos anteriores. Emite o warning `"Modelo de perfil não reconhecido automaticamente."`.
- **Papel no Sistema:** funciona como rede de segurança obrigatória em `cutting_engine.py` (`rules.get(item.modelo) or rules["OUTRO"]`). **Nunca delete `"OUTRO"` de `./backend/app/data/regras_corte.json`.**

---

## 3. Referência das 8 Categorias Construtivas

| Categoria | Subcategorias Possíveis | Força `qtd_puxadores = 0`? | Ramo Especial em `compute_item_cuts` / `compute_item_glasses`? | Observação de Manutenção |
| :--- | :--- | :--- | :--- | :--- |
| **`LINHA ALLU`** | `ESCADA ALLU`, `LATERAL NICHO ALLU`, `NICHO ALLU`, `ILHA ALLU`, `PE ALLU`, `ALLU EM U`, `BARRA ALLU` | **Sim** | **Sim** (ramo ALLU + multiplicador `qtd_estruturas` + `eh_formato_u` + sem vidro) | `LATERAL NICHO ALLU` precisa vir antes de `NICHO ALLU`. |
| **`CRISTALEIRA`** | `FRENTE PROVENCE URDA` | **Sim** | **Sim** (cortes explícitos `corte_h_mm` e `corte_v_mm`) | Exige padrão `PLACA LARGURA X ALTURA` + `02 UNIDADES MEDIDA...`. |
| **`PRATELEIRA / TAMPO VISOR`** | `TAMPO GAVETEIRO VISOR`, `PRATELEIRA VISOR` | **Sim** | **Sim (no vidro)** — fallback para medida explícita apenas se descontos de vidro forem `0.0` | `altura_mm` armazena a **profundidade** da peça. |
| **`FRENTE GAVETA`** | `FRENTE GAVETA` | Não | Não (ramo geral; puxador mapeado como `HORIZONTAL (BASCULA/GAVETA)`) | Requer `C/PUXADOR`, `_PUXADOR`, `USINADO`, `CATCH` ou `DJEI` para ter puxador. |
| **`FRENTE BASCULA`** | `BASCULA INFERIOR (HF)`, `BASCULA SUPERIOR (HF)`, `BASCULA INVERSA`, `BASCULA COMUM` | Não | Não (ramo geral; puxador mapeado como `HORIZONTAL (BASCULA/GAVETA)`) | Mesmo critério de detecção de puxador de `FRENTE GAVETA`. |
| **`PORTA PASSAGEM / DIVISORIA`** | `PORTA CASCATA`, `PORTA PASSAGEM SUSPENSA`, `PORTA FECHAMENTO PISO E TETO`, `PORTA FECHAMENTO SUSPENSA` | Não | Não (ramo geral + puxador implícito para `RISK`/`DJEI`/`GROOVE`/`CORRER INTEIRA`) | Deve preceder `PORTA DE CORRER` em `_extract_categoria_subcategoria()`. |
| **`PORTA DE BATER`** | `PORTA BATER` | Não | Não (ramo geral + puxador implícito para `RISK`/`DJEI`/`GROOVE`/`CORRER INTEIRA`) | Suporta divisórias/travessas horizontais. |
| **`PORTA DE CORRER`** | `PORTA CORRER ESPELHEIRA`, `PORTA CORRER` | Não | Não (ramo geral + puxador implícito para `RISK`/`DJEI`/`GROOVE`/`CORRER INTEIRA`) | Também captura `SOFT CLOSING` e `SISTEMA AVANTE`. |
| **`OUTRO`** | `OUTRO` | Não (`fallback 0`) | Não (ramo geral) | Indica padrão textual inédito no ERP. |

---

## Dependências (Grafo)

**⬅️ Complementa e é referenciado por:**
- [[03-Dominio-Calculos/Guia-Completo-Regras-e-Manutencao]]
- [[03-Dominio-Calculos/Regras-Extracao-e-Corte-Perfis]]

**➡️ Relacionado a:**
- [[03-Dominio-Calculos/Otimizacao-Barras-6m]]
- [[00-Visao-Geral/Index_Corte_local_portas]]
