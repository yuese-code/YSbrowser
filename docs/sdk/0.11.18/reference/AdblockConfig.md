# AdblockConfig

从 `ysbrowser_sdk.sync_api` 或 `ysbrowser_sdk.async_api` 导入。构造配置对象为同步操作。

```python signature
AdblockConfig(mode: 'str' = 'disabled', lists: 'tuple[str, ...]' = ('easylist', 'easyprivacy'), custom_urls: 'tuple[str, ...]' = (), cache_dir: 'str | None' = None, max_age_hours: 'float' = 24, offline: 'bool' = False, allow_stale: 'bool' = True, rule_scope: 'str' = 'all', cosmetic: 'bool' = True, scriptlets: 'bool' = True) -> None
```

| 参数 | 用途 |
| --- | --- |
| `mode` | 默认 `disabled`。开启过滤时选 `standard` 或 `aggressive`。 |
| `lists` | 过滤列表 ID，默认包含 EasyList 与 EasyPrivacy。显式传入时替换默认选择。 |
| `custom_urls` | 自定义 HTTPS 规则订阅，默认空。 |
| `cache_dir` | 指定规则缓存目录。 |
| `max_age_hours` | 缓存检查更新的间隔，默认 24 小时，可设 0–8760。 |
| `offline` | 只用本地缓存，默认关闭。 |
| `allow_stale` | 更新失败时允许使用已有规则缓存，默认开启。 |
| `rule_scope` | 默认 `all`。选择 `network` 时仅使用网络过滤。 |
| `cosmetic` | 启用过滤且范围为 `all` 时控制 CSS 隐藏，默认开启。 |
| `scriptlets` | 启用过滤且范围为 `all` 时控制规则脚本注入，默认开启。 |

## AdblockConfig.to_dict

```python signature
to_dict() -> dict
```

返回配置字典，列表 ID 和自定义订阅为 JSON 数组。准备原生 CDP 规则快照时请使用 [广告过滤手册](../adblock.md) 中的快照接口。
