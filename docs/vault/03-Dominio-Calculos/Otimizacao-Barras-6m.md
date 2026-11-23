---
modulo: "backend/app/bar_optimizer.py"
tipo: "dominio"
data_atualizacao: 2026-11-23
tags: [regras-negocio, otimizacao, barras-6m, cutting-stock, portas, serra-manual]
---

# Regra: Otimização Linear de Barras de 6m em Dois Cenários (Material vs Tempo)

**Contexto:** Organiza 100% das peças viáveis calculadas por `./backend/app/cutting_engine.py` para corte em barras padrão de 6 m (6000 mm, configurável), agrupando perfis físicos compatíveis e calculando **em paralelo dois cenários completos**: aproveitamento máximo de material e otimização do tempo de execução. A divisão artificial anterior em Grupo 1 (`<= perda_maxima`) e Grupo 2 e o parâmetro `Perda Máxima (cm)` foram removidos.

## Regra de Agrupamento (`resolve_profile_group`)

1. **Prioridade 1 — Código do Perfil cadastrado:** Utiliza `codigo_perfil_lateral` ou `codigo_perfil_puxador` definido por modelo em `./backend/app/data/regras_corte.json` (editável na aba `Regras e Descontos (mm)`). Modelos distintos com o mesmo código (ex.: `CATCH` e `DJEI` usando `5307` nas laterais) são unificados no mesmo grupo de corte.
2. **Prioridade 2 — Fallback `Modelo — Tipo`:** Quando o código do perfil não está preenchido, agrupa por `<MODELO> — Lateral` ou `<MODELO> — Puxador`.
3. **Acabamento:** Por padrão, otimiza em barra bruta (unificado). O parâmetro `separar_por_acabamento` permite segmentar adicionalmente por acabamento do perfil.

## Dois Cenários Paralelos (`build_bar_optimization`)

Todas as peças com `medida_corte_mm <= comprimento_barra_mm - desponte_mm` entram nos dois cenários; peças maiores são isoladas em `pecas_inviaveis_flat`:

- **Cenário 1 — Aproveitamento de Material (`cenarios.material`, via `_build_material_group`):**
  - Empacotamento global no menor número de barras possível (`_pack_min_bars`): portfólio BFD (`_bin_pack_bfd`), FFD (`_bin_pack_ffd`) e Preenchimento Exato (`_bin_pack_exact_fill` com `_find_bar_patterns`), seguido de redução exata 3-para-2 (`_reduce_bins_3_to_2`) e concentração de retalho na última barra (`_concentrate_scrap`).
  - **Modo Serra Manual — Mesma Medida Primeiro (`priorizar_mesma_medida=True`, via `_pack_same_measure_first`):** empacota priorizando barras que já possuem a mesma medida antes de aplicar Best-Fit, mantendo 0 sobras no cavalete e reduzindo drasticamente trocas manuais de batente e barras complexas (`>= 4` medidas distintas, contabilizadas em `medidas_distintas_barra` e `barras_complexas_qtd`).
  - **Encadeamento inteligente de medidas e ângulos (`_assign_and_order_material_bars` + `_order_pieces_by_angle`):** ordena a sequência de barras e orienta peças assimétricas (`45° / 90°` ↔ `90° / 45°`) para casar medida e ângulo entre peças e barras consecutivas, reduzindo trocas de batente e giros de serra sem alterar o consumo de barras.
- **Cenário 2 — Tempo de Execução (`cenarios.tempo_execucao`, via `_build_tempo_execucao_group`):**
  - Agrupa cortes idênticos em lote estritamente **da maior para a menor medida**, ordenando/orientando ângulos dentro do passo (`_order_pieces_by_angle`).
  - Quando `limite_sobras_simultaneas` é `None` (padrão), aloca via First-Fit Decreasing (FFD) reaproveitando todas as barras semi-cortadas.
  - **Cavalete por Ondas com Drenagem Automática (`limite_sobras_simultaneas >= 1`):** mantém uma janela ativa (`active_rack`) com no máximo `N` barras semi-cortadas simultâneas usando **Best-Fit**; sempre que o cavalete atinge `N` barras e uma nova barra seria necessária, **pausa a abertura de novas barras e drena o cavalete** (`_drain_rack`), cortando nas sobras ativas as maiores medidas compatíveis até liberar as vagas antes de abrir a próxima onda. Barras cuja sobra não comporta nenhuma peça pendente saem imediatamente (`_retire_dead_bars`).
  - `_annotate_rack_lifecycle` anota cada alocação com `vaga_cavalete`, `proximo_passo`, `eh_fim_barra`, `acao_cavalete` (`Guardar · Vaga #K (volta #P)`, `Manter · Vaga #K (volta #P)`, `Fim · Libera Vaga #K`, `Encerrar (sem cavalete)` ou `Fim da barra`), `cavalete_ocupacao` e `eh_drenagem` por passo, além de apurar `retomadas_sobras`, `pico_sobras_simultaneas` (`<= limite_sobras_simultaneas` quando definido) e `ciclos_drenagem` (`total_ciclos_drenagem`). Quando há limite ativo, `roteiro_flat` preserva a ordem cronológica das ondas/drenagem (`(grupo_nome, passo)`).

## Ângulos de Corte (`45°` / `90°`), Trocas de Ângulo e Perfil Simétrico (`//` vs `\/`)

