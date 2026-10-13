"""morning-bites: 中文界面的译文(app/zh.py 用)。

三种条目:
  CATALOG    整句对照, 键是页面上出现的英文原句(去掉首尾空白)。
  TEMPLATES  句型, (正则, 中文格式串)。整句 fullmatch; 捕获组按 {0} {1} … 填回,
             填回前每个捕获组自己再翻一遍(所以「5h 19m」这类片段只写一次)。
  EMBEDDED   嵌在 components.html 里的 JS / 配置, 原样字符串替换。

有意偏离英文原文的中文(按本站实际改写, 合并上游时别「修正」回去):
  数据源写成 Cboe / 「数据源」而不是 Yahoo Finance; 采集靠定时任务(09:03 / 16:23)而不是
  worker 容器或按钮; gamma 优先用 Cboe 厂商值; 最大痛点按指南 57 个到期日的实测改写为
  「描述而非预测」; 筛选器是勾选「查看详情」而不是点击整行。

术语与晨刊一致: Call 墙 / Put 墙 / 翻转位 / 净 GEX / 认沽/认购比 / 未平仓量(OI)/
隐含波动率(IV)/ 最大痛点。数值、代码、日期一律不译。
"""

CATALOG: dict[str, str] = {
    "Language": "语言",  # 右上角切换(标签隐藏, 读屏会读)
    "cboe": "Cboe",  # 句中出现的数据源名(库里存小写)
    "yahoo": "Yahoo",
}
TEMPLATES: list[tuple[str, str]] = []


# ===== 页头、侧栏、合约卡片与各模块的句子(天气 / 新鲜度 / 开收盘 / 代码建议 / 采集状态 / 指南链接 / 希腊值解读) =====

CATALOG.update({
    # dashboard.py:116 howto() 默认标题
    "ℹ️ How to read this": "ℹ️ 怎么读",

    # dashboard.py:138-139
    "📌 pinned": "📌 已固定",
    "📌 Pin": "📌 固定",
    # dashboard.py:146
    "No history for the selected contract.": "所选合约没有历史数据。",
    # dashboard.py:154
    "Option price": "期权价格",
    # dashboard.py:157-162 (howto("Contract") 里的 st.write)
    "Price history of this specific contract (last price at each collection). "
    "Compare the option's price action with the underlying's move and with the IV "
    "dynamics below — if the option is gaining faster than the stock move explains, "
    "it's likely volatility itself that's rising (see Vega in the greeks block).":
        "这张合约的价格历史(每次采集时的最新成交价)。把期权的价格走势与标的的涨跌、"
        "以及下方的 IV 变化对照着看——如果期权涨得比股价变动所能解释的更快,"
        "多半是波动率本身在上升(见希腊值区块里的 Vega)。",
    # dashboard.py:164
    "Contract implied volatility": "合约隐含波动率",
    # dashboard.py:183-187
    "IV well above RV — the market is pricing a premium for future uncertainty "
    "(normal ahead of earnings/events). IV below RV is a rare situation — the option "
    "may be underpriced relative to the underlying's actual recent volatility.":
        "IV 明显高于 RV——市场在为未来的不确定性计入溢价(财报/重大事件前很常见)。"
        "IV 低于 RV 的情况很少见——相对于标的近期的实际波动,期权可能被低估了。",
    # dashboard.py:189-192
    "Realized volatility of the underlying: not stored yet — it is written once a day "
    "by the collection pass, so it appears after the next collection.":
        "标的的已实现波动率:尚未存储——它由采集流程每天写入一次,下次采集后就会出现。",
    # dashboard.py:194
    "Greeks over time": "希腊值走势",
    # dashboard.py:199 target.caption(greek.capitalize()) 与 dashboard.py:249 瀑布图类目轴。
    # 希腊值按术语表保留英文; 这几条恒等条目不能删: zh._walk_spec 只在类目轴「每个值都在
    # CATALOG 里」时才翻 x, 少一个 Start/End/Residual 就整条轴不翻。
    "Delta": "Delta",
    "Gamma": "Gamma",
    "Theta": "Theta",
    "Vega": "Vega",
    "Rho": "Rho",
    "Vanna": "Vanna",
    "Charm": "Charm",
    "Start": "起点",
    "Residual": "残差",
    "End": "终点",
    # dashboard.py:205
    "📊 Interpreting current values and their trend": "📊 解读当前数值及其趋势",

    # dashboard.py:222
    "Where the price went": "价格去哪了",
    # dashboard.py:241-245
    "Not enough usable days yet to split the price change by greek. This needs "
    "at least two days whose implied volatility passed the data-quality guard — "
    "and with collection on a schedule, days that are actually a day apart.":
        "可用的天数还不够,暂时无法按希腊值拆分价格变化。至少需要两天的隐含波动率"
        "通过数据质量检查——而且要定时采集,让这些天真的相隔一天。",
    # dashboard.py:265 瀑布图 y 轴题
    "¢ per share": "¢ / 股",
    # dashboard.py:272
    "Running total by day, in cents — when each greek did its work":
        "按日累计(美分)——每个希腊值在哪些天起了作用",

    # dashboard.py:501-504 页首副标题
    "Open-source options positioning dashboard — dealer gamma exposure, max pain, "
    "open interest, and IV surface for your whole watchlist.":
        "开源期权持仓看板——做市商 Gamma 敞口、最大痛点、未平仓量与 IV 曲面,"
        "覆盖你的整个关注列表。",

    # dashboard.py:507 侧边栏
    "Watchlist": "关注列表",
    # dashboard.py:540-554
    "Add ticker": "添加代码",
    "AAPL or Apple": "AAPL 或 Apple",
    "Search by symbol or company name, or type a symbol that is not "
    "listed. Data comes from Yahoo Finance (yfinance), and not every "
    "listed chain is available there. US-listed options only — European "
    "and Asian listings (SAP.DE, ASML.AS) have no options data here, but "
    "most large non-US companies also trade in the US as ADRs, which do: "
    "try ASML, SAP, SHEL, NVO, BUD.":
        "按代码或公司名搜索,也可以直接输入列表里没有的代码。本站数据来自 Cboe 的延迟行情"
        "(SPY、QQQ、SPX 与晨刊共用同一份),并不是每条挂牌的期权链都取得到。只支持美国上市的期权——"
        "欧洲和亚洲的挂牌(SAP.DE、ASML.AS)在这里没有期权数据,但大多数大型非美公司"
        "也以 ADR 形式在美国交易,ADR 是有期权数据的:可以试试 ASML、SAP、SHEL、NVO、BUD。",
    # dashboard.py:563-567
    "The symbol directory has not been downloaded yet, so this box cannot "
    "search by company name — type the symbol itself. It arrives on the "
    "collector's next pass.":
        "代码目录还没有下载,所以这个框暂时不能按公司名搜索——请直接输入代码。"
        "采集器下一轮运行时会把目录取来。",
    # dashboard.py:617-620
    "History for a new ticker starts at the first collection — the first "
    "chart will have one point, and fills in from there.":
        "新代码的历史从第一次采集开始——第一张图只有一个点,之后逐步补满。",
    # dashboard.py:622
    "Add": "添加",
    # dashboard.py:680-685
    "Collect data": "采集数据",
    "Best run while the US options market is open. Outside market "
    "hours, Yahoo Finance often reports open_interest=0 across the whole "
    "chain; such a chain is not stored, and is not counted as a failure.":
        "立即手动采集一次, 最好在美国期权市场开盘时点。本站已由定时任务在工作日纽约时间 09:03 与 16:23 自动采集, 一般不用点。"
        "非交易时段数据源常把整条期权链的 open_interest 报为 0;这样的期权链不会保存,也不计为失败。",
    # dashboard.py:687 st.spinner
    "Collecting data...": "正在采集数据…",
    # dashboard.py:716-720
    "Collect automatically": "自动采集",
    "Runs in the background worker container, not in this page — it keeps "
    "collecting while nobody is looking, and stops when you stop the containers.":
        "本站的采集由服务器上的定时任务完成(工作日纽约时间 09:03 与 16:23), 不受这里控制。"
        "这里的间隔只用来判断页面上的数据算不算过期: 请保持「每 4 小时」, 改小了页面会整天提示数据过期。",
    # config.py:113-119 COLLECTOR_INTERVAL_CHOICES(下拉选项显示名)
    "Off": "关闭",
    "Every 15 minutes": "每 15 分钟",
    "Hourly": "每小时",
    "Every 4 hours": "每 4 小时",
    "Once a day": "每天一次",
    # dashboard.py:747-750
    "Collect once first and this will say how much disk a month of collection "
    "costs for your watchlist.":
        "先采集一次,这里就会显示按你的关注列表采集一个月要占多少磁盘。",
    # dashboard.py:762-767
    "**Outside market hours the collector does not run.** US options trade "
    "09:30–16:00 New York on weekdays; while the market is shut the chain does not "
    "change, so one snapshot per closed day is taken as a safety net and the rest "
    "are skipped — roughly four fifths of the week not spent on duplicates.":
        "**非交易时段采集器不运行。**美国期权在工作日纽约时间 09:30–16:00 交易;"
        "休市期间期权链不会变化,所以每个休市日只取一张快照兜底,其余全部跳过——"
        "一周里大约五分之四的时间因此不必花在重复数据上。",
    # dashboard.py:769
    "Automatic collection is off. Use the button above to collect on demand.":
        "自动采集已关闭。需要时用上面的按钮手动采集。",
    # dashboard.py:785
    "📋 Collection log": "📋 采集日志",
    # dashboard.py:789
    "No collections yet.": "还没有采集记录。",

    # dashboard.py:819
    "Add a ticker to the watchlist on the left to get started.":
        "先在左侧把代码加入关注列表。",
    # dashboard.py:822
    "Ticker to analyze": "要分析的标的",
    # dashboard.py:831
    "Slower on tickers with a long collection history.": "采集历史长的标的加载会更慢。",

    # dashboard.py:1001-1006 视图切换(分段控件的选项与折叠的标签)
    "View": "视图",
    "Overview": "概览",
    "Changes": "变化",
    "Max Pain / GEX": "最大痛点 / GEX",
    "GEX Heatmap": "GEX 热力图",
    "Volatility (IV)": "波动率(IV)",
    "Contract": "合约",
    "Screener": "筛选器",
    "Unusual Activity": "异常成交",
    "OI Delta": "OI 变化",

    # metrics_core.py:1736-1742 interpret_greeks 的 trend()(作为捕获组再翻)
    "(not enough reliable data to compare with the previous snapshot)":
        "(可靠数据不足,无法与上一快照比较)",
    "(unchanged since the previous snapshot)": "(与上一快照相比没有变化)",
    "(up since the previous snapshot)": "(较上一快照上升)",
    "(down since the previous snapshot)": "(较上一快照下降)",
    # metrics_core.py:1747-1748 Rho / 1751-1752 Vanna 没有运行时值以外的片段, 见 TEMPLATES

    # weather.py:24-45 WEATHER_WORDS
    "Clear": "晴",
    "Fair": "晴间多云",
    "Unsettled": "多变",
    "Showers": "阵雨",
    "Storm": "风暴",
    "Positive gamma with the flip far off — dealer hedging is damping moves.":
        "正 Gamma,且离翻转位很远——做市商对冲正在抑制波动。",
    "Positive gamma, but the flip is within reach — the damping may not hold.":
        "正 Gamma,但翻转位近在咫尺——抑制作用未必守得住。",
    "The price is sitting on the gamma flip — the regime can turn either way.":
        "价格正落在 Gamma 翻转位上——格局可能朝任一方向转变。",
    "Negative gamma, though the flip is close — moves are amplified for now.":
        "负 Gamma,不过翻转位已经不远——眼下波动仍会被放大。",
    "Negative gamma and no boundary nearby — dealer hedging amplifies moves.":
        "负 Gamma,附近也没有边界——做市商对冲会放大波动。",
    # weather.py:204-216 panel() 的数值标签(<dt>)
    "Price": "价格",
    "Net GEX": "净 GEX",
    "Call wall": "Call 墙",
    "Put wall": "Put 墙",
    "Gamma flip": "翻转位",
    "Distance": "距翻转位",
    # weather.py:218-226 panel() 范围眉题(<span> 文字节点, 去首尾空白后)
    "· gamma weather": "· Gamma 天气",
    "· gamma weather · from an earlier collection than the rest of this screen":
        "· Gamma 天气 · 来自比本页其余内容更早的一次采集",

    # market_calendar.py:333 time_to_open_phrase
    "opening now.": "马上开盘。",
    # market_calendar.py:367 status_note
    "Market open — the first collection of the session has not landed yet.":
        "开盘中——本交易时段的第一次采集还没到。",

    # collector.py:58-66 ZeroOpenInterestChain 的两种原因(作为捕获组再翻)
    "the market is closed, and outside regular hours the data source "
    "reports open interest as zero across most of the chain; not saving, and "
    "not counted as a failure. The next session's collection will store it.":
        "当前休市,常规时段之外数据源会把大部分合约的未平仓量报为零;不保存,也不计为失败。"
        "下一个交易时段的采集会把它存下来。",
    "during the session, so the data source returned a corrupted or incomplete "
    "snapshot; not saving.":
        "发生在交易时段内,说明数据源返回了损坏或不完整的快照;不保存。",
    # collector.py:194
    "Empty option chain": "期权链为空",

    # guide.py:29-39 VIEW_LESSONS 的课名(title 提示里作为捕获组再翻)
    "The put/call ratio": "认沽/认购比",
    "Reading positioning day to day": "逐日解读持仓",
    "Max pain": "最大痛点",
    "How to read a GEX heatmap": "怎么读 GEX 热力图",
    "Implied volatility, skew and the expected move": "隐含波动率、偏斜与预期波动",
    "Option greeks: where the price went": "期权希腊值:价格去哪了",
    "The options chain": "期权链",
    "Unusual options activity": "期权异常成交",
    "Open interest changes day to day": "未平仓量的逐日变化",
})

