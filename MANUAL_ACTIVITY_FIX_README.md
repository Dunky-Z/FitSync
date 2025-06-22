# 手动活动检测功能修复

## 问题描述

在Strava同步过程中，遇到手动创建的活动时会出现以下问题：

1. **误判Cookie过期**：手动创建的活动没有原始文件（FIT/TCX/GPX），下载时返回HTML页面
2. **重复输入Cookie**：系统误认为Cookie过期，提示用户重新输入
3. **同步效率低**：尝试下载不存在的文件浪费时间
4. **用户体验差**：频繁的Cookie重新输入打断同步流程

## 解决方案

### 1. 手动活动识别机制

添加了智能识别手动创建活动的功能：

**识别条件**：
- 没有设备名称（`device_name`为空）
- 没有上传ID（`upload_id`为空）  
- 没有外部ID（`external_id`为空）

**代码实现**：
```python
def _is_manual_activity(self, activity_data: Dict) -> bool:
    """检查活动是否为手动创建（没有原始文件）"""
    device_name = activity_data.get('device_name')
    upload_id = activity_data.get('upload_id')
    external_id = activity_data.get('external_id')
    
    has_device = device_name and device_name.strip()
    has_upload_id = upload_id is not None
    has_external_id = external_id and external_id.strip()
    
    return (not has_device and not has_upload_id and not has_external_id)
```

### 2. 原始文件检测

增强了文件存在性检测：

**检测逻辑**：
- 首先检查是否为手动活动
- 然后根据设备类型和运动类型判断
- 支持常见的运动设备（Garmin、Polar、Suunto、Wahoo、Zwift等）

**代码实现**：
```python
def _has_original_file(self, activity_data: Dict) -> bool:
    """检查活动是否有原始文件可下载"""
    if self._is_manual_activity(activity_data):
        return False
    
    # 检查设备和运动类型
    device_indicators = ['garmin', 'polar', 'suunto', 'wahoo', 'zwift', ...]
    has_device_indicator = any(d in device_name.lower() for d in device_indicators)
    
    return has_device_indicator or (has_likely_type and upload_id is not None)
```

### 3. 改进的下载流程

优化了文件下载过程：

**下载前检查**：
```python
def download_activity_file(self, activity_id: str, save_path: str) -> bool:
    # 首先获取活动详情，检查是否有原始文件
    activity_details = self.get_activity_details(activity_id)
    if activity_details:
        if not self._has_original_file(activity_details):
            print(f"跳过手动创建的活动: {activity_details.get('name', activity_id)}")
            return False
    
    # 继续下载流程...
```

**响应内容判断**：
```python
# 检查是否返回了HTML页面（表示没有原始文件）
if 'text/html' in content_type:
    # 如果是正常的Strava页面，说明活动没有原始文件
    if any(indicator in response.text.lower() for indicator in [
        'strava', 'activity', 'manual'
    ]):
        print(f"活动 '{activity_name}' 是手动创建的，跳过下载")
        return False, None  # 不是Cookie问题
    else:
        print("Cookie可能已过期，请重新输入Cookie")
        return True, None   # 是Cookie问题
```

### 4. 同步流程优化

在双向同步中提前过滤手动活动：

```python
def _process_single_activity(self, activity_data: Dict, source_platform: str, target_platform: str) -> str:
    if source_platform == "strava":
        # 检查是否为手动创建的活动
        if not self.strava_client._has_original_file(activity_data):
            print(f"跳过手动创建的活动: {metadata.name}")
            return "skipped"
    
    # 继续处理其他活动...
```

## 技术特性

### 支持的设备类型
- **GPS手表**：Garmin、Polar、Suunto、Coros、Fitbit
- **骑行设备**：Wahoo、Garmin Edge系列
- **室内训练**：Zwift、TrainerRoad
- **手机应用**：iPhone Strava、Android Strava

### 支持的运动类型
- 跑步（Run、Running）
- 骑行（Ride、Cycling）
- 游泳（Swim、Swimming）
- 步行/徒步（Walk、Hike）
- 其他有GPS轨迹的运动

### 边界情况处理
- **空数据活动**：自动识别为手动活动
- **部分数据活动**：根据现有字段智能判断
- **未知设备**：保守处理，尽量避免误判

## 测试验证

创建了完整的测试套件：

```bash
python tests/test_manual_activity_detection.py
```

**测试覆盖**：
- ✅ 手动创建活动识别
- ✅ 设备上传活动识别  
- ✅ 室内训练活动识别
- ✅ 手机GPS活动识别
- ✅ 边界情况处理
- ✅ 文件类型检测

## 用户体验改进

### 修复前
```
[StravaClient] 响应状态码: 200
[StravaClient] Content-Type: text/html; charset=utf-8
[StravaClient] 保存的Cookie可能已过期，需要更新Cookie
请重新输入Cookie...
```

### 修复后
```
[StravaClient] 检测到手动创建活动: 调试同步工具测试文件
跳过手动创建的活动: 调试同步工具测试文件
活动同步状态: skipped
```

## 效果总结

### ✅ 已解决的问题
1. **消除了误判Cookie过期的问题**
2. **减少了不必要的用户交互**
3. **提高了同步效率和速度**
4. **改善了整体用户体验**

### 📈 性能提升
- **同步速度**：跳过无文件活动，减少无效下载
- **API效率**：避免重复的失败请求
- **用户体验**：减少手动输入，提高自动化程度

### 🛡️ 兼容性保证
- **向后兼容**：不影响现有功能
- **容错性**：对未知情况采用保守策略
- **可扩展性**：易于添加新的设备和运动类型支持

## 使用方法

功能已自动集成到同步流程中，用户无需额外配置：

```bash
# 正常使用同步功能
python src/main_sync.py

# 手动活动将自动被跳过，不会影响同步流程
# 同步日志会显示跳过的手动活动信息
```

此修复显著提升了Strava同步的稳定性和用户体验，特别是对于有手动创建活动的用户账户。 