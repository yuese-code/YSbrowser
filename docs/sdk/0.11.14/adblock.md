# 广告与跟踪请求过滤

需要包含原生广告过滤接口的 YSbrowser 构建。SDK 0.11.14 的新 Context 与 `AdblockConfig()` 默认使用 Disabled（关闭），不会自动下载过滤规则。需要拦截时显式传入 `mode="standard"` 或 `mode="aggressive"`。旧版浏览器不会被误报为已开启，显式配置时会提示升级。

```python
from ysbrowser_sdk.sync_api import YSBrowser, AdblockConfig, filter_catalog

with YSBrowser("/path/to/chrome", headless=True) as browser:
    context = browser.new_context(adblock=AdblockConfig(
        mode="standard", lists=("easylist", "easyprivacy")))
    page = context.new_page()
    page.goto("https://example.com")
    print(context.adblock_status())
```

模式为 `standard`、`aggressive`、`disabled`。Standard 对基础列表主要过滤第三方请求；Aggressive 同时处理网站自身请求。手动选择的可选、自定义列表可过滤第一方请求。Disabled 停止广告过滤，不修改代理或指纹配置。对现有 Context 调用 `set_adblock()` 可更新规则；已完成的请求不会撤销，刷新页面可重新加载。

`filter_catalog()` 返回可选列表 ID、名称和来源网址，不下载规则。`lists` 明确指定选中列表，`custom_urls` 接收 HTTPS 文本订阅网址。第一次使用下载到本机缓存，后续按有效期复用，并使用 ETag/Last-Modified 检查更新。每个 Context 在页面创建前完成规则加载；远程浏览器通过 CDP 接收规则内容，不要求远程主机拥有相同缓存路径。

`cache_dir` 自定义缓存目录；`offline=True` 禁止下载，缺失或损坏时报错；默认 `allow_stale=True` 在更新失败时允许使用已校验的旧缓存，状态中的 `stale` 会标明。默认 24 小时检查更新。规则缓存共享，Context 的模式、网站例外与统计独立。

异步 API 的配置相同，使用 `await browser.new_context(...)` 和 `await context.set_adblock(...)`。`ContextConfig(adblock=...)` 支持导出与恢复。

直接命令行启动可先生成快照：

```text
ysbrowser-sdk adblock-lists
ysbrowser-sdk adblock-prepare --mode standard --list easylist --list easyprivacy --output rules.json
chrome --adblock-mode=standard --adblock-rules=/absolute/path/rules.json
```

Windows 可将最后一行替换为实际 `ysbrowser.exe` 路径。浏览器不自动安装全部列表；无规则时弹窗明确提示尚未加载。工具栏提供本站三模式选择、已拦截请求数量、可展开详情和“过滤列表”入口。详情最多保留最近 256 条，请求 URL 去除查询参数和凭据。

执行范围包括网络请求、HTTP 重定向检查、页面和 Worker WebSocket、固定本地替代资源、CSS 隐藏和 scriptlet。`adblock_status()` 返回实际能力与列表统计。拦截计数仅统计网络请求，不把隐藏元素或脚本执行次数混入。

`rule_scope="network"` 只执行网络过滤；`rule_scope="all"` 可分别通过 `cosmetic=False` 或 `scriptlets=False` 关闭页面过滤的一部分。命令行快照支持 `--rule-scope network`、`--no-cosmetic`、`--no-scriptlets`。旧浏览器没有完整能力时，显式请求完整范围会报兼容性错误，不会静默宣称生效。

可直接隐藏的可选列表规则及激进模式 CSS 规则在文档起始阶段注入原生用户样式表，后续匹配元素也受样式控制。需要发现新 class/id 或检查动态条件的规则仍按需处理，不能保证所有页面的所有广告都在首帧前消失。

普通 CSS 隐藏保留 DOM，原始字段仍可读取；列表中显式的 `:remove()` 等动作会修改 DOM。动态元素、开放的 Shadow DOM 与子框架会重新检查。Standard 的基础隐藏规则主要处理第三方内容，Aggressive 同时处理第一方；主动选择的可选、自定义列表可以处理第一方。scriptlet 在匹配文档的页面脚本之前运行，只能调用随引擎固定的资源函数，不执行订阅中的任意原始 JavaScript，特权 `trusted-*` 资源不会向普通订阅开放。