_TREND = (r"( \((?:not enough reliable data to compare with|unchanged since|up since|down since)"
          r" the previous snapshot\))?")
_AGE = r"(\d+[dhm](?: \d+[hm])?)"
_Q = r"“([^”]+)”"
_CARRY = r" tracks the same underlying and is fully supported — the analytics carry over\."

TEMPLATES += [
    # --- 时长片段: freshness.py:179-185 age_phrase, market_calendar.py:338-341 ---
    (r"(\d+)d (\d+)h", "{0} 天 {1} 小时"),
    (r"(\d+)d", "{0} 天"),
    (r"(\d+)h (\d+)m", "{0} 小时 {1} 分钟"),
    (r"(\d+)h", "{0} 小时"),
    (r"(\d+)m", "{0} 分钟"),
    # market_calendar.py:337-342 time_to_open_phrase
    (r"opens in ([0-9dhm ]+)\.", "{0}后开盘。"),
    # market_calendar.py:368 status_note
    (r"Market closed — (opening now\.|opens in [0-9dhm ]+\.) The chain does not change until then\.",
     "休市——{0}在那之前期权链不会变化。"),

    # --- 日期 %d %b %Y(dashboard.py:615, 664), 月份逐个写 ---
    (r"(\d{2}) Jan (\d{4})", "{1}-01-{0}"),
    (r"(\d{2}) Feb (\d{4})", "{1}-02-{0}"),
    (r"(\d{2}) Mar (\d{4})", "{1}-03-{0}"),
    (r"(\d{2}) Apr (\d{4})", "{1}-04-{0}"),
    (r"(\d{2}) May (\d{4})", "{1}-05-{0}"),
    (r"(\d{2}) Jun (\d{4})", "{1}-06-{0}"),
    (r"(\d{2}) Jul (\d{4})", "{1}-07-{0}"),
    (r"(\d{2}) Aug (\d{4})", "{1}-08-{0}"),
    (r"(\d{2}) Sep (\d{4})", "{1}-09-{0}"),
    (r"(\d{2}) Oct (\d{4})", "{1}-10-{0}"),
    (r"(\d{2}) Nov (\d{4})", "{1}-11-{0}"),
    (r"(\d{2}) Dec (\d{4})", "{1}-12-{0}"),

    # --- 侧边栏 ---
    # dashboard.py:615
    (r"Already collected since ([^.]+)\.", "自 {0} 起已在采集。"),
    # dashboard.py:662-666 停采代码按钮的 help
    (r"Not being collected: every attempt has failed since ([^,]+), and nothing has ever been "
     r"collected for it\. Check the spelling, or remove it\. Nothing has been deleted\.",
     "已停止采集:自 {0} 起每次尝试都失败,且从未采集到任何数据。请检查拼写,或将其移除。"
     "没有删除任何数据。"),
    # dashboard.py:691 / 695 / 699 / 701 采集结果(status 来自 collector.py, 再翻)
    (r"([^\s:<>]+): OK", "{0}:成功"),
    (r"([^\s:<>]+): ((?:skipped|closed|failed): .+)", "{0}:{1}"),
    # collector.py 的 status 前缀; 带「已停采」尾巴的那种写在前面
    (r"failed: (.+?) — this symbol has now failed (\d+) times without ever collecting anything, "
     r"so it will not be requested again\. Nothing has been deleted\.",
     "失败:{0}——这个代码已失败 {1} 次且从未采集到任何数据,今后不再请求。没有删除任何数据。"),
    (r"failed: (.+)", "失败:{0}"),
    (r"closed: (.+)", "休市:{0}"),
    (r"skipped: (.+)", "已跳过:{0}"),
    # collector.py:146-149 冷却中
    (r"the data source is limiting requests from this installation\. Nothing will be collected "
     r"until (\d{2}:\d{2}) UTC\.",
     "数据源正在限制本实例的请求。UTC {0} 之前不会采集任何数据。"),
    # collector.py:176-180 停采
    (r"no snapshot has ever been collected for this symbol after (\d+) attempts\. Nothing has "
     r"been deleted; remove it from the watchlist, or fix the symbol and add it again\.",
     "这个代码尝试了 {0} 次,一张快照也没采集到。没有删除任何数据;请把它从关注列表移除,"
     "或改正代码后重新添加。"),
    # collector.py:203-206 morning-bites 同一报价时刻
    (r"the source's quote time (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) UTC is already stored "
     r"— nothing new to collect\.",
     "数据源的报价时刻 {0} UTC 已经存过——没有新数据可采集。"),
    # collector.py:245-248 被限流
    (r"the data source is limiting requests from this installation \((.*)\)\. Collection is "
     r"paused until (\d{2}:\d{2}) UTC\.",
     "数据源正在限制本实例的请求({0})。采集暂停到 UTC {1}。"),
    # collector.py:256-259 限流后其余代码
    (r"collection paused because the data source is limiting requests\. Next attempt after "
     r"(\d{2}:\d{2}) UTC\.",
     "数据源正在限制请求,采集已暂停。UTC {0} 之后再试。"),
    # collector.py:55-67 ZeroOpenInterestChain(原因句在 CATALOG)
    (r"(\d+%) of contracts have open_interest=0 \(threshold (\d+%)\) — (.+)",
     "{0} 的合约 open_interest=0(阈值 {1})——{2}"),
    # providers/yahoo.py:124-128 Yahoo 取不到现价(原始异常里唯一已知的一种)
    (r"no price for (\S+) — either the symbol does not exist, or Yahoo Finance is rate-limiting "
     r"this installation\. Check the spelling first; if it is right, wait a few minutes and "
     r"collect again\.",
     "取不到 {0} 的价格——要么这个代码不存在,要么 Yahoo Finance 正在限制本实例的请求。"
     "先检查拼写;拼写无误的话,等几分钟再采集。"),

    # dashboard.py:735-745 磁盘增长(有/无「尚未计入」两种)
    (r"About ([\d.,]+) GB per month at this interval, for your current watchlist\. Nothing is "
     r"ever deleted; expired contracts move to a separate table after (\d+) days\. Not counted "
     r"yet: (.+?) — (?:it has|they have) not been collected, so there is no chain size to measure\.",
     "按这个间隔,当前关注列表每月约增长 {0} GB。数据从不删除;到期合约过 {1} 天后移到单独的表。"
     "尚未计入:{2}——还没有采集过,无从测算期权链大小。"),
    (r"About ([\d.,]+) GB per month at this interval, for your current watchlist\. Nothing is "
     r"ever deleted; expired contracts move to a separate table after (\d+) days\.",
     "按这个间隔,当前关注列表每月约增长 {0} GB。数据从不删除;到期合约过 {1} 天后移到单独的表。"),
    # dashboard.py:777-783 冷却警告
    (r"\*\*The data source is limiting requests\.\*\* Collection is paused until (\d{2}:\d{2}) "
     r"\(([^()]+)\)\. This is not the market being closed — it is Yahoo Finance refusing requests "
     r"from this installation, usually after too many in a short time\. Nothing is lost; the next "
     r"pass collects as usual\.",
     "**数据源正在限制请求。**采集暂停到 {0}({1})。这不是休市——是数据源在拒绝本实例的"
     "请求,通常是因为短时间内请求太多。没有丢失任何数据;下一轮照常采集。"),
    # dashboard.py:786
    (r"Times in your own timezone \(([^()]+)\)\.", "时间按你所在的时区显示({0})。"),
    # dashboard.py:805-815
    (r"`oi_zero_fraction` — the fraction of contracts with open_interest=0 in the collected chain\. "
     r"Above (\d+%) the snapshot is considered suspect and is not saved \(status=failed, reason in "
     r"`error_message`\), even if the request to the data source itself completed without a network "
     r"error\. The most common cause is collecting outside regular market hours — Yahoo Finance often "
     r"reports open_interest=0 across the whole chain while the market is closed\. Those runs say so "
     r"in `error_message` and are not counted as failures: they do not raise the \"collection is "
     r"failing\" note or suspend a symbol\. The same refusal during a session is a real failure\.",
     "`oi_zero_fraction`——采集到的期权链中 open_interest=0 的合约占比。超过 {0} 时这份快照被视为"
     "可疑、不予保存(`status=failed`,原因写在 `error_message`),即使向数据源的请求本身没有网络错误。"
     "最常见的原因是在常规交易时段之外采集——休市时数据源常把整条期权链的 open_interest "
     "报为 0。这类运行会在 `error_message` 里注明,不计为失败:不会触发「采集持续失败」的提示,"
     "也不会让代码被停采。交易时段内出现同样的拒收,才是真正的失败。"),

    # --- 主区 ---
    # dashboard.py:829
    (r"Load full history \(default: last (\d+) days\)", "加载全部历史(默认:最近 {0} 天)"),
    # dashboard.py:941
    (r"No data for (.+?)\. Click “Collect data” on the left\.",
     "{0} 还没有数据。请点左侧的「采集数据」。"),
    # dashboard.py:950-954
    (r"Showing data from \*\*([^*]+)\*\*\. This ticker also has history from (.+?), which is kept "
     r"but not shown: two providers calculate implied volatility differently, so mixing them on one "
     r"chart would draw moves that never happened\.",
     "当前显示来自 **{0}** 的数据。这个标的还有来自 {1} 的历史,已保留但不显示:两个数据源计算"
     "隐含波动率的方法不同,混在一张图上会画出从未发生过的波动。"),

    # freshness.py:118-122
    (r"\*\*Nothing has been collected for this symbol yet\.\*\* The last (\d+) attempts failed\. "
     r"It may not be listed with the current data source\.",
     "**这个代码还没有采集到任何数据。**最近 {0} 次尝试都失败了。当前数据源可能没有收录它。"),
    # freshness.py:134-138
    (r"\*\*Collection for this symbol is failing\.\*\* The last (\d+) attempts were refused; the "
     r"newest data here is from " + _AGE + r" ago\. Other symbols are unaffected\.",
     "**这个代码的采集持续失败。**最近 {0} 次尝试都被拒绝;这里最新的数据来自 {1}前。"
     "其他代码不受影响。"),
    # freshness.py:158-162
    (r"Market closed since the last collection \(" + _AGE + r" ago\)\. The chain does not change "
     r"until the next session\.",
     "自上次采集({0}前)以来一直休市。下一个交易时段开始前期权链不会变化。"),
    # freshness.py:165-169
    (r"\*\*This data is " + _AGE + r" old\.\*\* The market has been open for " + _AGE + r" since "
     r"the last successful collection, so this is not the market being closed\.",
     "**这些数据已是 {0}前的了。**自上次成功采集以来,市场已开盘 {1},所以这不是休市造成的。"),

    # --- suggestions.py(侧边栏 warning / error 与主区 ⛔, 以及 collector 的 skipped:) ---
    # suggestions.py:308-312 系列根代码
    (_Q + r" is a series of (.+?) options rather than an underlying: (.+?) serves those contracts "
     r"inside the (.+?) chain\. Add \*\*(.+?)\*\* to collect them\.",
     "「{0}」是 {1} 期权的一个系列,而不是标的:{2} 在 {3} 的期权链里提供这些合约。"
     "添加 **{4}** 即可采集它们。"),
    # suggestions.py:314-318 数据源不提供, 有替代
    (_Q + r" is a real symbol with listed options, but (.+?) does not serve its option chain, so "
     r"there would be nothing to collect\. \*\*(.+?)\*\*" + _CARRY,
     "「{0}」是有挂牌期权的真实代码,但 {1} 不提供它的期权链,所以无从采集。"
     "**{2}** 跟踪同一标的,完全支持——各项分析照样适用。"),
    # suggestions.py:322-328 VIX
    (_Q + r" is a real symbol with listed options, but they are priced off VIX futures, which (.+?) "
     r"does not serve — every greek computed here would be wrong, so it is not collected\. There is "
     r"no honest substitute: an ETF on VIX futures is a different instrument with its own term "
     r"structure, not a proxy for the index\.",
     "「{0}」是有挂牌期权的真实代码,但这些期权以 VIX 期货定价,而 {1} 不提供 VIX 期货——"
     "在这里算出的每个希腊值都会是错的,所以不采集。没有诚实的替代品:VIX 期货 ETF 是另一种工具,"
     "有自己的期限结构,不能代替指数。"),
    # suggestions.py:335-341 货币对 / 金属 / 指数名
    (_Q + r" has no US-listed options of its own\. \*\*(.+?)\*\*" + _CARRY,
     "「{0}」本身没有美国上市的期权。**{1}** 跟踪同一标的,完全支持——各项分析照样适用。"),
    (_Q + r" has no US-listed options of its own\. Currency pairs have no US-listed options at all "
     r"— this product covers what trades on US options exchanges\.",
     "「{0}」本身没有美国上市的期权。货币对根本没有美国上市的期权——本产品只覆盖在美国期权"
     "交易所交易的品种。"),
    # suggestions.py:355-366 非美挂牌
    (_Q + r" is a listing on a non-US exchange, and this product covers options listed in the US\. "
     r"\*\*(.+?)\*\* is the same company's US listing and is fully supported — the analytics carry over\.",
     "「{0}」是非美国交易所的挂牌,本产品只覆盖在美国上市的期权。**{1}** 是同一家公司在美国的挂牌,"
     "完全支持——各项分析照样适用。"),
    (_Q + r" is a listing on a non-US exchange, and this product covers options listed in the US\. "
     r"Most large non-US companies also trade here as ADRs — try the US symbol if there is one\.",
     "「{0}」是非美国交易所的挂牌,本产品只覆盖在美国上市的期权。大多数大型非美公司也以 ADR "
     "形式在美国交易——如果有美国代码,请试那个。"),
    # suggestions.py:373-376 疑似拼错
    (_Q + r" has no listed options, so there is nothing to collect for it\. Did you mean "
     r"\*\*(.+?)\*\*\?",
     "「{0}」没有挂牌期权,无从采集。你是不是想输入 **{1}**?"),
    # suggestions.py:444-447 兜底
    (_Q + r" has no listed options, so there is nothing to collect for it\. Check the symbol as it "
     r"trades in the US\.",
     "「{0}」没有挂牌期权,无从采集。请按它在美国交易时的代码核对。"),

    # --- render_option_detail / render_greek_attribution ---
    # dashboard.py:175-182 合约 IV 与标的 RV(末尾的「RV(10d) **x%** · …」原样)
    (r"Current contract IV: \*\*(.+?)\*\*\. Realized volatility of the underlying \(close-to-close, "
     r"from (.+?) daily closes as of (.+?) — its depth doesn't depend on how many days we've been "
     r"collecting option chains, which is why it isn't drawn as a line on the same chart: the time "
     r"scales are too different\): (.*)",
     "当前合约 IV:**{0}**。标的的已实现波动率(收盘到收盘,基于 {1} 截至 {2} 的日收盘价——"
     "它能回溯多久与我们采集了多少天期权链无关,所以没有画在同一张图上:两者的时间尺度差得太远):{3}"),
    # dashboard.py:233-239
    (r"This contract traded under (\d+)c on (\d+) of the day\(s\) collected, and the split is not "
     r"shown for those: at a few cents a contract, every greek is arithmetic about rounding and the "
     r"decomposition would be noise reported as a finding\. Deeper in-the-money contracts on this "
     r"ticker will show it\.",
     "已采集的交易日中有 {1} 天这张合约的成交价低于 {0}c,这些天不显示拆分:合约只值几美分时,"
     "每个希腊值都只是在算舍入,拆出来的只是被当成结论的噪声。这个标的上实值更深的合约会显示拆分。"),
    # dashboard.py:285-289
    (r"A day is the LAST collection of each trading day, New York time — (\d+) interval\(s\) in this "
     r"window\. Collect on a schedule for these numbers to mean what they say\.",
     "这里的「一天」指每个交易日(纽约时间)的最后一次采集——本窗口内共 {0} 个区间。"
     "要让这些数字名副其实,请定时采集。"),
    # dashboard.py:291-317 ⚠️ 注记(st.caption(f"⚠️ {note}"))
    (r"⚠️ (\d+) day\(s\) left out: the contract traded below (\d+)c there, where implied volatility "
     r"inverted from a one-cent quote makes every greek meaningless\.",
     "⚠️ 剔除了 {0} 天:那几天合约成交价低于 {1}c,用一美分报价反解出的隐含波动率会让每个希腊值"
     "都失去意义。"),
    (r"⚠️ (\d+) day\(s\) left out: their implied volatility failed the outlier guard, so the greeks "
     r"are missing rather than wrong\.",
     "⚠️ 剔除了 {0} 天:这几天的隐含波动率没通过离群值检查,所以希腊值是缺失,而不是算错。"),
    (r"⚠️ (\d+) trading day\(s\) inside the window were never collected — their moves are folded "
     r"into the neighbouring interval, not counted as zero\. The gamma term approximates a move "
     r"locally; over a stretched interval it approximates less well, and the difference lands in the "
     r"residual\.",
     "⚠️ 窗口内有 {0} 个交易日从未采集——这些天的变动并入相邻区间,而不是按零计算。Gamma 项是对"
     "价格变动的局部近似;区间被拉长后近似变差,差额落进残差。"),
    (r"⚠️ The residual is (\d+%) of the whole move: the model does not explain this contract — the "
     r"spread, a stale print or a rate move did more than the greeks\.",
     "⚠️ 残差占整个变动的 {0}:模型解释不了这张合约——买卖价差、过时的成交价或利率变动起的作用"
     "比希腊值还大。"),

    # --- metrics_core.py:1744-1763 interpret_greeks(经 st.write(f"- {note}")) ---
    (r"- Delta (\S+)" + _TREND + r" — for a \$1 move in the underlying, the contract price changes "
     r"by roughly \$(\S+)\.",
     "- Delta {0}{1} —— 标的每变动 $1,合约价格大约变动 ${2}。"),
    (r"- Gamma (\S+)" + _TREND + r" — how fast delta itself changes per \$1 move in the underlying; "
     r"the higher it is, the sharper dealers' hedging needs shift\.",
     "- Gamma {0}{1} —— 标的每变动 $1,Delta 本身变化多快;数值越高,做市商的对冲需求变化越剧烈。"),
    (r"- Theta (\S+)" + _TREND + r" — the contract loses roughly \$(\S+) per day from the passage of "
     r"time alone, all else equal\.",
     "- Theta {0}{1} —— 其他条件不变时,仅因时间流逝,合约每天大约损失 ${2}。"),
    (r"- Vega (\S+)" + _TREND + r" — a 1 pp rise in implied volatility changes the contract price by "
     r"roughly \$(\S+)\.",
     "- Vega {0}{1} —— 隐含波动率每上升 1 个百分点,合约价格大约变动 ${2}。"),
    (r"- Rho (\S+)" + _TREND + r" — sensitivity to the interest rate, usually a secondary factor for "
     r"options under a one-year horizon\.",
     "- Rho {0}{1} —— 对利率的敏感度,对期限一年以内的期权通常是次要因素。"),
    (r"- Vanna (\S+)" + _TREND + r" — how delta responds to a change in volatility \(symmetrically: "
     r"how vega responds to a price move\)\.",
     "- Vanna {0}{1} —— Delta 对波动率变化的反应(反过来看也一样:Vega 对价格变动的反应)。"),
    (r"- Charm (\S+)" + _TREND + r" — how much delta \"ages\" over one year at an unchanged price, "
     r"i\.e\. about (\S+) per day \(time decay of delta itself, not of the contract price\)\.",
     "- Charm {0}{1} —— 价格不变时,Delta 在一年里「老化」多少,即每天约 {2}"
     "(这是 Delta 本身的时间衰减,不是合约价格的)。"),

    # --- weather.py ---
    # weather.py:94-104 describe() 没有翻转位时的句子
    (r"This chain has no gamma flip within (\d+%) of the price, so only the sign of gamma is known "
     r"— positive, hedging damps moves\.",
     "这条期权链在距价格 {0} 以内没有 Gamma 翻转位,所以只知道 Gamma 的正负——为正,"
     "对冲在抑制波动。"),
    (r"This chain has no gamma flip within (\d+%) of the price, so only the sign of gamma is known "
     r"— negative, hedging amplifies moves\.",
     "这条期权链在距价格 {0} 以内没有 Gamma 翻转位,所以只知道 Gamma 的正负——为负,"
     "对冲在放大波动。"),
    # weather.py:92 describe() 的 scope(单独出现时)
    (r"next (\d+) days · (\d+) (?:expiry|expiries)", "未来 {0} 天 · {1} 个到期日"),
    # weather.py:218-226 panel() 范围眉题, 有 scope 的两种(无 scope 的两种在 CATALOG)
    (r"· gamma weather · next (\d+) days · (\d+) (?:expiry|expiries)",
     "· Gamma 天气 · 未来 {0} 天 · {1} 个到期日"),
    (r"· gamma weather · next (\d+) days · (\d+) (?:expiry|expiries) · from an earlier collection "
     r"than the rest of this screen",
     "· Gamma 天气 · 未来 {0} 天 · {1} 个到期日 · 来自比本页其余内容更早的一次采集"),

    # --- guide.py:57-63 link(): 文字节点与 title 提示 ---
    (r"Guide · lesson (\d+)", "指南 · 第 {0} 课"),
    (r"Lesson (\d+) of the GammaGrid Guide: (.+)", "GammaGrid 指南第 {0} 课:{1}"),
]


