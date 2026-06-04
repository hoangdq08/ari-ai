from __future__ import annotations

import logging
import sys
from typing import Any


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("nong_tri_ai")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s request_id=%(request_id)s %(message)s")
    )
    logger.addHandler(handler)
    return logger


class RequestLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        extra = kwargs.setdefault("extra", {})
        extra.setdefault("request_id", self.extra.get("request_id", "-"))
        return msg, kwargs


def get_request_logger(request_id: str) -> RequestLoggerAdapter:
    return RequestLoggerAdapter(configure_logging(), {"request_id": request_id})
