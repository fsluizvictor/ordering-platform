from __future__ import annotations

from shared.logging_setup import setup_logging

from order_service.adapters.inbound.http.app import create_app
from order_service.config.settings import SERVICE_NAME, log_level, port

setup_logging(SERVICE_NAME, log_level())
app = create_app()


def main() -> None:
    app.run(host="0.0.0.0", port=port(), debug=False)


if __name__ == "__main__":
    main()