# ===== 概览、变化、最大痛点 / GEX、GEX 热力图; 「变化」阶梯表(day_summary) =====

# 译者 B: app/dashboard.py 1012–1609(概览 / 变化 / 最大痛点·GEX / GEX 热力图)
# 与 app/day_summary.py(「变化」视图的阶梯表、标题句、数值与变化量)。

CATALOG.update({
    # ---------------------------------------------------------------- 概览
    # dashboard.py:1012
    "Overview": "概览",
    # dashboard.py:1015
    "Put/Call Ratio": "认沽/认购比",
    # dashboard.py:1023
    "The ratio of put to call volume/open interest. A value noticeably above "
    "0.7–1.0 usually signals a defensive/bearish stance, below — a bullish one. "
    "The absolute level matters less than a sharp deviation from the ticker's own "
    "history on this chart — compare the current value to past ones, not to "
    "general rules of thumb.":
        "认沽与认购的成交量 / 未平仓量之比。明显高于 0.7–1.0 通常意味着防御 / 看跌的姿态，"
        "低于则偏看涨。绝对水平不如它在本图上相对该标的自身历史的急剧偏离重要——"
        "拿当前值和它过去的值比，而不是和通用的经验法则比。",
    # dashboard.py:1030
    "Volatility surface (IV surface)": "波动率曲面（IV 曲面）",
    # dashboard.py:1035
    "Not enough data for a volatility surface — need at least 2 distinct strikes "
    "and 2 distinct expiries with known IV in the latest snapshot.":
        "数据不足以构建波动率曲面——最新快照中至少需要 2 个不同的行权价和 "
        "2 个不同的到期日带有已知 IV。",
    # dashboard.py:1066 Plotly 悬停提示(整串查表, 花括号是 Plotly 占位符, 原样)
    "Strike ≈ %{customdata[0]}<br>DTE: %{customdata[1]} d<br>IV: %{z:.2f}<extra></extra>":
        "行权价 ≈ %{customdata[0]}<br>DTE：%{customdata[1]} 天<br>IV：%{z:.2f}<extra></extra>",
    # dashboard.py:1085 / 1362 Plotly 曲面 x 轴、Altair x 轴
    "Strike": "行权价",
    # dashboard.py:1087 曲面 y 轴; 1315 下拉框标签
    "Expiry": "到期日",
    # dashboard.py:1092 曲面 z 轴「IV」、1363 Altair y 轴「GEX」原样, 不设条目
    # dashboard.py:1098 / 1378(howto() 的默认标题同句)
    "ℹ️ How to read this": "ℹ️ 怎么读",
    # dashboard.py:1100
    "The implied volatility surface across the whole chain at the latest "
    "snapshot: strike on one axis, expiry date on the other, height/color — the "
    "IV itself. For each strike the OTM contract's IV is used (put below the "
    "current underlying price, call above): ITM contracts' IV is usually less "
    "reliable due to low liquidity and wide spreads.\n\n"
    "Real strikes and expiries rarely fall on a regular grid (different expiries "
    "have different strike spacing and ranges, far dates are coarser), so the "
    "surface is filled in by linear interpolation between the actual points (and "
    "at the edges, where interpolation runs out of data, by nearest neighbor) to "
    "avoid gaps/holes. This is display smoothing only, not new data — the source "
    "points remain the app's own snapshots, with no calls to external sources. "
    "Because of the interpolation, a grid node under the cursor almost never "
    "matches an actually traded contract — the tooltip shows the nearest real "
    "strike and DTE in days rather than the interpolated values.\n\n"
    "The typical shape is a \"smile\" or a skew across strikes at each expiry "
    "(see the Volatility (IV) tab for a single-expiry slice) and a rising/falling "
    "overall IV level as expiry moves further out (term structure). Sharp local "
    "spikes on the surface usually indicate sparse data in that region rather "
    "than a real market effect — trust the overall shape more than individual "
    "bumps.":
        "最新快照中整条期权链的隐含波动率曲面：一个轴是行权价，另一个轴是到期日，"
        "高度 / 颜色就是 IV 本身。每个行权价取虚值合约的 IV（低于标的现价取 Put，"
        "高于取 Call）：实值合约流动性差、买卖价差宽，其 IV 通常不太可靠。\n\n"
        "真实的行权价与到期日很少落在规则的网格上（不同到期日的行权价间距与范围各不相同，"
        "远月更稀疏），所以曲面在实际数据点之间用线性插值填充（在边缘、插值没有数据可用的地方，"
        "用最近邻填充），以免出现缺口 / 空洞。这只是显示上的平滑，不是新数据——"
        "源数据点仍是本应用自己的快照，不调用任何外部数据源。由于插值，光标下的网格节点"
        "几乎从不对应一张实际交易的合约——所以悬停提示显示的是最近的真实行权价和以天计的 DTE，"
        "而不是插值得出的数值。\n\n"
        "典型形状是：每个到期日沿行权价呈「波动率微笑」或偏斜（单个到期日的切面见"
        "「波动率（IV）」页），整体 IV 水平随到期日变远而上升或下降（期限结构）。"
        "曲面上尖锐的局部突起通常说明该区域数据稀疏，而不是真实的市场效应——"
        "多相信整体形状，少相信个别凸起。",
    # dashboard.py:1128 子标题; 1497 指标
    "Underlying price": "标的价格",

    # ---------------------------------------------------------------- 变化
    # dashboard.py:1140
    "No day summaries yet for this ticker. One is written after every collection, "
    "and the worker fills in the days it missed — so this view fills itself in as "
    "collection runs.":
        "这个标的还没有日汇总。每次采集后都会写入一条，定时采集任务也会补上漏掉的日子——"
        "所以随着采集运行，这个视图会自己填满。",
    # dashboard.py:1152
    "Compare from": "对比：从",
    # dashboard.py:1156(与筛选器的「to」同键, 合并时请对齐)
    "to": "到",
    # dashboard.py:1165
    "That day has no summary row.": "这一天没有日汇总行。",
    # dashboard.py:1247 阶梯表表头
    "change": "变化",
    # dashboard.py:1260
    "GEX profile, both days": "两天的 GEX 分布",
    # dashboard.py:1279
    "Two trading days of your own collection, side by side. A day is New "
    "York's date, and the row describes that day's last collection. It "
    "counts only once that day's session has opened: weekends, exchange "
    "holidays and the snapshot taken overnight before the bell are not "
    "days of their own, so on a Monday the day before is Friday. The same "
    "rule OI Delta uses, so the two views never disagree about what "
    "\"yesterday\" means.\n\n"
    "Colour is reserved for the regime: green when the day moved towards "
    "dealer hedging damping moves, purple when it moved towards amplifying "
    "them. Everything else changed without changing what kind of day it "
    "is, so it is printed in plain ink.\n\n"
    "Levels are reported in strikes because that is the grid they live on: "
    "a wall that moved \"+1 strike\" moved to the next listed strike, which "
    "is a fact about this chain, while the same move as a percentage is a "
    "fact about nothing. Max pain is compared for the same expiry only — "
    "when the nearest expiry rolls over, the line says which one was "
    "nearest before.":
        "并排对比你自己采集的两个交易日。「一天」按纽约日期算，这一行描述的是当天最后一次采集。"
        "只有当天的交易时段已经开盘，这一天才算数：周末、交易所假日以及开盘铃响前隔夜拍下的快照"
        "都不单独算一天，所以周一的前一天是周五。这与「OI 变化」用的规则相同，"
        "所以两个视图对「昨天」的理解永远一致。\n\n"
        "颜色只留给格局：当天朝做市商对冲抑制波动的方向移动时为绿色，朝放大波动的方向移动时为紫色。"
        "其余各项虽有变化，但没有改变这一天属于哪类格局，所以用普通字色显示。\n\n"
        "关键价位的变化以行权价档数报告，因为它们就落在这张网格上：一堵墙移动了「+1 档行权价」，"
        "就是移到了下一个挂牌行权价，这是关于这条期权链的事实；同样的移动换成百分比，"
        "则什么也说明不了。最大痛点只在同一到期日之间比较——最近到期日更替时，"
        "该行会注明此前最近的是哪一个。",

    # day_summary.py:changes() 阶梯表各行标签
    "Gamma weather": "Gamma 天气",
    "Price": "价格",
    "Net GEX": "净 GEX",
    "Call wall": "Call 墙",
    "Put wall": "Put 墙",
    "Max pain": "最大痛点",            # 没有最近到期日时
    "Expected move": "预期波动",       # 同上
    "Put/Call · volume": "认沽/认购比 · 成交量",
    "Put/Call · open interest": "认沽/认购比 · 未平仓量",
    "IV · volume-weighted": "IV · 成交量加权",
    "Open interest · calls": "未平仓量 · Call",
    "Open interest · puts": "未平仓量 · Put",
    "Expiries listed": "挂牌到期日数",
    "Contracts in the chain": "期权链中的合约数",

    # day_summary.py:format_value(状态行) — weather.WEATHER_WORDS 的首字
    "Clear": "晴",
    "Fair": "晴间多云",
    "Unsettled": "多变",
    "Showers": "阵雨",
    "Storm": "风暴",
    # day_summary.py:headline() 里 _word() 小写后的同五个词(由下方模板捕获再查)
    "clear": "晴",
    "fair": "晴间多云",
    "unsettled": "多变",
    "showers": "阵雨",
    "storm": "风暴",

    # day_summary.py:format_delta
    "gone": "已消失",
    "new": "新出现",
    "unchanged": "未变",
    "amplifying": "放大波动",
    "damping": "抑制波动",

    # day_summary.py:headline()
    "Net gamma changed sign: dealer hedging now damps moves.":
        "净 Gamma 变号：做市商对冲现在会抑制波动。",
    "Net gamma changed sign: dealer hedging now amplifies moves.":
        "净 Gamma 变号：做市商对冲现在会放大波动。",
    "First day on record — nothing to compare yet.":
        "记录中的第一天——还没有可比较的对象。",
    # 「Levels moved: …」: call wall / put wall / max pain 按此顺序的任意非空子集
    "Levels moved: call wall.": "关键价位有变动：Call 墙。",
    "Levels moved: put wall.": "关键价位有变动：Put 墙。",
    "Levels moved: max pain.": "关键价位有变动：最大痛点。",
    "Levels moved: call wall, put wall.": "关键价位有变动：Call 墙、Put 墙。",
    "Levels moved: call wall, max pain.": "关键价位有变动：Call 墙、最大痛点。",
    "Levels moved: put wall, max pain.": "关键价位有变动：Put 墙、最大痛点。",
    "Levels moved: call wall, put wall, max pain.":
        "关键价位有变动：Call 墙、Put 墙、最大痛点。",

    # ---------------------------------------------------------------- 最大痛点 / GEX
    # dashboard.py:1323
    "Max Pain": "最大痛点",
    # dashboard.py:1325
    "Max Pain strike": "最大痛点行权价",
    # dashboard.py:1325 / 1498–1500 指标的空值
    "n/a": "暂无",
    # dashboard.py:1328(需要裁决: 「价格向最大痛点靠拢」的说法)
    "The strike at which total payouts by option sellers are minimal. The price at "
    "expiration statistically gravitates toward this level, since market makers "
    "prefer to close the maximum number of contracts without payouts — the effect "
    "strengthens closer to the expiry date. It is not a guaranteed forecast but a "
    "tendency that fundamental news can override.":
        "期权卖方总赔付最小(也就是买方最「痛」)的那个行权价。常有说法认为到期时价格会被"
        "吸向这里, 但 GammaGrid 指南用 57 个真实到期日核对, 到期前一晚的最大痛点与到期日收盘的"
        "中位偏差是 2.04%, 最后一天朝它走的次数还不到背离它的一半 —— 把它当作「这个到期日的持仓"
        "压在哪」的描述, 不要当预测(详见下方补充说明)。",
    # dashboard.py:1335
    "Approximate Gamma Exposure (GEX)": "近似 Gamma 敞口（GEX）",
    # dashboard.py:1373
    "No data to compute GEX for the selected expiry.": "所选到期日没有可用于计算 GEX 的数据。",
    # dashboard.py:1375(需要裁决: 「用 Black-Scholes 估算」)
    "Estimated via the Black-Scholes formula and a sign heuristic (puts contribute "
    "negatively). Does not reflect actual market-maker positioning — an approximation only.":
        "gamma 优先用数据源(Cboe)给的值, 缺失时用 Black-Scholes 补算; 正负按一条经验法则"
        "(Put 的贡献记为负)。不反映做市商的实际持仓——仅为近似。",
    # dashboard.py:1380
    "Positive total gamma — the market as a whole is more \"sticky\", range-bound: "
    "dealer hedging dampens sharp moves. Negative — moves can accelerate, since "
    "hedging works in the same direction as the trend. On the by-strike chart, the "
    "largest bars by magnitude often become support/resistance levels created by "
    "hedging flows, especially closer to the expiry date.":
        "总 Gamma 为正——市场整体更「黏」、偏区间震荡：做市商对冲会抑制剧烈波动。"
        "为负——波动可能加速，因为对冲与趋势同向。在按行权价的图上，绝对值最大的几根柱子"
        "往往会成为对冲资金流造成的支撑 / 阻力位，越接近到期日越明显。",

    # ---------------------------------------------------------------- GEX 热力图
    # dashboard.py:1388
    "GEX Heatmap: strike × expiry": "GEX 热力图：行权价 × 到期日",
    # dashboard.py:1398
    "Snapshot (Replay — collection history, no auto-refresh)":
        "快照（回放——采集历史，不自动刷新）",
    # dashboard.py:1404
    "Latest snapshot (current state)": "最新快照（当前状态）",
    "Historical snapshot — Replay mode": "历史快照——回放模式",
    # dashboard.py:1417
    "That collection is in the log but stored no rows — pick another moment.":
        "这次采集在日志里有记录，但没有存下任何行——请换一个时刻。",
    # dashboard.py:1433
    "Every expiry in this snapshot has already stopped trading, so the whole "
    "matrix would be zero by definition. Pick a more recent snapshot above.":
        "这张快照里的每个到期日都已停止交易，整个矩阵按定义都会是零。请在上面选一张更近的快照。",
    # dashboard.py:1447
    "Nearest expiries": "最近的到期日数",
    # dashboard.py:1458
    "Nearest expiries: 1 (the only one still trading)": "最近的到期日数：1（唯一仍在交易的）",
    # dashboard.py:1467
    "Strikes each side of the money": "平值两侧各取的行权价数",
    # dashboard.py:1469
    "How many strikes above and below the strike closest to the underlying "
    "price to draw. 10 shows 21 rows.":
        "以最接近标的价格的行权价为中心，上下各画多少个行权价。取 10 显示 21 行。",
    # dashboard.py:1477
    "No data to build the heatmap for the selected snapshot.": "所选快照没有可用于绘制热力图的数据。",
    # dashboard.py:1498–1501 指标
    "Call Wall": "Call 墙",
    "Put Wall": "Put 墙",
    "Gamma Flip": "翻转位",
    "Regime": "格局",
    "Neg": "负 Gamma",
    "Pos": "正 Gamma",
    # dashboard.py:1504
    "No strikes to show for this snapshot.": "这张快照没有可显示的行权价。",
    # dashboard.py:1548 下方模板的可选片段
    "— the table scrolls": "——表格可滚动",
    # dashboard.py:1563(含 f-string 常量 GAMMA_FLIP_MAX_DISTANCE:.0% = 25%;
    # 需要裁决: 首段「Black-Scholes」; 末段「只有按钮才会采集」)
    "Each cell is the approximate GEX (Black-Scholes, same sign heuristic as on the "
    "Max Pain/GEX tab) for a specific strike and expiry, computed on a single "
    "snapshot — no need to pick expiries one at a time, the whole chain is visible at "
    "once. Numbers are abbreviated (1.2k = 1,200, 1.5m = 1,500,000) — exact values "
    "aren't needed for visual comparison, and shorter text leaves more room for "
    "expiry columns. Green — positive GEX (dealers dampen the move), purple — "
    "negative (dealers amplify the move), black — near zero. The color scale is "
    "calibrated to the 90th percentile of values rather than the true maximum — "
    "otherwise a single strong outlier stretches the scale until every other cell "
    "becomes nearly indistinguishably washed out; the most extreme values are simply "
    "painted the limit color, and the exact number is still visible as text. 0 means "
    "this strike simply has no listing for that expiry (not \"no data\") — that's "
    "normal: near expiries usually have a tighter range of actual strikes than far "
    "ones; expiries with no nonzero values at all within the shown strike range are "
    "hidden from the table entirely. The strike closest to the current underlying "
    "price is marked “➤” and outlined, and the table shows a strike window "
    "centered on it.\n\n"
    "**Call Wall / Put Wall** — the strike with maximum open interest in calls/puts "
    "respectively, aggregated over the shown expiries — a common proxy for "
    "support/resistance levels created by dealer hedging flows.\n\n"
    "**Gamma Flip** — the approximate underlying price at which total GEX across the "
    "shown expiries flips sign (linear interpolation between the nearest strikes). "
    "The cumulative profile can cross zero several times far from the money, where "
    "exposure is near nothing. A crossing counts only if the profile reaches a "
    "meaningful size on both sides of it — a curve that merely grazes zero is not a "
    "flip — and of the crossings that count, the level shown is the one nearest the "
    "current price. No flip is shown when none count, or when the nearest one is "
    "more than 25% away from the price; then only the "
    "regime is known. "
    "This is not a re-pricing of greeks at hypothetical underlying prices (more "
    "accurate but noticeably more expensive to compute), but a proxy based on the "
    "already-computed profile at the current price — the same class of assumption as "
    "net GEX. **Regime** Neg/Pos — the sign of total net GEX across the shown "
    "expiries.\n\n"
    "A ticker can have 20-30+ expiries (including far-dated LEAPS 1-2 years out) "
    "with very different strike ranges — the full matrix would be mostly empty and "
    "unreadable. The sliders above limit the view to the nearest N expiries and a "
    "number of strikes each side of the money; the expiry count also decides which "
    "subset Call/Put Wall, Gamma Flip, and per-expiry Net GEX are computed over, "
    "while the strike count is display only — the flip is found over the whole "
    "strike range. The approximation formulas themselves don't change.\n\n"
    "The snapshot selector lets you pick an earlier collection from history (Replay) "
    "and see how the picture looked at that moment — no new data is needed, and "
    "there is no real-time auto-refresh (collection happens only via the “Collect "
    "data” button).":
        "每个单元格是某一行权价、某一到期日的近似 GEX（gamma 优先用 Cboe 给的值、缺失时用 Black-Scholes 补算，符号经验法则与"
        "「最大痛点 / GEX」页相同），基于同一张快照计算——不必逐个挑选到期日，整条期权链一次看全。"
        "数字做了缩写（1.2k = 1,200，1.5m = 1,500,000）——目视比较不需要精确值，"
        "文字短一些也能给到期日列腾出更多位置。绿色——正 GEX（做市商抑制波动），"
        "紫色——负 GEX（做市商放大波动），黑色——接近零。色阶按数值的第 90 百分位校准，"
        "而不是按真实最大值——否则一个强离群值会把色阶拉开，其余单元格几乎都褪成难以分辨的一片；"
        "最极端的数值直接涂成上限颜色，精确数字仍以文字显示。0 表示这个行权价在该到期日"
        "根本没有挂牌（不是「没有数据」）——这很正常：近月的实际行权价范围通常比远月窄；"
        "在所显示的行权价范围内一个非零值都没有的到期日，会从表中整列隐藏。"
        "最接近标的现价的行权价标有「➤」并加框，表格显示以它为中心的一段行权价窗口。\n\n"
        "**Call 墙 / Put 墙**——分别是 Call / Put 未平仓量最大的行权价，按所显示的到期日汇总——"
        "常用来近似做市商对冲资金流形成的支撑 / 阻力位。\n\n"
        "**Gamma 翻转位**——所显示到期日的总 GEX 改变符号时对应的近似标的价格"
        "（在最近的两个行权价之间线性插值）。累积分布可能在远离平值、敞口几乎为零的地方多次穿过零。"
        "只有分布在穿越点两侧都达到有意义的规模，这次穿越才算数——只是擦过零的曲线不算翻转；"
        "在算数的穿越点中，显示的是离现价最近的那个。如果一个都不算数，或者最近的那个离现价超过 25%，"
        "就不显示翻转位；这时只知道格局。"
        "这不是在假设的标的价格上重新计算希腊值（更准确，但计算开销明显更大），"
        "而是基于现价下已算好的分布做的近似——与净 GEX 属于同一类假设。"
        "**格局** 负 Gamma / 正 Gamma——所显示到期日总净 GEX 的符号。\n\n"
        "一个标的可能有 20–30 个以上的到期日（包括 1–2 年后的远期 LEAPS），行权价范围差别很大——"
        "完整矩阵大部分是空的，没法读。上面的滑块把视图限制在最近的 N 个到期日、"
        "平值两侧各若干个行权价；到期日数还决定 Call / Put 墙、Gamma 翻转位和各到期日净 GEX "
        "在哪个子集上计算，而行权价数只影响显示——翻转位是在整个行权价范围上找的。"
        "近似公式本身不变。\n\n"
        "快照选择器可以从历史中挑一次较早的采集（回放），看看那一刻的图景——不需要新数据，"
        "也不会实时自动刷新（本站由定时任务在工作日纽约时间 09:03 与 16:23 采集，侧栏「采集数据」按钮可随时手动补采）。",
})

TEMPLATES += [
    # dashboard.py:1014
    (r"Data for (\S+) collected (.+)", "{0} 的数据，采集于 {1}"),
    # dashboard.py:1211–1212(只有第一天那种带英文; 两个日期之间的箭头本身不含字母)
    (r"(\d{4}-\d{2}-\d{2}) → (\d{4}-\d{2}-\d{2})  ·  first day on record — nothing to compare yet",
     "{0} → {1}  ·  记录中的第一天——还没有可比较的对象"),
    # day_summary.py:changes() 带到期日的行标签与注记(到期日可能是日期或时间戳, 不限格式)
    (r"Max pain · (.+)", "最大痛点 · {0}"),
    (r"Expected move · (.+)", "预期波动 · {0}"),
    (r"nearest expiry was (.+)", "此前最近到期日为 {0}"),
    # dashboard.py:1231–1234 到期日行的注记(两段都有时以「; 」相连)
    (r"expired: ([^;]+); newly listed: (.+)", "已到期：{0}；新挂牌：{1}"),
    (r"expired: ([^;]+)", "已到期：{0}"),
    (r"newly listed: (.+)", "新挂牌：{0}"),
    # day_summary.py:headline() — 天气词已被 _word() 小写, 捕获后查上面的小写条目
    (r"Gamma weather turned from (\w+) to (\w+)\.", "Gamma 天气由{0}转为{1}。"),
    (r"Same weather as the day before \((\w+)\); the levels held\.",
     "天气与前一天相同（{0}），各关键价位未动。"),
    # day_summary.py:_printed_delta — 「+1 strike · +5.00」「-2 strikes · -10.00」「+0.5 strikes · +2.50」
    (r"([+-][\d.e+]+) strikes? · ([+-][\d,]+\.\d{2})", "{0} 档行权价 · {1}"),
    # day_summary.py:_printed_delta — 预期波动区间宽度的变化
    (r"([+-][\d,]+\.\d{2}) wide", "区间宽度 {0}"),
    # dashboard.py:1312 到期日下拉框的选项
    (r"(\d{4}-\d{2}-\d{2})  ⚠️ no gamma left", "{0}  ⚠️ 已无 Gamma"),
    # dashboard.py:1343
    (r"⚠️ This expiry \(([^()]+)\) has no time left as of the latest collection \(([^()]+)\), "
     r"so gamma — and therefore GEX — is zero by definition, not missing\. "
     r"Pick a later expiry to see a profile\.",
     "⚠️ 截至最近一次采集（{1}），这个到期日（{0}）已没有剩余时间，所以 Gamma——进而 GEX——"
     "按定义为零，而不是缺数据。选一个更晚的到期日才能看到分布。"),
    # dashboard.py:1350 / 1352
    (r"Net GEX: (-?[\d,]+) — positive gamma: dealers dampen price moves",
     "净 GEX：{0}——正 Gamma：做市商抑制价格波动"),
    (r"Net GEX: (-?[\d,]+) — negative gamma: dealers amplify price moves",
     "净 GEX：{0}——负 Gamma：做市商放大价格波动"),
    # dashboard.py:1529–1532(可选的「隐藏」片段由下一条模板翻)
    (r"Net GEX across (\d+) of (\d+) shown expiries \((\d+) total\)"
     r"(?: (— \d+ hidden \(no activity in this strike range\)))?:",
     "净 GEX：所显示 {1} 个到期日中的 {0} 个（共 {2} 个）{3}："),
    (r"— (\d+) hidden \(no activity in this strike range\)",
     "——{0} 个已隐藏（该行权价范围内无活动）"),
    # dashboard.py:1545–1549(可选片段「— the table scrolls」在 CATALOG)
    (r"(\d+) strikes around the money \(([^,()]+), marked “➤”\): up to (\d+) each side"
     r"(?: (— the table scrolls))?",
     "平值附近 {0} 个行权价（平值行权价 {1}，标为「➤」）：每侧最多 {2} 个{3}"),
]


