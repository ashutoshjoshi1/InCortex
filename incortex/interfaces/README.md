# `interfaces/` — User Interfaces

Front-ends through which humans talk to InCortex.

Modules (Design_Doc §20):

- `voice.py` — ✅ the voice conversation loop: listen → gate on hearing confidence → think → speak (launch with `python scripts/run_voice.py`)
- `cli.py` — the CLI currently lives in `scripts/run_cli.py`; it moves here when the API phase restructures entrypoints
- `web.py` — planned: web interface

**Status:** voice implemented in Phase 6. Plain-language walkthrough: [docs/understanding/phase_6_voice_system.md](../../docs/understanding/phase_6_voice_system.md).
