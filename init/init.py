import sys

from driver import connect


async def init():
    """检查系统、设备版本和开发者模式，并返回已连接的 lockdown 客户端。"""
    if sys.platform not in ("win32", "darwin"):
        print("仅支持 macOS 和 Windows")
        sys.exit(1)

    lockdown = await connect.get_lockdown()

    version = connect.get_version(lockdown)
    print(f"Your system version is {version}")
    try:
        major_version = int(str(version).split(".")[0])
    except (TypeError, ValueError):
        print(f"无法解析系统版本：{version}")
        await lockdown.close()
        sys.exit(1)

    if major_version < 17:
        print("仅支持 iOS 17 及以上版本")
        await lockdown.close()
        sys.exit(1)

    developer_mode_status = await connect.get_developer_mode_status(lockdown)
    if not developer_mode_status:
        connect.reveal_developer_mode(lockdown)
        print("您未开启开发者模式，请打开设备的 设置-隐私与安全性-开发者模式 来开启，开启后需要重启并输入密码，完成后再次运行本程序")
        await lockdown.close()
        sys.exit(1)

    return lockdown
