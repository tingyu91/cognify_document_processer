import json
import logging
import sys
import time
from app.config import settings


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            log["exc"] = self.formatException(record.exc_info)
        skip = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)
        for k, v in record.__dict__.items():
            if k not in skip and not k.startswith("_"):
                log[k] = v
        return json.dumps(log, ensure_ascii=False, default=str)


def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if settings.environment == "development" else logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    if settings.environment == "development":
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
                datefmt="%H:%M:%S",
            )
        )
    else:
        handler.setFormatter(_JsonFormatter())
    root.handlers.clear()
    root.addHandler(handler)
    for noisy in ["httpx", "httpcore", "anthropic", "boto3", "botocore", "urllib3"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
