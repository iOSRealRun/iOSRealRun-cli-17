# iOSRealRun-cli-17

通过电脑控制 iPhone 或 iPad 模拟位置移动。程序读取按行进顺序排列的闭合路线，
将 BD-09 坐标转换为 WGS-84，并按设定的平均速度持续下发位置。

## 环境要求

- Windows 或 macOS
- Python 3.9 或更高版本
- iOS 或 iPadOS 17 及以上
- Windows 建议安装 iTunes，以提供 Apple Mobile Device 驱动
- 设备已连接、解锁并信任电脑，且已开启开发者模式
- 同一时间只连接一台 iPhone 或 iPad

当前实现使用进程内 userspace RSD 隧道，通常不再需要 Windows 管理员权限或
macOS root 权限。

## 安装

在项目目录创建虚拟环境并安装依赖：

### Windows

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

之后可直接双击 `run.bat` 启动。也可以在终端运行：

```powershell
.\.venv\Scripts\python.exe main.py
```

### macOS

```shell
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python main.py
```

## 配置

编辑 `config.yaml`：

```yaml
v: 3.3
speedVariation: 0.05
routeConfig: "HNroute.txt"
libimobiledeviceDir: "libimobiledevice"
imageDir: "DeveloperDiskImage"
```

- `v`：每圈平均速度，单位米/秒。
- `speedVariation`：实时速度相对平均值的小幅波动比例。`0.05` 表示约 ±5%，
  设置为 `0` 可关闭波动。
- `routeConfig`：路线文件路径。

## 路线文件

路线使用百度 BD-09 坐标，由多个 JSON 对象以英文逗号连接，最外层不要加 `[]`：

```text
{"lng":"120.7335575","lat":"30.5280238"},{"lng":"120.7335665","lat":"30.5279500"}
```

坐标应按行进顺序排列，只绘制一圈；程序会自动从最后一个点返回起点并持续循环。

## 退出

优先按 `Ctrl+C`。正常退出时应看到：

```text
Location cleared
Bye
```

直接关闭控制台时程序会尝试自动清除模拟定位。如果使用任务管理器强制结束、
`taskkill /F`、断电或系统崩溃，进程内清理可能来不及执行；下次启动会先尝试
清除遗留定位，必要时请重启设备。