- **Orientação automática de peças mistas (`_orient_piece_for_angle`):** peças com pontas diferentes (`45° / 90°`) são automaticamente invertidas (`45°/90° → 90°/45° → 45°/90°`) para entrar no mesmo ângulo do corte anterior.
- **Contagem de trocas de ângulo (`total_trocas_angulo` / `trocas_angulo_barra`):** soma transições entre peças consecutivas (`prev_angle != a_esq`) e mudanças internas em peças mistas (`a_esq != a_dir`).
- **Perfil Simétrico (`//` com giro de 180°) vs Assimétrico (`\/` sem giro):**
  - Quando duas peças adjacentes em 45° possuem `perfil_simetrico=True` (`perfil_simetrico_lateral` / `perfil_simetrico_puxador`), `_apply_bar_nesting` alterna `invertida` (`False, True, False, ...`), marca `juncao_entrada = "//"` e contabiliza `economia_chanfro_mm` em cada junção usando `_calc_pair_overlap_um`: `ov_um = min(w_prev, w_curr, c_prev // 2, c_curr // 2)` (se `largura_perfil_mm == 0.0`, alterna e marca `"//"` com economia `0.0 mm`).
  - Quando `perfil_simetrico=False`, as peças não podem girar (`invertida=False`), mantêm corte em V `juncao_entrada = "\/"` com economia `0.0 mm` (demais transições recebem `""` na 1ª peça, `"||"` em `90°+90°` e `"45↔90"` nas mistas).
  - **Impacto no empacotamento e consumo:** no Cenário 1 (`_build_material_group`), grupos homogêneos `45°/45°` simétricos com `W > 0` empacotam usando `pack_w_um = c_um + K_um - W` e `pack_cap_um = usable_um + K_um - W` (`_pack_min_bars` respeitando `sum(c) + (N-1)*K - (N-1)*W <= usable`), enquanto grupos heterogêneos usam o envelope conservador; no Cenário 2 (`_build_tempo_execucao_group`), o FFD consulta `_calc_pair_overlap_um(bar_state["pieces"][-1], p)` a cada encaixe em barra semi-cortada (`consumido_util_um += c_um + K_um - ov_um`).
  - `_build_bar_dict` apura `material_util_um = max(0, soma_pecas_um - econ_um)`, `consumido_um = D_um + material_util_um + kerfs_um`, `aproveitamento_pct`, `perfil_simetrico`, `modo_juncao_45` (`"// (Girar)"` vs `"\/ (Sem giro)"`), `economia_chanfro_mm`, `cortes_paralelos_qtd` e `cortes_v_qtd`.

## KPIs, Ajustes no Corte e Comparativo

- **Ajustes no Corte (`ajustes_corte` / `total_ajustes_corte`):** contabiliza **estritamente trocas consecutivas de medida** (`medida[i] != medida[i-1]`, via `_annotate_and_count_adjustments`), sem incluir a regulagem inicial do primeiro corte (logo, peças todas iguais resultam em `0` ajustes; no Cenário 2 equivale a `max(0, medidas_distintas - 1)`).
- **Resumo por cenário (`resumo`) e grupo:** `total_grupos`, `total_pecas_entrada`, `total_pecas_alocadas`, `total_pecas_inviaveis`, `total_barras`, `total_metros_pecas`, `aproveitamento_medio_pct` (% médio por barra via `_calc_avg_yield_and_loss`), `total_perda_mm`, `total_perda_metros`, `perda_media_barra_mm`, `total_ajustes_corte`, `total_trocas_angulo`, `total_economia_chanfro_mm`, `total_cortes_paralelos`, `total_cortes_v`, `total_barras_complexas` (`barras_complexas_qtd`), `total_retomadas_sobras` (`retomadas_sobras`), `pico_sobras_simultaneas`, `total_sobras_encerradas_limite` (`sobras_encerradas_limite`) e `total_ciclos_drenagem` (`ciclos_drenagem`).
- **Comparativo direto (`comparativo`):** expõe `diferenca_barras_tempo_vs_material`, `diferenca_perda_mm_tempo_vs_material`, `diferenca_perda_metros_tempo_vs_material`, `reducao_ajustes_tempo_vs_material`, `reducao_ajustes_pct`, `reducao_trocas_angulo_tempo_vs_material`, `diferenca_economia_chanfro_mm_tempo_vs_material`, `pico_sobras_tempo`, `total_retomadas_tempo` e `barras_complexas_material`.

## Parâmetros Configuráveis (`OptimizationConfig`)

- `comprimento_barra_mm` (padrão `6000.0` mm / 6 m)
- `espessura_serra_mm` (kerf descontado entre cortes, padrão `0.0` mm)
- `desponte_mm` (perda fixa nas pontas, padrão `0.0` mm)
- `separar_por_acabamento` (padrão `False`)
- `priorizar_mesma_medida` (padrão `False`, ativa `_pack_same_measure_first` no Cenário Material)
- `limite_sobras_simultaneas` (padrão `None`, inteiro `>= 1` que ativa ondas com drenagem automática de cavalete no Cenário Tempo)

## Motor em Micrômetros

- Converte medidas para micrômetros inteiros (`SCALE_UM = 1000`, `_to_um`, `_from_um`) evitando desvios de ponto flutuante em medidas decimais (ex.: `833.333 mm`), mantendo invariante estrito de conservação de peças nos dois cenários e no roteiro.

## Dependências (Grafo)

**⬅️ Consumido por:**
- [[02-Backend-API/API-Extracao-ERP-Portas]]
- [[01-Frontend-UI/Interface-Web-Corte-Portas]]

**➡️ Relacionado a:**
- [[03-Dominio-Calculos/Regras-Extracao-e-Corte-Perfis]]
