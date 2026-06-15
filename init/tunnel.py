import asyncio
import multiprocessing
import traceback

from driver import connect

def tunnel_proc(queue: multiprocessing.Queue):
    try:
        server_rsd = connect.get_serverrsd()
        asyncio.run(connect.tunnel(server_rsd, queue))
    except Exception:
        queue.put(("error", traceback.format_exc()))
        raise


def tunnel():
    # start the tunnel in another process
    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=tunnel_proc, args=(queue,))
    process.start()
    
    # get the address and port of the tunnel
    address, port = queue.get()
    if address == "error":
        process.join(timeout=1)
        raise RuntimeError(f"Failed to start tunnel:\n{port}")

    return process, address, port
