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
import os
import sys
from pathlib import Path

# --- 1. Custom Out-of-Order (OoO) Core Configuration ---
class MyOutOfOrderCore(BaseCPUCore):
    def __init__(self, width, rob_size, num_int_regs, num_fp_regs):
        # Using X86 Detailed Out-of-Order CPU model
        core = X86O3CPU()

        # Pipeline Width: Defines how many instructions can be processed per cycle
        core.fetchWidth = width
        core.decodeWidth = width
        core.renameWidth = width
        core.dispatchWidth = width
        core.issueWidth = width
        core.wbWidth = width
        core.commitWidth = width

        # Buffer and Register Resources: Critical for Instruction Level Parallelism (ILP)
        core.numROBEntries = rob_size
        core.numPhysIntRegs = num_int_regs
        core.numPhysFloatRegs = num_fp_regs

        # Branch Predictor: NW algorithm contains many loops and 'if' branches
        core.branchPred = TournamentBP()

        # Instruction Tracing: Captures execution flow into a CSV file
        inst_trace = InstCsvTrace()
        inst_trace.trace_file = "inst_trace.csv"
        inst_trace.trace_fetch = True
        inst_trace.trace_mem = True
        inst_trace.start_after_inst = 0
        inst_trace.stop_after_inst = 0
        core.probeListener = inst_trace

        super().__init__(core, ISA.X86)

class MyOutOfOrderProcessor(BaseCPUProcessor):
    def __init__(self, width, rob_size, num_int_regs, num_fp_regs):
        super().__init__(
            cores=[MyOutOfOrderCore(width, rob_size, num_int_regs, num_fp_regs)]
        )

# --- 2. Hardware Hierarchy Setup ---
# Cache sizes are set small to demonstrate the "Painful" vs "Easy" cache thrashing effect
cache_hierarchy = PrivateL1PrivateL2CacheHierarchy(
    l1d_size="4kB", l1i_size="4kB", l2_size="16kB"
)

# 4GB Single Channel DDR4 Memory
main_memory = SingleChannelDDR4_2400(size="4GB")

# High-performance processor configuration (8-wide issue)
my_ooo_processor = MyOutOfOrderProcessor(
    width=8, rob_size=192, num_int_regs=256, num_fp_regs=256
)

# Assemble the simulated board
board = SimpleBoard(
    processor=my_ooo_processor,
    memory=main_memory,
    cache_hierarchy=cache_hierarchy,
    clk_freq="3GHz",
)

# --- 3. Command Line Arguments Handling ---
# Usage: gem5 run_nw_tiled.py [matrix_size] [block_size]
# Default: N=512, Block=1 (Painful Mode)
matrix_size = "512"
block_size = "1"

if len(sys.argv) > 1:
    matrix_size = sys.argv[1]
if len(sys.argv) > 2:
    block_size = sys.argv[2]

# Ensure the binary path is correct relative to your workspace
# Assuming your binary 'nw_tiled_x86' is compiled in the same directory
binary_path = Path("./nw_bench_x86").resolve()

# Set the System-call Emulation (SE) workload
board.set_se_binary_workload(
    binary=BinaryResource(local_path=str(binary_path)),
    arguments=[matrix_size, block_size],
)

# --- 4. Simulation Execution ---
simulator = Simulator(board)
outdir = m5.options.outdir

# Output statistical reports in both Text and JSON formats
simulator.add_text_stats_output(os.path.join(outdir, "stats.txt"))
simulator.add_json_stats_output(os.path.join(outdir, "stats.json"))

print(f"Starting Simulation with N={matrix_size} and BlockSize={block_size}...")
simulator.run()
print(f"Simulation completed. Check results in: {outdir}")