# ===== IV、合约、筛选器、异常成交、OI 变化; 全站的表头与图表序列名 =====

# 译者 C: dashboard.py 1610– 末尾(Volatility (IV) / Contract / Screener / Unusual Activity / OI Delta)
# + 全应用的表格列名、索引名、图表序列名。

CATALOG.update({
    # ---------------------------------------------------------------- Volatility (IV)
    # dashboard.py:1611
    "IV: volume-weighted average for the ticker": "IV:该标的的成交量加权平均",
    # dashboard.py:1633 (howto Volatility (IV))
    "Rising average IV usually precedes an anticipated move (earnings, news) or "
    "already reflects increased market uncertainty. Falling — the market is calming "
    "down. Compare the current level against the historical range on this chart, "
    "not against absolute numbers — \"normal\" IV differs a lot between tickers.":
        "平均 IV 上升,通常出现在预期中的行情(财报、新闻)之前,或者已经反映出市场不确定性在增加;"
        "下降则说明市场正在平静下来。请拿当前水平与本图上的历史区间比较,而不是与绝对数值比较——"
        "不同标的的「正常」IV 差别很大。",
    # dashboard.py:1640
    "IV: chain slice (latest snapshot)": "IV:期权链切片(最新快照)",
    # dashboard.py:1642, 1716(Contract 视图的到期日下拉框)
    "Expiry": "到期日",
    # dashboard.py:1649
    "No data for this expiry in the latest snapshot.": "最新快照中没有这个到期日的数据。",
    # dashboard.py:1659, 及 howto() 的默认标题
    "ℹ️ How to read this": "ℹ️ 怎么读",
    # dashboard.py:1661
    "The curve's shape shows which strikes the market prices as riskier (higher "
    "implied volatility). A steep skew toward puts at low strikes (put skew) "
    "usually means elevated demand for downside protection — the typical picture "
    "for most stocks.":
        "曲线的形状显示市场把哪些行权价定价为风险更高(隐含波动率更高)。低行权价一侧明显向 Put "
        "倾斜(Put 偏斜),通常意味着对下行保护的需求偏高——这是大多数股票的典型形态。",
    # dashboard.py:1667
    "IV history and the rest of the greeks for a specific contract — on the Contract tab.":
        "单个合约的 IV 历史及其余希腊值——见「合约」页。",

    # ---------------------------------------------------------------- Contract
    # dashboard.py:1670
    "Contract: price and greeks over time": "合约:价格与希腊值随时间的变化",
    # dashboard.py:1673
    "Pinned contracts (click a name to show it below):": "已固定的合约(点击名称在下方显示):",
    # dashboard.py:1709 (checkbox help)
    "Contracts that have already expired. Nothing was deleted — they simply "
    "cannot appear in these lists on their own, because the lists come from "
    "the current chain.":
        "已经到期的合约。没有任何数据被删除——只是它们无法自己出现在这些列表里,"
        "因为列表取自当前的期权链。",
    # dashboard.py:1734
    "Strike": "行权价",
    # dashboard.py:1749
    "Type": "类型",

    # ---------------------------------------------------------------- Screener
    # dashboard.py:1782
    "A slice of the latest snapshot (not history) — every contract of the ticker with "
    "greeks and DTE. Clicking a row opens the same charts as the Contract tab.":
        "最新快照的一个切片(不是历史)——该标的的全部合约,附希腊值与 DTE。"
        "勾选某一行的「查看详情」, 下面会显示与「合约」页相同的图表。",
    # dashboard.py:1810 (checkbox help)
    "Their greeks and DTE are as of the collection, which is why they can "
    "still show time left. Collect again to refresh the chain.":
        "它们的希腊值与 DTE 以采集那一刻为准,所以仍可能显示还有剩余时间。重新采集即可刷新期权链。",
    # dashboard.py:1817
    "No data for the screener.": "筛选器没有数据。",
    # dashboard.py:1819 FILTER_SPECS 标签
    "Option price": "期权价格",
    "DTE (days)": "DTE(天)",
    "Open interest": "未平仓量",
    "IV": "IV",
    "Delta": "Delta",
    "Gamma": "Gamma",
    "Theta": "Theta",
    "Vega": "Vega",
    "Rho": "Rho",
    "Vanna": "Vanna",
    "Charm": "Charm",
    # dashboard.py:1838
    "🔍 Filters (ranges)": "🔍 筛选(区间)",
    # dashboard.py:1856, 1866
    "from": "从",
    "to": "到",
    # dashboard.py:1883
    "No contract falls within the selected filter ranges.": "没有合约落在所选的筛选区间内。",
    # dashboard.py:1894, 1906 (data_editor 勾选列的显示标签; 列真名不变)
    "Show details": "查看详情",

    # ---------------------------------------------------------------- Unusual Activity
    # dashboard.py:1959
    "Unusual Activity (latest snapshot)": "异常成交(最新快照)",

    # ---------------------------------------------------------------- OI Delta
    # dashboard.py:1989
    "Open Interest change (latest day vs. previous)": "未平仓量变化(最新一日对比前一日)",
    # dashboard.py:1999
    "Data from at least two distinct trading days is needed to compute the OI change.":
        "计算 OI 变化至少需要两个不同交易日的数据。",
    # dashboard.py:2004 (howto OI Delta)
    "`open_interest` — the current value as of the latest day, for scale: a "
    "1000-contract increase is a lot at OI=2000 and barely noticeable at "
    "OI=200000. `oi_delta` — the absolute signed change: positive — new "
    "positions opened at this strike since the previous trading day (OI grew), "
    "negative — some positions closed. `oi_delta_pct` — the same change as a "
    "percentage of the previous value (empty if the previous OI was 0 — growth "
    "\"from zero\" has no percentage form). Rows are sorted by the magnitude of "
    "the absolute delta, not by percentage or sign — the largest OI moves in "
    "either direction are on top. It is precisely the large moves (regardless "
    "of sign) that most often form new dealer hedging-flow levels (see the Max "
    "Pain/GEX tab).\n\n"
    "The data source's open interest barely updates intraday, so the comparison "
    "is between the latest snapshots of two distinct trading days rather than "
    "the two most recent collections — if you collected data several times "
    "today, only the freshest collection of the day is used for the comparison. "
    "A day counts once its session has opened: before the bell, and on weekends "
    "and holidays, the comparison is between the last two sessions.":
        "**未平仓量**(`open_interest`)——最新一日的当前值,用来体现规模:增加 1000 张合约,"
        "在 OI=2000 时算很多,在 OI=200000 时几乎察觉不到。**OI 变化**(`oi_delta`)——带正负号的"
        "绝对变化:为正,表示自上一交易日以来这个行权价上开了新仓(OI 增加);为负,表示有部分仓位平掉了。"
        "**OI 变化 %**(`oi_delta_pct`)——同一变化占前值的百分比(前值 OI 为 0 时留空——「从零」"
        "开始的增长没有百分比形式)。各行按绝对变化的大小排序,而不是按百分比或正负——两个方向上最大的 "
        "OI 变动都排在最上面。恰恰是这些大的变动(不论正负)最常形成新的做市商对冲流价位"
        "(见「最大痛点/GEX」页)。\n\n"
        "数据源的未平仓量在盘中几乎不更新,所以比较的是两个不同交易日各自的最新快照,而不是最近两次采集——"
        "如果你今天采集了好几次,比较时只用当天最新的那一次。一个交易日要等它的交易时段开盘后才算数:"
        "开盘铃响之前,以及周末和节假日,比较的是最近两个交易时段。",

    # ================================================================ 列名 / 索引名 / 序列名(全应用)
    # 图表: dashboard.py:1020 Put/Call 比(viewtime.with_viewer_index 的索引名 collected_at)
    "pcr_volume": "认沽/认购比(成交量)",
    "pcr_oi": "认沽/认购比(OI)",
    "collected_at": "采集时间",
    # dashboard.py:1617
    "iv_weighted_avg": "成交量加权 IV",
    # dashboard.py:155, 165; Screener 表
    "last_price": "期权价格",
    "implied_volatility": "隐含波动率",
    # dashboard.py:200 希腊值图; 归因累计图 (273); Screener 表
    "delta": "Delta",
    "gamma": "Gamma",
    "theta": "Theta",
    "vega": "Vega",
    "rho": "Rho",
    "vanna": "Vanna",
    "charm": "Charm",
    # dashboard.py:273 归因累计图的索引名(每个交易日最后一次采集)
    "day": "交易日",
    # dashboard.py:1267 GEX 剖面索引名; 1658 IV 切片索引名; Screener / 异常成交 / OI 变化表
    "strike": "行权价",
    # dashboard.py:1658 IV 切片的两条序列(也是 Contract 页「类型」下拉框的选项显示)
    "call": "Call",
    "put": "Put",
    # dashboard.py:1538 每个到期日的净 GEX(转置后是行标签, 见报告)
    "net_gex": "净 GEX",
    # Screener (metrics_core.py:972) / 异常成交 (1574) / OI 变化 (1776–1795)
    "expiry": "到期日",
    "option_type": "类型",
    "dte": "DTE",
    "open_interest": "未平仓量",
    "volume": "成交量",
    "avg_volume": "平均成交量",
    "volume_zscore": "成交量 z 分数",
    "oi_delta": "OI 变化",
    "oi_delta_pct": "OI 变化 %",
    # dashboard.py:798 采集日志表
    "started_at": "开始时间",
    "ticker": "代码",
    "status": "状态",
    "rows_fetched": "抓取行数",
    "oi_zero_fraction": "OI 为零占比",
    "error_message": "错误信息",
})

