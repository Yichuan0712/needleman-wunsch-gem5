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

On Windows, the output will be `nw_bench_x86.exe`. Update `binary_path` in `run_nw_config.json` if needed.

### 2. Configure parameters

Edit `run_nw_config.json` in the same directory as `run_nw.py`. All parameters are optional (defaults shown):

```json
{
  "matrix_size": 512,
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
| `matrix_size` | Sequence length (N). Matrix is (N+1)×(N+1). | 1–65536 |
| `block_size` | Tile size for cache blocking. 1 = row-by-row (cache-unfriendly). 8–64 = cache-friendly. | 1 to matrix_size |
| `binary_path` | Path to nw_bench_x86 executable. | Relative to cwd or absolute |
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

Ensure `nw_bench_x86` (or `nw_bench_x86.exe` on Windows) is in the same directory as `run_nw.py`, then:

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
