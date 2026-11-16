import ctypes
import sys
import threading

CTRL_C_EVENT = 0
CTRL_BREAK_EVENT = 1
CTRL_CLOSE_EVENT = 2
CTRL_LOGOFF_EVENT = 5
CTRL_SHUTDOWN_EVENT = 6


def install_console_close_handler(on_close, cleanup_done: threading.Event, timeout: float = 4.0):
    """Handle console close/logoff/shutdown by waiting briefly for async cleanup.

    The callback runs on a Windows-created console control thread. It requests
    shutdown on the asyncio loop and waits until the main task has cleared the
    simulated location. Ctrl+C is intentionally left to Python's normal handler.
    """
    if sys.platform != "win32":
        return lambda: None

    from ctypes import wintypes

    handler_routine = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    def handler(event):
        if event in (CTRL_CLOSE_EVENT, CTRL_LOGOFF_EVENT, CTRL_SHUTDOWN_EVENT):
            on_close()
            cleanup_done.wait(timeout)
            return True
        return False

    callback = handler_routine(handler)
    if not kernel32.SetConsoleCtrlHandler(callback, True):
        raise ctypes.WinError(ctypes.get_last_error())

    def uninstall():
        kernel32.SetConsoleCtrlHandler(callback, False)

    return uninstall
