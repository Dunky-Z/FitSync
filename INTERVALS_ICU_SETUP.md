# Intervals.icu 集成设置指南

本文档介绍如何配置和使用 Intervals.icu 集成功能，实现运动文件的上传。

## 1. 获取 Intervals.icu API 凭据

### 1.1 登录 Intervals.icu
访问 [https://intervals.icu](https://intervals.icu) 并登录您的账户。

### 1.2 获取用户ID
- 登录后，查看浏览器地址栏
- 用户ID通常显示在URL中，格式如：`https://intervals.icu/activities/i244263`
- 其中 `i244263` 就是您的用户ID

### 1.3 获取API密钥
1. 点击右上角的用户头像，选择 "Settings"
2. 在设置页面向下滚动，找到 "API Access" 部分
3. 在 "Personal API Key" 字段中，您可以看到您的API密钥
4. 如果没有API密钥，点击 "Generate" 按钮生成一个

## 2. 配置说明

### 2.1 支持的文件格式
- `.fit` - Garmin等设备的原生格式
- `.tcx` - Training Center XML格式
- `.gpx` - GPS Exchange格式

### 2.2 配置信息
运行程序时，系统会提示您输入：
- **用户ID**: 您的Intervals.icu用户ID（如：i244263）
- **API密钥**: 您的个人API密钥

## 3. 使用方法

### 3.1 独立上传工具
使用 `upload_to_intervals.py` 脚本上传单个文件：

```bash
# 基本上传
python upload_to_intervals.py /path/to/activity.fit

# 指定活动名称和描述
python upload_to_intervals.py /path/to/activity.fit --name "晨跑训练" --description "今天的晨跑训练，感觉不错"

# 测试连接
python upload_to_intervals.py --test-connection /path/to/any.fit
```

### 3.2 交互式测试工具
使用 `test_intervals_icu.py` 进行交互式测试：

```bash
python test_intervals_icu.py
```

该工具提供以下功能：
1. 测试文件上传
2. 测试获取活动列表
3. 测试连接

## 4. API 限制和注意事项

### 4.1 文件大小限制
- Intervals.icu 对上传文件大小有限制
- 建议单个文件不超过 50MB

### 4.2 上传频率
- 个人API密钥通常没有严格的频率限制
- 但建议合理使用，避免过于频繁的请求

### 4.3 支持的压缩格式
- 除了原始格式外，还支持 `.zip` 和 `.gz` 压缩文件
- 系统会自动处理压缩文件

## 5. 故障排除

### 5.1 连接失败
如果连接测试失败，请检查：
1. 用户ID是否正确（应该以'i'开头）
2. API密钥是否正确复制
3. 网络连接是否正常
4. Intervals.icu服务是否可用

### 5.2 上传失败
常见上传失败原因：
1. **文件格式不支持**: 确保文件是 .fit、.tcx 或 .gpx 格式
2. **文件损坏**: 尝试用其他工具打开文件验证完整性
3. **文件过大**: 检查文件大小是否超过限制
4. **API凭据问题**: 重新验证用户ID和API密钥

### 5.3 权限问题
如果遇到权限相关错误：
1. 确认API密钥是否有效
2. 检查Intervals.icu账户状态
3. 尝试重新生成API密钥

## 6. 高级功能

### 6.1 外部ID关联
上传时可以设置 `external_id` 参数，用于关联其他平台的活动：

```python
result = intervals_client.upload_activity(
    file_path="activity.fit",
    name="训练活动",
    description="来自其他平台的同步",
    external_id="strava_12345"  # 关联到Strava活动ID
)
```

### 6.2 批量上传
可以编写脚本实现批量上传：

```python
import os
from config_manager import ConfigManager
from intervals_icu_client import IntervalsIcuClient

config_manager = ConfigManager()
client = IntervalsIcuClient(config_manager)

# 遍历目录中的所有.fit文件
for file in os.listdir("./activities"):
    if file.endswith('.fit'):
        client.upload_file(os.path.join("./activities", file))
```

## 7. 集成到主程序

Intervals.icu客户端已经集成到主同步程序中，可以作为上传目标平台使用。在主程序的平台选择界面中选择 "Intervals.icu" 即可。

## 8. 相关链接

- [Intervals.icu 官网](https://intervals.icu)
- [Intervals.icu API 文档](https://intervals.icu/api-docs.html)
- [Intervals.icu 论坛](https://forum.intervals.icu)

## 9. 技术支持

如果遇到问题，可以：
1. 查看程序的调试输出信息
2. 检查 `sync_logs.log` 日志文件
3. 在Intervals.icu论坛寻求帮助
4. 提交GitHub Issue（如果使用开源版本） 