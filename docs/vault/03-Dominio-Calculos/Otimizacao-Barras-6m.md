---
modulo: "backend/app/bar_optimizer.py"
tipo: "dominio"
data_atualizacao: 2026-11-19
tags: [regras-negocio, otimizacao, barras-6m, cutting-stock, portas]
---

# Regra: Otimização Linear de Barras de 6m em Grupos

**Contexto:** Organiza as barras calculadas por `./backend/app/cutting_engine.py` para corte em barras padrão de 6 m (6000 mm, configurável), agrupando perfis compatíveis e separando o plano em dois grupos operacionais.

## Regra de Agrupamento (`resolve_profile_group`)

1. **Prioridade 1 — Código do Perfil cadastrado:** Utiliza `codigo_perfil_lateral` ou `codigo_perfil_puxador` definido por modelo em `./backend/app/data/regras_corte.json` (editável na aba `Regras e Descontos (mm)`). Modelos distintos com o mesmo código (ex.: `CATCH` e `DJEI` usando `5307` nas laterais) são unificados no mesmo grupo de corte.
2. **Prioridade 2 — Fallback `Modelo — Tipo`:** Quando o código do perfil não está preenchido, agrupa por `<MODELO> — Lateral` ou `<MODELO> — Puxador`.
3. **Acabamento:** Por padrão, otimiza em barra bruta (unificado). O parâmetro `separar_por_acabamento` permite segmentar adicionalmente por acabamento do perfil.

## Separação em Dois Grupos

- **Grupo 1 — Organizados na Barra de 6m (`barras_fechadas` / `barras_otimizadas_flat`):**
  - Combinações cuja sobra final seja menor ou igual à perda máxima configurável (`perda_maxima_mm`, padrão `200 mm` = `20 cm`).
  - Peças dentro de cada barra ordenadas do maior para o menor comprimento.
- **Grupo 2 — Peças Restantes (Maior → Menor) e Otimização em Menor Nº de Barras (`nao_alocados` / `barras_grupo2` / `barras_grupo2_flat`):**
  - Mantém integralmente a listagem ordenada estritamente **do maior para o menor** (`medida_corte_mm` decrescente) das peças que não fecharam barra no Grupo 1 ou excederam a barra útil.
  - Otimiza todas as peças viáveis (`<= comprimento_barra_mm - desponte_mm`) no menor número possível de barras de 6 m (`_pack_min_bars`), combinando BFD/FFD/Preenchimento Exato, redução 3-para-2 (`_reduce_bins_3_to_2`) e concentração de sobra (`_concentrate_scrap`).

## KPIs Calculados por Grupo e Consolidado

- **Grupo 1:** `total_barras_6m`, `aproveitamento_medio_pct` (% médio por barra), `total_perda_mm`, `total_perda_metros` e `perda_media_barra_grupo1_mm`.
- **Grupo 2 Otimizado:** `total_barras_grupo2`, `aproveitamento_medio_grupo2_pct` (% médio por barra), `total_perda_grupo2_mm`, `total_perda_grupo2_metros`, `perda_media_barra_grupo2_mm` e `total_pecas_inviaveis`.
- **Geral Consolidado (Grupo 1 + Grupo 2):** `total_barras_geral`, `aproveitamento_medio_geral_pct` (% médio por barra), `total_perda_geral_mm`, `total_perda_geral_metros` e `perda_media_barra_geral_mm`.

## Parâmetros Configuráveis (`OptimizationConfig`)

- `comprimento_barra_mm` (padrão `6000.0` mm / 6 m)
- `perda_maxima_mm` (padrão `200.0` mm / 20 cm)
- `espessura_serra_mm` (kerf descontado entre cortes, padrão `0.0` mm)
- `desponte_mm` (perda fixa nas pontas, padrão `0.0` mm)
- `separar_por_acabamento` (padrão `False`)

## Motor Híbrido em Micrômetros

- Converte medidas para micrômetros inteiros (`SCALE_UM = 1000`) evitando desvios de ponto flutuante em medidas decimais (ex.: `833.333 mm`).
- Estágio 1: Portfólio de 3 heurísticas com branch-and-bound exato por barra (`tightest`, `conserve_small`, `BFD seeded`).
- Estágio 2: Refinamento por trocas `1-por-1` e `1-por-2`, backtracking multi-barras com orçamento limitado e polimento final de perda, garantindo invariante estrito de conservação de peças.

## Dependências (Grafo)

**⬅️ Consumido por:**
- [[02-Backend-API/API-Extracao-ERP-Portas]]
- [[01-Frontend-UI/Interface-Web-Corte-Portas]]

**➡️ Relacionado a:**
- [[03-Dominio-Calculos/Regras-Extracao-e-Corte-Perfis]]
