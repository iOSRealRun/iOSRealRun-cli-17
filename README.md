# iOSRealRun-cli-17

## 用法简介

### 前置条件

1. 系统是 `Linux`、`Windows` 或 `MacOS`
2. iPhone 或 iPad 系统版本大于等于 17
3. Windows 需要安装 iTunes
4. 已安装 `Python3` 和 `pip3`
5. **重要**: 只能有一台 iPhone 或 iPad 连接到电脑，否则会出问题

### 步骤

1. 克隆本项目到本地并进入项目目录
2. 安装依赖（建议使用虚拟环境）
    ```shell
    pip3 install -r requirements.txt
    ```
3. 修改配置和路线文件
4. 将设备连接到电脑，解锁；如果出现信任提示，请点击信任
5. 运行程序：
    ```shell
    python3 main.py
    ```
6. 结束请使用 `Ctrl + C`，程序会清除模拟定位并关闭连接

### Route 选择

默认使用 `HNroute.txt`。也可以指定保持相同格式的自定义路线文件：

```shell
python3 main.py --route ./routes/custom-route.txt
```

如果项目中存在可选的 `routes/` 目录，可以列出其中的路线文件：

```shell
python3 main.py --list-routes
```

### 连接诊断

`--diagnostic` 会完成设备、Developer Mode、tunnel、RSD 和 DVT 检查，但不启动路线模拟：

```shell
python3 main.py --diagnostic
```

`--dry-run` 也会建立连接，但使用单独的 dry-run 成功提示：

```shell
python3 main.py --udid <UDID> --dry-run
```

### iOS 17 tunnel 支持矩阵

| 主机 / iOS | 后端 | 权限 | 验证状态 |
| --- | --- | --- | --- |
| Linux / 17.4 及以上 | userspace / CoreDeviceProxy | 不需要 root | iOS 18.6.2 已完成实体设备验证 |
| Linux / 17.0–17.3.1 | `tunneld` / RSD | 需要 root 启动 daemon | 已通过自动化测试和 mock 验证；尚未完成实体设备验证 |
| macOS / 17.0–17.3.1 | native / remoted | 不需要 root | 已通过自动化测试和 mock 验证；尚未完成实体设备验证 |
| Windows / 17.0–17.3.1 | `tunneld` / RSD | 需要管理员权限启动 daemon | 已通过自动化测试和 mock 验证；尚未完成实体设备验证 |
| macOS 或 Windows / 17.4 及以上 | userspace / CoreDeviceProxy | 通常不需要 root 或管理员权限 | 已通过自动化测试和 mock 验证；尚未完成实体设备验证 |

Linux 或 Windows 上的 iOS 17.0–17.3.1 需要先在另一个终端启动 privileged `tunneld`：

```shell
sudo python3 -m pymobiledevice3 remote tunneld
python3 main.py --udid <UDID> --diagnostic
```

程序不会自行提权或启动 daemon。Linux/Windows 上如果 userspace 能力探测失败，会查询 `tunneld`；macOS 上则使用 pymobiledevice3 的 native/remoted 后端。诊断日志会报告最终选择的 backend。
