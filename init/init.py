import sys
import ctypes
import os

from driver import connect


async def init():
    if sys.platform == "win32":
        if not ctypes.windll.shell32.IsUserAnAdmin():
            print("请以管理员权限运行")
            sys.exit(1)
    elif sys.platform == "darwin":
        if os.geteuid() != 0:
            print("请以root权限运行")
            sys.exit(1)
    else:
        print("仅支持macOS和Windows")
        sys.exit(1)

    lockdown = await connect.get_usbmux_lockdownclient()

    version = connect.get_version(lockdown)
    print(f"Your system version is {version}")
    major = int(version.split(".")[0]) if version else 0
    if major < 17:
        print("仅支持iOS 17及以上版本")
        sys.exit(1)

    developer_mode_status = await connect.get_developer_mode_status(lockdown)
    if not developer_mode_status:
        await connect.reveal_developer_mode(lockdown)
        print("您未开启开发者模式，请打开设备的 设置-隐私与安全性-开发者模式 来开启，开启后需要重启并输入密码，完成后再次运行此程序")
        sys.exit(1)
