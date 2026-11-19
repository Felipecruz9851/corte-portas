"""Otimizador de corte linear em barras (padrão 6 m) com agrupamento por código de perfil."""

from __future__ import annotations

import math
from bisect import bisect_left
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.cutting_engine import CuttingRule

SCALE_UM = 1000  # 1 mm = 1000 µm (evita imprecisão de ponto flutuante)


def _to_um(mm: float) -> int:
    return int(round(float(mm) * SCALE_UM))


def _from_um(um: int) -> float:
    return round(um / SCALE_UM, 3)


@dataclass
class OptimizationConfig:
    """Parâmetros configuráveis para otimização em barras de 6 m."""

    comprimento_barra_mm: float = 6000.0
    perda_maxima_mm: float = 200.0
    espessura_serra_mm: float = 0.0
    desponte_mm: float = 0.0
    separar_por_acabamento: bool = False

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["perda_maxima_cm"] = round(self.perda_maxima_mm / 10.0, 2)
        return data


def resolve_profile_group(
    bar: Dict[str, Any],
    rules: Optional[Dict[str, CuttingRule]] = None,
    separar_por_acabamento: bool = False,
) -> Tuple[str, str, str, str, str]:
    """Resolve a chave de agrupamento de uma barra de corte.

    Prioridade:
    1. Código do perfil cadastrado (`codigo_perfil` na barra ou na regra do modelo);
    2. Fallback: `<MODELO> — <Tipo (Puxador ou Lateral)>`.
    """
    eh_puxador = bool(bar.get("eh_perfil_puxador"))
    tipo_perfil = (bar.get("tipo_perfil") or "").strip() or (
        "Puxador" if eh_puxador else "Lateral"
    )
    modelo = (bar.get("modelo") or "OUTRO").strip()

    codigo_perfil = (bar.get("codigo_perfil") or "").strip()
    if not codigo_perfil and rules:
        rule = rules.get(modelo)
        if rule is not None:
            codigo_perfil = (
                rule.codigo_perfil_puxador if eh_puxador else rule.codigo_perfil_lateral
            ).strip()

    if codigo_perfil:
        base_key = f"COD::{codigo_perfil.upper()}"
        base_label = codigo_perfil
        origem = "codigo_perfil"
    else:
        base_key = f"MT::{modelo.upper()}::{tipo_perfil.upper()}"
        base_label = f"{modelo} — {tipo_perfil}"
        origem = "modelo_tipo"

    if separar_por_acabamento:
        acab = (bar.get("acabamento_perfil") or "PADRAO").strip()
        group_key = f"{base_key}::ACAB::{acab.upper()}"
        group_label = f"{base_label} · {acab}"
    else:
        group_key = base_key
        group_label = base_label

    return group_key, group_label, origem, codigo_perfil, tipo_perfil


