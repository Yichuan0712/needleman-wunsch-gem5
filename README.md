# Needleman-Wunsch gem5 Benchmark

A gem5 microarchitecture simulation project for the Needleman-Wunsch sequence alignment algorithm.

## Usage

Assume project root is `/workspace` and gem5 is at `/workspace/gem5_base`. All commands use full paths; no `cd` required. Adjust paths as needed.

### 1. Compile the benchmark

**X86:**
```bash
gcc -o /workspace/demo/programs/nw_bench_x86 /workspace/demo/programs/nw_bench.c
```

**ARM:**
```bash
gcc -o /workspace/demo/programs/nw_bench_arm /workspace/demo/programs/nw_bench.c
```

### 2. Run the simulation

Set `binary_path` in `run_nw_config.json` to the full path of the binary so it works regardless of cwd. Use `-d` to pin the output directory.

**X86:**
```bash
/workspace/gem5_base/build/X86/gem5.opt -d /workspace/m5out /workspace/demo/x86/board_configurations/run_nw.py /workspace/demo/x86/board_configurations/run_nw_config.json
```

**ARM:**
```bash
/workspace/gem5_base/build/ARM/gem5.opt -d /workspace/m5out /workspace/demo/ARM/board_configurations/run_nw.py /workspace/demo/ARM/board_configurations/run_nw_config.json
```

### 3. Compute metrics

```bash
python3 /workspace/compute_metrics.py /workspace/m5out
```

Omitting the argument defaults to `m5out` in the current directory.

### 4. Check results

The output directory contains:

- `stats.txt` / `stats.json` — performance statistics
- `inst_trace.csv` — instruction execution trace

---

### Parameter configuration

Edit `run_nw_config.json` (same directory as `run_nw.py`) to adjust parameters. All are optional:

- **X86:** `demo/x86/board_configurations/run_nw_config.json`
- **ARM:** `demo/ARM/board_configurations/run_nw_config.json`

```json
{
  "sequence_length": 128,
  "block_size": 1,
  "binary_path": "/workspace/demo/programs/nw_bench_x86",
  "clk_freq": "3GHz",
  "l1d_size": "4kB",
  "l1i_size": "4kB",
  "l2_size": "16kB",
  "memory_size": "4GB",
  "cpu_width": 8,
  "rob_size": 192,
  "num_int_regs": 256,
  "num_fp_regs": 256,
  "trace_file": "inst_trace.csv",
  "trace_fetch": true,
  "trace_mem": true,
  "trace_start_after_inst": 0,
  "trace_stop_after_inst": 0,
  "match_score": 2,
  "mismatch_penalty": -1,
  "gap_penalty": -2,
  "random_seed": 42
}
```

**Parameter reference:**

| Parameter | Description | Range / Examples |
|-----------|-------------|------------------|
| `sequence_length` | Length of each sequence; DP matrix is (N+1)×(N+1) | 1–256 |
| `block_size` | Tile size; 1=row-by-row, 8–64=cache-friendly | 1 to sequence_length |
| `binary_path` | Full path to executable (recommended when using full-path commands) | `/workspace/demo/programs/nw_bench_x86` |
| `clk_freq` | CPU clock frequency | 1GHz, 2GHz, 3GHz |
| `l1d_size` / `l1i_size` / `l2_size` | Cache sizes | 4kB, 8kB, 16kB, 32kB |
| `memory_size` | Main memory size | 1GB, 4GB, 8GB |
| `cpu_width` | Pipeline width | 4–8 |
| `rob_size` | ROB entries | 32–512 |
| `num_int_regs` / `num_fp_regs` | Physical registers | 64–512 |
| `trace_*` | Instruction trace options | — |
| `match_score` / `mismatch_penalty` / `gap_penalty` | NW scoring parameters | — |
| `random_seed` | RNG seed | 0–2³¹-1 |

**Metric formulas and stats fields:**

| Metric | Formula | Stats fields (from stats.txt / stats.json) |
|--------|---------|-------------------------------------------|
| **CPI** | numCycles / simInsts | `numCycles` = simTicks / (simFreq ÷ clk_freq). Use `simTicks`, `simFreq`, `simInsts`. clk_freq from run_nw_config.json. |
| **MPKI (L1I)** | misses × 1000 / simInsts | `board.cache_hierarchy.l1i-cache-0.demandMisses::total` (or `prefetcher.demandMshrMisses`) |
| **MPKI (L1D)** | misses × 1000 / simInsts | `board.cache_hierarchy.l1d-cache-0.demandMisses::total` (or `prefetcher.demandMshrMisses`) |
| **MPKI (L2)** | misses × 1000 / simInsts | `board.cache_hierarchy.l2-cache-0.demandMisses::total` (or `demandMshrMisses::total`) |
| **Branch mispred rate** | mispredicted / committed_branches | `board.processor.cores.core.iew.branchMispredicts` ÷ `commitStats0.committedControl::IsControl` |
| **0-fetch cycles frac** | nisnDist::0 / numCycles | `board.processor.cores.core.fetch.nisnDist::0` (proxy for 0-issue; gem5 has no numIssuedDist) |
| **Idle cycles frac** | idleCycles / numCycles | Sum of `decode.idleCycles` + `rename.idleCycles` + `iew.idleCycles` (stages may overlap) |
| **Cache blocked frac** | sum(blockedCycles) / numCycles | Sum of `l1d-cache-0.blockedCycles::no_mshrs` + `::no_targets`, same for l1i and l2 |

> CPI < 1 is normal for out-of-order superscalar CPUs (multiple instructions per cycle). IPC = 1/CPI.
