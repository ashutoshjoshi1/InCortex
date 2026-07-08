"""InCortex API launcher (Phase 10).

Serves the brain over HTTP per Design_Doc §19. Requires the api extra:
pip install fastapi uvicorn (or: pip install -e ".[api]").

Run:  python scripts/run_api.py [config.toml]
Docs: interactive OpenAPI at http://<host>:<port>/docs
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from incortex.core import CortexConfig, load_config

DEFAULT_CONFIG_HINT = """\
No config file given - using defaults (in-memory storage, tools disabled).
Pass a TOML file to persist memory, e.g.:

  [memory]
  db_path = "data/incortex.db"

  [tools]
  enabled = true
"""


def main():
    try:
        import uvicorn
    except ImportError:
        print("The API needs the 'api' extra: pip install fastapi uvicorn")
        raise SystemExit(1)
    from incortex.api import create_app

    if len(sys.argv) > 1:
        config = load_config(sys.argv[1])
        print(f"Config: {sys.argv[1]}")
    else:
        config = CortexConfig()
        print(DEFAULT_CONFIG_HINT)
    app = create_app(config=config)
    print(f"InCortex API on http://{config.api.host}:{config.api.port} "
          f"(interactive docs at /docs)")
    uvicorn.run(app, host=config.api.host, port=config.api.port,
                log_level="warning")


if __name__ == "__main__":
    main()
