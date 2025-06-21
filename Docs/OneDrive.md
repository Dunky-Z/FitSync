# OneDrive API 申请

> 以下内容大部分参考自文档[OneDrive Vercel Index](https://ovi.swo.moe/zh/docs/advanced)，因为担心链接失效，所以自行整理一份。

## 注册应用程序

打开以下链接：

- [Microsoft Azure App registrations](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)（ OneDrive 国际版、企业版与教育版，E5 订阅专用）
- [Microsoft Azure.cn App registrations](https://portal.azure.cn/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)（OneDrive 世纪互联专用）

创建一个应用程序：

1. 登入你的微软账户，点击 `New registration`。
2. 输入一个名字，例如`sync`
3. 将 `Supported account types` 设置为：

    ```
    Accounts in any organizational directory (Any Azure AD directory - Multitenant) and personal Microsoft accounts (e.g. Skype, Xbox)

    ```

    OneDrive 世纪互联用户设置为 - 任何组织目录（任何 Azure AD 目录 - 多租户）中的帐户。
4. 将 `Redirect URI (optional)` 设置为 `Web`（在下拉菜单里）以及 `http://localhost`。
5. 点击注册。

![](https://picbed-1311007548.cos.ap-shanghai.myqcloud.com/markdown_picbed/img//2025/06/20/56154131bfd12ac08221bd128ccb25ee.png)

## 获取client_id和client_secret

点击 `Overview` > `Essentials`，获取 `Application (client) ID`：

![](https://picbed-1311007548.cos.ap-shanghai.myqcloud.com/markdown_picbed/img//2025/06/21/fe6b3e0681170266acfdb52d41d933a1.png)


点击 `Certificates & secrets`，点击 `New client secret`，创建一个新 secret ，描述为 `client_secret`，将 `Expires` 设置为 `Custom`，将 `Start` 与 `End` 设置为能设置的最长时间，一般为两年。最后点击 `Add` 按钮，即可获取 `client_secret`。

![](https://picbed-1311007548.cos.ap-shanghai.myqcloud.com/markdown_picbed/img//2025/06/21/916dfad17629924b58479bf4312d6fa9.png)


复制 `client_secret` 的值，保存到本地。只有一次复制机会。

![](https://picbed-1311007548.cos.ap-shanghai.myqcloud.com/markdown_picbed/img//2025/06/21/c8f02174bf4b29c20d2ef49a223c209d.png)


## 修改API权限

点击 API permissions，再点击 Microsoft Graph，再点击 Delegated permissions，然后搜索，添加以下权限：

![](https://picbed-1311007548.cos.ap-shanghai.myqcloud.com/markdown_picbed/img//2025/06/21/a7aff83c94a47dee024306a1caff2c75.png)

![](https://picbed-1311007548.cos.ap-shanghai.myqcloud.com/markdown_picbed/img//2025/06/21/194d69c933561adce58f71b81dd71b0f.png)

![](https://picbed-1311007548.cos.ap-shanghai.myqcloud.com/markdown_picbed/img//2025/06/21/f06ac6e1420e8a75583e3990fa322414.png)

## 获取授权代码(code)

```bash
GET https://login.live.com/oauth20_authorize.srf?client_id={client_id}&scope={scope}
  &response_type=code&redirect_uri={redirect_uri}
```

- `client_id` 是你在 Azure 中注册的应用程序的 `Application (client) ID`。
- `scope` 是你在 Azure 中注册的应用程序的 `Delegated permissions`，每个权限之间用空格隔开。
- `redirect_uri` 是你在 Azure 中注册的应用程序的 `Redirect URI (optional)`。

以我的注册为例，请求如下：

```bash
https://login.live.com/oauth20_authorize.srf?client_id=1f2xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx&scope=Files.ReadWrite Files.ReadWrite.All Files.ReadWrite.AppFolder Files.ReadWrite.Selected offline_access User.Read&response_type=code&redirect_uri=http://localhost
```

浏览器中打开这个链接后地址栏会跳转至授权页面，点击 `Accept` 按钮后，会跳转至 `redirect_uri` 指定的页面，并携带授权码。将地址栏中的授权码复制下来。他是以code开头：

![](https://picbed-1311007548.cos.ap-shanghai.myqcloud.com/markdown_picbed/img//2025/06/21/856c658d5b341e477a1d0f86dfa40ad5.png)

## 获取访问令牌（access_token）

```bash
POST https://login.live.com/oauth20_token.srf
Content-Type: application/x-www-form-urlencoded

client_id={client_id}&redirect_uri={redirect_uri}&client_secret={client_secret}
&code={code}&grant_type=authorization_code
```

- `client_id` 是你在 Azure 中注册的应用程序的 `Application (client) ID`。
- `redirect_uri` 是你在 Azure 中注册的应用程序的 `Redirect URI (optional)`。
- `client_secret` 是你在 Azure 中注册的应用程序的 `client_secret`。
- `code` 是你在浏览器中获取的授权码。

以我的注册为例，请求如下：

```bash
POST https://login.live.com/oauth20_token.srf
Content-Type: application/x-www-form-urlencoded

client_id=1f2xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx&redirect_uri=http://localhost&client_secret=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx&code=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx&grant_type=authorization_code
```

你可以使用Postman或者curl等工具发送请求，获取access_token。curl比较方便，命令行就可以操作，命令如下：

```bash
curl -X POST https://login.live.com/oauth20_token.srf \
-H "Content-Type: application/x-www-form-urlencoded" \
-d "client_id=1f2xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
-d "redirect_uri=http://localhost" \
-d "client_secret=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
-d "code=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
-d "grant_type=authorization_code"
```

返回值中就有我们需要的access_token，保存到本地。

```
{
  "token_type":"bearer",
  "expires_in": 3600,
  "scope":"wl.basic onedrive.readwrite",
  "access_token":"EwCo...AA==",
  "refresh_token":"eyJh...9323"
}
```

# 获取刷新令牌（refresh_token）

和上一步类似：

```bash
POST https://login.live.com/oauth20_token.srf
Content-Type: application/x-www-form-urlencoded

client_id={client_id}&redirect_uri={redirect_uri}&client_secret={client_secret}
&refresh_token={refresh_token}&grant_type=refresh_token
```

- `client_id` 是你在 Azure 中注册的应用程序的 `Application (client) ID`。
- `redirect_uri` 是你在 Azure 中注册的应用程序的 `Redirect URI (optional)`。
- `client_secret` 是你在 Azure 中注册的应用程序的 `client_secret`。
- `refresh_token` 是你在上一步获取的 `refresh_token`。

以我的注册为例，请求如下：

```bash
curl -X POST https://login.live.com/oauth20_token.srf \
-H "Content-Type: application/x-www-form-urlencoded" \
-d "client_id=1f2xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
-d "redirect_uri=http://localhost" \
-d "client_secret=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
-d "refresh_token=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
-d "grant_type=refresh_token"
```

返回值中就有我们需要的refresh_token，保存到本地。

# 配置文件

在项目根目录下创建`.app_config.json`文件，内容如下：

```json
{
  "onedrive": {
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uri": "http://localhost",
    "refresh_token": "YOUR_REFRESH_TOKEN",
    "access_token": "YOUR_ACCESS_TOKEN",
    "tenant_id": "common",
    "expires_in": 3600
  }
}
```

将其中的值替换为申请得到的值。