# FitSync - 多平台运动数据同步工具

一个功能强大的运动数据同步工具，支持在Strava、Garmin Connect、OneDrive、IGPSport、Intervals.icu等平台之间进行双向数据同步。

## 主要特性

### 双向同步功能

- **多平台支持**：Strava、Garmin Connect、OneDrive、IGPSport、Intervals.icu
- **智能活动匹配**：基于时间、运动类型、距离、时长的多维度匹配算法
- **增量同步**：只同步新增活动，避免重复处理
- **API限制管理**：智能管理Strava API调用限制（每日180次，每15分钟90次）
- **历史迁移模式**：支持历史活动的批量迁移

| Source   \ Target | **Strava**    | **Garmin Global** | **Garmin CN** | **IGPSport** | **Intervals.icu** | **OneDrive** |
| ----------------- | ------------- | ----------------- | ------------- | ------------ | ----------------- | ------------ |
| **Strava**        | x             | 🔁 Bi-dir         | ❌           | ➡️ Single-dir | ❌               | ➡️ Single-dir|
| **Garmin Global** | 🔁 Bi-dir     | x                 | ❌           | ➡️ Single-dir | ❌               | ➡️ Single-dir|
| **Garmin CN**     | ❌            | ❌                | x            | ❌            | ❌               | ❌           |
| **IGPSport**      | ❌            | ❌                | ❌           | x             | ➡️ Single-dir    | ❌          |
| **Intervals.icu** | ❌            | ❌                | ❌           | ❌            | x                | ❌           |
| **OneDrive**      | ❌            | ❌                | ❌           | ❌            | ❌               | x            |
| **Others**        | ❌            | ❌                | ❌           | ❌            | ❌               | ❌           |

### SQLite数据库系统

- **高性能存储**：使用SQLite替代JSON文件，提供更好的查询性能
- **数据完整性**：ACID事务保证数据安全
- **自动迁移**：从旧的JSON格式无缝迁移到SQLite
- **智能缓存**：本地文件缓存管理，避免重复下载

### 智能匹配算法

- **多维度匹配**：时间（5分钟容差）、运动类型、距离（5%容差）、时长（10%容差）
- **置信度评分**：0.0-1.0评分系统，确保匹配准确性
- **运动类型标准化**：自动识别相似运动类型（如跑步、越野跑、跑步机跑步）

### 文件格式转换

- **多格式支持**：FIT、TCX、GPX格式之间的转换
- **自动转换**：上传时自动根据目标平台需求转换格式
- **批量转换**：支持批量文件格式转换

## 快速开始

### 环境要求

- Python 3.7+
- 操作系统：Windows、macOS、Linux

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置说明

项目使用统一的配置文件 `.app_config.json` 管理所有平台的配置信息。

#### 支持的平台配置

1. **Strava API配置**
   - client_id：Strava应用ID
   - client_secret：Strava应用密钥
   - refresh_token：刷新令牌

2. **Garmin Connect配置**
   - username：用户名
   - password：密码
   - auth_domain：认证域（GLOBAL或CN）

3. **OneDrive配置**
   - client_id：Azure应用ID
   - client_secret：Azure应用密钥
   - redirect_uri：重定向URI

4. **IGPSport配置**
   - username：用户名
   - password：密码

5. **Intervals.icu配置**
   - user_id：用户ID
   - api_key：API密钥

### 运行程序

#### 交互式模式

```bash
python src/main_sync.py
```

#### 自动化模式

```bash
# 单向同步
python src/main_sync.py --auto --directions strava_to_garmin --batch-size 10

# 双向同步
python src/main_sync.py --auto --directions strava_to_garmin garmin_to_strava --batch-size 5

# 历史迁移模式
python src/main_sync.py --auto --directions strava_to_garmin --batch-size 20 --migration-mode
```

#### 文件转换工具

```bash
# 交互式转换
python src/file_converter.py --interactive

# 单文件转换
python src/file_converter.py input.fit gpx

# 批量转换
python src/file_converter.py --batch /path/to/files gpx
```

## 同步方向支持

### 当前支持的同步方向

- **Strava → Garmin Connect**：将Strava活动同步到Garmin
- **Garmin Connect → Strava**：将Garmin活动同步到Strava
- **Strava → OneDrive**：将Strava活动文件备份到OneDrive
- **Garmin Connect → OneDrive**：将Garmin活动文件备份到OneDrive
- **Strava → IGPSport**：将Strava活动同步到IGPSport
- **IGPSport → Intervals.icu**：将IGPSport活动同步到Intervals.icu

> 注意，目前同步到OneDrive的目的是为了Fog of World使用，所以同步到OneDrive的文件格式为GPX，而不是FIT，并且同步到OneDrive的目录是Fog of World的目录。在Fog of World中，开启OneDrive同步后可以将OneDrive的GPX轨迹导入到Fog of World中。

## 数据库架构

