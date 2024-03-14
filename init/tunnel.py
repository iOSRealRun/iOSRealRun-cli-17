import asyncio
import multiprocessing
from pymobiledevice3.exceptions import NoDeviceConnectedError
from driver import connect
import sys
def tunnel_proc(queue: multiprocessing.Queue):
    try:
        server_rsd = connect.get_serverrsd()
    except NoDeviceConnectedError:
        print("设备未连接")
        sys.exit(1)
    asyncio.run(connect.tunnel(server_rsd, queue))


def tunnel():
    # start the tunnel in another process
    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=tunnel_proc, args=(queue,))
    process.start()
    
    # get the address and port of the tunnel
    address, port = queue.get()
    print(address, port)
    return process, address, port