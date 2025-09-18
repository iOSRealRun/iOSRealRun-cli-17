import asyncio
import multiprocessing

from driver import connect

async def _tunnel_proc_async(queue: multiprocessing.Queue):
    server_rsd = await connect.get_serverrsd()
    await connect.tunnel(server_rsd, queue)

def tunnel_proc(queue: multiprocessing.Queue):
    asyncio.run(_tunnel_proc_async(queue))

def tunnel():
    # start the tunnel in another process
    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=tunnel_proc, args=(queue,))
    process.start()

    # get the address and port of the tunnel
    address, port = queue.get()

    return process, address, port