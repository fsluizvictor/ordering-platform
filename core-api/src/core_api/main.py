from __future__ import annotations

from shared.logging_setup import setup_logging

from core_api.adapters.inbound.http.app import create_app
from core_api.config.settings import SERVICE_NAME, log_level_setting, port

setup_logging(SERVICE_NAME, log_level_setting())
app = create_app()


def main() -> None:
    app.run(host="0.0.0.0", port=port(), debug=False)


if __name__ == "__main__":
    main()
