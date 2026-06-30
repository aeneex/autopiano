import os
import sys
import ctypes
import logging

logger = logging.getLogger("AutoPiano")
_winmm = None

def setup_logging():
    """Configure logging to both console and a file in logs/app.log."""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'app.log')
    
    # Set up root logger configuration
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] (%(filename)s:%(lineno)d): %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logger.info("Logging initialized. Writing logs to %s", log_file)

def set_high_precision_timer():
    """Enable 1ms timer resolution on Windows for precise sleep intervals."""
    global _winmm
    if sys.platform == 'win32':
        try:
            _winmm = ctypes.WinDLL('winmm')
            status = _winmm.timeBeginPeriod(1)
            if status == 0:
                logger.info("Windows high-resolution timer (1ms) enabled.")
            else:
                logger.warning("Failed to enable Windows high-resolution timer (Status code: %d).", status)
        except Exception as e:
            logger.warning("Failed to enable Windows high-resolution timer: %s", e)

def restore_timer_precision():
    """Restore default timer resolution on Windows."""
    global _winmm
    if sys.platform == 'win32' and _winmm is not None:
        try:
            status = _winmm.timeEndPeriod(1)
            if status == 0:
                logger.info("Windows high-resolution timer restored.")
            else:
                logger.warning("Failed to restore Windows high-resolution timer (Status code: %d).", status)
        except Exception as e:
            logger.warning("Failed to restore Windows timer resolution: %s", e)
