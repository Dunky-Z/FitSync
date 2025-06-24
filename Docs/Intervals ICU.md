# Intervals.icu API申请

访问 [https://intervals.icu](https://intervals.icu) 并登录您的账户。

1. 点击侧边栏`设置`
2. 在设置页面向下滚动，找到 `开发者设置` 部分
3. 记录下`运动员ID`，`API秘钥`

![](https://picbed-1311007548.cos.ap-shanghai.myqcloud.com/markdown_picbed/img//2025/06/24/cf438af2cc6c5e3026c04c1f3f2c4149.png)

# 配置文件

在项目根目录下创建`.app_config.json`文件，内容如下：

```json
{
  "intervals_icu": {
    "user_id": "YOUR_USER_ID",
    "api_key": "YOUR_API_KEY"
  }
}
```
