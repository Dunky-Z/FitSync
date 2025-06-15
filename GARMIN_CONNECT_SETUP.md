# Garmin Connect 设置指南

本指南将帮助您配置和使用Garmin Connect上传功能。

## 🚀 功能概述

- 从Strava下载的活动可以自动上传到Garmin Connect
- 支持全球版(garmin.com)和中国版(garmin.cn)
- 支持FIT、TCX、GPX多种格式
- 自动检测重复活动

## 📦 安装依赖

首先确保安装了所需的依赖：

```bash
pip install garth
```

或者安装完整的依赖：

```bash
pip install -r requirements.txt
```

## 🔧 配置步骤

### 1. 准备Garmin Connect账户

确保您有有效的Garmin Connect账户：

- **全球版用户**：注册于 https://connect.garmin.com
- **中国版用户**：注册于 https://connect.garmin.cn

### 2. 测试Garmin功能

在使用之前，可以运行测试脚本确认功能正常：

```bash
cd src
python test_garmin_upload.py
```

### 3. 配置登录信息

运行主程序时，系统会提示您输入：

- **用户名/邮箱**：您的Garmin Connect登录邮箱
- **密码**：您的Garmin Connect密码
- **服务器区域**：
  - 选择"全球版 (garmin.com)"：适用于大多数用户
  - 选择"中国版 (garmin.cn)"：适用于中国大陆用户

## 🎯 使用方法

### 基本使用流程

1. **启动程序**：
   ```bash
   cd src
   python main.py
   ```

2. **选择数据源**：
   - 从Strava API获取最新活动（推荐）
   - 手动输入活动ID

3. **选择上传平台**：
   - 在平台选择中勾选"Garmin Connect"
   - 可以同时选择多个平台

4. **首次配置**：
   - 输入Garmin Connect登录信息
   - 选择服务器区域
   - 选择是否保存凭据

5. **自动上传**：
   - 程序会自动处理文件并上传

### 调试模式

如果遇到问题，可以使用调试模式获取详细信息：

```bash
cd src
python main.py --debug
```

## 📁 支持的文件格式

- **FIT**：原始设备数据格式（推荐）
- **TCX**：Training Center XML格式
- **GPX**：GPS Exchange格式

## 🔐 凭据管理

### 自动保存

程序会将您的登录信息保存在`.app_config.json`文件中：

```json
{
  "garmin": {
    "username": "your@email.com",
    "password": "your_password",
    "auth_domain": "GLOBAL",
    "session_cookies": "",
    "oauth_token": "",
    "oauth_token_secret": ""
  }
}
```

### 安全性

- 配置文件已添加到`.gitignore`，不会被提交到版本控制
- 密码以明文存储在本地，请确保设备安全
- 如需要更高安全性，每次使用时可选择不保存凭据

## 🚨 常见问题

### 依赖问题

**问题**：导入garth库失败
```
ImportError: 需要安装garth库：pip install garth
```

**解决方案**：
```bash
pip install garth
```

### 登录问题

**问题**：用户名或密码错误
```
❌ Garmin Connect上传失败: 登录失败
```

**解决方案**：
1. 确认用户名和密码正确
2. 检查是否选择了正确的服务器区域
3. 尝试在浏览器中登录确认账户状态

### 服务器区域选择

- **中国大陆用户**：通常使用中国版(garmin.cn)
- **其他地区用户**：使用全球版(garmin.com)
- **不确定**：先尝试全球版，如果登录失败再尝试中国版

### 重复活动

**问题**：
```
⚠️ 活动已存在于Garmin Connect中（重复活动）
```

**说明**：这是正常现象，Garmin Connect会自动检测并拒绝重复的活动。

### 网络问题

**问题**：上传超时或连接失败

**解决方案**：
1. 检查网络连接
2. 确认防火墙设置
3. 如在中国大陆，确保可以访问相应的Garmin服务器

## 🔄 重置配置

如果需要重新配置：

1. **清除保存的凭据**（删除.app_config.json中的garmin部分）
2. **重新运行程序**，系统会提示重新输入登录信息

## 📊 上传状态说明

- **SUCCESS**：上传成功
- **DUPLICATE_ACTIVITY**：重复活动（已存在）
- **UPLOAD_EXCEPTION**：上传异常（网络问题、文件格式等）

## 🎯 最佳实践

1. **首次使用**：建议先用测试脚本验证功能
2. **网络环境**：确保稳定的网络连接
3. **文件格式**：FIT格式通常有最好的兼容性
4. **重复检查**：Garmin会自动处理重复活动，无需担心
5. **错误处理**：使用调试模式获取详细错误信息

## 📞 获取支持

如果遇到问题：

1. 查看本文档的常见问题部分
2. 运行测试脚本检查基本功能
3. 使用`--debug`模式获取详细日志
4. 在项目仓库中提交Issue并附带错误信息

---

🎉 享受从Strava到Garmin Connect的无缝数据同步！ 