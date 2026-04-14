from __future__ import annotations

import logging
from typing import Optional


def setup_logging(*, level: str = "INFO") -> None:
    if logging.getLogger().handlers:
        logging.getLogger().setLevel(level.upper())
        return

    try:
        from rich.logging import RichHandler

        handlers: list[logging.Handler] = [
            RichHandler(
                rich_tracebacks=True,
                show_time=True,
                show_level=True,
                show_path=False,
                markup=False,
            )
        ]
        logging.basicConfig(
            level=level.upper(),
            format="%(name)s: %(message)s",
            datefmt="[%X]",
            handlers=handlers,
        )
    except Exception:
        logging.basicConfig(
            level=level.upper(),
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )

