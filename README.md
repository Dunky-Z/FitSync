# Strava to TrainingPeaks 多平台同步工具

一个功能强大的工具，可以从Strava下载活动并同步到多个训练平台，包括IGPSport和Garmin Connect。

## 🚀 主要功能

- **多数据源支持**：
  - 从Strava API自动获取最新活动
  - 手动输入活动ID下载
  - 支持本地文件上传

- **多平台同步**：
  - **IGPSport**：中国本土运动平台
  - **Garmin Connect**：全球领先的运动数据平台
  - 可同时上传到多个平台

- **智能文件处理**：
  - 自动检测现有文件，避免重复下载
  - 支持FIT、TCX、GPX等多种格式
  - 智能文件命名（活动名+ID）

- **用户友好**：
  - 交互式命令行界面
  - 凭据安全保存
  - 详细的调试信息

## 📦 安装依赖

```bash
pip install -r requirements.txt
```

### 额外依赖说明

- **Garmin Connect功能**需要`garth`库：
  ```bash
  pip install garth
  ```

## 🔧 配置

### Strava API配置

1. 访问 [Strava API设置](https://www.strava.com/settings/api)
2. 创建应用程序获取Client ID和Client Secret
3. 使用OAuth流程获取Refresh Token
4. 配置会自动保存到`.app_config.json`

详细步骤请参考：[STRAVA_API_SETUP.md](STRAVA_API_SETUP.md)

### 平台账户

- **IGPSport**：需要IGPSport账户（支持中国用户）
- **Garmin Connect**：需要Garmin Connect账户
  - 支持全球版(garmin.com)和中国版(garmin.cn)

## 🎯 使用方法

### 基本使用

```bash
cd src
python main.py
```

### 调试模式

```bash
cd src
python main.py --debug
```

### 测试Garmin功能

```bash
cd src
python test_garmin_upload.py
```

## 📋 使用流程

1. **选择数据源**：
   - Strava API自动获取 (推荐)
   - 手动输入活动ID
   - 提供本地文件路径

2. **选择活动**：
   - 从最新活动列表中选择
   - 自动显示活动详情（名称、类型、日期、距离）

3. **选择上传平台**：
   - IGPSport
   - Garmin Connect
   - 可多选同时上传

4. **输入凭据**：
   - 首次使用需要输入各平台登录信息
   - 凭据会安全保存供下次使用

5. **自动处理**：
   - 文件验证
   - 平台上传
   - 结果摘要

## 🔍 支持的文件格式

- **FIT**：原始设备数据格式（推荐）
- **TCX**：Training Center XML格式
- **GPX**：GPS Exchange格式

## 📁 项目结构

```
├── src/
│   ├── main.py              # 主程序
│   ├── garmin_client.py     # Garmin Connect客户端
│   ├── garmin_url_dict.py   # Garmin API配置
│   └── test_garmin_upload.py # Garmin功能测试
├── .app_config.json         # 统一配置文件
├── requirements.txt         # Python依赖
└── README.md               # 项目说明
```

## 🔐 配置文件说明

`.app_config.json`包含所有平台的配置：

```json
{
  "strava": {
    "client_id": "你的Strava应用ID",
    "client_secret": "你的Strava应用密钥",
    "refresh_token": "你的Strava刷新令牌",
    "access_token": "自动生成的访问令牌",
    "cookie": "用于下载的Strava Cookie"
  },
  "igpsport": {
    "login_token": "IGPSport登录令牌",
    "username": "IGPSport用户名",
    "password": "IGPSport密码"
  },
  "garmin": {
    "username": "Garmin Connect用户名",
    "password": "Garmin Connect密码",
    "auth_domain": "GLOBAL或CN",
    "session_cookies": "会话Cookie",
    "oauth_token": "OAuth令牌",
    "oauth_token_secret": "OAuth密钥"
  },
  "general": {
    "debug_mode": false,
    "auto_save_credentials": true
  }
}
```

## 🚨 常见问题

### Strava相关
- **API配置问题**：确保正确配置Client ID、Secret和Refresh Token
- **下载失败**：检查Cookie是否有效，或重新获取

### Garmin Connect相关
- **依赖缺失**：运行`pip install garth`安装所需库
- **登录失败**：检查用户名密码，确认选择了正确的服务器区域
- **重复活动**：Garmin会自动检测重复活动并拒绝

### IGPSport相关
- **登录问题**：确保使用有效的IGPSport账户
- **上传失败**：检查网络连接和文件格式

## 🔄 更新日志

- **v2.0**：新增Garmin Connect支持，多平台同步
- **v1.5**：统一配置文件，改进用户体验
- **v1.0**：基础Strava到IGPSport同步功能

## 📄 许可证

[MIT License](LICENSE)

## 🤝 贡献

欢迎提交Issues和Pull Requests！

## 📞 支持

如果遇到问题，请：
1. 查看常见问题部分
2. 使用`--debug`模式获取详细信息
3. 提交Issue并附带错误日志


需要不挂梯子使用Connect登录，会自动弹出更新手机号