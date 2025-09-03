import logging
import os
from typing import Optional


def configure_root_logger(level: Optional[str] = None) -> None:
  lvl = level or os.getenv("LOGLEVEL", "INFO").upper()
  try:
    logging.basicConfig(
      level=getattr(logging, lvl, logging.INFO),
      format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
  except Exception:
    pass


def get_logger(name: str) -> logging.Logger:
  if not logging.getLogger().handlers:
    configure_root_logger()
  return logging.getLogger(name) 