# Part 4 数据路径与缓存策略

数据 router 的请求缓存键由方法、供应商配置、参数和请求中的日期共同确定；带日期的历史请求因此不会命中另一个时点的数据。当前 TTL：

| 路径 | 类别 | TTL | 时点保护 |
|---|---|---:|---|
| 价格 | price | 盘中 15 分钟；收盘后策略 24 小时 | OHLCV 按请求日期过滤 |
| 技术指标 | technical | 15 分钟 | 使用请求日期计算 |
| 新闻 | news | 60 分钟 | 发布时间窗口过滤；覆盖不足标 unavailable |
| 宏观 | macro | 60 分钟（默认） | 上游按观察日期过滤 |
| 基本面/SEC | fundamental | 24 小时 | 有 filing date 的 SEC 记录按 as-of 过滤 |
| 内部人 | news | 60 分钟 | 历史无披露日期时 withheld |
| 社交 | social | 60 分钟 | 历史实时源不可用，不注入当前帖子 |
| 记忆教训 | 不走数据缓存 | — | 仅返回分析日期前已结算教训 |
| 标的身份 | identity | 7 天 | live profile 历史运行 withheld |

缓存默认位于 `data_cache_dir`。可通过 `CacheController` 的 TTL policy 调整；清理时删除缓存目录下 JSON 与 lock 文件。新增数据源时应使用唯一数据类别、供应商和完整请求参数构造 `CacheKey`，并对日期字段保留 `as_of`。

注：收盘后 TTL 策略可由 `TTLPolicy.for_request(..., market_open=False)` 选择；目前 router 尚未连接交易日历，因此线上 router 对价格使用盘中默认 TTL。
