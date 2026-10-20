# UI 设计系统：青绿山水 · 档案册

> 方向：把苏州园林当作一座**数字档案馆**来做，而不是常见的绿色渐变后台。
> 关键词：黛青、宣纸、宋体、窗棂、印章朱砂、台账式排版。

## 1. 设计来源（已吸收，不复制）

| 参考 | 采纳的部分 | 明确不采纳 |
|------|------------|------------|
| [苏州博物馆官网](https://www.szmuseum.com/) | 墨色/暖灰/朱砂的信号色关系；几何框架与印章式标识；让图像成为主体 | 固定 1366px、fullpage.js、自动轮播 |
| [故宫博物院数字文物库](https://digicol.dpm.org.cn/) | 松绿 + 古金 + 暖纸的档案气质；4 列密集藏品网格；70/30 详情布局 | 12px 正文、5 个悬浮小图标、知识图谱的复杂度 |
| [故宫名画记](https://minghuaji.dpm.org.cn/) | 纸面 + 墨褐 + 宋体标题；时间轴、画作查看器的层级 | 授权字体、1260px 固定宽度、hover-only 交互 |
| [数字藏经洞](https://cave17.e-dunhuang.com/) | 羊皮纸、朱砂、深褐的“文物纸面”暖色层（用于证书） | 视口锁定的 rem、满屏纹理 |
| [Han Design](https://github.com/you-want/han-design) | 青绿山水/水墨/青瓷的 token 结构；朱砂 ≤5%、金 <3% 的克制原则 | 22 套主题全量引入、书法字体做正文 |
| [cultural-relics-museum](https://github.com/zhangbo126/cultural-relics-museum) | GitHub 上少见的、验证过的高级中式深色界面；金/朱砂/玉色的比例 | 3D 场景复杂度、深色作为全站底色 |
| vue-pure-admin / Geeker-Admin / Soybean Admin | 后台壳的几何（224px 侧栏、56–60px 顶栏、24px 内容边距）；Element Plus 原生 token 思路 | 框架默认蓝、彩色胶囊菜单、10–12px 大圆角卡片 |

## 2. 色彩令牌

定义在 `src/assets/styles/variables.scss`，并通过 `:root` 的 `--el-*` 变量驱动 Element Plus。

| 语义 | 值 | 用途 |
|------|----|------|
| 黛青 `$primary-color` | `#2f6b5a` | 主按钮、链接、选中态 |
| 深黛 `$primary-dark` | `#0e3b33` | 首页 Hero、后台侧栏、深色块 |
| 远山蓝 `$secondary-color` | `#4c6e8a` | 区块链/数据层辅助色 |
| 印章朱砂 `$accent-color` | `#a6402f` | 确权、警示、关键强调（≤5% 面积） |
| 青铜 `$bronze` | `#c1925b` | 存证/来源标识（<3% 面积） |
| 宣纸 `$bg-primary` | `#f4f6f2` | 页面底色 |
| 纸面 `$bg-card` | `#fcfdfb` | 卡片、证书 |
| 墨 `$text-primary` | `#17201c` | 正文与标题 |
| 次级墨 `$text-secondary` | `#5b675f` | 元数据、说明 |
| 界线 `$border-color` | `#d8e1da` | 1px 分隔线 |

## 3. 字体与字号

- 标题：`Noto Serif SC` / `Source Han Serif SC` / `Songti SC` / `SimSun`（宋体，档案与牌匾感）
- 正文与 UI：`Noto Sans SC` / `PingFang SC` / `Microsoft YaHei`
- 数据、编号、哈希：`JetBrains Mono` / Consolas，`font-variant-numeric: tabular-nums`
- 字号：12 / 13 / 14 / 16 / 18 / 20 / 24 / 30 / 38 / 48；正文 14–16px，行高 1.6–1.8
- 字体通过 `index.html` 的 Google Fonts 渐进加载；加载失败自动回退系统宋体/雅黑，不影响布局

## 4. 几何与材质

- 圆角：2px（标签/输入）、4px（按钮）、6px（卡片）、8px（弹窗），不使用大面积 10–12px 胶囊
- 边框：1px 发丝线；卡片同时使用细边框 + 极轻阴影，不做悬浮上移
- 纹理：窗棂/铺地 SVG 以 6%–12% 透明度用于深色面；不在正文区铺满
- 印章：方形朱砂块 + 宋体字，只在证书、确权、Hero 等少数位置出现
- 动效：160–220ms 的 hover/focus；Hero 一次墨迹揭示；尊重 `prefers-reduced-motion`
- 可访问性：全局 `:focus-visible`、对比度校验、键盘可达；不使用 hover-only 的关键信息

## 5. 页面模式

- **首页**：深黛 Hero + 月洞门 SVG + 宋体大标题 + 台账式统计；四道工序、四类能力、园林档案、技术台账
- **登录/注册**：左侧深色档案封面（月洞门/朱砂印），右侧宣纸表单；移除无效的第三方登录
- **后台**：248px 深黛侧栏（窗棂纹理）+ 56/64px 纸面顶栏 + 24–32px 内容边距；激活项用 2px 朱砂左线，而不是整行渐变
- **仪表盘**：深黛欢迎条 + 台账式统计卡片 + 重新配色的 ECharts + 待办/活动列表
- **资产目录**：纸面卡片、1px 边框、4:3 图像、等宽资产编号；统计卡改为台账格
- **证书**：860px 纸面文档，宋体标题，朱砂章节线，等宽哈希；保留打印样式

## 6. 不要做的事

- 绿色渐变按钮、emoji 作为 UI 图标、Three.js 粒子背景、玻璃拟态卡片堆叠
- 所有内容都做成同样的圆角 SaaS 卡片、统一的柔和阴影、悬浮位移
- 大面积饱和朱砂或金色；朱砂只做信号，不做背景
- 大字号渐变标题、全大写英文眉标、无意义编号
- 框架默认蓝 `#409eff` / 靛蓝 `#5b5bd6` / 酸绿 `#00dc82`
- 固定 1260/1366px 布局、12px 正文、仅 hover 可用的交互

## 7. 维护约定

1. 新页面必须使用 `variables.scss` 令牌；不要再写死十六进制色值（图表配置除外，需集中管理）。
2. Element Plus 组件通过 `--el-*` CSS 变量定制，不在业务页面写 `!important` 覆盖。
3. 新增页面标题使用 `$font-display`；数据编号使用 `$font-mono`。
4. 任何新动画必须提供 `prefers-reduced-motion` 降级。
5. 改全局样式前先看 `main.scss` 与 `App.vue`，避免再次出现两套覆盖互相打架。
