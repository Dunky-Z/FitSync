# Strava API 设置指南

为了使用程序从Strava API获取活动列表，您需要完成以下设置步骤：

## 1. 创建Strava应用程序

1. 访问 [Strava API设置页面](https://www.strava.com/settings/api)
2. 点击 "Create App" 创建新应用程序
3. 填写应用信息：
   - **Application Name**: 任意名称，如 "Strava to IGPSport"
   - **Category**: 选择 "Data Importer"
   - **Club**: 留空
   - **Website**: 可以填写 `http://localhost`
   - **Authorization Callback Domain**: 填写 `localhost`
4. 点击 "Create" 创建应用程序

## 2. 获取Client ID和Client Secret

创建应用程序后，您将看到：
- **Client ID**: 一个数字ID
- **Client Secret**: 一个长字符串

请记录这两个值。

## 3. 获取Refresh Token

### 方法一：使用OAuth流程（推荐）

1. 在浏览器中访问以下URL（请替换YOUR_CLIENT_ID为您的实际Client ID）：
```
https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=read,activity:read
```

2. 授权后，浏览器会跳转到类似这样的URL：
```
http://localhost/?state=&code=AUTHORIZATION_CODE&scope=read,activity:read
```

3. 复制URL中的 `code` 参数值（AUTHORIZATION_CODE部分）

4. 使用以下curl命令获取refresh token（请替换相应的值）：
```bash
curl -X POST https://www.strava.com/oauth/token \
  -F client_id=YOUR_CLIENT_ID \
  -F client_secret=YOUR_CLIENT_SECRET \
  -F code=AUTHORIZATION_CODE \
  -F grant_type=authorization_code
```

5. 响应中会包含 `refresh_token`，请记录这个值。

### 方法二：使用在线工具

您也可以使用类似 [Strava OAuth Playground](https://developers.strava.com/playground/) 这样的在线工具来获取tokens。

## 4. 更新配置文件

编辑项目根目录下的 `.strava_config.json` 文件，填入您获取的值：

```json
{
  "client_id": "您的Client ID",
  "client_secret": "您的Client Secret",
  "refresh_token": "您的Refresh Token",
  "access_token": ""
}
```

注意：`access_token` 字段留空，程序会自动获取和刷新。

## 5. 测试配置

运行程序并选择"从Strava API获取最新活动"选项，如果配置正确，程序会显示您最新的活动列表供选择。

## 常见问题

### Q: 授权后看到"Application Error"页面
A: 这是正常的，因为我们使用的是localhost作为回调地址。只需要从浏览器地址栏复制code参数即可。

### Q: 获取活动列表时报错"unauthorized"
A: 请检查您的Client ID、Client Secret和Refresh Token是否正确填写。

### Q: Token过期错误
A: 程序会自动刷新access token，如果仍然报错，可能需要重新获取refresh token。

## 权限说明

程序只请求以下权限：
- `read`: 读取基本用户信息
- `activity:read`: 读取活动数据

程序不会修改、删除您的任何Strava数据。 