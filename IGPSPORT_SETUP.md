# IGPSport 配置指南

本文档介绍如何配置IGPSport平台以支持活动同步功能。

## 前提条件

1. 拥有IGPSport账户（[注册地址](https://my.igpsport.com/)）
2. 安装必要的Python依赖包

## 配置步骤

### 方法一：自动配置（推荐）

运行同步程序时，系统会自动提示您输入IGPSport登录信息：

```bash
python src/main_sync.py
```

选择包含IGPSport的同步方向后，系统会提示：
- IGPSport用户名/邮箱
- IGPSport密码
- 是否保存登录凭据

### 方法二：手动配置

1. 编辑项目根目录下的 `.app_config.json` 文件
2. 在 `igpsport` 部分添加配置：

```json
{
  "igpsport": {
    "username": "your_username_or_email",
    "password": "your_password",
    "login_token": ""
  }
}
```

### 方法三：使用登录令牌

如果您有IGPSport的登录令牌（loginToken），可以直接配置：

```json
{
  "igpsport": {
    "login_token": "your_login_token",
    "username": "",
    "password": ""
  }
}
```

## 获取登录令牌（高级用户）

1. 在浏览器中打开 [IGPSport网站](https://my.igpsport.com/) 并登录
2. 按F12打开开发者工具
3. 转到 Application/Storage > Cookies
4. 找到 `loginToken` 的值
5. 将其配置到 `.app_config.json` 中

## 支持的文件格式

IGPSport支持以下运动文件格式：
- FIT文件
- TCX文件
- GPX文件

## 注意事项

1. **上传限制**：IGPSport可能对上传频率有限制，建议适度使用批量同步
2. **文件大小**：确保活动文件大小在IGPSport允许的范围内
3. **网络连接**：上传过程需要稳定的网络连接
4. **重复活动**：系统会自动检测并跳过已同步的活动

## 常见问题

### Q: 登录失败怎么办？
A: 请检查用户名和密码是否正确，确保账户没有被锁定。

### Q: 上传失败怎么办？
A: 检查网络连接，确认文件格式支持，查看错误日志获取详细信息。

### Q: 如何清除保存的凭据？
A: 删除 `.app_config.json` 文件中 `igpsport` 部分的配置信息。

## 同步配置示例

完整的配置文件示例：

```json
{
  "strava": {
    "client_id": "your_client_id",
    "client_secret": "your_client_secret",
    "refresh_token": "your_refresh_token"
  },
  "igpsport": {
    "username": "your_username",
    "password": "your_password",
    "login_token": ""
  }
}
```

## 技术支持

如果遇到问题，请：
1. 检查日志文件 `sync_logs.log` 获取详细错误信息
2. 确认所有依赖包已正确安装
3. 在项目GitHub页面提交issue

---

配置完成后，您就可以使用 `Strava -> IGPSport` 同步功能了！ 