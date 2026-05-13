import asyncio
import multiprocessing
from queue import Empty

from driver import connect


def tunnel_proc(queue: multiprocessing.Queue):
    try:
        asyncio.run(connect.create_tunnel_from_lockdown(queue))
    except Exception as exc:
        queue.put({
            "status": "error",
            "error": repr(exc),
        })


def tunnel():
    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=tunnel_proc, args=(queue,))
    process.start()

    while True:
        try:
            result = queue.get(timeout=1)
        except Empty:
            if not process.is_alive():
                raise RuntimeError("Tunnel process exited before returning connection info")
            continue

        if result.get("status") == "ok":
            return process, result["address"], result["port"]

        process.join(timeout=1)
        raise RuntimeError(f"Tunnel setup failed: {result.get('error', 'unknown error')}")
