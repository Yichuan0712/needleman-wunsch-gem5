#!/usr/bin/env python3
"""
Compute gem5 simulation metrics from stats.txt or stats.json.
Usage: python compute_metrics.py [path/to/m5out]
Default: ./m5out
"""

import json
import re
import sys
from pathlib import Path


def parse_stats_txt(path: Path) -> dict[str, float]:
    """Parse gem5 stats.txt format: 'name    value    # comment'"""
    stats = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("-"):
                continue
            # Split by 2+ spaces; first part is name, second is value
            parts = re.split(r"\s{2,}", line, maxsplit=2)
            if len(parts) >= 2:
                name = parts[0].strip()
                val_str = parts[1].split()[0] if parts[1].split() else ""
                try:
                    val = float(val_str)
                    stats[name] = val
                except (ValueError, IndexError):
                    pass
    return stats


def get_stat(stats: dict, *keys, default=0.0) -> float:
    """Get first matching key from stats."""
    for k in keys:
        if k in stats:
            return stats[k]
    return default


def parse_clk_freq(freq_str: str) -> float:
    """Parse '3GHz' -> 3e9"""
    m = re.match(r"([\d.]+)\s*([gGmMkK])?[hH]z", freq_str)
    if m:
        val = float(m.group(1))
        unit = (m.group(2) or "G").upper()
        scale = {"K": 1e3, "M": 1e6, "G": 1e9}[unit]
        return val * scale
    return 3e9  # default 3GHz


def compute_metrics(stats_dir: Path, clk_freq_hz: float = 3e9) -> dict:
    stats_path = stats_dir / "stats.txt"
    if not stats_path.exists():
        stats_path = stats_dir / "stats.json"
        if not stats_path.exists():
            raise FileNotFoundError(f"No stats.txt or stats.json in {stats_dir}")

    if stats_path.suffix == ".json":
        with open(stats_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        stats = _flatten_json(data)
    else:
        stats = parse_stats_txt(stats_path)

    sim_insts = get_stat(stats, "simInsts")
    sim_ticks = get_stat(stats, "simTicks", "finalTick")
    sim_freq = get_stat(stats, "simFreq", default=1e12)

    # numCycles = simTicks / (ticks_per_cycle)
    # ticks_per_cycle = simFreq / clk_freq  (e.g. 1e12/3e9 = 333.33 for 3GHz)
    ticks_per_cycle = sim_freq / clk_freq_hz
    num_cycles = sim_ticks / ticks_per_cycle if ticks_per_cycle else 0

    # 1) CPI = numCycles / simInsts (can be <1 for OoO superscalar)
    cpi = num_cycles / sim_insts if sim_insts else 0

    # 2) Cache MPKI: use demandMisses::total (standard) or prefetcher.demandMshrMisses
    l1i_misses = get_stat(
        stats,
        "board.cache_hierarchy.l1i-cache-0.demandMisses::total",
        "board.cache_hierarchy.l1i-cache-0.prefetcher.demandMshrMisses",
    )
    l1d_misses = get_stat(
        stats,
        "board.cache_hierarchy.l1d-cache-0.demandMisses::total",
        "board.cache_hierarchy.l1d-cache-0.prefetcher.demandMshrMisses",
    )
    l2_misses = get_stat(
        stats,
        "board.cache_hierarchy.l2-cache-0.demandMisses::total",
        "board.cache_hierarchy.l2-cache-0.demandMshrMisses::total",
    )

    # MPKI = (misses * 1000) / simInsts
    mpki_l1i = l1i_misses * 1000 / sim_insts if sim_insts else 0
    mpki_l1d = l1d_misses * 1000 / sim_insts if sim_insts else 0
    mpki_l2 = l2_misses * 1000 / sim_insts if sim_insts else 0

    # 3) Branch misprediction rate = mispredicted / committed_branches
    committed_branches = get_stat(
        stats,
        "board.processor.cores.core.commitStats0.committedControl::IsControl",
    )
    mispredicted = get_stat(
        stats,
        "board.processor.cores.core.iew.branchMispredicts",
        "board.processor.cores.core.decode.branchMispred",
    )
    mispred_rate = mispredicted / committed_branches if committed_branches else 0

    # 4) Stall indicators
    # 4.1 0-fetch cycles: nisnDist::0 = cycles with 0 instructions fetched (proxy for 0-issue)
    zero_issue_cycles = get_stat(
        stats,
        "board.processor.cores.core.fetch.nisnDist::0",
    )
    f_zero_issue = zero_issue_cycles / num_cycles if num_cycles else 0

    # 4.2 idle cycles: sum of stage idles (may overlap)
    decode_idle = get_stat(stats, "board.processor.cores.core.decode.idleCycles")
    rename_idle = get_stat(stats, "board.processor.cores.core.rename.idleCycles")
    iew_idle = get_stat(stats, "board.processor.cores.core.iew.idleCycles")
    idle_cycles = decode_idle + rename_idle + iew_idle
    f_idle = idle_cycles / num_cycles if num_cycles else 0

    # 4.3 cache blocked: sum blockedCycles::no_mshrs + ::no_targets for each cache
    l1d_blocked = (
        get_stat(stats, "board.cache_hierarchy.l1d-cache-0.blockedCycles::no_mshrs")
        + get_stat(stats, "board.cache_hierarchy.l1d-cache-0.blockedCycles::no_targets")
    )
    l1i_blocked = (
        get_stat(stats, "board.cache_hierarchy.l1i-cache-0.blockedCycles::no_mshrs")
        + get_stat(stats, "board.cache_hierarchy.l1i-cache-0.blockedCycles::no_targets")
    )
    l2_blocked = (
        get_stat(stats, "board.cache_hierarchy.l2-cache-0.blockedCycles::no_mshrs")
        + get_stat(stats, "board.cache_hierarchy.l2-cache-0.blockedCycles::no_targets")
    )
    total_blocked = l1d_blocked + l1i_blocked + l2_blocked
    f_blocked = total_blocked / num_cycles if num_cycles else 0

    return {
        "CPI": cpi,
        "MPKI_L1I": mpki_l1i,
        "MPKI_L1D": mpki_l1d,
        "MPKI_L2": mpki_l2,
        "branch_mispred_rate": mispred_rate,
        "f_zero_issue": f_zero_issue,
        "f_idle": f_idle,
        "f_cache_blocked": f_blocked,
        "_raw": {
            "simInsts": sim_insts,
            "numCycles": num_cycles,
            "simTicks": sim_ticks,
            "committed_branches": committed_branches,
            "mispredicted": mispredicted,
        },
    }


def _flatten_json(obj, prefix=""):
    """Flatten nested JSON for stats lookup."""
    result = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_prefix = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict) and "value" in v:
                result[new_prefix] = v["value"]
            else:
                result.update(_flatten_json(v, new_prefix))
    return result


