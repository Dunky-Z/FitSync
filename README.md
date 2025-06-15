# Strava-Garmin 双向同步工具

一个功能强大的多平台运动数据同步工具，支持 Strava、Garmin Connect 和 IGPSport 之间的数据同步。

## 🚀 主要功能

### 1. 单向上传（原有功能）
- 从 Strava 下载活动文件
- 上传到 Garmin Connect 和 IGPSport
- 支持多种文件格式（FIT、TCX、GPX）

### 2. 双向同步（新功能）
- **Strava ↔ Garmin Connect** 双向自动同步
- 智能活动匹配，避免重复同步
- 增量同步，只处理新活动
- API限制管理，避免超出调用限制
- 本地缓存，提高同步效率

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

### 单向上传（兼容原功能）
```bash
cd src
python main_refactored.py
```

### 双向同步（新功能）
```bash
cd src
python main_sync.py
```

#### 交互模式
运行后选择操作：
- **开始双向同步**: 执行 Strava ↔ Garmin 同步
- **配置同步规则**: 设置同步方向和规则
- **查看同步状态**: 显示同步统计和状态
- **清理缓存文件**: 清理过期的活动文件缓存

#### 自动模式
```bash
# 自动执行双向同步
python main_sync.py --auto

# 只同步 Strava -> Garmin
python main_sync.py --auto --directions strava_to_garmin

# 指定批处理大小
python main_sync.py --auto --batch-size 20

# 启用调试模式
python main_sync.py --debug
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
│   ├── main_sync.py              # 双向同步主程序
│   ├── main_refactored.py        # 单向上传主程序
│   ├── bidirectional_sync.py     # 双向同步核心逻辑
│   ├── sync_manager.py           # 同步状态管理
│   ├── activity_matcher.py       # 活动匹配算法
│   ├── garmin_sync_client.py     # Garmin同步客户端
│   ├── strava_client.py          # Strava客户端（扩展）
│   ├── config_manager.py         # 配置管理
│   ├── ui_utils.py              # 用户界面工具
│   └── ...
├── .app_config.json         # 统一配置文件
├── requirements.txt         # Python依赖
└── README.md               # 项目说明
```

## 🔐 配置文件说明

`.app_config.json`包含所有平台的配置：

```json
{
  "strava": {
    "client_id": "your_client_id",
    "client_secret": "your_client_secret", 
    "refresh_token": "your_refresh_token",
    "access_token": "",
    "cookie": ""
  },
  "garmin": {
    "username": "your_username",
    "password": "your_password",
    "auth_domain": "GLOBAL"
  },
  "igpsport": {
    "username": "",
    "password": "",
    "login_token": ""
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