# Strava API 申请

登录[Strava](https://www.strava.com/settings/api)，申请 API，获取`Client ID`和`Client Secret`。

填写内容可以参考下图：

![](https://picbed-1311007548.cos.ap-shanghai.myqcloud.com/markdown_picbed/img//2025/06/21/da617be82a9e689b2a64e9273a154482.png)

其中授权回调域填写任意网址即可，比如`http://localhost`。

申请完成后会得到下面的信息：

![](https://picbed-1311007548.cos.ap-shanghai.myqcloud.com/markdown_picbed/img//2025/02/09/a5024f9e2e150810251222315be11ac9.png)

将下面链接中的`client_id`值换成上图中的客户 ID，然后浏览器中访问这个链接：

```txt
http://www.strava.com/oauth/authorize?client_id=xxxxxxx&response_type=code&redirect_uri=http://localhost/exchange_token&approval_prompt=force&scope=activity:read_all
```

会提示需要授权，点击授权后此时跳转到一个无法访问的网页，将地址栏中的`code`值记录下来，后面需要用到：

![](https://picbed-1311007548.cos.ap-shanghai.myqcloud.com/markdown_picbed/img//2025/03/08/c3a74e83d363bb0f453ad37712dd28ac.png)

需要用这个`code`发起一个 cURL 请求得到`refresh_token`，具体做法是在命令行终端中执行下面的命令：

```bash
curl -X POST https://www.strava.com/oauth/token \
-F client_id=YOURCLIENTID \
-F client_secret=YOURCLIENTSECRET \
-F code=AUTHORIZATIONCODE \
-F grant_type=authorization_code
```

- `client_id`值替换为申请得到的`客户ID`
- `client_secret`值替换为申请得到的`客户端密钥`
- `code`替换为上一步浏览器中得到的`code`

执行成功后可以得到下面的返回信息，需要将返回值中的`refresh_token`和`access_token`记录下来：

```bash
{"token_type":"Bearer","expires_at":1740213400,"expires_in":21600,"refresh_token":"123456789123456789","access_token":"123456789123456789","athlete":{"id":117756825,"username":"dunky_zhang","resource_state":2,"firstname":"Dominic","lastname":"Zhang","bio":"骑行小白","city":"","state":"","country":null,"sex":"M","premium":true,"summit":true,"created_at":"2023-05-10T13:54:32Z","updated_at":"2025-02-06T05:29:52Z","badge_type_id":1,"weight":66.0,"profile_medium":"https://dgalywyr863hv.cloudfront.net/pictures/athletes/117756825/32138099/2/medium.jpg","profile":"https://dgalywyr863hv.cloudfront.net/pictures/athletes/117756825/32138099/2/large.jpg","friend":null,"follower":null}}}}
```

# 配置文件

在项目根目录下创建`.app_config.json`文件，内容如下：

```json
{
  "strava": {
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "refresh_token": "YOUR_REFRESH_TOKEN",
    "access_token": "YOUR_ACCESS_TOKEN",
  }
}
```

将其中的值替换为申请得到的值。