def _find_bar_patterns(
    weights: List[int],
    avail_qty: List[int],
    w_min_um: int,
    cap_um: int,
    start_idx: int,
    mode: str = "tightest",
    max_patterns: int = 1,
    node_limit: int = 6000,
) -> List[Dict[int, int]]:
    """Busca exata com branch-and-bound de padrões válidos de 1 barra contendo `start_idx`.

    Um padrão válido usa apenas índices >= `start_idx`, contém ao menos 1 peça de `start_idx`,
    e tem soma em `[w_min_um, cap_um]`.
    """
    m = len(weights)
    if start_idx >= m or avail_qty[start_idx] <= 0:
        return []
    anchor_w = weights[start_idx]
    if anchor_w > cap_um:
        return []

    # Soma restante a partir de cada índice (excluindo a peça âncora já alocada)
    suffix_sum = [0] * (m + 1)
    for i in range(m - 1, -1, -1):
        suffix_sum[i] = suffix_sum[i + 1] + weights[i] * avail_qty[i]

    min_w_global = weights[-1]
    avail_work = list(avail_qty)
    avail_work[start_idx] -= 1

    # Para avançar rápido quando rem_space < weights[idx], usamos pesos negativos apenas se necessário;
    # como weights está em ordem decrescente, preparamos lista ascendente para bisect_left se m > 12.
    neg_weights = [-w for w in weights]

    nodes = 0
    best_tight: Optional[Tuple[int, int, Dict[int, int]]] = None  # (sum_um, -count, pattern)
    best_conserve: Optional[Tuple[int, int, Dict[int, int]]] = None  # (-count, sum_um, pattern)
    collected: List[Tuple[int, int, Dict[int, int]]] = []
    collect_limit = max(max_patterns * 6, 36)

    cur_pattern: Dict[int, int] = {start_idx: 1}

    def record_candidate(cur_sum: int, cur_count: int) -> None:
        nonlocal best_tight, best_conserve
        snap = dict(cur_pattern)
        if mode == "tightest":
            cand = (cur_sum, -cur_count, snap)
            if best_tight is None or (cand[0], cand[1]) > (best_tight[0], best_tight[1]):
                best_tight = cand
        elif mode == "conserve_small":
            cand = (-cur_count, cur_sum, snap)
            if best_conserve is None or (cand[0], cand[1]) > (
                best_conserve[0],
                best_conserve[1],
            ):
                best_conserve = cand
        else:
            collected.append((cur_sum, -cur_count, snap))

    if anchor_w >= w_min_um:
        record_candidate(anchor_w, 1)
        if mode == "tightest" and anchor_w == cap_um:
            return [best_tight[2]] if best_tight else []
        if mode == "conserve_small":
            return [best_conserve[2]] if best_conserve else []

    def next_fitting_idx(idx: int, rem_space: int) -> int:
        if idx >= m or weights[idx] <= rem_space:
            return idx
        return bisect_left(neg_weights, -rem_space, lo=idx, hi=m)

    def dfs(idx: int, cur_sum: int, cur_count: int, rem_avail_after_anchor: int) -> None:
        nonlocal nodes
        if nodes >= node_limit:
            return
        if mode == "tightest" and best_tight is not None and best_tight[0] == cap_um:
            return
        if mode == "top_k" and len(collected) >= collect_limit:
            return
        if mode == "conserve_small" and best_conserve is not None:
            best_cnt = -best_conserve[0]
            if cur_count >= best_cnt:
                return

        rem_space = cap_um - cur_sum
        if rem_space < min_w_global:
            return

        idx = next_fitting_idx(idx, rem_space)
        if idx >= m:
            return

        # Soma disponível real a partir de `idx`
        max_add = suffix_sum[idx]
        if idx == start_idx:
            max_add -= anchor_w
        if cur_sum + max_add < w_min_um:
            return
        if mode == "tightest" and best_tight is not None:
            if cur_sum + max_add < best_tight[0]:
                return

        # Poda de folha: se cabe no máximo 1 peça adicional (rem_space < 2 * min_w_global)
        if rem_space < 2 * min_w_global:
            if mode == "top_k":
                need_min = max(0, w_min_um - cur_sum)
                for j in range(idx, m):
                    if avail_work[j] > 0 and need_min <= weights[j] <= rem_space:
                        cur_pattern[j] = cur_pattern.get(j, 0) + 1
                        record_candidate(cur_sum + weights[j], cur_count + 1)
                        if cur_pattern[j] == 1:
                            del cur_pattern[j]
                        else:
                            cur_pattern[j] -= 1
                        if len(collected) >= collect_limit:
                            return
                return
            for j in range(idx, m):
                if avail_work[j] > 0 and weights[j] <= rem_space:
                    if cur_sum + weights[j] >= w_min_um:
                        cur_pattern[j] = cur_pattern.get(j, 0) + 1
                        record_candidate(cur_sum + weights[j], cur_count + 1)
                        if cur_pattern[j] == 1:
                            del cur_pattern[j]
                        else:
                            cur_pattern[j] -= 1
                    return
            return

        nodes += 1
        avail = avail_work[idx]
        if avail <= 0:
            dfs(idx + 1, cur_sum, cur_count, rem_avail_after_anchor)
            return

        w_i = weights[idx]
        max_take = min(avail, rem_space // w_i)
        if mode == "conserve_small" and best_conserve is not None:
            best_cnt = -best_conserve[0]
            max_take = min(max_take, max(0, best_cnt - cur_count))

        for take in range(max_take, -1, -1):
            if nodes >= node_limit:
                break
            if mode == "tightest" and best_tight is not None and best_tight[0] == cap_um:
                break
            if mode == "top_k" and len(collected) >= collect_limit:
                break
            if mode == "conserve_small" and best_conserve is not None:
                if take > 0 and cur_count + take > -best_conserve[0]:
                    continue

            new_sum = cur_sum + take * w_i
            new_count = cur_count + take
            if take > 0:
                cur_pattern[idx] = cur_pattern.get(idx, 0) + take
                if new_sum >= w_min_um:
                    record_candidate(new_sum, new_count)

            # Em conserve_small, se já atingimos w_min_um com `take`, estender só aumenta peças
            if not (mode == "conserve_small" and take > 0 and new_sum >= w_min_um):
                dfs(idx + 1, new_sum, new_count, rem_avail_after_anchor)

            if take > 0:
                prev_q = cur_pattern[idx] - take
                if prev_q <= 0:
                    del cur_pattern[idx]
                else:
                    cur_pattern[idx] = prev_q

    dfs(start_idx, anchor_w, 1, suffix_sum[start_idx] - anchor_w)

    if mode == "tightest":
        return [best_tight[2]] if best_tight is not None else []
    if mode == "conserve_small":
        return [best_conserve[2]] if best_conserve is not None else []

    collected.sort(key=lambda item: (-item[0], -item[1]))
    seen = set()
    unique_patterns: List[Dict[int, int]] = []
    for _, _, pat in collected:
        sig = tuple(sorted(pat.items()))
        if sig not in seen:
            seen.add(sig)
            unique_patterns.append(pat)
            if len(unique_patterns) >= max_patterns:
                break
    return unique_patterns


def _greedy_largest_first(
    weights: List[int],
    counts: List[int],
    w_min_um: int,
    cap_um: int,
    mode: str,
) -> Tuple[List[Dict[int, int]], List[int]]:
    rem = list(counts)
    bars: List[Dict[int, int]] = []
    m = len(weights)
    anchor = 0
    node_limit = 800 if mode == "conserve_small" else 2000

    while anchor < m:
        if rem[anchor] <= 0:
            anchor += 1
            continue
        rem_total = sum(weights[i] * rem[i] for i in range(anchor, m))
        if rem_total < w_min_um:
            break
        patterns = _find_bar_patterns(
            weights,
            rem,
            w_min_um,
            cap_um,
            anchor,
            mode=mode,
            max_patterns=1,
            node_limit=node_limit,
        )
        if not patterns:
            anchor += 1
            continue
        pat = patterns[0]
        bars.append(pat)
        for idx, q in pat.items():
            rem[idx] -= q

    return bars, rem


def _bfd_seeded_solve(
    weights: List[int],
    counts: List[int],
    w_min_um: int,
    cap_um: int,
) -> Tuple[List[Dict[int, int]], List[int]]:
    """Best-Fit Decreasing mantendo bins que atingiram [w_min_um, cap_um] e reotimizando o resto."""
    bins: List[Tuple[int, Dict[int, int]]] = []  # (remaining_space, pattern)
    for idx, q in enumerate(counts):
        w = weights[idx]
        for _ in range(q):
            best_b = -1
            best_rem = cap_um + 1
            for b_idx, (b_rem, _) in enumerate(bins):
                if w <= b_rem < best_rem:
                    best_rem = b_rem
                    best_b = b_idx
                    if b_rem == w:
                        break
            if best_b >= 0:
                old_rem, pat = bins[best_b]
                pat[idx] = pat.get(idx, 0) + 1
                bins[best_b] = (old_rem - w, pat)
            else:
                bins.append((cap_um - w, {idx: 1}))

    closed_bars: List[Dict[int, int]] = []
    leftover = [0] * len(weights)
    for b_rem, pat in bins:
        used = cap_um - b_rem
        if w_min_um <= used <= cap_um:
            closed_bars.append(pat)
        else:
            for idx, q in pat.items():
                leftover[idx] += q

    extra_bars, final_rem = _greedy_largest_first(
        weights, leftover, w_min_um, cap_um, mode="tightest"
    )
    return closed_bars + extra_bars, final_rem


def _score_solution(
    bars: List[Dict[int, int]], weights: List[int]
) -> Tuple[int, int, int]:
    total_packed = sum(weights[i] * q for pat in bars for i, q in pat.items())
    total_pieces = sum(q for pat in bars for q in pat.values())
    return (len(bars), total_packed, -total_pieces)


def _improve_by_swaps(
    bars: List[Dict[int, int]],
    rem: List[int],
    weights: List[int],
    w_min_um: int,
    cap_um: int,
) -> Tuple[List[Dict[int, int]], List[int]]:
    """Tenta trocas 1-por-1 e 1-por-2 entre barras fechadas e sobras para fechar novas barras."""
    bars = [dict(b) for b in bars]
    rem = list(rem)
    m = len(weights)

    def try_extract_new_bars(trial_rem: List[int]) -> Optional[Tuple[List[Dict[int, int]], List[int]]]:
        if sum(weights[i] * trial_rem[i] for i in range(m)) < w_min_um:
            return None
        new_bars, after_rem = _greedy_largest_first(
            weights, trial_rem, w_min_um, cap_um, mode="tightest"
        )
        if new_bars:
            return new_bars, after_rem
        return None

    for _ in range(40):
        improved = False
        rem_indices = [i for i in range(m) if rem[i] > 0]
        if not rem_indices:
            break

        for b_idx, pat in enumerate(bars):
            bar_sum = sum(weights[i] * q for i, q in pat.items())
            out_candidates = sorted(pat.keys())

            # Caso A: troca 1 peça da barra por 1 peça das sobras
            for out_i in out_candidates:
                base_sum = bar_sum - weights[out_i]
                for in_i in rem_indices:
                    if in_i == out_i:
                        continue
                    new_bar_sum = base_sum + weights[in_i]
                    if not (w_min_um <= new_bar_sum <= cap_um):
                        continue
                    trial_rem = list(rem)
                    trial_rem[out_i] += 1
                    trial_rem[in_i] -= 1
                    extracted = try_extract_new_bars(trial_rem)
                    if extracted is not None:
                        new_bars, after_rem = extracted
                        pat[out_i] -= 1
                        if pat[out_i] <= 0:
                            del pat[out_i]
                        pat[in_i] = pat.get(in_i, 0) + 1
                        bars.extend(new_bars)
                        rem = after_rem
                        improved = True
                        break
                if improved:
                    break
            if improved:
                break

            # Caso B: troca 1 peça da barra por 2 peças das sobras (para m moderado)
            if m <= 35:
                for out_i in out_candidates:
                    base_sum = bar_sum - weights[out_i]
                    for pos1, in1 in enumerate(rem_indices):
                        if in1 == out_i:
                            continue
                        for in2 in rem_indices[pos1:]:
                            if in2 == out_i:
                                continue
                            if in1 == in2 and rem[in1] < 2:
                                continue
                            new_bar_sum = base_sum + weights[in1] + weights[in2]
                            if not (w_min_um <= new_bar_sum <= cap_um):
                                continue
                            trial_rem = list(rem)
                            trial_rem[out_i] += 1
                            trial_rem[in1] -= 1
                            trial_rem[in2] -= 1
                            extracted = try_extract_new_bars(trial_rem)
                            if extracted is not None:
                                new_bars, after_rem = extracted
                                pat[out_i] -= 1
                                if pat[out_i] <= 0:
                                    del pat[out_i]
                                pat[in1] = pat.get(in1, 0) + 1
                                pat[in2] = pat.get(in2, 0) + 1
                                bars.extend(new_bars)
                                rem = after_rem
                                improved = True
                                break
                        if improved:
                            break
                    if improved:
                        break
                if improved:
                    break

        if not improved:
            break

    return bars, rem


def _polish_waste(
    bars: List[Dict[int, int]],
    rem: List[int],
    weights: List[int],
    cap_um: int,
) -> Tuple[List[Dict[int, int]], List[int]]:
    """Trocas 1-por-1 que reduzem estritamente a perda das barras já fechadas."""
    bars = [dict(b) for b in bars]
    rem = list(rem)
    m = len(weights)

    for _ in range(40):
        improved = False
        for pat in bars:
            bar_sum = sum(weights[i] * q for i, q in pat.items())
            if bar_sum == cap_um:
                continue
            max_gain = cap_um - bar_sum
            for out_i in list(pat.keys()):
                w_out = weights[out_i]
                for in_i in range(m):
                    if rem[in_i] <= 0:
                        continue
                    diff = weights[in_i] - w_out
                    if 0 < diff <= max_gain:
                        pat[out_i] -= 1
                        if pat[out_i] <= 0:
                            del pat[out_i]
                        pat[in_i] = pat.get(in_i, 0) + 1
                        rem[in_i] -= 1
                        rem[out_i] += 1
                        improved = True
                        break
                if improved:
                    break
            if improved:
                break
        if not improved:
            break

    return bars, rem


def _solve_counts(
    weights: List[int],
    counts: List[int],
    w_min_um: int,
    cap_um: int,
) -> List[Dict[int, int]]:
    """Otimiza quantidade máxima de barras válidas dentro de [w_min_um, cap_um]."""
    m = len(weights)
    if m == 0:
        return []
    total_w = sum(weights[i] * counts[i] for i in range(m))
    if total_w < w_min_um:
        return []

    ub = total_w // w_min_um

    # Estágio 1: Portfólio rápido de 3 heurísticas
    candidates = [
        _greedy_largest_first(weights, counts, w_min_um, cap_um, mode="tightest"),
        _greedy_largest_first(weights, counts, w_min_um, cap_um, mode="conserve_small"),
        _bfd_seeded_solve(weights, counts, w_min_um, cap_um),
    ]

    best_bars, best_rem = max(
        candidates, key=lambda pair: _score_solution(pair[0], weights)
    )

    # Estágio 2a: Trocas entre barras e sobras
    if len(best_bars) < ub:
        swapped_bars, swapped_rem = _improve_by_swaps(
            best_bars, best_rem, weights, w_min_um, cap_um
        )
        if _score_solution(swapped_bars, weights) > _score_solution(best_bars, weights):
            best_bars, best_rem = swapped_bars, swapped_rem

    # Estágio 2b: Backtracking multi-barras limitado se ainda abaixo do upper bound
    if len(best_bars) < ub:
        best_score = _score_solution(best_bars, weights)
        budget = [400]
        best_bt: Optional[Tuple[List[Dict[int, int]], List[int]]] = None

        def bt(rem_cur: List[int], start_idx: int, cur_bars: List[Dict[int, int]]) -> None:
            nonlocal best_score, best_bt
            if budget[0] <= 0 or best_score[0] >= ub:
                return
            budget[0] -= 1

            rem_sum = sum(weights[i] * rem_cur[i] for i in range(start_idx, m))
            if len(cur_bars) + (rem_sum // w_min_um) <= best_score[0]:
                return

            anchor = start_idx
            while anchor < m and rem_cur[anchor] <= 0:
                anchor += 1

            if anchor >= m or rem_sum < w_min_um:
                sc = _score_solution(cur_bars, weights)
                if sc > best_score:
                    best_score = sc
                    best_bt = ([dict(p) for p in cur_bars], list(rem_cur))
                return

            # Gera diversidade de padrões: tightest + conserve_small + top_k
            raw_pats: List[Dict[int, int]] = []
            for m_mode, k_lim in (("tightest", 1), ("conserve_small", 1), ("top_k", 4)):
                raw_pats.extend(
                    _find_bar_patterns(
                        weights,
                        rem_cur,
                        w_min_um,
                        cap_um,
                        anchor,
                        mode=m_mode,
                        max_patterns=k_lim,
                        node_limit=350,
                    )
                )

            dedup_pats: List[Dict[int, int]] = []
            seen_sigs = set()
            for pat in raw_pats:
                sig = tuple(sorted(pat.items()))
                if sig not in seen_sigs:
                    seen_sigs.add(sig)
                    dedup_pats.append(pat)
                    if len(dedup_pats) >= 5:
                        break

            for pat in dedup_pats:
                next_rem = list(rem_cur)
                for idx, q in pat.items():
                    next_rem[idx] -= q
                cur_bars.append(pat)
                bt(next_rem, anchor, cur_bars)
                cur_bars.pop()
                if best_score[0] >= ub or budget[0] <= 0:
                    return

            # Ramo de pular completamente `anchor` caso valha a pena
            rem_without_anchor = rem_sum - weights[anchor] * rem_cur[anchor]
            if len(cur_bars) + (rem_without_anchor // w_min_um) > best_score[0]:
                bt(rem_cur, anchor + 1, cur_bars)

        bt(list(counts), 0, [])
        if best_bt is not None and _score_solution(best_bt[0], weights) > _score_solution(
            best_bars, weights
        ):
            best_bars, best_rem = best_bt

    # Estágio 2c: Polimento de perda mantendo o número máximo de barras
    best_bars, best_rem = _polish_waste(best_bars, best_rem, weights, cap_um)

    # Garantia explícita de invariante: nunca consumir além de `counts`
    used_check = [0] * m
    valid_bars: List[Dict[int, int]] = []
    for pat in best_bars:
        pat_sum = sum(weights[i] * q for i, q in pat.items())
        if not (w_min_um <= pat_sum <= cap_um):
            continue
        if all(used_check[i] + q <= counts[i] for i, q in pat.items()):
            for i, q in pat.items():
                used_check[i] += q
            valid_bars.append(pat)

    return valid_bars


def _bin_pack_bfd(
    weights: List[int], counts: List[int], cap_um: int
) -> List[Dict[int, int]]:
    bins: List[Tuple[int, Dict[int, int]]] = []
    for idx, q in enumerate(counts):
        w = weights[idx]
        for _ in range(q):
            best_b = -1
            best_rem = cap_um + 1
            for b_idx, (b_rem, _) in enumerate(bins):
                if w <= b_rem < best_rem:
                    best_rem = b_rem
                    best_b = b_idx
                    if b_rem == w:
                        break
            if best_b >= 0:
                old_rem, pat = bins[best_b]
                pat[idx] = pat.get(idx, 0) + 1
                bins[best_b] = (old_rem - w, pat)
            else:
                bins.append((cap_um - w, {idx: 1}))
    return [pat for _, pat in bins]


def _bin_pack_ffd(
    weights: List[int], counts: List[int], cap_um: int
) -> List[Dict[int, int]]:
    bins: List[Tuple[int, Dict[int, int]]] = []
    for idx, q in enumerate(counts):
        w = weights[idx]
        for _ in range(q):
            placed = False
            for b_idx, (b_rem, pat) in enumerate(bins):
                if w <= b_rem:
                    pat[idx] = pat.get(idx, 0) + 1
                    bins[b_idx] = (b_rem - w, pat)
                    placed = True
                    break
            if not placed:
                bins.append((cap_um - w, {idx: 1}))
    return [pat for _, pat in bins]


def _bin_pack_exact_fill(
    weights: List[int], counts: List[int], cap_um: int
) -> List[Dict[int, int]]:
    rem = list(counts)
    bins: List[Dict[int, int]] = []
    m = len(weights)
    anchor = 0
    while anchor < m:
        if rem[anchor] <= 0:
            anchor += 1
            continue
        rem_total = sum(weights[i] * rem[i] for i in range(anchor, m))
        if rem_total <= cap_um:
            pat = {i: rem[i] for i in range(anchor, m) if rem[i] > 0}
            if pat:
                bins.append(pat)
            break
        pats = _find_bar_patterns(
            weights,
            rem,
            w_min_um=weights[anchor],
            cap_um=cap_um,
            start_idx=anchor,
            mode="tightest",
            max_patterns=1,
            node_limit=800,
        )
        pat = pats[0] if pats else {anchor: 1}
        bins.append(pat)
        for idx, q in pat.items():
            rem[idx] -= q
    return bins


def _bin_fill_um(pat: Dict[int, int], weights: List[int]) -> int:
    return sum(weights[i] * q for i, q in pat.items())


def _score_min_bins(bins: List[Dict[int, int]], weights: List[int]) -> Tuple[int, int]:
    fills = [_bin_fill_um(pat, weights) for pat in bins]
    return (-len(bins), sum(f * f for f in fills))


def _reduce_bins_3_to_2(
    bins: List[Dict[int, int]],
    weights: List[int],
    cap_um: int,
    lb: int,
) -> List[Dict[int, int]]:
    """Tenta fundir 3 bins subutilizados em 2 bins exatos quando acima do lower bound."""
    bins = [dict(b) for b in bins]
    for _ in range(30):
        if len(bins) <= lb or len(bins) < 3:
            break
        bins.sort(key=lambda b: _bin_fill_um(b, weights))
        fills = [_bin_fill_um(b, weights) for b in bins]
        reduced = False

        n = len(bins)
        # Prioriza combinações envolvendo os bins mais vazios no início da lista
        tail_limit = min(n - 2, 4)
        for t in range(tail_limit):
            for i in range(t + 1, n - 1):
                if fills[t] + fills[i] > 2 * cap_um:
                    continue
                for j in range(i + 1, n):
                    s3 = fills[t] + fills[i] + fills[j]
                    if s3 > 2 * cap_um:
                        continue
                    pool: Dict[int, int] = Counter()
                    for b_idx in (t, i, j):
                        for k_idx, q in bins[b_idx].items():
                            pool[k_idx] += q

                    if s3 <= cap_um:
                        new_bins = [dict(pool)]
                    else:
                        sub_indices = sorted(pool.keys())
                        sub_w = [weights[k] for k in sub_indices]
                        sub_c = [pool[k] for k in sub_indices]
                        target_min = max(1, s3 - cap_um)

                        found_sub: Optional[Dict[int, int]] = None
                        for start_sub in range(len(sub_w)):
                            pats = _find_bar_patterns(
                                sub_w,
                                sub_c,
                                target_min,
                                cap_um,
                                start_idx=start_sub,
                                mode="tightest",
                                max_patterns=1,
                                node_limit=600,
                            )
                            if pats:
                                found_sub = pats[0]
                                break
                        if found_sub is None:
                            continue

                        bin_a: Dict[int, int] = {}
                        bin_b: Dict[int, int] = {}
                        for pos, q in found_sub.items():
                            orig_idx = sub_indices[pos]
                            bin_a[orig_idx] = q
                        for orig_idx, total_q in pool.items():
                            rem_q = total_q - bin_a.get(orig_idx, 0)
                            if rem_q > 0:
                                bin_b[orig_idx] = rem_q
                        new_bins = [b for b in (bin_a, bin_b) if b]

                    bins = [
                        b for idx_b, b in enumerate(bins) if idx_b not in (t, i, j)
                    ] + new_bins
                    reduced = True
                    break
                if reduced:
                    break
            if reduced:
                break

        if not reduced:
            break

    return bins


def _concentrate_scrap(
    bins: List[Dict[int, int]], weights: List[int], cap_um: int
) -> List[Dict[int, int]]:
    """Concentra preenchimento nas barras maiores para preservar o maior retalho no fim."""
    bins = [dict(b) for b in bins if b]
    for _ in range(40):
        bins.sort(key=lambda b: _bin_fill_um(b, weights), reverse=True)
        fills = [_bin_fill_um(b, weights) for b in bins]
        improved = False
        n = len(bins)

        for hi in range(n - 1):
            space_hi = cap_um - fills[hi]
            if space_hi <= 0:
                continue
            for lo in range(n - 1, hi, -1):
                # 1) Mover 1 peça de lo -> hi se couber
                for idx in sorted(bins[lo].keys()):
                    w_move = weights[idx]
                    if w_move <= space_hi:
                        bins[hi][idx] = bins[hi].get(idx, 0) + 1
                        bins[lo][idx] -= 1
                        if bins[lo][idx] <= 0:
                            del bins[lo][idx]
                        if not bins[lo]:
                            bins.pop(lo)
                        improved = True
                        break
                if improved:
                    break

                # 2) Trocar 1 menor de hi por 1 maior de lo aumentando fill(hi)
                for idx_hi in sorted(bins[hi].keys(), reverse=True):
                    w_hi = weights[idx_hi]
                    for idx_lo in sorted(bins[lo].keys()):
                        diff = weights[idx_lo] - w_hi
                        if 0 < diff <= space_hi:
                            bins[hi][idx_hi] -= 1
                            if bins[hi][idx_hi] <= 0:
                                del bins[hi][idx_hi]
                            bins[hi][idx_lo] = bins[hi].get(idx_lo, 0) + 1

                            bins[lo][idx_lo] -= 1
                            if bins[lo][idx_lo] <= 0:
                                del bins[lo][idx_lo]
                            bins[lo][idx_hi] = bins[lo].get(idx_hi, 0) + 1
                            improved = True
                            break
                    if improved:
                        break
                if improved:
                    break
            if improved:
                break

        if not improved:
            break

    return [b for b in bins if b]


def _pack_min_bars(
    weights: List[int],
    counts: List[int],
    cap_um: int,
) -> List[Dict[int, int]]:
    """Otimiza peças elegíveis no menor número possível de barras (<= cap_um)."""
    m = len(weights)
    if m == 0 or sum(counts) == 0:
        return []

    total_w = sum(weights[i] * counts[i] for i in range(m))
    if total_w <= cap_um:
        return [{i: counts[i] for i in range(m) if counts[i] > 0}]

    lb_vol = (total_w + cap_um - 1) // cap_um
    lb_half = sum(counts[i] for i in range(m) if weights[i] * 2 > cap_um)
    lb = max(lb_vol, lb_half)

    candidates = [
        _bin_pack_bfd(weights, counts, cap_um),
        _bin_pack_ffd(weights, counts, cap_um),
        _bin_pack_exact_fill(weights, counts, cap_um),
    ]
    best_bins = max(candidates, key=lambda b: _score_min_bins(b, weights))

    if len(best_bins) > lb:
        reduced = _reduce_bins_3_to_2(best_bins, weights, cap_um, lb)
        if _score_min_bins(reduced, weights) > _score_min_bins(best_bins, weights):
            best_bins = reduced

    best_bins = _concentrate_scrap(best_bins, weights, cap_um)

    # Garantia explícita de invariante: soma <= cap_um e consumo exato de counts
    used_check = [0] * m
    valid_bins: List[Dict[int, int]] = []
    for pat in best_bins:
        clean_pat = {i: q for i, q in pat.items() if q > 0}
        if not clean_pat:
            continue
        pat_sum = _bin_fill_um(clean_pat, weights)
        if pat_sum <= cap_um and all(
            used_check[i] + q <= counts[i] for i, q in clean_pat.items()
        ):
            for i, q in clean_pat.items():
                used_check[i] += q
            valid_bins.append(clean_pat)

    return valid_bins


def _format_padrao_corte(pieces: List[Dict[str, Any]]) -> str:
    """Formata o padrão de corte da barra em ordem decrescente de medida."""
    counts: Dict[float, int] = Counter()
    for p in pieces:
        counts[float(p["medida_corte_mm"])] += 1
    parts = []
    for med in sorted(counts.keys(), reverse=True):
        med_str = f"{med:g}"
        parts.append(f"{counts[med]}× {med_str} mm")
    return " + ".join(parts)


def _materialize_bars(
    patterns: List[Dict[int, int]],
    weights: List[int],
    buckets: Dict[int, deque],
    gm: Dict[str, Any],
    cfg: OptimizationConfig,
    L_um: int,
    D_um: int,
    K_um: int,
    grupo_otimizacao: int,
) -> List[Dict[str, Any]]:
    """Converte padrões abstratos de corte em registros detalhados ordenados."""
    bars: List[Dict[str, Any]] = []
    for pat in patterns:
        bar_pieces: List[Dict[str, Any]] = []
        for idx, q in pat.items():
            w = weights[idx]
            for _ in range(q):
                bar_pieces.append(buckets[w].popleft())

        bar_pieces.sort(
            key=lambda x: (-x["medida_corte_mm"], x["op"], x["codigo"])
        )
        soma_pecas_um = sum(p["_c_um"] for p in bar_pieces)
        kerfs_um = max(0, len(bar_pieces) - 1) * K_um
        serra_desp_um = D_um + kerfs_um
        consumido_um = soma_pecas_um + serra_desp_um
        sobra_um = max(0, L_um - consumido_um)

        clean_pieces = [
            {k: v for k, v in p.items() if not k.startswith("_")}
            for p in bar_pieces
        ]
        ops_sorted = sorted({p["op"] for p in clean_pieces if p["op"]})
        perda_mm = _from_um(sobra_um)

        bars.append(
            {
                "grupo_otimizacao": grupo_otimizacao,
                "grupo_key": gm["grupo_key"],
                "grupo_nome": gm["grupo_nome"],
                "origem_agrupamento": gm["origem_agrupamento"],
                "codigo_perfil": gm["codigo_perfil"],
                "barra_numero": 0,
                "comprimento_barra_mm": round(cfg.comprimento_barra_mm, 3),
                "qtd_pecas": len(clean_pieces),
                "soma_pecas_mm": _from_um(soma_pecas_um),
                "perda_serra_desponte_mm": _from_um(serra_desp_um),
                "consumido_mm": _from_um(consumido_um),
                "perda_mm": perda_mm,
                "perda_cm": round(perda_mm / 10.0, 2),
                "aproveitamento_pct": round((soma_pecas_um / L_um) * 100.0, 2),
                "padrao_corte": _format_padrao_corte(clean_pieces),
                "ops": ", ".join(ops_sorted[:10])
                + (f" (+{len(ops_sorted) - 10})" if len(ops_sorted) > 10 else ""),
                "pecas": clean_pieces,
            }
        )

    bars.sort(key=lambda b: (b["perda_mm"], -b["soma_pecas_mm"], -b["qtd_pecas"]))
    for i, b in enumerate(bars, start=1):
        b["barra_numero"] = i
    return bars


def _calc_avg_yield_and_loss(
    soma_pecas_mm: float, total_perda_mm: float, qtd_barras: int, barra_mm: float
) -> Tuple[float, float]:
    if qtd_barras <= 0 or barra_mm <= 0:
        return 0.0, 0.0
    aproveitamento = round((soma_pecas_mm / (qtd_barras * barra_mm)) * 100.0, 2)
    perda_media = round(total_perda_mm / qtd_barras, 2)
    return aproveitamento, perda_media


def build_bar_optimization(
    detailed_bars: List[Dict[str, Any]],
    config: Optional[OptimizationConfig] = None,
    rules: Optional[Dict[str, CuttingRule]] = None,
) -> Dict[str, Any]:
    """Otimiza cortes de barras agrupados por Código de Perfil (ou Modelo + Tipo).

    Separa cada grupo e o consolidado em:
    - Grupo 1: Barras fechadas (ex.: 6m) com perda <= `perda_maxima_mm`
    - Grupo 2: Peças restantes ordenadas estritamente do maior para o menor,
      além da otimização dessas peças viáveis no menor nº possível de barras de 6m.
    """
    cfg = config or OptimizationConfig()
    L_um = max(1, _to_um(cfg.comprimento_barra_mm))
    D_um = max(0, _to_um(cfg.desponte_mm))
    K_um = max(0, _to_um(cfg.espessura_serra_mm))
    Pmax_um = max(0, _to_um(cfg.perda_maxima_mm))

    usable_um = max(1, L_um - D_um)
    cap_um = usable_um + K_um
    w_min_um = max(1, cap_um - Pmax_um)

    # Agrupamento e expansão em peças unitárias
    groups_pieces: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    group_meta: Dict[str, Dict[str, Any]] = {}

    for bar in detailed_bars:
        med_mm = round(float(bar.get("medida_corte_mm") or 0.0), 3)
        qtd = int(round(float(bar.get("qtd_barras") or 0)))
        if med_mm <= 0 or qtd <= 0:
            continue

        g_key, g_label, origem, cod_perfil, tipo_perfil = resolve_profile_group(
            bar, rules=rules, separar_por_acabamento=cfg.separar_por_acabamento
        )
        if g_key not in group_meta:
            group_meta[g_key] = {
                "grupo_key": g_key,
                "grupo_nome": g_label,
                "origem_agrupamento": origem,
                "codigo_perfil": cod_perfil,
                "modelos_set": set(),
                "tipos_set": set(),
                "acabamentos_set": set(),
            }
        gm = group_meta[g_key]
        gm["modelos_set"].add((bar.get("modelo") or "OUTRO").strip())
        gm["tipos_set"].add(tipo_perfil)
        gm["acabamentos_set"].add((bar.get("acabamento_perfil") or "PADRAO").strip())

        c_um = _to_um(med_mm)
        for _ in range(qtd):
            groups_pieces[g_key].append(
                {
                    "grupo_key": g_key,
                    "grupo_nome": g_label,
                    "origem_agrupamento": origem,
                    "codigo_perfil": cod_perfil,
                    "tipo_perfil": tipo_perfil,
                    "op": str(bar.get("op") or ""),
                    "codigo": str(bar.get("codigo") or ""),
                    "pedido": str(bar.get("pedido") or ""),
                    "data_entrega": str(bar.get("data_entrega") or ""),
                    "modelo": str(bar.get("modelo") or "OUTRO"),
                    "acabamento_perfil": str(bar.get("acabamento_perfil") or "PADRAO"),
                    "funcao_barra": str(bar.get("funcao_barra") or ""),
                    "orientacao": str(bar.get("orientacao") or ""),
                    "eh_perfil_puxador": bool(bar.get("eh_perfil_puxador")),
                    "tipo_corte": str(bar.get("tipo_corte") or ""),
                    "observacao_corte": str(bar.get("observacao_corte") or ""),
                    "medida_corte_mm": med_mm,
                    "_c_um": c_um,
                    "_w_um": c_um + K_um,
                }
            )

    grupos_out: List[Dict[str, Any]] = []
    nao_alocados_flat_raw: List[Dict[str, Any]] = []
    pecas_inviaveis_flat_raw: List[Dict[str, Any]] = []

    for g_key, pieces in groups_pieces.items():
        gm = group_meta[g_key]
        oversized: List[Dict[str, Any]] = []
        eligible: List[Dict[str, Any]] = []

        for p in pieces:
            if p["_c_um"] > usable_um:
                p_clean = {k: v for k, v in p.items() if not k.startswith("_")}
                p_clean["motivo"] = (
                    f"Maior que a barra útil ({_from_um(usable_um):g} mm)"
                )
                oversized.append(p_clean)
            else:
                eligible.append(p)

        # Buckets determinísticos por peso efetivo w_um (prioriza entregas mais próximas)
        buckets: Dict[int, deque] = defaultdict(deque)
        for p in sorted(
            eligible, key=lambda x: (x["data_entrega"], x["op"], x["codigo"])
        ):
            buckets[p["_w_um"]].append(p)

        weights = sorted(buckets.keys(), reverse=True)
        counts = [len(buckets[w]) for w in weights]

        # Grupo 1: barras dentro do limite de perda configurável
        patterns_g1 = _solve_counts(weights, counts, w_min_um, cap_um)
        barras_fechadas = _materialize_bars(
            patterns_g1, weights, buckets, gm, cfg, L_um, D_um, K_um, grupo_otimizacao=1
        )

        # Peças elegíveis que sobraram do Grupo 1 vão para o Grupo 2
        g2_eligible_internal: List[Dict[str, Any]] = []
        g2_buckets: Dict[int, deque] = defaultdict(deque)
        for w in weights:
            while buckets[w]:
                p = buckets[w].popleft()
                g2_eligible_internal.append(p)
                g2_buckets[w].append(p)

        # Lista completa do Grupo 2 (elegíveis restantes + maiores que a barra) -> Maior -> Menor
        nao_alocados: List[Dict[str, Any]] = list(oversized)
        motivo_g2 = (
            f"Perda acima de {round(cfg.perda_maxima_mm / 10.0, 2):g} cm ({cfg.perda_maxima_mm:g} mm)"
        )
        for p in g2_eligible_internal:
            p_clean = {k: v for k, v in p.items() if not k.startswith("_")}
            p_clean["motivo"] = motivo_g2
            nao_alocados.append(p_clean)

        nao_alocados.sort(
            key=lambda x: (-x["medida_corte_mm"], x["data_entrega"], x["op"], x["codigo"])
        )
        nao_alocados_flat_raw.extend(nao_alocados)
        pecas_inviaveis_flat_raw.extend(oversized)

        nao_alocados_agrupados = _group_unplaced_pieces(nao_alocados)

        # Otimização do Grupo 2: menor número possível de barras de 6m com peças elegíveis
        g2_weights = sorted(g2_buckets.keys(), reverse=True)
        g2_counts = [len(g2_buckets[w]) for w in g2_weights]
        patterns_g2 = _pack_min_bars(g2_weights, g2_counts, cap_um)
        barras_grupo2 = _materialize_bars(
            patterns_g2, g2_weights, g2_buckets, gm, cfg, L_um, D_um, K_um, grupo_otimizacao=2
        )

        # KPIs do Grupo 1
        total_pecas_entrada = len(pieces)
        total_pecas_alocadas = sum(b["qtd_pecas"] for b in barras_fechadas)
        total_pecas_nao_alocadas = len(nao_alocados)
        soma_alocados_mm = round(sum(b["soma_pecas_mm"] for b in barras_fechadas), 3)
        soma_nao_alocados_mm = round(
            sum(p["medida_corte_mm"] for p in nao_alocados), 3
        )
        soma_perda_mm = round(sum(b["perda_mm"] for b in barras_fechadas), 3)
        qtd_barras = len(barras_fechadas)
        aproveitamento_medio, perda_media_g1 = _calc_avg_yield_and_loss(
            soma_alocados_mm, soma_perda_mm, qtd_barras, cfg.comprimento_barra_mm
        )

        # KPIs do Grupo 2 Otimizado
        qtd_barras_g2 = len(barras_grupo2)
        total_pecas_alocadas_g2 = sum(b["qtd_pecas"] for b in barras_grupo2)
        total_pecas_inviaveis = len(oversized)
        soma_alocados_g2_mm = round(sum(b["soma_pecas_mm"] for b in barras_grupo2), 3)
        soma_perda_g2_mm = round(sum(b["perda_mm"] for b in barras_grupo2), 3)
        aproveitamento_g2, perda_media_g2 = _calc_avg_yield_and_loss(
            soma_alocados_g2_mm, soma_perda_g2_mm, qtd_barras_g2, cfg.comprimento_barra_mm
        )

        # KPIs Consolidados do Grupo (G1 + G2)
        qtd_barras_total = qtd_barras + qtd_barras_g2
        soma_geral_mm = round(soma_alocados_mm + soma_alocados_g2_mm, 3)
        perda_geral_mm = round(soma_perda_mm + soma_perda_g2_mm, 3)
        aproveitamento_geral_grp, perda_media_geral_grp = _calc_avg_yield_and_loss(
            soma_geral_mm, perda_geral_mm, qtd_barras_total, cfg.comprimento_barra_mm
        )

        grupos_out.append(
            {
                "grupo_key": gm["grupo_key"],
                "grupo_nome": gm["grupo_nome"],
                "origem_agrupamento": gm["origem_agrupamento"],
                "codigo_perfil": gm["codigo_perfil"],
                "modelos": sorted(gm["modelos_set"]),
                "tipos_perfil": sorted(gm["tipos_set"]),
                "acabamentos": sorted(gm["acabamentos_set"]),
                "qtd_barras_6m": qtd_barras,
                "total_pecas_entrada": total_pecas_entrada,
                "total_pecas_alocadas": total_pecas_alocadas,
                "total_pecas_nao_alocadas": total_pecas_nao_alocadas,
                "total_metros_entrada": round(
                    (soma_alocados_mm + soma_nao_alocados_mm) / 1000.0, 3
                ),
                "total_metros_alocados": round(soma_alocados_mm / 1000.0, 3),
                "total_metros_nao_alocados": round(soma_nao_alocados_mm / 1000.0, 3),
                "total_perda_mm": soma_perda_mm,
                "perda_media_barra_grupo1_mm": perda_media_g1,
                "aproveitamento_medio_pct": aproveitamento_medio,
                "qtd_barras_grupo2": qtd_barras_g2,
                "total_pecas_alocadas_grupo2": total_pecas_alocadas_g2,
                "total_pecas_inviaveis": total_pecas_inviaveis,
                "total_metros_alocados_grupo2": round(soma_alocados_g2_mm / 1000.0, 3),
                "total_perda_grupo2_mm": soma_perda_g2_mm,
                "total_perda_grupo2_metros": round(soma_perda_g2_mm / 1000.0, 3),
                "perda_media_barra_grupo2_mm": perda_media_g2,
                "aproveitamento_medio_grupo2_pct": aproveitamento_g2,
                "qtd_barras_total": qtd_barras_total,
                "total_perda_geral_mm": perda_geral_mm,
                "total_perda_geral_metros": round(perda_geral_mm / 1000.0, 3),
                "perda_media_barra_geral_mm": perda_media_geral_grp,
                "aproveitamento_medio_geral_pct": aproveitamento_geral_grp,
                "barras_fechadas": barras_fechadas,
                "barras_grupo2": barras_grupo2,
                "nao_alocados": nao_alocados,
                "nao_alocados_agrupados": nao_alocados_agrupados,
            }
        )

    grupos_out.sort(
        key=lambda g: (
            -g["qtd_barras_6m"],
            -g["qtd_barras_grupo2"],
            -g["total_pecas_entrada"],
            g["grupo_nome"],
        )
    )

    barras_otimizadas_flat: List[Dict[str, Any]] = []
    barras_grupo2_flat: List[Dict[str, Any]] = []
    for g in sorted(grupos_out, key=lambda x: x["grupo_nome"]):
        for b in g["barras_fechadas"]:
            barras_otimizadas_flat.append(dict(b))
        for b in g["barras_grupo2"]:
            barras_grupo2_flat.append(dict(b))
    for i, b in enumerate(barras_otimizadas_flat, start=1):
        b["barra_global_numero"] = i
    for i, b in enumerate(barras_grupo2_flat, start=1):
        b["barra_global_numero"] = i

    nao_alocados_flat = sorted(
        nao_alocados_flat_raw,
        key=lambda x: (
            -x["medida_corte_mm"],
            x["grupo_nome"],
            x["data_entrega"],
            x["op"],
            x["codigo"],
        ),
    )
    nao_alocados_agrupados_flat = _group_unplaced_pieces(nao_alocados_flat)
    pecas_inviaveis_flat = sorted(
        pecas_inviaveis_flat_raw,
        key=lambda x: (
            -x["medida_corte_mm"],
            x["grupo_nome"],
            x["data_entrega"],
            x["op"],
            x["codigo"],
        ),
    )

    total_barras_6m = sum(g["qtd_barras_6m"] for g in grupos_out)
    total_pecas_entrada = sum(g["total_pecas_entrada"] for g in grupos_out)
    total_pecas_alocadas = sum(g["total_pecas_alocadas"] for g in grupos_out)
    total_pecas_nao_alocadas = sum(g["total_pecas_nao_alocadas"] for g in grupos_out)
    total_metros_entrada = round(
        sum(g["total_metros_entrada"] for g in grupos_out), 3
    )
    total_metros_alocados = round(
        sum(g["total_metros_alocados"] for g in grupos_out), 3
    )
    total_metros_nao_alocados = round(
        sum(g["total_metros_nao_alocados"] for g in grupos_out), 3
    )
    total_perda_mm = round(sum(g["total_perda_mm"] for g in grupos_out), 3)
    aproveitamento_g1, perda_media_g1_geral = _calc_avg_yield_and_loss(
        total_metros_alocados * 1000.0,
        total_perda_mm,
        total_barras_6m,
        cfg.comprimento_barra_mm,
    )

    total_barras_g2 = sum(g["qtd_barras_grupo2"] for g in grupos_out)
    total_pecas_alocadas_g2 = sum(g["total_pecas_alocadas_grupo2"] for g in grupos_out)
    total_pecas_inviaveis = sum(g["total_pecas_inviaveis"] for g in grupos_out)
    total_metros_alocados_g2 = round(
        sum(g["total_metros_alocados_grupo2"] for g in grupos_out), 3
    )
    total_perda_g2_mm = round(sum(g["total_perda_grupo2_mm"] for g in grupos_out), 3)
    aproveitamento_g2_geral, perda_media_g2_geral = _calc_avg_yield_and_loss(
        total_metros_alocados_g2 * 1000.0,
        total_perda_g2_mm,
        total_barras_g2,
        cfg.comprimento_barra_mm,
    )

    total_barras_geral = total_barras_6m + total_barras_g2
    total_perda_geral_mm = round(total_perda_mm + total_perda_g2_mm, 3)
    aproveitamento_geral_consolidado, perda_media_geral = _calc_avg_yield_and_loss(
        (total_metros_alocados + total_metros_alocados_g2) * 1000.0,
        total_perda_geral_mm,
        total_barras_geral,
        cfg.comprimento_barra_mm,
    )

    return {
        "config": cfg.to_dict(),
        "resumo": {
            "total_grupos": len(grupos_out),
            "grupos_com_barras_fechadas": sum(
                1 for g in grupos_out if g["qtd_barras_6m"] > 0
            ),
            "total_pecas_entrada": total_pecas_entrada,
            "total_pecas_alocadas": total_pecas_alocadas,
            "total_pecas_nao_alocadas": total_pecas_nao_alocadas,
            "total_barras_6m": total_barras_6m,
            "total_metros_entrada": total_metros_entrada,
            "total_metros_alocados": total_metros_alocados,
            "total_metros_nao_alocados": total_metros_nao_alocados,
            "total_perda_mm": total_perda_mm,
            "total_perda_metros": round(total_perda_mm / 1000.0, 3),
            "perda_media_barra_grupo1_mm": perda_media_g1_geral,
            "aproveitamento_medio_pct": aproveitamento_g1,
            "total_barras_grupo2": total_barras_g2,
            "total_pecas_alocadas_grupo2": total_pecas_alocadas_g2,
            "total_pecas_inviaveis": total_pecas_inviaveis,
            "total_metros_alocados_grupo2": total_metros_alocados_g2,
            "total_perda_grupo2_mm": total_perda_g2_mm,
            "total_perda_grupo2_metros": round(total_perda_g2_mm / 1000.0, 3),
            "perda_media_barra_grupo2_mm": perda_media_g2_geral,
            "aproveitamento_medio_grupo2_pct": aproveitamento_g2_geral,
            "total_barras_geral": total_barras_geral,
            "total_perda_geral_mm": total_perda_geral_mm,
            "total_perda_geral_metros": round(total_perda_geral_mm / 1000.0, 3),
            "perda_media_barra_geral_mm": perda_media_geral,
            "aproveitamento_medio_geral_pct": aproveitamento_geral_consolidado,
        },
        "grupos": grupos_out,
        "barras_otimizadas_flat": barras_otimizadas_flat,
        "barras_grupo2_flat": barras_grupo2_flat,
        "pecas_inviaveis_flat": pecas_inviaveis_flat,
        "nao_alocados_flat": nao_alocados_flat,
        "nao_alocados_agrupados_flat": nao_alocados_agrupados_flat,
    }


def _group_unplaced_pieces(pieces: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Agrupa peças não alocadas mantendo ordenação estrita do maior para o menor."""
    grouped: Dict[tuple, Dict[str, Any]] = {}
    for p in pieces:
        key = (
            p["grupo_nome"],
            p["codigo_perfil"],
            p["modelo"],
            p["tipo_perfil"],
            p["acabamento_perfil"],
            p["funcao_barra"],
            p["tipo_corte"],
            p["medida_corte_mm"],
            p.get("motivo", ""),
        )
        if key not in grouped:
            grouped[key] = {
                "grupo_key": p["grupo_key"],
                "grupo_nome": p["grupo_nome"],
                "origem_agrupamento": p["origem_agrupamento"],
                "codigo_perfil": p["codigo_perfil"],
                "modelo": p["modelo"],
                "tipo_perfil": p["tipo_perfil"],
                "acabamento_perfil": p["acabamento_perfil"],
                "funcao_barra": p["funcao_barra"],
                "tipo_corte": p["tipo_corte"],
                "medida_corte_mm": p["medida_corte_mm"],
                "motivo": p.get("motivo", ""),
                "qtd_pecas": 0,
                "total_mm": 0.0,
                "ops": set(),
            }
        entry = grouped[key]
        entry["qtd_pecas"] += 1
        entry["total_mm"] = round(entry["total_mm"] + p["medida_corte_mm"], 3)
        if p.get("op"):
            entry["ops"].add(p["op"])

    out: List[Dict[str, Any]] = []
    for entry in grouped.values():
        ops_sorted = sorted(entry["ops"])
        out.append(
            {
                "grupo_key": entry["grupo_key"],
                "grupo_nome": entry["grupo_nome"],
                "origem_agrupamento": entry["origem_agrupamento"],
                "codigo_perfil": entry["codigo_perfil"],
                "modelo": entry["modelo"],
                "tipo_perfil": entry["tipo_perfil"],
                "acabamento_perfil": entry["acabamento_perfil"],
                "funcao_barra": entry["funcao_barra"],
                "tipo_corte": entry["tipo_corte"],
                "medida_corte_mm": entry["medida_corte_mm"],
                "motivo": entry["motivo"],
                "qtd_pecas": entry["qtd_pecas"],
                "total_mm": entry["total_mm"],
                "total_metros": round(entry["total_mm"] / 1000.0, 3),
                "qtd_ops": len(ops_sorted),
                "ops": ", ".join(ops_sorted[:10])
                + (f" (+{len(ops_sorted) - 10})" if len(ops_sorted) > 10 else ""),
            }
        )

    out.sort(
        key=lambda x: (
            -x["medida_corte_mm"],
            x["grupo_nome"],
            x["modelo"],
            x["funcao_barra"],
        )
    )
    return out
