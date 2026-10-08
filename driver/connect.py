import logging
import multiprocessing

from pymobiledevice3.lockdown import create_using_usbmux, LockdownClient

from pymobiledevice3.cli.remote import install_driver_if_required
from pymobiledevice3.cli.remote import select_device, RemoteServiceDiscoveryService
from pymobiledevice3.cli.remote import start_tunnel
from pymobiledevice3.cli.remote import verify_tunnel_imports

from pymobiledevice3.services.amfi import AmfiService

from pymobiledevice3.exceptions import NoDeviceConnectedError

def get_usbmux_lockdownclient():
    while True:
        try:
            lockdown = create_using_usbmux()
        except NoDeviceConnectedError:
            print("请连接设备后按回车...")
            input()
        else:
            break
    while True:
        lockdown = create_using_usbmux()
        if lockdown.all_values.get("PasswordProtected"):
            print("请解锁设备后按回车...")
            input()
        else:
            break
    return create_using_usbmux()

def get_version(lockdown: LockdownClient):
    return lockdown.all_values.get("ProductVersion")

def get_developer_mode_status(lockdown: LockdownClient):
    return lockdown.developer_mode_status

def reveal_developer_mode(lockdown: LockdownClient):
    AmfiService(lockdown).create_amfi_show_override_path_file()

def enable_developer_mode(lockdown: LockdownClient):
    AmfiService(lockdown).enable_developer_mode()

def get_serverrsd():
    install_driver_if_required()
    if not verify_tunnel_imports():
        exit(1)
    return select_device(None)


async def tunnel(rsd: RemoteServiceDiscoveryService, queue: multiprocessing.Queue):
    async with start_tunnel(rsd, None) as tunnel_result:
        queue.put((tunnel_result.address, tunnel_result.port))
        await tunnel_result.client.wait_closed()


# ---------------------------------------------------------------------------
# iOS 14~16 支持: 免隧道, 挂 DeveloperDiskImage 后直连 lockdown DVT
# (iOS 17+ 走上面的 RSD tun 隧道, 不需要开发者镜像)
# ---------------------------------------------------------------------------

DDI_REPO = "doronz88/DeveloperDiskImage"
DDI_REF = "main"
DDI_IMAGE_NAME = "DeveloperDiskImage.dmg"
DDI_SIGNATURE_NAME = "DeveloperDiskImage.dmg.signature"
# 官方源放最前, 后面是国内可达的 GitHub 加速镜像 (前缀代理). 镜像内容由设备端签名校验,
# 对不上会被拒绝挂载, 所以走第三方镜像不改变信任根.
DDI_MIRROR_TEMPLATES = (
    "https://raw.githubusercontent.com/{repo}/{ref}",
    "https://ghproxy.net/https://raw.githubusercontent.com/{repo}/{ref}",
    "https://gh-proxy.com/https://raw.githubusercontent.com/{repo}/{ref}",
)
DDI_TIMEOUT = 30
DDI_MIN_IMAGE_BYTES = 1024 * 1024


def _ddi_setting(name, env):
    import os
    import yaml
    from pathlib import Path
    val = os.environ.get(env)
    if val:
        return val.strip()
    try:
        with open(Path(__file__).resolve().parent.parent / "config.yaml") as f:
            cfg = yaml.safe_load(f) or {}
    except Exception:
        return ""
    got = cfg.get(name)
    return str(got).strip() if got not in (None, "") else ""


def _ddi_version(lockdown):
    ver = str(get_version(lockdown))
    parts = ver.split(".")
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
        return f"{parts[0]}.{parts[1]}"
    return ver


def _ddi_override_dir():
    from pathlib import Path
    val = _ddi_setting("ddi_dir", "ZXF_DDI_DIR")
    return Path(val).expanduser() if val else None


def _ddi_cache_dir(version):
    from pymobiledevice3.common import get_home_folder
    return get_home_folder() / "DeveloperDiskImages" / version


def _ddi_project_dir(version):
    from pathlib import Path
    return Path(__file__).resolve().parent.parent / ".ddi" / version


