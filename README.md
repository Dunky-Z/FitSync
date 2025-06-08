# Strava to IGPSport 活动文件传输工具

将Strava活动文件自动下载并上传到IGPSport平台的Python工具。

## 🎉 最新改进

- ✅ **智能文件检查**: 下载前自动检查是否已存在相同活动ID的文件
- 🔐 **双平台Cookie管理**: 自动保存和管理Strava和IGPSport的登录状态
- 📁 **TCX直接支持**: IGPSport直接支持TCX格式，无需转换
- 🚀 **一键重复使用**: 后续运行无需重新登录或下载

## 功能特性

- 🚀 **自动下载**: 从Strava自动下载活动文件（TCX/GPX格式）
- 🔐 **Cookie管理**: 自动保存和管理Strava登录Cookie
- 🔄 **格式转换**: 自动将TCX文件转换为GPX格式（保留供扩展使用）
- ☁️ **智能上传**: 完整的IGPSport上传流程（OSS + 服务器通知）
- 🇨🇳 **中文界面**: 完全中文化的用户界面
- 🎯 **智能检测**: 自动检测已下载文件，避免重复下载
- ⚡ **快速认证**: 自动重用保存的登录状态

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 运行程序
```bash
python3 src/main.py
```

### 使用流程

#### 首次使用
1. **选择运动类型**: Bike, Run, Swim, Other
2. **选择文件来源**: 下载或提供文件路径
3. **输入活动ID**: 输入Strava活动ID
4. **Strava认证**: 输入Strava Cookie（会自动保存）
5. **IGPSport登录**: 输入IGPSport账号密码（会自动保存）
6. **自动上传**: 程序自动完成文件处理和上传

#### 后续使用（无需重新登录！）
1. **选择运动类型**: Bike, Run, Swim, Other
2. **输入活动ID**: 输入新的Strava活动ID
3. **自动处理**: 程序自动检查文件、使用保存的登录状态完成上传

### Cookie获取方法（仅首次使用）

#### Strava Cookie
1. 在浏览器中打开 https://www.strava.com 并登录
2. 按F12打开开发者工具
3. 转到 Network(网络) 标签
4. 刷新页面
5. 找到任意一个请求，在Request Headers中找到Cookie
6. 复制完整的Cookie值并粘贴到程序中

#### IGPSport Token（备用方案）
如果自动登录失败，可以手动获取Token：

1. 在浏览器中打开 https://my.igpsport.com 并登录
2. 按F12打开开发者工具
3. 转到 Application/Storage > Cookies
4. 找到 `loginToken` 的值

## 智能功能

### 📁 文件检查
- 下载前自动检查Downloads文件夹
- 发现同名活动文件时提示是否重用
- 避免重复下载，节省时间和流量

### 🔐 Cookie管理
- **Strava Cookie**: 自动保存在 `.strava_cookie`
- **IGPSport Cookie**: 自动保存在 `.igpsport_cookie`
- 程序启动时自动检测和使用有效的登录状态
- Cookie过期时自动提示重新认证

### 📄 格式支持
- **直接支持**: TCX格式直接上传到IGPSport
- **扩展准备**: GPX转换代码保留供后续扩展
- **输入格式**: TCX, GPX, FIT

## 文件结构

```
├── src/
│   └── main.py          # 主程序
├── requirements.txt     # Python依赖
├── .strava_cookie      # Strava Cookie（自动生成，已忽略）
├── .igpsport_cookie    # IGPSport Cookie（自动生成，已忽略）
├── .gitignore          # Git忽略文件
└── README.md           # 说明文档
```

## 上传流程

1. **智能文件获取**
   - 检查是否已存在相同活动文件
   - 如果不存在，使用保存的Cookie自动下载
   - 支持TCX、GPX、FIT格式

2. **文件验证**
   - 验证文件格式和完整性
   - 确保文件可以被正确处理

3. **IGPSport上传**
   - 检查保存的登录状态
   - 如需要，自动重新认证
   - 获取阿里云OSS临时凭证
   - 上传文件到OSS存储
   - 通知IGPSport服务器完成导入

## 技术特点

- **智能状态管理**: 自动保存和重用认证信息
- **健壮的错误处理**: 详细的错误信息和fallback机制
- **API兼容**: 完全兼容IGPSport官方API
- **安全性**: 敏感信息本地存储，已加入gitignore
- **用户友好**: 智能检测，减少重复操作

## 使用场景

### 💡 典型工作流程
1. **首次设置**: 配置Strava和IGPSport认证（仅一次）
2. **日常使用**: 
   - 运行程序
   - 输入活动ID
   - 程序自动完成所有步骤
3. **批量处理**: 重复输入多个活动ID，快速批量上传

### 🎯 适用人群
- 需要将Strava数据同步到IGPSport的运动员
- 使用多个运动平台管理数据的用户
- 希望自动化数据传输流程的技术用户

## 注意事项

- ✅ 确保有有效的IGPSport账号
- ✅ Strava活动必须是可访问的（公开或已登录）
- ✅ 首次使用需要配置认证信息
- ✅ Cookie文件已添加到.gitignore，不会意外提交
- ✅ 后续使用几乎无需人工干预

## 故障排除

### 下载失败
- 检查Strava Cookie是否过期（程序会自动提示）
- 确认活动ID正确且可访问

### 登录失败  
- 检查IGPSport用户名密码
- 尝试手动获取loginToken
- 删除 `.igpsport_cookie` 文件重新登录

### 上传失败
- 检查网络连接
- 确认IGPSport账号状态正常
- 查看控制台错误信息

### Cookie问题
- 删除对应的cookie文件重新认证
- 确保浏览器中已正确登录对应平台

## 支持的文件格式

- **输入**: TCX, GPX, FIT
- **处理**: 直接上传TCX，保留GPX转换功能
- **输出**: 成功导入到IGPSport平台

---

🎉 享受从Strava到IGPSport的无缝、智能活动数据传输！

## 更新日志

### v2.0 (最新)
- ✅ 新增智能文件检查功能
- ✅ 新增IGPSport Cookie自动管理
- ✅ 优化用户体验，减少重复操作
- ✅ 支持TCX直接上传，提高兼容性

### v1.0 
- ✅ 基础Strava下载功能
- ✅ IGPSport上传流程
- ✅ Strava Cookie管理
- ✅ 中文化界面
