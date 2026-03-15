from gem5.components.boards.simple_board import SimpleBoard
from gem5.components.cachehierarchies.classic.private_l1_private_l2_cache_hierarchy import (
    PrivateL1PrivateL2CacheHierarchy,
)
from gem5.components.memory.single_channel import SingleChannelDDR4_2400
from gem5.resources.resource import BinaryResource
from gem5.simulate.simulator import Simulator
from gem5.isas import ISA

from gem5.components.processors.base_cpu_core import BaseCPUCore
from gem5.components.processors.base_cpu_processor import BaseCPUProcessor

from m5.objects import X86O3CPU, TournamentBP, InstCsvTrace

import m5
import json
import os
import sys
from pathlib import Path

# --- 1. Load Configuration from JSON (must be first) ---
# Usage: gem5 run_nw.py [run_nw_config.json]
# Default: run_nw_config.json in the same directory as this script
script_dir = Path(__file__).resolve().parent
config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else script_dir / "run_nw_config.json"
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

def _get(key, default):
    return config.get(key, default)

# --- 2. Custom Out-of-Order (OoO) Core Configuration ---
class MyOutOfOrderCore(BaseCPUCore):
    def __init__(self, width, rob_size, num_int_regs, num_fp_regs, trace_cfg):
        core = X86O3CPU()
        core.fetchWidth = width
        core.decodeWidth = width
        core.renameWidth = width
        core.dispatchWidth = width
        core.issueWidth = width
        core.wbWidth = width
        core.commitWidth = width
        core.numROBEntries = rob_size
        core.numPhysIntRegs = num_int_regs
        core.numPhysFloatRegs = num_fp_regs
        core.branchPred = TournamentBP()

        inst_trace = InstCsvTrace()
        inst_trace.trace_file = trace_cfg.get("trace_file", "inst_trace.csv")
        inst_trace.trace_fetch = trace_cfg.get("trace_fetch", True)
        inst_trace.trace_mem = trace_cfg.get("trace_mem", True)
        inst_trace.start_after_inst = trace_cfg.get("trace_start_after_inst", 0)
        inst_trace.stop_after_inst = trace_cfg.get("trace_stop_after_inst", 0)
        core.probeListener = inst_trace

        super().__init__(core, ISA.X86)

class MyOutOfOrderProcessor(BaseCPUProcessor):
    def __init__(self, width, rob_size, num_int_regs, num_fp_regs, trace_cfg):
        super().__init__(
            cores=[MyOutOfOrderCore(width, rob_size, num_int_regs, num_fp_regs, trace_cfg)]
        )

# --- 3. Build Hardware from Config ---
trace_cfg = {
    "trace_file": _get("trace_file", "inst_trace.csv"),
    "trace_fetch": _get("trace_fetch", True),
    "trace_mem": _get("trace_mem", True),
    "trace_start_after_inst": _get("trace_start_after_inst", 0),
    "trace_stop_after_inst": _get("trace_stop_after_inst", 0),
}

cache_hierarchy = PrivateL1PrivateL2CacheHierarchy(
    l1d_size=_get("l1d_size", "4kB"),
    l1i_size=_get("l1i_size", "4kB"),
    l2_size=_get("l2_size", "16kB"),
)

main_memory = SingleChannelDDR4_2400(size=_get("memory_size", "4GB"))

my_ooo_processor = MyOutOfOrderProcessor(
    width=_get("cpu_width", 8),
    rob_size=_get("rob_size", 192),
    num_int_regs=_get("num_int_regs", 256),
    num_fp_regs=_get("num_fp_regs", 256),
    trace_cfg=trace_cfg,
)

board = SimpleBoard(
    processor=my_ooo_processor,
    memory=main_memory,
    cache_hierarchy=cache_hierarchy,
    clk_freq=_get("clk_freq", "3GHz"),
)

# --- 4. Workload Setup ---
matrix_size = str(_get("matrix_size", 512))
block_size = str(_get("block_size", 1))
match_score = str(_get("match_score", 2))
mismatch_penalty = str(_get("mismatch_penalty", -1))
gap_penalty = str(_get("gap_penalty", -2))
random_seed = str(_get("random_seed", 42))

binary_path = Path(_get("binary_path", "./nw_bench_x86")).resolve()

board.set_se_binary_workload(
    binary=BinaryResource(local_path=str(binary_path)),
    arguments=[matrix_size, block_size, match_score, mismatch_penalty, gap_penalty, random_seed],
)

# --- 5. Simulation Execution ---
simulator = Simulator(board)
outdir = m5.options.outdir

# Output statistical reports in both Text and JSON formats
simulator.add_text_stats_output(os.path.join(outdir, "stats.txt"))
simulator.add_json_stats_output(os.path.join(outdir, "stats.json"))

print(f"Starting Simulation with N={matrix_size} and BlockSize={block_size}...")
simulator.run()
print(f"Simulation completed. Check results in: {outdir}")