def _ddi_dirs(version):
    from pathlib import Path
    dirs = []
    override = _ddi_override_dir()
    if override is not None:
        dirs.append(override)
    dirs.append(_ddi_cache_dir(version))
    dirs.append(_ddi_project_dir(version))
    for root in (Path("/Applications/Xcode.app"), Path.home() / "Xcode.app"):
        dirs.append(root / "Contents" / "Developer" / "Platforms"
                    / "iPhoneOS.platform" / "DeviceSupport" / version)
    return dirs


def _ddi_local(version):
    for d in _ddi_dirs(version):
        image = d / DDI_IMAGE_NAME
        signature = d / DDI_SIGNATURE_NAME
        if image.is_file() and signature.is_file():
            return image, signature
    return None


def _ddi_save(version, image, signature):
    from pathlib import Path
    override = _ddi_override_dir()
    dests = [override] if override is not None else []
    dests += [_ddi_cache_dir(version), _ddi_project_dir(version)]
    for dest in dests:
        try:
            Path(dest).mkdir(parents=True, exist_ok=True)
            (Path(dest) / DDI_IMAGE_NAME).write_bytes(image)
            (Path(dest) / DDI_SIGNATURE_NAME).write_bytes(signature)
        except OSError as e:
            print(f"写镜像缓存失败 ({dest}: {e}), 换下一个位置")
            continue
        return Path(dest) / DDI_IMAGE_NAME, Path(dest) / DDI_SIGNATURE_NAME
    return None


def _ddi_download(version):
    import requests
    override = _ddi_setting("ddi_mirror", "ZXF_DDI_MIRROR")
    templates = ((override,) if override else ()) + DDI_MIRROR_TEMPLATES
    rel = f"DeveloperDiskImages/{version}"
    last_err = ""
    for tmpl in templates:
        base = tmpl.format(repo=DDI_REPO, ref=DDI_REF)
        try:
            img = requests.get(f"{base}/{rel}/{DDI_IMAGE_NAME}", timeout=DDI_TIMEOUT)
            sig = requests.get(f"{base}/{rel}/{DDI_SIGNATURE_NAME}", timeout=DDI_TIMEOUT)
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            continue
        if img.status_code == 404 or sig.status_code == 404:
            print(f"镜像仓库里没有 iOS {version} 的 DeveloperDiskImage")
            exit(1)
        if img.status_code != 200 or sig.status_code != 200:
            last_err = f"HTTP {img.status_code}/{sig.status_code}"
            continue
        if (len(img.content) < DDI_MIN_IMAGE_BYTES
                or img.content[:1024].lstrip().lower().startswith(b"<")):
            last_err = "镜像内容异常 (可能被镜像站返回了错误页)"
            continue
        saved = _ddi_save(version, img.content, sig.content)
        if saved is not None:
            print(f"开发者镜像已保存到 {saved[0].parent}")
            return saved
        last_err = "下载成功但没找到可写目录"
    print(f"下载 DeveloperDiskImage 失败 ({last_err})")
    print("保持联网; 或用 ZXF_DDI_DIR 指定本地镜像目录, "
          "ZXF_DDI_MIRROR 指定可用镜像站, 或设 HTTPS_PROXY 后重试.")
    exit(1)


def ensure_developer_image(lockdown):
    from pymobiledevice3.exceptions import (AlreadyMountedError,
                                            DeveloperModeIsNotEnabledError)
    from pymobiledevice3.services.mobile_image_mounter import DeveloperDiskImageMounter

    mounter = DeveloperDiskImageMounter(lockdown)
    try:
        if mounter.is_image_mounted(mounter.IMAGE_TYPE):
            print("开发者镜像已挂载")
            return
    except Exception:
        pass

    version = _ddi_version(lockdown)
    found = _ddi_local(version)
    if found is None:
        found = _ddi_download(version)
    image, signature = found
    try:
        mounter.mount(image, signature)
    except AlreadyMountedError:
        print("开发者镜像已挂载")
        return
    except DeveloperModeIsNotEnabledError:
        print("开发者镜像需要先开开发者模式, 请打开 设置-隐私与安全性-开发者模式 后重启再试")
        exit(1)
    except Exception as e:
        print(f"挂载开发者镜像失败 ({type(e).__name__}: {e}), "
              f"需要 iOS {version} 的镜像; 请解锁手机、重插线后重试")
        exit(1)
    print(f"开发者镜像已挂载 ({version})")
