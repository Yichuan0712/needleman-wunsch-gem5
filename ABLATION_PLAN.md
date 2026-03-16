# Ablation Study Plan

**Project:** Bioinformatics Sequence Alignment Across CPU Microarchitectures

**Hypothesis:** NW performance is mainly limited by cache/memory stalls and branch prediction rather than raw compute width. Improving the memory hierarchy will help more than simply widening the O3 core.

**Constraint:** All ablations are implemented by editing `run_nw_config.json` only. No code changes.

**Evaluation:** Compare CPI vs baseline; track L1I/L1D/L2 MPKI and branch misprediction rate; use stall proxies (0-fetch cycles, idle cycles, cache blocked cycles) to explain CPI changes.

---

## JSON Parameters (All Supported)

| Parameter | Description |
|-----------|-------------|
| sequence_length | 1–256 |
| block_size | 1 to sequence_length |
| binary_path | Path to nw_bench_x86 or nw_bench_arm |
| l1d_size, l1i_size, l2_size | Cache sizes |
| memory_size | Main memory |
| cpu_width | Pipeline width |
| rob_size | ROB entries |
| num_int_regs, num_fp_regs | Physical registers |
| clk_freq | CPU frequency |
| match_score, mismatch_penalty, gap_penalty | NW scoring |
| random_seed | RNG seed for sequence generation |

---

## Baseline Configuration

```json
{
  "sequence_length": 128,
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

---

## Ablation 1: Pipeline Width

**Goal:** Test whether NW benefits from a wider core. Hypothesis: limited benefit if memory is the bottleneck.

| Run | cpu_width |
|-----|-----------|
| 1.1 | 2 |
| 1.2 | 4 |
| 1.3 | 8 | *(baseline)*
| 1.4 | 12 |
| 1.5 | 16 |

---

## Ablation 2: Reorder Buffer (ROB) Size

**Goal:** Test whether more in-flight instructions help more than width.

| Run | rob_size |
|-----|----------|
| 2.1 | 64 |
| 2.2 | 128 |
| 2.3 | 192 | *(baseline)*
| 2.4 | 256 |
| 2.5 | 384 |
| 2.6 | 512 |

---

## Ablation 3: Physical Register File

**Goal:** Assess impact of register pressure on rename/issue stalls.

| Run | num_int_regs | num_fp_regs |
|-----|--------------|-------------|
| 3.1 | 128 | 128 |
| 3.2 | 256 | 256 | *(baseline)*
| 3.3 | 384 | 384 |
| 3.4 | 512 | 512 |

---

## Ablation 4: Cache Size

**Goal:** Measure sensitivity to cache capacity. Expect large CPI improvement if memory is the bottleneck.

| Run | l1d_size | l1i_size | l2_size |
|-----|----------|----------|---------|
| 4.1 | 2kB | 2kB | 8kB |
| 4.2 | 4kB | 4kB | 16kB | *(baseline)*
| 4.3 | 8kB | 8kB | 32kB |
| 4.4 | 16kB | 16kB | 64kB |
| 4.5 | 32kB | 32kB | 128kB |

---

## Ablation 5: Block Size (Cache Blocking)

**Goal:** Compare row-by-row (cache-unfriendly) vs tiled (cache-friendly) access.

| Run | block_size |
|-----|------------|
| 5.1 | 1 | *(baseline)*
| 5.2 | 4 |
| 5.3 | 8 |
| 5.4 | 16 |
| 5.5 | 32 |
| 5.6 | 64 |

---

## Ablation 6: Sequence Length (Workload Scale)

**Goal:** Study scaling behavior as problem size increases.

| Run | sequence_length |
|-----|-----------------|
| 6.1 | 32 |
| 6.2 | 64 |
| 6.3 | 128 | *(baseline)*
| 6.4 | 192 |
| 6.5 | 256 |

---

## Metrics to Collect

| Metric | Purpose |
|--------|---------|
| CPI | Primary performance; compare vs baseline |
| MPKI (L1I) | Instruction fetch bottleneck |
| MPKI (L1D) | Data access bottleneck |
| MPKI (L2) | Last-level cache pressure |
| Branch mispred rate | Control-flow bottleneck |
| 0-fetch cycles fraction | Front-end starvation |
| Idle fraction | Back-end starvation |
| Cache blocked fraction | Memory system blocking |