模式或配置更新会恢复仍由过滤器控制的隐藏样式；已执行的脚本和删除动作不能撤销，需要重新加载文档。工具栏手动切换本站模式会自动刷新当前页面；SDK / CDP 更新配置不会隐式刷新业务页面，需要时由调用方重新加载。CSS 隐藏、脚本注入和网络拦截均可能影响网站功能，采集完整性必须以原始字段校验为准。

引擎固定为 Brave adblock-rust 0.13.5，脚本与替代资源固定版本。随浏览器提供 `ys_adblock_NOTICES.txt`、对应引擎及资源源码归档和许可证；过滤列表由 SDK 或浏览器设置页按需下载，不随浏览器预置完整规则。

## 手动操作浏览器

点击工具栏盾牌 → **过滤列表**，或在地址栏打开 `chrome://ys-adblock/`。可以搜索和勾选下方列出的 56 个列表，也可以添加 HTTPS 自定义订阅（最多 32 个）。

点击“保存并应用”后，浏览器下载缺失的规则；“更新已选列表”会主动检查更新。更新失败时，有已校验缓存的订阅继续使用缓存；新订阅下载失败则保留原有配置。页面显示处理进度与错误，可取消下载。保存后刷新已打开的网页，使新规则完整生效。

普通用户目录保存选择和规则缓存，重启后恢复，已选列表每 24 小时检查更新。无痕或独立 Context 的设置仅在该会话内生效。显式 SDK / CDP 配置优先，不会被后台订阅更新覆盖。每个来源最大 16 MiB，所选来源合计最大 48 MiB。

## `lists` 支持的过滤列表

当前 SDK 提供 **56 个列表**：2 个默认基础列表和 54 个可选列表。下表的 `lists` 值可直接复制，区分大小写；显示名称不是配置 ID。

省略 `lists` 时使用 `("easylist", "easyprivacy")`。显式传入 `lists` 会替换默认选择，而不是追加；如需保留基础拦截，请一并写上这两个 ID。可选列表不会根据浏览器语言自动全部启用，也不会全部下载。

例如，保留基础列表并增加中文广告过滤：

```python
AdblockConfig(
    mode="standard",
    lists=(
        "easylist",
        "easyprivacy",
        "92AA0D3B-34AC-4657-9A5C-DBAD339AF8E2",  # 中文网站广告
    ),
)
```

### 默认基础列表

| `lists` 值 | 名称 / 用途 |
| --- | --- |
| `easylist` | EasyList · 常规广告过滤 |
| `easyprivacy` | EasyPrivacy · 跟踪请求过滤 |

### 可选列表

需在 `lists` 中明确选择。名称说明了过滤目标；其实际效果取决于订阅规则、网页和启用的执行范围。

