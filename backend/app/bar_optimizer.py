"""Otimizador de corte linear em barras (padrão 6 m) em dois cenários: Material vs Tempo de Execução."""

from __future__ import annotations

import re
from bisect import bisect_left
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.cutting_engine import CuttingRule, _norm_angle, format_cut_angles

SCALE_UM = 1000  # 1 mm = 1000 µm (evita imprecisão de ponto flutuante)


def _resolve_bar_angles(bar: Dict[str, Any]) -> Tuple[int, int]:
    """Resolve ângulos (esquerdo, direito) em {45, 90} a partir da barra ou texto."""
    raw_esq = bar.get("angulo_esq")
    raw_dir = bar.get("angulo_dir")
    if raw_esq is not None and raw_dir is not None:
        try:
            e = int(round(float(raw_esq)))
            d = int(round(float(raw_dir)))
            if e in (45, 90) and d in (45, 90):
                return e, d
        except (TypeError, ValueError):
            pass

    raw_text = str(bar.get("angulos_corte") or bar.get("tipo_corte") or "")
    matches = re.findall(r"\b(45|90)\b", raw_text)
    if len(matches) >= 2:
        return int(matches[0]), int(matches[1])
    if len(matches) == 1:
        ang = int(matches[0])
        return ang, ang
    return 45, 45


def _format_angles(a_esq: int, a_dir: int) -> str:
    return format_cut_angles(a_esq, a_dir)


def _angle_sig(a_esq: int, a_dir: int) -> Tuple[int, int]:
    return (min(a_esq, a_dir), max(a_esq, a_dir))


def _to_um(mm: float) -> int:
    return int(round(float(mm) * SCALE_UM))


def _from_um(um: int) -> float:
    return round(um / SCALE_UM, 3)


