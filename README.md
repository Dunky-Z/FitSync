# Strava to TrainingPeaks 运动数据同步工具

一个功能强大的运动数据同步工具，支持在Strava、Garmin Connect、TrainingPeaks等平台之间进行双向数据同步。

## ✨ 主要特性

### 🔄 双向同步功能
- **Strava ↔ Garmin Connect** 双向同步
- **智能活动匹配**：基于时间、运动类型、距离、时长的多维度匹配算法
- **增量同步**：只同步新增活动，避免重复处理
- **API限制管理**：智能管理Strava API调用限制（每日200次）

### 🗄️ SQLite数据库系统
- **高性能存储**：使用SQLite替代JSON文件，提供更好的查询性能
- **数据完整性**：ACID事务保证数据安全
- **自动迁移**：从旧的JSON格式无缝迁移到SQLite
- **智能缓存**：本地文件缓存管理，避免重复下载

### 🎯 智能匹配算法
- **多维度匹配**：时间（5分钟容差）、运动类型、距离（5%容差）、时长（10%容差）
- **置信度评分**：0.0-1.0评分系统，确保匹配准确性
- **运动类型标准化**：自动识别相似运动类型（如跑步、越野跑、跑步机跑步）

## 🚀 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 配置API凭据
1. **Strava API配置**：参考 [STRAVA_API_SETUP.md](STRAVA_API_SETUP.md)
2. **Garmin Connect配置**：参考 [GARMIN_CONNECT_SETUP.md](GARMIN_CONNECT_SETUP.md)

### 运行双向同步
```bash
# 交互模式
python src/main_sync.py

# 自动模式
python src/main_sync.py --auto --directions strava_to_garmin --batch-size 10

# 双向同步
python src/main_sync.py --auto --directions both --batch-size 5 --debug
```

## 🧪 测试系统

项目包含完整的测试套件，验证所有核心功能：

### 运行测试
```bash
# 运行所有测试
python run_tests.py

# 运行快速测试
python run_tests.py --test quick

# 运行特定测试
python run_tests.py --test sync        # 双向同步测试
python run_tests.py --test migration   # 数据库迁移测试
python run_tests.py --test main        # 主要功能测试
```

### 测试覆盖
- ✅ **同步管理器测试**：活动指纹生成、状态跟踪、缓存管理
- ✅ **活动匹配器测试**：多维度匹配算法、置信度评分
- ✅ **平台客户端测试**：Strava和Garmin API连接
- ✅ **数据库迁移测试**：JSON到SQLite的完整迁移流程
- ✅ **性能对比测试**：JSON vs SQLite性能基准测试

## 📊 数据库架构

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
```

### 数据迁移
系统会自动检测旧的JSON数据库文件并迁移到SQLite：
```bash
# 自动迁移（首次运行时）
python src/main_sync.py

# 手动测试迁移
python tests/test_database_migration.py
```

## 🔧 高级功能

### API限制管理
- **Strava限制**：每日180次（保留20次余量），每15分钟90次（保留10次余量）
- **智能调度**：自动检查API限制，避免超限
- **实时监控**：显示剩余API调用次数

### 缓存系统
- **本地文件缓存**：避免重复下载相同活动文件
- **智能清理**：自动清理30天以上的过期缓存
- **文件完整性**：验证缓存文件存在性和大小

### 同步策略
- **首次同步**：获取最近30天的活动
- **增量同步**：从上次同步时间开始，1小时重叠避免遗漏
- **断点续传**：支持中断后继续同步
- **错误恢复**：自动重试失败的同步操作

## 📈 性能优势

基于1000条记录的性能测试对比：

| 指标 | JSON文件 | SQLite数据库 | 优势 |
|------|----------|-------------|------|
| **查询性能** | 线性遍历 | 索引查询 | **SQLite快数倍** |
| **数据完整性** | 无保障 | ACID事务 | **SQLite更安全** |
| **并发访问** | 文件锁定 | 数据库锁 | **SQLite更稳定** |
| **复杂查询** | 不支持 | SQL查询 | **SQLite功能更强** |

## 🗂️ 项目结构

```
strava-to-trainingpeaks/
├── src/                          # 源代码目录
│   ├── main_sync.py             # 双向同步主程序
│   ├── database_manager.py      # SQLite数据库管理器
│   ├── sync_manager.py          # 同步管理器
│   ├── activity_matcher.py      # 活动匹配器
│   ├── bidirectional_sync.py    # 双向同步核心
│   ├── strava_client.py         # Strava客户端
│   ├── garmin_sync_client.py    # Garmin同步客户端
│   └── ...                      # 其他模块
├── tests/                        # 测试目录
│   ├── test_sync.py             # 双向同步测试
│   ├── test_database_migration.py # 数据库迁移测试
│   └── test_main.py             # 主要功能测试
├── run_tests.py                 # 测试运行脚本
├── sync_database.db             # SQLite数据库文件
├── activity_cache/              # 活动文件缓存目录
└── README.md                    # 项目文档
```

## 🔮 未来计划

### 第二阶段：扩展平台支持
- **IGPSport平台**：添加IGPSport双向同步支持
- **TrainingPeaks增强**：完善TrainingPeaks集成
- **更多平台**：支持更多运动平台

### 第三阶段：高级功能
- **Web管理界面**：基于Web的同步管理界面
- **数据分析**：运动数据统计和分析功能
- **自动调度**：定时自动同步功能
- **云端备份**：数据库云端备份和恢复

## 📝 更新日志

### v2.0.0 (2025-06-15)
- ✨ **重大更新**：从JSON文件升级到SQLite数据库系统
- 🚀 **性能提升**：查询性能大幅提升，支持复杂SQL查询
- 🔄 **自动迁移**：无缝从旧JSON格式迁移到SQLite
- 🧪 **完整测试**：添加全面的测试套件和性能基准测试
- 📊 **数据完整性**：ACID事务保证数据安全
- 🎯 **智能缓存**：优化文件缓存管理系统

### v1.0.0 (2025-06-14)
- 🎉 **首次发布**：Strava ↔ Garmin Connect双向同步功能
- 🤖 **智能匹配**：多维度活动匹配算法
- 📈 **API管理**：Strava API限制智能管理
- 💾 **本地缓存**：活动文件本地缓存系统

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目！

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

需要不挂梯子使用Connect登录，会自动弹出更新手机号

[Yesaye/tampermonkey-script: 油猴脚本](https://github.com/Yesaye/tampermonkey-script)
[tyb311/SportTrails: 运动轨迹多平台管理软件【XOSS-iGPSPORT】](https://github.com/tyb311/SportTrails)