# PDF worker: time and memory per file (#236, review round 1, item 2)

`linker_genie.pdfwork` opens each customer PDF in a process of its own. Its two limits,
`SECONDS` and `MEMORY_BYTES`, come from this measurement.

- **What**: every PDF of the live snapshot's uploads (`~/de-linker-data/20261018-1043/uploads`)
  up to the 16 MiB cap (`schema.MAX_PDF_BYTES`): 384 files, from one-page certificates to
  the 16 MiB multilingual quick-installation guides.
- **How**: one child per file, exactly as the service starts it
  (`python -I -m linker_genie.pdfwork 60 4 200`: page cap, rendered-page cap, text-page
  threshold), under `/usr/bin/time -l` for the wall clock and the peak resident memory.
  Script: `measure_pdf.py` in the session scratchpad (inline below).
- **Where**: this Mac (Apple silicon), 2026-10-18. The VPS has one CPU and 3.9 GB RAM
  (`nproc`, `free -m`, read on 2026-10-18).

| | Result |
|---|---|
| Files | 384, all answered with status 0 |
| Median wall clock (process start to answer) | 0.1 s |
| Slowest | 1.22 s (`GW_STS-125kW_Quick-Installation-Guide-Multilingual_V1.0.pdf`), 1.16 s, 1.15 s, 1.11 s, 0.95 s |
| Largest peak resident memory | 495 MiB (`GW_BAT-C-60-112kWh_Quick-Installation-Guide-POLY_V1.7.pdf`, 16.5 MB, four rendered pages), then 399, 267, 267, 241 MiB |

Limits chosen:

- `SECONDS = 15`: about twelve times the slowest file here, room for the VPS's single
  slower CPU; four rendered pages read side by side then take about 15 s more
  (`attachments.PAGE_TOKENS`), which keeps the turn inside the shell's 60 s.
- `MEMORY_BYTES = 2 GiB` (`RLIMIT_AS`, enforced on Linux only): about four times the
  largest peak, and half the VPS's memory, so a hostile file fails alone.

```python
for f in sorted(U.rglob("*.pdf")):            # U = snapshot uploads
    if f.stat().st_size > 16 * 1024 * 1024:
        continue
    d = subprocess.run(["/usr/bin/time", "-l", *pdfwork.COMMAND, "60", "4", "200"],
                       input=f.read_bytes(), capture_output=True)
    # wall clock around the call; peak RSS from "maximum resident set size"
```