@dataclass
class OptimizationConfig:
    """Parâmetros configuráveis para otimização linear em barras (padrão 6 m)."""

    comprimento_barra_mm: float = 6000.0
    espessura_serra_mm: float = 0.0
    desponte_mm: float = 0.0
    separar_por_acabamento: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def resolve_profile_group(
    bar: Dict[str, Any],
    rules: Optional[Dict[str, CuttingRule]] = None,
    separar_por_acabamento: bool = False,
) -> Tuple[str, str, str, str, str]:
    """Resolve o agrupamento físico de perfil de uma barra de corte.

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
    """Busca exata com branch-and-bound de padrões válidos de 1 barra contendo `start_idx`."""
    m = len(weights)
    if start_idx >= m or avail_qty[start_idx] <= 0:
        return []
    anchor_w = weights[start_idx]
    if anchor_w > cap_um:
        return []

    suffix_sum = [0] * (m + 1)
    for i in range(m - 1, -1, -1):
        suffix_sum[i] = suffix_sum[i + 1] + weights[i] * avail_qty[i]

    min_w_global = weights[-1]
    avail_work = list(avail_qty)
    avail_work[start_idx] -= 1
    neg_weights = [-w for w in weights]

    nodes = 0
    best_tight: Optional[Tuple[int, int, Dict[int, int]]] = None
    best_conserve: Optional[Tuple[int, int, Dict[int, int]]] = None
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

    def dfs(idx: int, cur_sum: int, cur_count: int) -> None:
        nonlocal nodes
        if nodes >= node_limit:
            return
        if mode == "tightest" and best_tight is not None and best_tight[0] == cap_um:
            return
        if mode == "top_k" and len(collected) >= collect_limit:
            return
        if mode == "conserve_small" and best_conserve is not None:
            if cur_count >= -best_conserve[0]:
                return

        rem_space = cap_um - cur_sum
        if rem_space < min_w_global:
            return

        idx = next_fitting_idx(idx, rem_space)
        if idx >= m:
            return

        max_add = suffix_sum[idx]
        if idx == start_idx:
            max_add -= anchor_w
        if cur_sum + max_add < w_min_um:
            return
        if mode == "tightest" and best_tight is not None:
            if cur_sum + max_add < best_tight[0]:
                return

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
            dfs(idx + 1, cur_sum, cur_count)
            return

        w_i = weights[idx]
        max_take = min(avail, rem_space // w_i)
        if mode == "conserve_small" and best_conserve is not None:
            max_take = min(max_take, max(0, (-best_conserve[0]) - cur_count))

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

            if not (mode == "conserve_small" and take > 0 and new_sum >= w_min_um):
                dfs(idx + 1, new_sum, new_count)

            if take > 0:
                prev_q = cur_pattern[idx] - take
                if prev_q <= 0:
                    del cur_pattern[idx]
                else:
                    cur_pattern[idx] = prev_q

    dfs(start_idx, anchor_w, 1)

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
    """Funde 3 bins subutilizados em 2 bins exatos quando acima do lower bound."""
    bins = [dict(b) for b in bins]
    for _ in range(30):
        if len(bins) <= lb or len(bins) < 3:
            break
        bins.sort(key=lambda b: _bin_fill_um(b, weights))
        fills = [_bin_fill_um(b, weights) for b in bins]
        reduced = False

        n = len(bins)
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
                for idx in sorted(bins[lo].keys()):
                    if weights[idx] <= space_hi:
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


def _orient_piece_for_angle(
    piece: Dict[str, Any],
    cur_angle: Optional[int],
    next_hint: Optional[int] = None,
    keep_internal: bool = False,
) -> Tuple[Dict[str, Any], int]:
    """Orienta peça assimétrica (45°/90°) para casar com o ângulo atual da serra."""
    a_esq = _norm_angle(piece.get("angulo_esq"), 45)
    a_dir = _norm_angle(piece.get("angulo_dir"), 45)
    if a_esq != a_dir:
        if cur_angle == 45:
            a_esq, a_dir = 45, 90
        elif cur_angle == 90:
            a_esq, a_dir = 90, 45
        elif next_hint == 90:
            a_esq, a_dir = 45, 90
        elif next_hint == 45:
            a_esq, a_dir = 90, 45
        else:
            a_esq, a_dir = 45, 90

    out_p = dict(piece) if keep_internal else {k: v for k, v in piece.items() if not k.startswith("_")}
    out_p["angulo_esq"] = a_esq
    out_p["angulo_dir"] = a_dir
    out_p["angulos_corte"] = _format_angles(a_esq, a_dir)
    return out_p, a_dir


def _order_pieces_by_angle(
    pieces: List[Dict[str, Any]],
    start_angle: Optional[int],
    end_hint: Optional[int] = None,
    keep_internal: bool = False,
) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    """Ordena e orienta peças agrupando por ângulo e encadeando peças 45°/90°."""
    if not pieces:
        return [], start_angle

    ordered_src = sorted(
        pieces, key=lambda x: (x["data_entrega"], x["op"], x["codigo"])
    )
    pure_45: List[Dict[str, Any]] = []
    mixed: List[Dict[str, Any]] = []
    pure_90: List[Dict[str, Any]] = []

    for p in ordered_src:
        sig = p.get("_ang_sig")
        if sig is None:
            sig = _angle_sig(*_resolve_bar_angles(p))
        if sig == (45, 45):
            pure_45.append(p)
        elif sig == (90, 90):
            pure_90.append(p)
        else:
            mixed.append(p)

    if start_angle in (45, 90):
        first_ang = start_angle
    elif end_hint in (45, 90):
        opp = 90 if end_hint == 45 else 45
        if (opp == 45 and pure_45) or (opp == 90 and pure_90) or mixed:
            first_ang = opp
        else:
            first_ang = end_hint
    else:
        first_ang = 45 if len(pure_45) >= len(pure_90) else 90

    other_ang = 90 if first_ang == 45 else 45
    first_pure = pure_45 if first_ang == 45 else pure_90
    second_pure = pure_90 if first_ang == 45 else pure_45

    if second_pure:
        mixed_next_hint: Optional[int] = other_ang
    elif end_hint in (45, 90):
        mixed_next_hint = end_hint
    else:
        mixed_next_hint = None

    out: List[Dict[str, Any]] = []
    cur_angle = start_angle

    for p in first_pure:
        cp, cur_angle = _orient_piece_for_angle(
            p, cur_angle, mixed_next_hint, keep_internal=keep_internal
        )
        out.append(cp)

    for idx_m, p in enumerate(mixed):
        hint = mixed_next_hint if idx_m == len(mixed) - 1 else None
        cp, cur_angle = _orient_piece_for_angle(
            p, cur_angle, hint, keep_internal=keep_internal
        )
        out.append(cp)

    for p in second_pure:
        cp, cur_angle = _orient_piece_for_angle(
            p, cur_angle, end_hint, keep_internal=keep_internal
        )
        out.append(cp)

    return out, cur_angle


def _pop_pieces_for_weight(
    w_buckets: Dict[Tuple[int, int], deque],
    qty: int,
    cur_angle: Optional[int],
) -> List[Dict[str, Any]]:
    """Retira `qty` peças do peso `w`, priorizando o ângulo atual da serra."""
    if cur_angle in (45, 90):
        opp = 90 if cur_angle == 45 else 45
        sig_order: List[Tuple[int, int]] = [(cur_angle, cur_angle), (45, 90), (opp, opp)]
    else:
        n45 = len(w_buckets.get((45, 45), ()))
        n90 = len(w_buckets.get((90, 90), ()))
        if n45 >= n90:
            sig_order = [(45, 45), (45, 90), (90, 90)]
        else:
            sig_order = [(90, 90), (45, 90), (45, 45)]

    for sig in w_buckets.keys():
        if sig not in sig_order:
            sig_order.append(sig)

    picked: List[Dict[str, Any]] = []
    for sig in sig_order:
        dq = w_buckets.get(sig)
        while dq and len(picked) < qty:
            picked.append(dq.popleft())
        if len(picked) >= qty:
            break
    return picked


def _assign_and_order_material_bars(
    patterns: List[Dict[int, int]],
    weights: List[int],
    buckets_by_w_sig: Dict[int, Dict[Tuple[int, int], deque]],
) -> List[List[Dict[str, Any]]]:
    """Encadeia barras e orienta cortes para reduzir trocas de medida e de ângulo."""
    rem: List[Counter[int]] = []
    for pat in patterns:
        c: Counter[int] = Counter()
        for idx, q in pat.items():
            if q > 0:
                c[weights[idx]] += q
        if c:
            rem.append(c)

    def _w_has_angle_match(w: int, ang: Optional[int]) -> bool:
        if ang not in (45, 90):
            return False
        wb = buckets_by_w_sig.get(w)
        if not wb:
            return False
        return bool(wb.get((ang, ang)) or wb.get((45, 90)))

    ordered_bars: List[List[Dict[str, Any]]] = []
    last_med: Optional[int] = None
    last_angle: Optional[int] = None

    while rem:
        best_i = 0
        best_key: Optional[Tuple[int, int, int, int, int, int, int]] = None
        for i, c in enumerate(rem):
            has_med = 1 if (last_med is not None and last_med in c) else 0
            is_mono = 1 if len(c) == 1 else 0
            has_med_ang = (
                1 if (has_med and _w_has_angle_match(last_med, last_angle)) else 0
            )
            has_any_ang = (
                1
                if (
                    last_angle in (45, 90)
                    and any(_w_has_angle_match(w, last_angle) for w in c)
                )
                else 0
            )
            key = (
                has_med_ang,
                has_med,
                1 if (has_med and is_mono) else 0,
                has_any_ang,
                -len(c),
                max(c.keys()),
                sum(w * q for w, q in c.items()),
            )
            if best_key is None or key > best_key:
                best_key = key
                best_i = i

        cur_c = rem.pop(best_i)
        rem_freq: Counter[int] = Counter()
        for c in rem:
            for w in c:
                rem_freq[w] += 1

        distinct = sorted(cur_c.keys(), reverse=True)
        bar_pieces: List[Dict[str, Any]] = []
        cur_angle = last_angle
        last_w_used: Optional[int] = None

        if len(distinct) == 1:
            w0 = distinct[0]
            raw_pcs = _pop_pieces_for_weight(buckets_by_w_sig[w0], cur_c[w0], cur_angle)
            bar_pieces, cur_angle = _order_pieces_by_angle(raw_pcs, cur_angle)
            last_w_used = w0
        else:
            if last_med is not None and last_med in cur_c:
                first_m = last_med
            elif last_angle in (45, 90):
                ang_cands = [w for w in distinct if _w_has_angle_match(w, last_angle)]
                first_m = ang_cands[0] if ang_cands else distinct[0]
            else:
                first_m = distinct[0]

            others = [w for w in distinct if w != first_m]
            last_m = max(others, key=lambda w: (rem_freq[w], w))
            middles = [w for w in others if w != last_m]

            # Processa first_m
            raw_first = _pop_pieces_for_weight(
                buckets_by_w_sig[first_m], cur_c[first_m], cur_angle
            )
            pcs_first, cur_angle = _order_pieces_by_angle(raw_first, cur_angle)
            bar_pieces.extend(pcs_first)

            # Processa middles priorizando continuidade de ângulo
            rem_middles = list(middles)
            while rem_middles:
                match_idx = next(
                    (
                        idx_m
                        for idx_m, wm in enumerate(rem_middles)
                        if _w_has_angle_match(wm, cur_angle)
                    ),
                    0,
                )
                wm = rem_middles.pop(match_idx)
                raw_mid = _pop_pieces_for_weight(
                    buckets_by_w_sig[wm], cur_c[wm], cur_angle
                )
                pcs_mid, cur_angle = _order_pieces_by_angle(raw_mid, cur_angle)
                bar_pieces.extend(pcs_mid)

            # Processa last_m
            raw_last = _pop_pieces_for_weight(
                buckets_by_w_sig[last_m], cur_c[last_m], cur_angle
            )
            pcs_last, cur_angle = _order_pieces_by_angle(raw_last, cur_angle)
            bar_pieces.extend(pcs_last)
            last_w_used = last_m

        ordered_bars.append(bar_pieces)
        if bar_pieces:
            last_med = last_w_used
            last_angle = cur_angle

    return ordered_bars


def _format_sequence_rle(pieces: List[Dict[str, Any]]) -> str:
    """Formata a sequência exata de cortes na barra (esquerda → direita) agrupando adjacentes."""
    if not pieces:
        return ""
    runs: List[Tuple[float, int, int, int]] = []
    for p in pieces:
        med = round(float(p["medida_corte_mm"]), 3)
        a_esq = _norm_angle(p.get("angulo_esq"), 45)
        a_dir = _norm_angle(p.get("angulo_dir"), 45)
        sig_a, sig_b = _angle_sig(a_esq, a_dir)
        if (
            runs
            and runs[-1][0] == med
            and runs[-1][1] == sig_a
            and runs[-1][2] == sig_b
        ):
            runs[-1] = (med, sig_a, sig_b, runs[-1][3] + 1)
        else:
            runs.append((med, sig_a, sig_b, 1))
    return " → ".join(
        f"{q}× {med:g} mm [{a1}°/{a2}°]" for med, a1, a2, q in runs
    )


def _annotate_and_count_adjustments(
    bars: List[Dict[str, Any]], count_measure_adjustments: bool = True
) -> Tuple[int, int]:
    """Conta trocas consecutivas de medida e trocas de ângulo (45° ↔ 90°)."""
    total_med_changes = 0
    total_angle_changes = 0
    prev_med: Optional[float] = None
    prev_angle: Optional[int] = None

    for bar in bars:
        internal_med = 0
        entry_med = False
        internal_ang = 0
        entry_ang = False
        angles_seen: List[str] = []
        angles_seen_set = set()

        for idx, p in enumerate(bar["pecas"]):
            med = round(float(p["medida_corte_mm"]), 3)
            a_esq = _norm_angle(p.get("angulo_esq"), 45)
            a_dir = _norm_angle(p.get("angulo_dir"), 45)
            canon = _format_angles(*_angle_sig(a_esq, a_dir))
            if canon not in angles_seen_set:
                angles_seen_set.add(canon)
                angles_seen.append(canon)

            if count_measure_adjustments and prev_med is not None and med != prev_med:
                total_med_changes += 1
                if idx == 0:
                    entry_med = True
                else:
                    internal_med += 1
            prev_med = med

            p_entry_ang = False
            if prev_angle is not None and a_esq != prev_angle:
                total_angle_changes += 1
                p_entry_ang = True
                if idx == 0:
                    entry_ang = True
                else:
                    internal_ang += 1

            p_intra_ang = a_esq != a_dir
            if p_intra_ang:
                total_angle_changes += 1
                internal_ang += 1

            p["troca_angulo_entrada"] = p_entry_ang
            p["troca_angulo_interna"] = p_intra_ang
            prev_angle = a_dir

        if count_measure_adjustments:
            bar["troca_entrada"] = entry_med
            bar["ajustes_internos"] = internal_med
            bar["ajustes_barra"] = internal_med + (1 if entry_med else 0)

        bar["troca_angulo_entrada"] = entry_ang
        bar["trocas_angulo_internas"] = internal_ang
        bar["trocas_angulo_barra"] = internal_ang + (1 if entry_ang else 0)
        bar["angulos_resumo"] = ", ".join(sorted(angles_seen))

    return total_med_changes, total_angle_changes


def _calc_pair_overlap_um(prev_p: Dict[str, Any], curr_p: Dict[str, Any]) -> int:
    """Retorna economia de chanfro (µm) em junção // entre duas peças 45° simétricas."""
    if (
        _norm_angle(prev_p.get("angulo_dir"), 45) == 45
        and _norm_angle(curr_p.get("angulo_esq"), 45) == 45
        and bool(prev_p.get("perfil_simetrico"))
        and bool(curr_p.get("perfil_simetrico"))
    ):
        w_prev = _to_um(prev_p.get("largura_perfil_mm") or 0.0)
        w_curr = _to_um(curr_p.get("largura_perfil_mm") or 0.0)
        c_prev = _to_um(prev_p["medida_corte_mm"])
        c_curr = _to_um(curr_p["medida_corte_mm"])
        return max(0, min(w_prev, w_curr, c_prev // 2, c_curr // 2))
    return 0


def _apply_bar_nesting(clean_pieces: List[Dict[str, Any]]) -> Tuple[int, int, int]:
    """Anota orientação (invertida), junção (// vs \\/) e economia de chanfro."""
    total_econ_um = 0
    cortes_paralelos = 0
    cortes_v = 0
    prev_inv = False

    for i, p in enumerate(clean_pieces):
        if i == 0:
            p["invertida"] = False
            p["juncao_entrada"] = ""
            p["economia_chanfro_mm"] = 0.0
            prev_inv = False
            continue

        prev_p = clean_pieces[i - 1]
        prev_dir = _norm_angle(prev_p.get("angulo_dir"), 45)
        curr_esq = _norm_angle(p.get("angulo_esq"), 45)

        if prev_dir == 45 and curr_esq == 45:
            if bool(prev_p.get("perfil_simetrico")) and bool(p.get("perfil_simetrico")):
                inv = not prev_inv
                ov_um = _calc_pair_overlap_um(prev_p, p)
                p["invertida"] = inv
                p["juncao_entrada"] = "//"
                p["economia_chanfro_mm"] = _from_um(ov_um)
                total_econ_um += ov_um
                cortes_paralelos += 1
                prev_inv = inv
            else:
                p["invertida"] = False
                p["juncao_entrada"] = "\\/"
                p["economia_chanfro_mm"] = 0.0
                cortes_v += 1
                prev_inv = False
        else:
            p["invertida"] = False
            p["juncao_entrada"] = "||" if (prev_dir == 90 and curr_esq == 90) else "45↔90"
            p["economia_chanfro_mm"] = 0.0
            prev_inv = False

    return total_econ_um, cortes_paralelos, cortes_v


def _build_bar_dict(
    cenario: str,
    gm: Dict[str, Any],
    barra_numero: int,
    clean_pieces: List[Dict[str, Any]],
    cfg: OptimizationConfig,
    L_um: int,
    D_um: int,
    K_um: int,
) -> Dict[str, Any]:
    econ_um, cortes_par, cortes_v = _apply_bar_nesting(clean_pieces)
    soma_pecas_um = sum(_to_um(p["medida_corte_mm"]) for p in clean_pieces)
    material_util_um = max(0, soma_pecas_um - econ_um)
    kerfs_um = max(0, len(clean_pieces) - 1) * K_um
    serra_desp_um = D_um + kerfs_um
    consumido_um = D_um + material_util_um + kerfs_um
    sobra_um = max(0, L_um - consumido_um)
    perda_mm = _from_um(sobra_um)
    seq_str = _format_sequence_rle(clean_pieces)
    ops_sorted = sorted({p["op"] for p in clean_pieces if p.get("op")})
    perfil_sim = bool(clean_pieces) and all(
        bool(p.get("perfil_simetrico")) for p in clean_pieces
    )

    return {
        "cenario": cenario,
        "grupo_key": gm["grupo_key"],
        "grupo_nome": gm["grupo_nome"],
        "origem_agrupamento": gm["origem_agrupamento"],
        "codigo_perfil": gm["codigo_perfil"],
        "barra_numero": barra_numero,
        "comprimento_barra_mm": round(cfg.comprimento_barra_mm, 3),
        "qtd_pecas": len(clean_pieces),
        "soma_pecas_mm": _from_um(soma_pecas_um),
        "perda_serra_desponte_mm": _from_um(serra_desp_um),
        "consumido_mm": _from_um(consumido_um),
        "perda_mm": perda_mm,
        "perda_cm": round(perda_mm / 10.0, 2),
        "aproveitamento_pct": round(min(100.0, (material_util_um / L_um) * 100.0), 2),
        "perfil_simetrico": perfil_sim,
        "modo_juncao_45": "// (Girar)" if perfil_sim else "\\/ (Sem giro)",
        "economia_chanfro_mm": _from_um(econ_um),
        "cortes_paralelos_qtd": cortes_par,
        "cortes_v_qtd": cortes_v,
        "padrao_corte": seq_str,
        "sequencia_corte": seq_str,
        "ops": ", ".join(ops_sorted[:10])
        + (f" (+{len(ops_sorted) - 10})" if len(ops_sorted) > 10 else ""),
        "pecas": clean_pieces,
        "troca_entrada": False,
        "ajustes_internos": 0,
        "ajustes_barra": 0,
        "angulos_resumo": "",
        "troca_angulo_entrada": False,
        "trocas_angulo_internas": 0,
        "trocas_angulo_barra": 0,
    }


def _build_material_group(
    eligible: List[Dict[str, Any]],
    gm: Dict[str, Any],
    cfg: OptimizationConfig,
    L_um: int,
    D_um: int,
    K_um: int,
    cap_um: int,
) -> Tuple[List[Dict[str, Any]], int, int]:
    """Cenário 1: otimização global de material + encadeamento de medidas e ângulos."""
    usable_um = max(1, L_um - D_um)
    homogeneous_sym_w_um = 0
    if eligible:
        first_pw = eligible[0]["_prof_w_um"]
        if (
            first_pw > 0
            and all(
                bool(p["perfil_simetrico"])
                and p["_ang_sig"] == (45, 45)
                and p["_prof_w_um"] == first_pw
                and first_pw <= p["_c_um"] // 2
                and (p["_c_um"] + K_um - first_pw) > 0
                for p in eligible
            )
        ):
            homogeneous_sym_w_um = first_pw

    pack_cap_um = max(1, usable_um + K_um - homogeneous_sym_w_um) if homogeneous_sym_w_um > 0 else cap_um

    buckets_by_w_sig: Dict[int, Dict[Tuple[int, int], deque]] = defaultdict(
        lambda: defaultdict(deque)
    )
    weight_counts: Counter[int] = Counter()
    for p in sorted(
        eligible, key=lambda x: (x["data_entrega"], x["op"], x["codigo"])
    ):
        pack_w = (
            (p["_c_um"] + K_um - homogeneous_sym_w_um)
            if homogeneous_sym_w_um > 0
            else p["_w_um"]
        )
        buckets_by_w_sig[pack_w][p["_ang_sig"]].append(p)
        weight_counts[pack_w] += 1

    weights = sorted(weight_counts.keys(), reverse=True)
    counts = [weight_counts[w] for w in weights]

    patterns = _pack_min_bars(weights, counts, pack_cap_um)
    ordered_bars = _assign_and_order_material_bars(
        patterns, weights, buckets_by_w_sig
    )

    bars: List[Dict[str, Any]] = []
    for idx_bar, bar_pieces in enumerate(ordered_bars, start=1):
        bars.append(
            _build_bar_dict("material", gm, idx_bar, bar_pieces, cfg, L_um, D_um, K_um)
        )

    ajustes, trocas_angulo = _annotate_and_count_adjustments(
        bars, count_measure_adjustments=True
    )
    return bars, ajustes, trocas_angulo


def _build_tempo_execucao_group(
    eligible: List[Dict[str, Any]],
    gm: Dict[str, Any],
    cfg: OptimizationConfig,
    L_um: int,
    D_um: int,
    K_um: int,
    cap_um: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int, int]:
    """Cenário 2: corte em lote por medida (maior → menor) com FFD em barras semi-cortadas."""
    usable_um = max(1, L_um - D_um)
    by_med: Dict[float, List[Dict[str, Any]]] = defaultdict(list)
    for p in eligible:
        by_med[round(float(p["medida_corte_mm"]), 3)].append(p)

    sorted_meds = sorted(by_med.keys(), reverse=True)
    open_bars: List[Dict[str, Any]] = []
    roteiro_medidas: List[Dict[str, Any]] = []
    route_prev_angle: Optional[int] = None
    total_trocas_angulo_lote = 0

    for passo_idx, med_mm in enumerate(sorted_meds, start=1):
        pcs_step, _ = _order_pieces_by_angle(
            by_med[med_mm], start_angle=route_prev_angle, keep_internal=True
        )
        trocas_angulo_passo = 0
        cur_step_ang = route_prev_angle
        for p in pcs_step:
            a_e = _norm_angle(p.get("angulo_esq"), 45)
            a_d = _norm_angle(p.get("angulo_dir"), 45)
            if cur_step_ang is not None and a_e != cur_step_ang:
                trocas_angulo_passo += 1
            if a_e != a_d:
                trocas_angulo_passo += 1
            cur_step_ang = a_d
        route_prev_angle = cur_step_ang
        total_trocas_angulo_lote += trocas_angulo_passo

        had_pieces_before: Dict[int, bool] = {}
        sobra_before_um: Dict[int, int] = {}
        step_allocs_by_bar: Dict[int, List[Dict[str, Any]]] = defaultdict(list)

        for p in pcs_step:
            c_um = p["_c_um"]
            placed_bar = None
            chosen_ov_um = 0
            chosen_inc_um = c_um

            for bar_state in open_bars:
                ov_um = _calc_pair_overlap_um(bar_state["pieces"][-1], p)
                inc_um = c_um + K_um - ov_um
                if bar_state["consumido_util_um"] + inc_um <= usable_um:
                    placed_bar = bar_state
                    chosen_ov_um = ov_um
                    chosen_inc_um = inc_um
                    break

            if placed_bar is None:
                b_num = len(open_bars) + 1
                placed_bar = {
                    "barra_numero": b_num,
                    "consumido_util_um": 0,
                    "soma_pecas_um": 0,
                    "econ_um": 0,
                    "pieces": [],
                }
                open_bars.append(placed_bar)
                had_pieces_before[b_num] = False
                sobra_before_um[b_num] = max(0, L_um - D_um)
                chosen_ov_um = 0
                chosen_inc_um = c_um
            else:
                b_num = placed_bar["barra_numero"]
                if b_num not in had_pieces_before:
                    had_pieces_before[b_num] = True
                    sobra_before_um[b_num] = max(
                        0, L_um - (D_um + placed_bar["consumido_util_um"])
                    )

            placed_bar["consumido_util_um"] += chosen_inc_um
            placed_bar["soma_pecas_um"] += c_um
            placed_bar["econ_um"] += chosen_ov_um
            clean_p = {k: v for k, v in p.items() if not k.startswith("_")}
            placed_bar["pieces"].append(clean_p)
            step_allocs_by_bar[b_num].append(clean_p)

        alocacoes: List[Dict[str, Any]] = []
        qtd_novas = 0
        qtd_sobras = 0
        step_ops = set()

        for b_num in sorted(step_allocs_by_bar.keys()):
            alloc_pcs = step_allocs_by_bar[b_num]
            bar_state = open_bars[b_num - 1]
            eh_sobra = bool(had_pieces_before[b_num])
            if eh_sobra:
                qtd_sobras += 1
                origem_str = f"Sobra da Barra #{b_num}"
            else:
                qtd_novas += 1
                origem_str = "Barra nova"

            sobra_depois_um = max(
                0, L_um - (D_um + bar_state["consumido_util_um"])
            )
            ops_alloc = sorted({p["op"] for p in alloc_pcs if p.get("op")})
            step_ops.update(ops_alloc)
            alloc_angles = sorted(
                {
                    _format_angles(
                        *_angle_sig(
                            _norm_angle(p.get("angulo_esq"), 45),
                            _norm_angle(p.get("angulo_dir"), 45),
                        )
                    )
                    for p in alloc_pcs
                }
            )

            alocacoes.append(
                {
                    "barra_numero": b_num,
                    "barra_global_numero": 0,  # preenchido após ordenação global
                    "eh_sobra": eh_sobra,
                    "origem_barra": origem_str,
                    "qtd_cortes": len(alloc_pcs),
                    "angulos_corte": ", ".join(alloc_angles),
                    "sobra_antes_mm": _from_um(sobra_before_um[b_num]),
                    "sobra_depois_mm": _from_um(sobra_depois_um),
                    "ops": ", ".join(ops_alloc[:10])
                    + (f" (+{len(ops_alloc) - 10})" if len(ops_alloc) > 10 else ""),
                    "pecas": alloc_pcs,
                }
            )

        ops_step_sorted = sorted(step_ops)
        step_angles = sorted(
            {
                _format_angles(
                    *_angle_sig(
                        _norm_angle(p.get("angulo_esq"), 45),
                        _norm_angle(p.get("angulo_dir"), 45),
                    )
                )
                for p in pcs_step
            }
        )
        roteiro_medidas.append(
            {
                "grupo_key": gm["grupo_key"],
                "grupo_nome": gm["grupo_nome"],
                "origem_agrupamento": gm["origem_agrupamento"],
                "codigo_perfil": gm["codigo_perfil"],
                "passo": passo_idx,
                "medida_corte_mm": med_mm,
                "qtd_total_pecas": len(pcs_step),
                "total_metros": round((len(pcs_step) * med_mm) / 1000.0, 3),
                "angulos_corte": ", ".join(step_angles),
                "troca_medida": passo_idx > 1,
                "troca_angulo": trocas_angulo_passo > 0,
                "trocas_angulo_passo": trocas_angulo_passo,
                "qtd_barras_novas": qtd_novas,
                "qtd_sobras_reaproveitadas": qtd_sobras,
                "ops": ", ".join(ops_step_sorted[:10])
                + (
                    f" (+{len(ops_step_sorted) - 10})"
                    if len(ops_step_sorted) > 10
                    else ""
                ),
                "alocacoes": alocacoes,
            }
        )

    bars: List[Dict[str, Any]] = []
    for bar_state in open_bars:
        clean_pieces = list(bar_state["pieces"])
        b_dict = _build_bar_dict(
            "tempo_execucao",
            gm,
            bar_state["barra_numero"],
            clean_pieces,
            cfg,
            L_um,
            D_um,
            K_um,
        )
        distinct_in_bar = len({p["medida_corte_mm"] for p in clean_pieces})
        b_dict["troca_entrada"] = False
        b_dict["ajustes_internos"] = max(0, distinct_in_bar - 1)
        b_dict["ajustes_barra"] = max(0, distinct_in_bar - 1)
        bars.append(b_dict)

    _annotate_and_count_adjustments(bars, count_measure_adjustments=False)
    ajustes_lote = max(0, len(roteiro_medidas) - 1)
    return bars, roteiro_medidas, ajustes_lote, total_trocas_angulo_lote


def _calc_avg_yield_and_loss(
    soma_pecas_mm: float, total_perda_mm: float, qtd_barras: int, barra_mm: float
) -> Tuple[float, float]:
    if qtd_barras <= 0 or barra_mm <= 0:
        return 0.0, 0.0
    aproveitamento = round((soma_pecas_mm / (qtd_barras * barra_mm)) * 100.0, 2)
    perda_media = round(total_perda_mm / qtd_barras, 2)
    return aproveitamento, perda_media


def _assemble_scenario_payload(
    scenario_id: str,
    nome: str,
    descricao: str,
    grupos_out: List[Dict[str, Any]],
    barra_mm: float,
    include_roteiro: bool = False,
) -> Dict[str, Any]:
    grupos_sorted = sorted(
        grupos_out,
        key=lambda g: (-g["qtd_barras"], -g["total_pecas_entrada"], g["grupo_nome"]),
    )

    barras_flat: List[Dict[str, Any]] = []
    global_map: Dict[Tuple[str, int], int] = {}
    for g in sorted(grupos_sorted, key=lambda x: x["grupo_nome"]):
        for b in g["barras"]:
            barras_flat.append(dict(b))
    for i, b in enumerate(barras_flat, start=1):
        b["barra_global_numero"] = i
        global_map[(b["grupo_key"], b["barra_numero"])] = i

    for g in grupos_sorted:
        for b in g["barras"]:
            b["barra_global_numero"] = global_map[(b["grupo_key"], b["barra_numero"])]
        if include_roteiro:
            for step in g.get("roteiro_medidas", []):
                for alloc in step["alocacoes"]:
                    alloc["barra_global_numero"] = global_map[
                        (step["grupo_key"], alloc["barra_numero"])
                    ]

    total_barras = sum(g["qtd_barras"] for g in grupos_sorted)
    total_pecas_entrada = sum(g["total_pecas_entrada"] for g in grupos_sorted)
    total_pecas_alocadas = sum(g["total_pecas_alocadas"] for g in grupos_sorted)
    total_pecas_inviaveis = sum(g["total_pecas_inviaveis"] for g in grupos_sorted)
    soma_pecas_mm = round(sum(g["total_metros_pecas"] * 1000.0 for g in grupos_sorted), 3)
    total_perda_mm = round(sum(g["total_perda_mm"] for g in grupos_sorted), 3)
    total_ajustes = sum(g["ajustes_corte"] for g in grupos_sorted)
    total_trocas_angulo = sum(g.get("trocas_angulo", 0) for g in grupos_sorted)
    total_econ_mm = round(sum(g.get("economia_chanfro_mm", 0.0) for g in grupos_sorted), 3)
    total_cortes_par = sum(g.get("cortes_paralelos_qtd", 0) for g in grupos_sorted)
    total_cortes_v = sum(g.get("cortes_v_qtd", 0) for g in grupos_sorted)
    soma_util_mm = max(0.0, round(soma_pecas_mm - total_econ_mm, 3))
    aproveitamento, perda_media = _calc_avg_yield_and_loss(
        soma_util_mm, total_perda_mm, total_barras, barra_mm
    )

    resumo = {
        "total_grupos": len(grupos_sorted),
        "total_pecas_entrada": total_pecas_entrada,
        "total_pecas_alocadas": total_pecas_alocadas,
        "total_pecas_inviaveis": total_pecas_inviaveis,
        "total_barras": total_barras,
        "total_metros_pecas": round(soma_pecas_mm / 1000.0, 3),
        "total_perda_mm": total_perda_mm,
        "total_perda_metros": round(total_perda_mm / 1000.0, 3),
        "perda_media_barra_mm": perda_media,
        "aproveitamento_medio_pct": aproveitamento,
        "total_ajustes_corte": total_ajustes,
        "total_trocas_angulo": total_trocas_angulo,
        "total_economia_chanfro_mm": total_econ_mm,
        "total_cortes_paralelos": total_cortes_par,
        "total_cortes_v": total_cortes_v,
    }

    payload: Dict[str, Any] = {
        "id": scenario_id,
        "nome": nome,
        "descricao": descricao,
        "resumo": resumo,
        "grupos": grupos_sorted,
        "barras_flat": barras_flat,
    }

    if include_roteiro:
        roteiro_flat = []
        for g in grupos_sorted:
            for step in g.get("roteiro_medidas", []):
                roteiro_flat.append(step)
        roteiro_flat.sort(
            key=lambda s: (-s["medida_corte_mm"], s["grupo_nome"], s["passo"])
        )
        payload["roteiro_flat"] = roteiro_flat

    return payload


def build_bar_optimization(
    detailed_bars: List[Dict[str, Any]],
    config: Optional[OptimizationConfig] = None,
    rules: Optional[Dict[str, CuttingRule]] = None,
) -> Dict[str, Any]:
    """Otimiza cortes em barras de 6 m por perfil físico em 2 cenários: Material vs Tempo."""
    cfg = config or OptimizationConfig()
    L_um = max(1, _to_um(cfg.comprimento_barra_mm))
    D_um = max(0, _to_um(cfg.desponte_mm))
    K_um = max(0, _to_um(cfg.espessura_serra_mm))

    usable_um = max(1, L_um - D_um)
    cap_um = usable_um + K_um

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
        a_esq, a_dir = _resolve_bar_angles(bar)
        ang_sig = _angle_sig(a_esq, a_dir)
        ang_str = _format_angles(a_esq, a_dir)

        eh_pux = bool(bar.get("eh_perfil_puxador"))
        modelo_bar = (bar.get("modelo") or "OUTRO").strip()
        rule_bar = rules.get(modelo_bar) if rules else None
        if "perfil_simetrico" in bar and bar["perfil_simetrico"] is not None:
            perfil_sim = bool(bar["perfil_simetrico"])
        elif rule_bar is not None:
            perfil_sim = bool(
                rule_bar.perfil_simetrico_puxador if eh_pux else rule_bar.perfil_simetrico_lateral
            )
        else:
            perfil_sim = False

        raw_larg = bar.get("largura_perfil_mm")
        if raw_larg is not None and float(raw_larg or 0.0) > 0.0:
            larg_perfil_mm = round(float(raw_larg), 3)
        elif rule_bar is not None:
            larg_perfil_mm = round(
                float(
                    rule_bar.largura_perfil_puxador_mm
                    if eh_pux
                    else rule_bar.largura_perfil_quadro_mm
                )
                or 0.0,
                3,
            )
        else:
            larg_perfil_mm = 0.0
        prof_w_um = max(0, _to_um(larg_perfil_mm))

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
                    "eh_perfil_puxador": eh_pux,
                    "tipo_corte": str(bar.get("tipo_corte") or ""),
                    "angulo_esq": a_esq,
                    "angulo_dir": a_dir,
                    "angulos_corte": ang_str,
                    "perfil_simetrico": perfil_sim,
                    "largura_perfil_mm": larg_perfil_mm,
                    "observacao_corte": str(bar.get("observacao_corte") or ""),
                    "medida_corte_mm": med_mm,
                    "_c_um": c_um,
                    "_w_um": c_um + K_um,
                    "_ang_sig": ang_sig,
                    "_prof_w_um": prof_w_um,
                }
            )

    grupos_material: List[Dict[str, Any]] = []
    grupos_tempo: List[Dict[str, Any]] = []
    pecas_inviaveis_raw: List[Dict[str, Any]] = []

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

        pecas_inviaveis_raw.extend(oversized)
        medidas_distintas = len({p["medida_corte_mm"] for p in eligible})
        angulos_presentes = sorted(
            {_format_angles(*p["_ang_sig"]) for p in eligible}
        )
        grupo_simetrico = bool(eligible) and all(
            bool(p["perfil_simetrico"]) for p in eligible
        )

        # Cenário 1: Aproveitamento de Material
        mat_bars, mat_adj, mat_ang_adj = _build_material_group(
            eligible, gm, cfg, L_um, D_um, K_um, cap_um
        )
        mat_soma_mm = round(sum(b["soma_pecas_mm"] for b in mat_bars), 3)
        mat_econ_mm = round(sum(b["economia_chanfro_mm"] for b in mat_bars), 3)
        mat_util_mm = max(0.0, round(mat_soma_mm - mat_econ_mm, 3))
        mat_perda_mm = round(sum(b["perda_mm"] for b in mat_bars), 3)
        mat_par_qtd = sum(b["cortes_paralelos_qtd"] for b in mat_bars)
        mat_v_qtd = sum(b["cortes_v_qtd"] for b in mat_bars)
        mat_aprov, mat_perda_media = _calc_avg_yield_and_loss(
            mat_util_mm, mat_perda_mm, len(mat_bars), cfg.comprimento_barra_mm
        )

        common_meta = {
            "grupo_key": gm["grupo_key"],
            "grupo_nome": gm["grupo_nome"],
            "origem_agrupamento": gm["origem_agrupamento"],
            "codigo_perfil": gm["codigo_perfil"],
            "modelos": sorted(gm["modelos_set"]),
            "tipos_perfil": sorted(gm["tipos_set"]),
            "acabamentos": sorted(gm["acabamentos_set"]),
            "angulos_presentes": angulos_presentes,
            "perfil_simetrico": grupo_simetrico,
            "total_pecas_entrada": len(pieces),
            "total_pecas_alocadas": len(eligible),
            "total_pecas_inviaveis": len(oversized),
            "medidas_distintas": medidas_distintas,
        }

        grupos_material.append(
            {
                **common_meta,
                "qtd_barras": len(mat_bars),
                "total_metros_pecas": round(mat_soma_mm / 1000.0, 3),
                "total_perda_mm": mat_perda_mm,
                "total_perda_metros": round(mat_perda_mm / 1000.0, 3),
                "perda_media_barra_mm": mat_perda_media,
                "aproveitamento_medio_pct": mat_aprov,
                "ajustes_corte": mat_adj,
                "trocas_angulo": mat_ang_adj,
                "economia_chanfro_mm": mat_econ_mm,
                "cortes_paralelos_qtd": mat_par_qtd,
                "cortes_v_qtd": mat_v_qtd,
                "barras": mat_bars,
            }
        )

        # Cenário 2: Tempo de Execução (Lote por Medida FFD Maior -> Menor)
        tmp_bars, tmp_roteiro, tmp_adj, tmp_ang_adj = _build_tempo_execucao_group(
            eligible, gm, cfg, L_um, D_um, K_um, cap_um
        )
        tmp_soma_mm = round(sum(b["soma_pecas_mm"] for b in tmp_bars), 3)
        tmp_econ_mm = round(sum(b["economia_chanfro_mm"] for b in tmp_bars), 3)
        tmp_util_mm = max(0.0, round(tmp_soma_mm - tmp_econ_mm, 3))
        tmp_perda_mm = round(sum(b["perda_mm"] for b in tmp_bars), 3)
        tmp_par_qtd = sum(b["cortes_paralelos_qtd"] for b in tmp_bars)
        tmp_v_qtd = sum(b["cortes_v_qtd"] for b in tmp_bars)
        tmp_aprov, tmp_perda_media = _calc_avg_yield_and_loss(
            tmp_util_mm, tmp_perda_mm, len(tmp_bars), cfg.comprimento_barra_mm
        )

        grupos_tempo.append(
            {
                **common_meta,
                "qtd_barras": len(tmp_bars),
                "total_metros_pecas": round(tmp_soma_mm / 1000.0, 3),
                "total_perda_mm": tmp_perda_mm,
                "total_perda_metros": round(tmp_perda_mm / 1000.0, 3),
                "perda_media_barra_mm": tmp_perda_media,
                "aproveitamento_medio_pct": tmp_aprov,
                "ajustes_corte": tmp_adj,
                "trocas_angulo": tmp_ang_adj,
                "economia_chanfro_mm": tmp_econ_mm,
                "cortes_paralelos_qtd": tmp_par_qtd,
                "cortes_v_qtd": tmp_v_qtd,
                "barras": tmp_bars,
                "roteiro_medidas": tmp_roteiro,
            }
        )

    cenario_material = _assemble_scenario_payload(
        "material",
        "Aproveitamento de Material",
        "Menor número de barras e menor perda total, com encadeamento de medidas entre barras.",
        grupos_material,
        cfg.comprimento_barra_mm,
        include_roteiro=False,
    )
    cenario_tempo = _assemble_scenario_payload(
        "tempo_execucao",
        "Tempo de Execução (Maior → Menor)",
        "Corte em lote por medida da maior para a menor reaproveitando sobras (mínimo de ajustes).",
        grupos_tempo,
        cfg.comprimento_barra_mm,
        include_roteiro=True,
    )

    mat_r = cenario_material["resumo"]
    tmp_r = cenario_tempo["resumo"]
    reducao_ajustes = mat_r["total_ajustes_corte"] - tmp_r["total_ajustes_corte"]
    reducao_pct = (
        round((reducao_ajustes / mat_r["total_ajustes_corte"]) * 100.0, 2)
        if mat_r["total_ajustes_corte"] > 0
        else 0.0
    )

    comparativo = {
        "diferenca_barras_tempo_vs_material": tmp_r["total_barras"] - mat_r["total_barras"],
        "diferenca_perda_mm_tempo_vs_material": round(
            tmp_r["total_perda_mm"] - mat_r["total_perda_mm"], 3
        ),
        "diferenca_perda_metros_tempo_vs_material": round(
            tmp_r["total_perda_metros"] - mat_r["total_perda_metros"], 3
        ),
        "reducao_ajustes_tempo_vs_material": reducao_ajustes,
        "reducao_ajustes_pct": reducao_pct,
        "reducao_trocas_angulo_tempo_vs_material": mat_r["total_trocas_angulo"]
        - tmp_r["total_trocas_angulo"],
        "diferenca_economia_chanfro_mm_tempo_vs_material": round(
            tmp_r["total_economia_chanfro_mm"] - mat_r["total_economia_chanfro_mm"], 3
        ),
    }

    pecas_inviaveis_flat = sorted(
        pecas_inviaveis_raw,
        key=lambda x: (
            -x["medida_corte_mm"],
            x["grupo_nome"],
            x["data_entrega"],
            x["op"],
            x["codigo"],
        ),
    )

    return {
        "config": cfg.to_dict(),
        "comparativo": comparativo,
        "cenarios": {
            "material": cenario_material,
            "tempo_execucao": cenario_tempo,
        },
        "pecas_inviaveis_flat": pecas_inviaveis_flat,
    }