### SQLite表结构

```sql
-- 活动记录表
CREATE TABLE activity_records (
    fingerprint TEXT PRIMARY KEY,    -- 活动指纹
    name TEXT NOT NULL,             -- 活动名称
    sport_type TEXT NOT NULL,       -- 运动类型
    start_time TEXT NOT NULL,       -- 开始时间
    distance REAL NOT NULL,         -- 距离（米）
    duration INTEGER NOT NULL,      -- 时长（秒）
    elevation_gain REAL,            -- 海拔增益（米）
    created_at TEXT NOT NULL,       -- 创建时间
    updated_at TEXT NOT NULL        -- 更新时间
);

-- 平台映射表
CREATE TABLE platform_mappings (
    fingerprint TEXT NOT NULL,      -- 活动指纹
    platform TEXT NOT NULL,         -- 平台名称
    activity_id TEXT NOT NULL,      -- 平台活动ID
    created_at TEXT NOT NULL,       -- 创建时间
    UNIQUE(fingerprint, platform)
);

-- 同步状态表
CREATE TABLE sync_status (
    fingerprint TEXT NOT NULL,      -- 活动指纹
    source_platform TEXT NOT NULL, -- 源平台
    target_platform TEXT NOT NULL, -- 目标平台
    status TEXT NOT NULL,           -- 同步状态
    updated_at TEXT NOT NULL,       -- 更新时间
    UNIQUE(fingerprint, source_platform, target_platform)
);

-- 文件缓存表
CREATE TABLE file_cache (
    fingerprint TEXT NOT NULL,      -- 活动指纹
    file_format TEXT NOT NULL,      -- 文件格式
    file_path TEXT NOT NULL,        -- 文件路径
    file_size INTEGER,              -- 文件大小
    created_at TEXT NOT NULL,       -- 创建时间
    UNIQUE(fingerprint, file_format)
);

-- 同步配置表
CREATE TABLE sync_config (
    key TEXT PRIMARY KEY,           -- 配置键
    value TEXT NOT NULL,            -- 配置值
    updated_at TEXT NOT NULL        -- 更新时间
);

-- API限制表
CREATE TABLE api_limits (
    platform TEXT PRIMARY KEY,      -- 平台名称
    daily_calls INTEGER DEFAULT 0,  -- 每日调用次数
    quarter_hour_calls INTEGER DEFAULT 0, -- 15分钟调用次数
    daily_limit INTEGER NOT NULL,   -- 每日限制
    quarter_hour_limit INTEGER NOT NULL, -- 15分钟限制
    last_reset TEXT NOT NULL        -- 最后重置时间
);
```

### 数据迁移

系统会自动检测旧的JSON数据库文件并迁移到SQLite：

```bash
# 自动迁移（首次运行时）
python src/main_sync.py

# 手动测试迁移
python tests/test_database_migration.py
```

## 命令行参数

### main_sync.py 参数

```bash
python src/main_sync.py [选项]

选项:
  --auto                    自动模式，跳过交互式选择
  --directions DIR [DIR...] 同步方向列表
  --batch-size N           每批处理的活动数量 (默认: 10)
  --migration-mode         启用历史迁移模式
  --debug                  启用调试模式
  --cleanup-cache          清理过期缓存文件
  --status                 显示同步状态
  --clear-garmin-session   清除Garmin会话

同步方向:
  strava_to_garmin        Strava到Garmin
  garmin_to_strava        Garmin到Strava
  strava_to_onedrive      Strava到OneDrive
  garmin_to_onedrive      Garmin到OneDrive
  strava_to_igpsport      Strava到IGPSport
  igpsport_to_intervals_icu IGPSport到Intervals.icu
```

### file_converter.py 参数

```bash
python src/file_converter.py [选项] [输入] [格式]

选项:
  -i, --interactive        交互模式
  -b, --batch             批量转换模式
  -o, --output OUTPUT     输出文件或目录
  --info                  显示文件信息
  -v, --verbose           详细输出

格式:
  fit, tcx, gpx           支持的文件格式
```

### 调试模式

```bash
# 启用调试输出
python src/main_sync.py --debug

# 查看同步状态
python src/main_sync.py --status

# 清理缓存
python src/main_sync.py --cleanup-cache
```

## 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 相关链接

- [Yesaye/tampermonkey-script: 油猴脚本](https://github.com/Yesaye/tampermonkey-script)
- [tyb311/SportTrails: 运动轨迹多平台管理软件【XOSS-iGPSPORT】](https://github.com/tyb311/SportTrails)
- [Strava API文档](https://developers.strava.com/)
- [Garmin Connect IQ](https://developer.garmin.com/)
- [Microsoft Graph API](https://docs.microsoft.com/en-us/graph/)
- [Intervals.icu API](https://intervals.icu/api)
- [mywhoosh to garmin](https://github.com/mvace/mywhoosh_to_garmin)
