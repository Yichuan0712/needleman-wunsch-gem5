# Needleman-Wunsch gem5 Benchmark

A gem5 microarchitecture simulation project for the Needleman-Wunsch sequence alignment algorithm.

## Prerequisites

- [gem5](https://www.gem5.org/) simulator
- GCC (for compiling the C benchmark)

## Usage

### 1. Compile the benchmark

```bash
cd /workspace/demo/programs
gcc -o nw_bench_x86 nw_bench.c
```

On Windows, the output will be `nw_bench_x86.exe`. Update `binary_path` in `run_nw_config.json` if needed. After compiling, either copy `nw_bench_x86` to the directory containing `run_nw.py`, or set `binary_path` to the correct path (e.g. `demo/programs/nw_bench_x86` when running from project root).

### 2. Configure parameters

Edit `run_nw_config.json` in the same directory as `run_nw.py` (i.e. `demo/x86/board_configurations/`). All parameters are optional (defaults shown):

```json
{
  "sequence_length": 512,
  "block_size": 1,
  "binary_path": "./nw_bench_x86",
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
| `sequence_length` | Length of each sequence (number of bases). Both seq1 and seq2 have this length. DP matrix is (N+1)×(N+1). | 1–65536 |
| `block_size` | Tile size for cache blocking. 1 = row-by-row (cache-unfriendly). 8–64 = cache-friendly. | 1 to sequence_length |
| `binary_path` | Path to nw_bench_x86 executable (relative to cwd when gem5 runs). | e.g. `./nw_bench_x86` or `demo/programs/nw_bench_x86` |
| `clk_freq` | CPU clock frequency. | 1GHz, 2GHz, 3GHz |
| `l1d_size` | L1 data cache size. | 4kB, 8kB, 32kB |
| `l1i_size` | L1 instruction cache size. | 4kB, 8kB, 32kB |
| `l2_size` | L2 cache size (shared). | 16kB, 64kB, 256kB |
| `memory_size` | Main memory size. | 1GB, 4GB, 8GB |
| `cpu_width` | Pipeline width (fetch/decode/issue). | 1–16, typical 4–8 |
| `rob_size` | Reorder buffer entries. Larger = more ILP. | 32–512 |
| `num_int_regs` | Physical integer registers. | 64–512 |
| `num_fp_regs` | Physical float registers. | 64–512 |
| `trace_file` | Output filename for instruction trace CSV. | — |
| `trace_fetch` | Record fetch events in trace. | true / false |
| `trace_mem` | Record memory accesses in trace. | true / false |
| `trace_start_after_inst` | Start tracing after N instructions. 0 = from start. | 0+ |
| `trace_stop_after_inst` | Stop tracing after N instructions. 0 = no limit. | 0+ |
| `match_score` | NW scoring: match reward. | -10 to 10 |
| `mismatch_penalty` | NW scoring: mismatch penalty. | -10 to 0 |
| `gap_penalty` | NW scoring: gap penalty. | -10 to 0 |
| `random_seed` | RNG seed for sequence generation. Same seed = reproducible. | 0–2³¹-1 |

### 3. Run the simulation

Ensure `binary_path` in `run_nw_config.json` correctly points to `nw_bench_x86` (see step 1), then:

```bash
/path/to/gem5.opt /path/to/run_nw.py [run_nw_config.json]
```

**Example (adjust paths for your environment):**

```bash
# Default: uses run_nw_config.json next to run_nw.py
/workspace/gem5_base/build/X86/gem5.opt /workspace/demo/x86/board_configurations/run_nw.py

# Custom config file
/workspace/gem5_base/build/X86/gem5.opt /workspace/demo/x86/board_configurations/run_nw.py /workspace/demo/x86/board_configurations/run_nw_config.json
```

### 4. Check results

After the simulation completes, check the output directory (printed at the end) for:

- `stats.txt` / `stats.json` — performance statistics
- `inst_trace.csv` — instruction execution trace

### 5. Compute metrics

To compute CPI, MPKI, branch misprediction rate, and stall indicators from stats:

```bash
python compute_metrics.py [m5out]
```

Default path is `m5out`. Output includes: CPI, MPKI (L1I/L1D/L2), branch mispred rate, 0-fetch cycles fraction, idle fraction, cache blocked fraction.

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

**Note:** CPI < 1 is normal for out-of-order superscalar CPUs (multiple instructions per cycle). IPC = 1/CPI.
