# 演示素材

本目录存放 README 与验收材料使用的真实界面截图和操作视频，全部由 `frontend/scripts/capture-media.mjs` 针对本地演示环境自动生成。

## 视频

| 文件 | 说明 |
|------|------|
| `video/suzhou-garden-demo.mp4` | 约 1 分钟、1280×720、H.264 演示视频，带中文字幕；覆盖登录、资产检索、详情、证据链、证书、溯源、水印实验室、后台、授权报表、任务队列、日志完整性、分享与证据包核验 |
| `video/demo-preview.gif` | 12 秒无声预览（960×540） |
| `video/demo-poster.jpg` | README 视频封面 |

视频中的字幕是录制时注入页面的浮层，不是后期剪辑；所有数据来自本地演示库，水印实验室为真实执行结果。

## 截图

| 文件 | 内容 |
|------|------|
| `screenshots/01-home.png` | 首页与平台数据概览 |
| `screenshots/02-asset-archive.png` | 资产档案：筛选、检索与卡片列表 |
| `screenshots/03-asset-detail.png` | 资产详情：预览、水印 ID、交易哈希与证书编号 |
| `screenshots/04-evidence-chain.png` | 证据链：上传 → 水印 → 存证 → 证书 → 发布 → 授权 → 下载 |
| `screenshots/05-certificate.png` | 存证证书、版本标注与扫码核验二维码 |
| `screenshots/06-watermark-lab.png` | 水印实验室：真实嵌入、8 项攻击、PSNR/NC/ID 恢复与耗时 |
| `screenshots/07-trace-result.png` | 水印 ID 溯源结果与证据包入口 |
| `screenshots/08-admin-dashboard.png` | 管理仪表盘：真实统计与图表 |
| `screenshots/09-license-usage.png` | 授权使用报表：配额、拒绝原因与下载趋势 |
| `screenshots/10-task-health.png` | 任务队列健康度：在线 worker 与心跳 |
| `screenshots/10-task-queue.png` | 任务队列：已完成任务筛选 |
| `screenshots/11-audit-integrity.png` | 操作日志 HMAC 完整性校验 |
| `screenshots/12-public-share.png` | 公开分享核验页（访问码通过后） |
| `screenshots/13-evidence-verify.png` | 证据包公开核验通过 |

## 重新生成

前置条件：后端 `http://127.0.0.1:5000` 与前端 `http://127.0.0.1:5173` 已启动，演示库包含 `ZZY-IMG-20261021-D16` 与 `user1/123456`、`admin/admin123` 账号。

```bash
cd frontend
node scripts/capture-media.mjs screenshots
node scripts/capture-media.mjs video
```

可选环境变量：

- `DEMO_BASE_URL`、`DEMO_API_URL`：前后端地址；
- `DEMO_PHOTO`：水印实验室样例图片，默认使用本地 `.scratch/demo/photos/CLT-01.jpg`；
- `FFMPEG_PATH`：ffmpeg 可执行文件；不设置时使用 `PATH` 中的 `ffmpeg`。

本机生成时可用 `python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"` 找到 `imageio-ffmpeg` 自带的 ffmpeg，并把路径传给 `FFMPEG_PATH`。

截图会保存到本目录，视频会重新转码 MP4、生成 GIF 与封面。截图与视频不包含真实用户隐私或访问令牌；演示数据中的账号为本地演示账号。
