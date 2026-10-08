import sys
import ctypes
import os

from driver import connect

# 连接方式按系统版本分流:
#   iOS 17+  -> tun 隧道 + RSD (需要 root)
#   iOS 14~16-> 免隧道, 挂 DeveloperDiskImage 后直连 lockdown DVT
MIN_IOS_MAJOR = 14
# 开发者模式是 iOS 16 才有的设置, 15 及以下查不到属正常, 跳过
DEVELOPER_MODE_SINCE_MAJOR = 16


def init():
    # check if root on mac or Administrator on windows
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

    # get lockdown client
    lockdown = connect.get_usbmux_lockdownclient()

    # check version
    version = connect.get_version(lockdown)
    print(f"Your system version is {version}")
    try:
        major = int(str(version).split(".")[0])
    except ValueError:
        major = 0
    if major < MIN_IOS_MAJOR:
        print(f"仅支持 {MIN_IOS_MAJOR} 及以上版本")
        sys.exit(1)

    # check developer mode status (仅 iOS 16 及以上有该设置)
    if major >= DEVELOPER_MODE_SINCE_MAJOR:
        developer_mode_status = connect.get_developer_mode_status(lockdown)
        if not developer_mode_status:
            connect.reveal_developer_mode(lockdown)
            print("您未开启开发者模式，请打开设备的 设置-隐私与安全性-开发者模式 来开启，开启后需要重启并输入密码，完成后再次运行此程序")
            sys.exit(1)
    else:
        print("iOS <16 无需开发者模式, 跳过检查")

    return lockdown, version, major
