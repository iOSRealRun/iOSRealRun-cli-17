import asyncio
import multiprocessing

from driver import connect

def tunnel_proc(queue: multiprocessing.Queue):
    asyncio.run(connect.tunnel(queue))


def tunnel():
    # start the tunnel in another process
    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=tunnel_proc, args=(queue,))
    process.start()
    
    # get the address and port of the tunnel
    address, port = queue.get()

    return process, address, port