import linecache
import logging
import os
import sys
import tracemalloc
from functools import wraps
from logging.handlers import RotatingFileHandler
from threading import Lock
from .otsconfig import config

log_formatter = logging.Formatter(
    '[%(asctime)s :: %(name)s :: %(pathname)s -> %(lineno)s:%(funcName)20s() :: %(levelname)s] -> %(message)s'
)
log_handler = RotatingFileHandler(config.get("_log_file"),
                                  mode='a',
                                  maxBytes=(5 * 1024 * 1024),
                                  backupCount=2,
                                  encoding='utf-8',
                                  delay=0)
stdout_handler = logging.StreamHandler(sys.stdout)
log_handler.setFormatter(log_formatter)
stdout_handler.setFormatter(log_formatter)

account_pool = []
temp_download_path = []
parsing = {}
pending = {}
download_queue = {}
parsing_lock = Lock()
pending_lock = Lock()
download_queue_lock = Lock()

# Worker management
worker_threads = []
worker_threads_lock = Lock()
worker_restart_callback = None  # Function to call to restart workers
consecutive_failures = 0
consecutive_failures_lock = Lock()

init_tray = False


def set_init_tray(value):
    global init_tray
    init_tray = value


def get_init_tray():
    return init_tray


loglevel = int(os.environ.get("LOG_LEVEL", 20))


def get_logger(name):
    logger = logging.getLogger(name)
    logger.addHandler(log_handler)
    logger.addHandler(stdout_handler)
    logger.setLevel(loglevel)
    return logger


logger_ = get_logger("runtimedata")


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger_.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_exception

def log_function_memory(wrap_func):
    tracemalloc.start()
    top_limit = 10
    def display_top(snapshot, snapshot_log_prefix, key_type='lineno'):
        snapshot = snapshot.filter_traces((
            tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
            tracemalloc.Filter(False, "<unknown>"),
        ))
        top_stats = snapshot.statistics(key_type)

        logger_.debug(f"{snapshot_log_prefix} Top {top_limit} lines")
        for index, stat in enumerate(top_stats[:top_limit], 1):
            frame = stat.traceback[0]
            logger_.debug("#%s: %s:%s: %.1f KiB"
                % (index, frame.filename, frame.lineno, stat.size / 1024))
            line = linecache.getline(frame.filename, frame.lineno).strip()
            if line:
                logger_.debug(f"{snapshot_log_prefix} -- {line}"  )

        other = top_stats[top_limit:]
        if other:
            size = sum(stat.size for stat in other)
            logger_.debug("%s other: %.1f KiB" % (len(other), size / 1024))
        total = sum(stat.size for stat in top_stats)
        logger_.debug("Total allocated size: %.1f KiB" % (total / 1024))

    @wraps(wrap_func)
    def snapshot_function_call(*args, **kwargs):
        prefix = f"{wrap_func.__name__}: "
        before_func = tracemalloc.take_snapshot()
        logger_.debug(f"Snapshotting before {wrap_func.__name__} call")
        ret_val = wrap_func(*args, **kwargs)
        display_top(before_func, prefix)
        logger_.debug(f"Snapshotting after {wrap_func.__name__} call")
        after_func = tracemalloc.take_snapshot()
        display_top(after_func, prefix)
        top_stats = after_func.compare_to(before_func, 'lineno')
        logger_.debug(f"{prefix} Top {top_limit} differences")
        for stat in top_stats[:10]:
            logger_.debug(f"{prefix}{stat}")
        return ret_val
    return snapshot_function_call


def register_worker(worker):
    """Register a worker thread for management"""
    with worker_threads_lock:
        worker_threads.append(worker)
        logger_.debug(f"Registered worker: {worker.__class__.__name__}, total workers: {len(worker_threads)}")


def kill_all_workers():
    """Kill all registered worker threads"""
    global worker_threads
    logger_.warning("Killing all worker threads...")

    with worker_threads_lock:
        for worker in worker_threads:
            try:
                logger_.info(f"Stopping worker: {worker.__class__.__name__}")
                worker.stop()
            except Exception as e:
                logger_.error(f"Error stopping worker {worker.__class__.__name__}: {e}")

        # Clear the list
        worker_threads = []
        logger_.info("All workers stopped and cleared")


def increment_failure_count():
    """Increment consecutive failure counter and trigger restart if threshold reached"""
    global consecutive_failures, worker_restart_callback

    with consecutive_failures_lock:
        consecutive_failures += 1
        current_count = consecutive_failures

    # Threshold for triggering worker restart
    FAILURE_THRESHOLD = 5

    if current_count >= FAILURE_THRESHOLD:
        logger_.error(f"Consecutive failures reached {current_count}, triggering worker restart...")

        # Reset counter before restart to avoid repeated restarts
        reset_failure_count()

        # Trigger restart if callback is set
        if worker_restart_callback:
            try:
                worker_restart_callback()
            except Exception as e:
                logger_.error(f"Error during worker restart: {e}")
        else:
            logger_.error("No worker restart callback registered!")
    else:
        logger_.warning(f"Download failure detected ({current_count}/{FAILURE_THRESHOLD})")


def reset_failure_count():
    """Reset consecutive failure counter (called on successful download)"""
    global consecutive_failures

    with consecutive_failures_lock:
        if consecutive_failures > 0:
            logger_.debug(f"Resetting failure count from {consecutive_failures} to 0")
        consecutive_failures = 0


def set_worker_restart_callback(callback):
    """Set the callback function to restart workers"""
    global worker_restart_callback
    worker_restart_callback = callback
    logger_.info(f"Worker restart callback registered: {callback.__name__}")
