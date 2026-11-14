# 广告与跟踪请求过滤

需要包含原生广告过滤接口的 YSbrowser 构建。新版浏览器的 SDK Context 默认使用 Standard；旧版浏览器不会被误报为已开启，显式配置时会提示升级。

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

Windows 可将最后一行替换为实际 `ysbrowser.exe` 路径。浏览器不自动安装全部列表；无规则时弹窗明确提示尚未加载。工具栏只提供本站三模式选择、已拦截请求数量及可展开详情。详情最多保留最近 256 条，请求 URL 去除查询参数和凭据。

执行范围包括网络请求、HTTP 重定向检查、页面和 Worker WebSocket、固定本地替代资源、CSS 隐藏和 scriptlet。`adblock_status()` 返回实际能力与列表统计。拦截计数仅统计网络请求，不把隐藏元素或脚本执行次数混入。

`rule_scope="network"` 只执行网络过滤；`rule_scope="all"` 可分别通过 `cosmetic=False` 或 `scriptlets=False` 关闭页面过滤的一部分。命令行快照支持 `--rule-scope network`、`--no-cosmetic`、`--no-scriptlets`。旧浏览器没有完整能力时，显式请求完整范围会报兼容性错误，不会静默宣称生效。

普通 CSS 隐藏保留 DOM，原始字段仍可读取；列表中显式的 `:remove()` 等动作会修改 DOM。动态元素、开放的 Shadow DOM 与子框架会重新检查。Standard 的基础隐藏规则主要处理第三方内容，Aggressive 同时处理第一方；主动选择的可选、自定义列表可以处理第一方。scriptlet 在匹配文档的页面脚本之前运行，只能调用随引擎固定的资源函数，不执行订阅中的任意原始 JavaScript，特权 `trusted-*` 资源不会向普通订阅开放。

模式或配置更新会恢复仍由过滤器控制的隐藏样式；已执行的脚本和删除动作不能撤销，需要重新加载文档。SDK 和工具栏不会为此自动刷新业务页面。CSS 隐藏、脚本注入和网络拦截均可能影响网站功能，采集完整性必须以原始字段校验为准。

引擎固定为 Brave adblock-rust 0.13.5，脚本与替代资源固定版本。随浏览器提供 `ys_adblock_NOTICES.txt`、对应引擎及资源源码归档和许可证；过滤列表仍由 SDK 按需下载。

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
