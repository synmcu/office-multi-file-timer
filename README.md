# office-multi-file-timer
office多文件批量精准控时器，支持关闭重置与手动延迟启动
# 🕒 Office Multi-File Precision Timer (Office多文件批量精准控时器)

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-windows-lightgrey.svg)](https://www.microsoft.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

一个专为大型会议、演讲、多文档汇报设计的 **Windows 桌面级 Office 文件自动控时工具**。支持 PPTX、DOCX、XLSX 等全系列 Office 文件的多路并行监控。通过高效的机器码编译，软件运行如飞、内存占用极低，且具备完美的防闪烁与数据持久化记忆功能。

---

## ✨ 核心特性

* 🚀 **多路智能监控**：无需手动绑定，后台自动检测系统中打开的 Word、PPT、Excel 窗口，并为其精准匹配独立的倒计时。
* ⏳ **开机手动延迟**：独创“缓冲期”功能。文件打开后，悬浮窗立刻就位，但倒计时会保持静止（默认10秒，可双击自定义），为演讲者预留完美的准备与调整时间。
* 🔄 **关闭即洗牌（不延续计时）**：中途关闭文件后再次打开，倒计时将自动恢复满格并重新触发延迟，绝不继承上次未完成的时间。
* 🎨 **100% 像素级真实预览**：底部配备高仿真预览面板。不仅可以调整字体大小和颜色，还能实时模拟悬浮窗在 Windows 桌面上的 **Alpha 不透明度（透明混合）** 效果。
* 🖱️ **经典就地双击修改**：抛弃繁琐的弹窗，双击列表中的任意一行，即可直接原地调整该文件的专属倒计时与延迟秒数。
* 🛡️ **托盘级防误关设计**：点击主界面关闭（X）后，程序会自动隐藏至系统右下角托盘默默守护，双击托盘图标即可随时唤醒，彻底防止误操作导致计时中断。
* 💾 **全配置记忆**：退出程序或重启电脑后，上次导入的文件列表、个性化皮肤色调、字号等全部自动复原，无需重复配置。

---

## 🛠️ 运行环境与依赖安装

本项目基于 Python 3 开发，核心依赖如下：

```bash
pip install pygetwindow pystray pillow pillow
