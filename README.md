# SSH LICCO

<p align="center">
  <strong>SSH Model Context Protocol Server - 为AI模型提供SSH功能</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/ssh-licco/">
    <img src="https://img.shields.io/pypi/v/ssh-licco.svg" alt="PyPI Version">
  </a>
  <a href="https://pypi.org/project/ssh-licco/">
    <img src="https://img.shields.io/pypi/pyversions/ssh-licco.svg" alt="Python Versions">
  </a>
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/pypi/l/ssh-licco.svg" alt="License">
  </a>
</p>

## 概述

SSH LICCO 是一个基于 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 的服务器实现，旨在为AI模型和应用程序提供完整的SSH连接功能。

许多主流AI模型本身不支持SSH协议，这限制了它们与远程服务器交互的能力。SSH LICCO 填补了这一空白，让AI能够：

- 连接到远程SSH服务器
- 执行命令并获取输出
- 管理多个并发SSH会话
- 生成和管理SSH密钥
- 进行文件传输（SFTP）

## 系统要求

- Python 3.10+
- Linux/macOS/Windows

## 安装

### 使用 pip 安装

```bash
pip install ssh-licco
```

### 从源码安装

```bash
git clone https://github.com/Echoqili/ssh-licco.git
cd ssh-licco
pip install -e .
```

## 快速开始

### 1. 基本使用

安装完成后，可以通过以下命令启动SSH MCP服务器：

```bash
ssh-licco
```

### 2. 在 Trae 中使用

在 Trae 的设置中添加 MCP 服务器：

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco"
    }
  }
}
```

### 3. 在 Claude Desktop 中使用

```json
{
  "mcpServers": {
    "ssh": {
      "command": "ssh-licco"
    }
  }
}
```

## 工具列表

| 工具名称 | 功能描述 |
|---------|---------|
| `ssh_config` | 配置SSH连接信息（保存到本地） |
| `ssh_login` | 使用保存的配置登录SSH服务器 |
| `ssh_connect` | 直接连接SSH服务器（完整参数） |
| `ssh_execute` | 在SSH会话中执行命令 |
| `ssh_disconnect` | 关闭SSH会话 |
| `ssh_list_sessions` | 列出所有活跃会话 |
| `ssh_generate_key` | 生成SSH密钥对 |
| `ssh_file_transfer` | SFTP文件传输（上传统送、下载、列表） |

## 使用示例

### 配置并登录

```json
// 1. 配置SSH服务器（只需一次）
{
  "host": "your-server-ip",
  "username": "root",
  "password": "your-password"
}

// 2. 登录并执行命令
{
  "command": "ls -la /home"
}
```

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 支持

如遇问题，请提交 [Issue](https://github.com/Echoqili/ssh-licco/issues)。
