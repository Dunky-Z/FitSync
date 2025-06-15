# 配置说明

## 统一配置文件 (.app_config.json)

该项目现在使用统一的配置文件 `.app_config.json` 来管理所有配置项，支持多平台同步：

### 配置结构

```json
{
  "strava": {
    "client_id": "你的Strava应用ID",
    "client_secret": "你的Strava应用密钥",
    "refresh_token": "你的Strava刷新令牌",
    "access_token": "自动生成的访问令牌",
    "cookie": "用于下载的Strava Cookie（可选）"
  },
  "igpsport": {
    "login_token": "IGPSport登录令牌（自动保存）",
    "username": "IGPSport用户名（可选保存）",
    "password": "IGPSport密码（可选保存）"
  },
  "garmin": {
    "username": "Garmin Connect用户名（可选保存）",
    "password": "Garmin Connect密码（可选保存）",
    "session_cookies": "Garmin会话Cookie（自动保存）",
    "oauth_token": "OAuth令牌（保留扩展用）",
    "oauth_token_secret": "OAuth密钥（保留扩展用）"
  },
  "general": {
    "debug_mode": false,
    "auto_save_credentials": true
  }
}
```

### 支持的平台

1. **IGPSport** - 中国本土运动平台
2. **Garmin Connect** - 佳明国际版，用于详细的运动数据分析

### 主要功能

1. **多平台同步**：一次下载，可选择上传到多个平台
2. **统一配置管理**：所有平台配置集中在一个文件中
3. **自动迁移**：程序会自动从旧的配置文件迁移设置
4. **活动文件命名**：使用Strava活动名 + 活动ID 作为文件名
5. **凭据保存**：支持保存各平台登录凭据，避免重复输入
6. **会话保持**：自动保存登录会话，提高使用效率

### 活动文件命名规则

- **新格式**：`{活动名}_{活动ID}.{扩展名}`
  - 示例：`Morning_Run_12345678.fit`
- **旧格式**：`activity_{活动ID}.{扩展名}`（向后兼容）
  - 示例：`activity_12345678.fit`

### 使用流程

1. **选择数据源**：从Strava API获取或手动输入活动ID
2. **下载文件**：自动下载FIT/TCX/GPX格式文件
3. **选择平台**：可选择上传到IGPSport、Garmin Connect或两者
4. **自动上传**：程序会依次上传到选定的平台

### 优势

- **Garmin Connect数据分析**：利用Garmin强大的数据分析功能
- **数据备份**：多平台存储，确保数据安全
- **便于管理**：统一的配置和操作界面
- **自动化**：最小化手动操作，提高效率

### 注意事项

- 程序会自动清理活动名中的非法文件名字符（如 `<>:"/\|?*`）
- 活动名长度限制为100个字符
- 程序会检查Downloads文件夹中是否已存在相同活动的文件
- 支持从旧配置文件自动迁移设置
- FIT格式文件对Garmin Connect兼容性最好
- IGPSport支持多种格式（FIT/TCX/GPX）

### 命令行参数

```bash
python src/main.py --help           # 显示帮助信息
python src/main.py                  # 正常模式运行
python src/main.py --debug          # 调试模式，显示详细信息
``` 