| `lists` 值 | 名称 / 过滤目标 |
| --- | --- |
| `AC023D22-AE88-4060-A978-4FEEEC4221693` | Cookie notice blocker |
| `67E792D4-AE03-4D1A-9EDE-80E01C81F9B8` | Annoying distractions blocker |
| `6b91e355-1421-4c03-9a30-911b4d0fb277` | AI suggestions blocker |
| `690FF3B4-8B6B-4709-8505-FEC6643D7BD9` | Newsletter popup blocker |
| `2F3DCE16-A19A-493C-A88F-2E110FBD37D6` | Mobile app promo blocker |
| `7911A1CB-304E-4CDB-ABB3-E2A94A37E4DD` | Social media blocker |
| `9E8EC586-4E17-4E5E-99D7-35172C4CEA74` | YouTube Shorts blocker |
| `5c6a6c95-b60a-4695-9efb-539359022531` | YouTube Playables blocker |
| `2D57ADED-3531-419A-9DED-7F8868BC1561` | YouTube recommendations blocker (mobile-only) |
| `7f11b964-4f36-4e06-9d75-bd16381b9386` | YouTube autodubbed videos blocker |
| `d579f370-6de3-4507-aa9a-cee4227e59f5` | YouTube end video elements blocker |
| `49958da7-f532-4a84-a765-9501729b8e75` | YouTube members-only video blocker |
| `BD308B90-D3BB-4041-9114-22E096B0BA77` | YouTube distractions elements blocker (mobile-only) |
| `3afa9d35-d837-45b5-b742-b3d0fe94e77c` | YouTube thumbnail image blocker |
| `E2FA7D98-0BD5-493E-8AF4-950604ADE9CB` | Tracking URL blocker |
| `1ED1870B-997C-4BFE-AEBC-B67D679BAF3B` | Chat app blocker |
| `78672887-A098-4D2C-B0CB-A3DEC4834DA7` | Paywall blocker |
| `F61D6B7B-4110-4EA4-9C81-38FB4CE90AEC` | Porn blocker |
| `9FCEECEC-52B4-4487-8E57-8781E82C91D0` | Arabic website ad blocker |
| `FD176DD1-F9A0-4469-B43E-B1764893DD5C` | Bulgarian website ad blocker |
| `92AA0D3B-34AC-4657-9A5C-DBAD339AF8E2` | Chinese website ad blocker |
| `CC98E4BA-9257-4386-A1BC-1BBF6980324F` | Chinese website annoyances blocker |
| `7CCB6921-7FDA-4A9B-B70A-12DD0A8F08EA` | Czech and Slovak website ad blocker |
| `9D644676-4784-4982-B94D-C9AB19098D2A` | Dutch website ad blocker |
| `0783DBFD-B5E0-4982-9B4A-711BDDB925B7` | Estonian website ad blocker |
| `1C6D8556-3400-4358-B9AD-72689D7B2C46` | Finnish website ad blocker |
| `9852EFC4-99E4-4F2D-A915-9C3196C7A1DE` | French website ad blocker |
| `E71426E7-E898-401C-A195-177945415F38` | German website ad blocker |
| `6C0F4C7F-969B-48A0-897A-14583015A587` | Greek website ad blocker |
| `85F65E06-D7DA-4144-B6A5-E1AA965D1E47` | Hebrew website ad blocker |
| `4C07DB6B-6377-4347-836D-68702CF1494A` | Hindi website ad blocker |
| `EDEEE15A-6FA9-4FAC-8CA8-3565508EAAC3` | Hungarian website ad blocker |
| `48796273-E783-431E-B864-44D3DCEA66DC` | Icelandic website ad blocker |
| `93123971-5AE6-47BA-93EA-BE1E4682E2B6` | Indonesian website ad blocker |
| `AB1A661D-E946-4F29-B47F-CA3885F6A9F7` | Italian website ad blocker |
| `03F91310-9244-40FA-BCF6-DA31B832F34D` | Japanese website ad blocker |
| `45B3ED40-C607-454F-A623-195FDD084637` | Korean website ad blocker |
| `15B64333-BAF9-4B77-ADC8-935433CD6F4C` | Latvian website ad blocker |
| `4E8B1A63-DEBE-4B8B-AD78-3811C632B353` | Lithuanian website ad blocker |
| `7BC951C6-B0B8-4223-97FC-3C22605734FC` | Macedonian website ad blocker |
| `8BEDBAA8-4FE2-4FEA-82F2-81B8124A4A74` | Nordic website ad blocker |
| `C3C2F394-D7BB-4BC2-9793-E0F13B2B5971` | Persian website ad blocker |
| `BF9234EB-4CB7-4CED-9FCB-F1FD31B0666C` | Polish website ad blocker |
| `AD3E8454-F376-11E8-8EB2-F2801F1B9FD1` | Romanian website ad blocker |
| `1088D292-2369-4D40-9BDF-C7DC03C05966` | Russian website ad blocker - AdGuard Russian |
| `80470EEC-970F-4F2C-BF6B-4810520C72E6` | Russian website ad blocker - RU AdList |
| `418D293D-72A8-4A28-8718-A1EE40A45AAF` | Slovenian website ad blocker |
| `AE657374-1851-4DC4-892B-9212B13B15A7` | Spanish website ad blocker |
| `1FEAF960-F377-11E8-8EB2-F2801F1B9FD1` | Spanish and Portuguese website ad blocker |
| `7DC2AC80-5BBC-49B8-B473-A31A1145CAC1` | Swedish website ad blocker |
| `658F092A-F377-11E8-8EB2-F2801F1B9FD1` | Thai website ad blocker |
| `1BE19EFD-9191-4560-878E-30ECA72B5B3C` | Turkish website ad blocker |
| `6A0209AC-9869-4FD6-A9DF-039B4200D52C` | Vietnamese website ad blocker |
| `564C3B75-8731-404C-AD7C-5683258BA0B0` | Experimental ad blocker |