def main():
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("m5out")
    base = base.resolve()

    # Try to get clk_freq from run_nw_config.json
    config_path = Path(__file__).resolve().parent / "demo" / "x86" / "board_configurations" / "run_nw_config.json"
    clk_freq_hz = 3e9
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        clk_str = config.get("clk_freq", "3GHz")
        clk_freq_hz = parse_clk_freq(clk_str)

    metrics = compute_metrics(base, clk_freq_hz)

    print("=" * 50)
    print("gem5 Simulation Metrics")
    print("=" * 50)
    ipc_str = f"  (IPC = {1/metrics['CPI']:.2f})" if metrics['CPI'] > 0 else ""
    print(f"CPI:                    {metrics['CPI']:.4f}{ipc_str}")
    print(f"MPKI L1I:               {metrics['MPKI_L1I']:.4f}")
    print(f"MPKI L1D:               {metrics['MPKI_L1D']:.4f}")
    print(f"MPKI L2:                {metrics['MPKI_L2']:.4f}")
    print(f"Branch mispred rate:   {metrics['branch_mispred_rate']:.4%}")
    print(f"0-fetch cycles frac:   {metrics['f_zero_issue']:.4%}  (proxy for 0-issue)")
    print(f"Idle cycles frac:      {metrics['f_idle']:.4%}")
    print(f"Cache blocked frac:    {metrics['f_cache_blocked']:.4%}")
    print("=" * 50)
    print(f"(simInsts={metrics['_raw']['simInsts']:.0f}, numCycles={metrics['_raw']['numCycles']:.0f})")


if __name__ == "__main__":
    main()