TEMPLATES += [
    # dashboard.py:1626 (IV 视图, 待重算的点数, 带千分位)
    (r"The earliest ([\d,]+) point\(s\) of this chart still carry the data source's own "
     r"volatility, from before this product started solving it from the contract's price\. "
     r"They are being recomputed in the background while the collector runs — nothing to "
     r"start, and the rest of this page is unaffected\.",
     "本图最早的 {0} 个点仍是数据源自带的波动率,来自本产品开始用合约价格反解波动率之前。"
     "采集器运行期间它们正在后台重算——无需启动任何操作,本页其余内容也不受影响。"),
    # dashboard.py:1677 已固定合约的按钮名
    (r"(\d{4}-\d{2}-\d{2})  strike (\S+)  (call|put)", "{0}  行权价 {1}  {2}"),
    # dashboard.py:1705 checkbox
    (r"Show expired contracts \((\d+) with collected history\)",
     "显示已到期合约(有采集历史的共 {0} 个)"),
    # dashboard.py:1718 到期日下拉框的 format_func
    (r"(\d{4}-\d{2}-\d{2})  ⏳ expired", "{0}  ⏳ 已到期"),
    # dashboard.py:1767
    (r"⏳ \*\*Expired contract\*\* — expired (\d{4}-\d{2}-\d{2})\. Stored history covers "
     r"(\d{4}-\d{2}-\d{2}) to (\d{4}-\d{2}-\d{2}), which starts when this ticker was first "
     r"collected rather than when the contract was listed\.",
     "⏳ **已到期合约**——到期日 {0}。已存的历史覆盖 {1} 至 {2},起点是这个标的首次被采集的时间,"
     "而不是合约上市的时间。"),
    # dashboard.py:1780
    (r"Options screener: (\S+)", "期权筛选器:{0}"),
    # dashboard.py:1807 checkbox
    (r"Include (\d+) contract\(s\) that have expired since this snapshot was collected "
     r"\((-?\d+) day\(s\) ago\)",
     "包含自这份快照采集以来({1} 天前)已经到期的 {0} 个合约"),
    # dashboard.py:1845 筛选列只有一个取值时
    (r"([^:]+): (\S+) \(single value\)", "{0}:{1}(唯一值)"),
    # dashboard.py:1876
    (r"Contracts shown: (\d+) of (\d+)", "显示合约:{0} / {1}"),
    # dashboard.py:1931 (客户端 JS 按此标题文字滚动, 由调用方另行处理)
    (r"📌 Contract details: (\d{4}-\d{2}-\d{2}) strike (\S+) (call|put)",
     "📌 合约详情:{0} 行权价 {1} {2}"),
    # dashboard.py:1967
    (r"Contracts found: (\d+)", "发现合约:{0} 个"),
    # dashboard.py:1971 (howto Unusual Activity; config.UNUSUAL_Z_THRESHOLD / UNUSUAL_MIN_VOLUME)
    (r"A contract is flagged when today's volume statistically significantly exceeds "
     r"\(z-score above ([\d.]+)\) this specific contract's own history — not a blanket "
     r"multiplier applied to every strike\. Contracts with volume below (\d+) never make the "
     r"list regardless of the statistics — that's noise from illiquid far strikes\. Contracts "
     r"without enough history use the crude check volume > 2×open interest instead\. Rows are "
     r"sorted by z-score — the most unusual on top\. This is not a sign of insider activity — "
     r"a large trade can be part of a hedge for an entirely different position\.\n\n"
     r"The data source's volume is cumulative since the start of the trading session, so the "
     r"history for the mean/standard deviation is built from one \(the latest\) snapshot per "
     r"trading day — multiple same-day collections are never mixed together when computing "
     r"the statistics\.",
     "当今天的成交量在统计上显著超过这个合约自身的历史(z 分数高于 {0})时,它就会被标出——"
     "而不是对所有行权价一律套用同一个倍数。成交量低于 {1} 的合约无论统计结果如何都不会上榜——"
     "那是流动性差的远端行权价带来的噪声。历史不足的合约改用粗略判据:成交量 > 2×未平仓量。"
     "各行按 z 分数排序,最异常的在最上面。这并不是内幕交易的迹象——一笔大单可能只是另一个"
     "完全不同的仓位的对冲的一部分。\n\n"
     "数据源的成交量是从交易时段开始累计的,所以计算均值/标准差所用的历史,每个交易日只取一份"
     "(最新的)快照——计算统计量时,绝不会把同一天的多次采集混在一起。"),
]

EMBEDDED: list[tuple[str, str]] = [
    ('"locale": "en"', '"locale": "zh_CN"'),  # TradingView 小部件
    # 筛选器点开合约后滚到「合约详情」标题的那段 JS 按标题文字找元素, 标题译了它也要跟着改
    ("includes('Contract details')", "includes('合约详情')"),
]

# 「中文 / EN」钉在右上角, Streamlit 自己的工具栏左边。
CSS_TOGGLE = """
<style>
  .st-key-gg-lang {
    position: fixed; top: 0.55rem; right: 3.4rem; z-index: 1000000;
    width: auto !important;
  }
  .st-key-gg-lang button { min-height: 1.9rem; padding: 0 0.7rem; }
</style>
"""

# 只在中文时加: 英文眉题用的全大写与宽字距, 对汉字没有意义还显得松散。
CSS_ZH = """
<style>
  .gg-weather-scope, .gg-levels dt, .gg-ladder th {
    text-transform: none !important; letter-spacing: 0.02em !important;
  }
</style>
"""
