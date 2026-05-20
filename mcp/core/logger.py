import logging
import os
import sys
from datetime import datetime


def get_log_dir():
    """
    Resolve a writable log directory whether running from source or
    as a PyInstaller-frozen executable.
    """
    if getattr(sys, "frozen", False):
        base_dir = os.path.join(os.path.dirname(sys.executable), "logs")
    else:
        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "logs")
        )

    os.makedirs(base_dir, exist_ok=True)
    return base_dir


def get_daily_logfile():
    """
    Return a log file path namespaced by today's date (MM-DD-YYYY.log).
    A new file is created automatically each day.
    """
    today = datetime.now().strftime("%m-%d-%Y")
    return os.path.join(get_log_dir(), f"{today}.log")


logging.basicConfig(
    filename=get_daily_logfile(),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)