### 查询来源与使用自定义订阅

```python
for item in filter_catalog():
    print(item["id"], item["title"], item["sources"])

config = AdblockConfig(
    lists=("easylist", "easyprivacy"),
    custom_urls=("https://your-domain.example/filters.txt",),
)
```

自定义 HTTPS 订阅网址写入 `custom_urls`，不要放进 `lists`；上面的域名是占位示例。未知 ID 会报错。`filter_catalog()` 只列目录，不发起下载；选中的规则在创建 Context 前按需下载并缓存。升级 SDK 后，以当前安装版本的 `filter_catalog()` 为准。

## SDK API 与原生 CDP

| SDK API | 用途 |
| --- | --- |
| `browser.new_context(adblock=AdblockConfig(...))` | 页面创建前配置过滤 |
| `context.set_adblock(config)` | 修改当前 Context 的完整过滤配置 |
| `context.adblock_status()` | 读取能力、模式、列表与网络拦截统计 |
| `filter_catalog()` | 枚举可选列表，不触发下载 |

同步 API 无需 `await`；异步 API 的三个浏览器/Context 方法需要 `await`。`set_adblock` 接收完整配置，而非部分字段补丁。

第三方 CDP 客户端也可连接配套 YSbrowser 的浏览器级会话，使用以下扩展命令；原版 Chrome 不提供这些命令。

| 命令 | 输入 | 返回 |
| --- | --- | --- |
| `Browser.setAdblockConfiguration` | `configuration`：JSON 字符串；`browserContextId`：可选 | `status`：JSON 字符串 |
| `Browser.getAdblockStatus` | `browserContextId`：可选 | `status`：JSON 字符串 |

```python
import asyncio
import json
from ysbrowser_sdk import AdblockConfig
from ysbrowser_sdk.adblock import prepare_adblock

# cdp 为客户端的浏览器级 CDP 会话；context_id 来自创建 Context 的返回值。
snapshot = await asyncio.to_thread(prepare_adblock, AdblockConfig(mode="standard"))
reply = await cdp.send("Browser.setAdblockConfiguration", {
    "browserContextId": context_id,
    "configuration": json.dumps(snapshot),
})
status = json.loads(reply["status"])
reply = await cdp.send("Browser.getAdblockStatus", {"browserContextId": context_id})
print(json.loads(reply["status"]))
```

快照中包含实际规则文本。CDP 不根据过滤列表 ID 自行下载订阅；建议使用 SDK 准备快照，再传递给本地或远程浏览器。不要把 SDK `AdblockConfig.to_dict()` 直接当作原生规则快照发送。


### 分别关闭 CSS 隐藏与规则脚本注入

每个 Context 可单独设置（网站自身的 JavaScript 不会被关闭）：

```python
AdblockConfig(mode="standard", cosmetic=False, scriptlets=False)
```

本次配套的 Windows 154、Linux 154、Windows 156 本地修复构建还支持浏览器进程级开关：

```text
--adblock-cosmetic=false --adblock-scriptlets=false
```

省略开关或传入 `true` 时允许 Context 自行配置；传入 `false` 后，SDK 或设置页重新配置也不能开启对应注入。两个开关都为 `false`、广告模式为 Standard 或 Aggressive 时，仅保留网络过滤；模式为 Disabled 时全部广告过滤关闭。可通过 `YSBrowser(..., args=["--adblock-cosmetic=false", "--adblock-scriptlets=false"])` 传入。两个进程开关随 YSbrowser 6.12 发布。

CLI `adblock-prepare` 同样默认 Disabled。要导出有效拦截规则，请明确指定 `--mode standard` 或 `--mode aggressive`。
