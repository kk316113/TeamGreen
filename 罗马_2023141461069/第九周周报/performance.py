# performance.py
import time
import functools
import logging

logger = logging.getLogger("B3.performance")

def monitor_execution(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        logger.info(f"{func.__name__} executed in {duration:.3f}s")
        return result
    return wrapper