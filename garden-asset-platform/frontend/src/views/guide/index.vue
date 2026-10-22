<template>
  <div class="guide-page">
    <!-- 封面 -->
    <header class="guide-hero">
      <div class="guide-hero-inner">
        <p class="guide-kicker">
          <span class="seal">使用指南 · 3 分钟上手</span>
        </p>
        <h1 class="guide-title">从一件园林影像，<br />到一条可核验的授权记录。</h1>
        <p class="guide-lead">
          这份指南按真实业务流程组织：先认识平台能做什么，再用一个演示账号走完
          <strong>上传 → 水印 → 存证 → 发布 → 授权 → 溯源</strong>。
          页面里的每一步都对应系统里的实际入口。
        </p>

        <div class="guide-hero-actions">
          <router-link to="/assets" class="guide-btn guide-btn-primary">进入资产档案</router-link>
          <a href="#workflow" class="guide-btn">查看完整流程</a>
          <router-link to="/login" class="guide-link-inline">先用演示账号登录 →</router-link>
        </div>

        <dl class="guide-facts">
          <div>
            <dt>数字资产</dt>
            <dd>{{ stats.assets }}</dd>
          </div>
          <div>
            <dt>园林档案</dt>
            <dd>{{ stats.gardens }}</dd>
          </div>
          <div>
            <dt>水印确权</dt>
            <dd>{{ stats.watermarked }}</dd>
          </div>
          <div>
            <dt>链上存证</dt>
            <dd>{{ stats.chained }}</dd>
          </div>
        </dl>
      </div>
    </header>

    <div class="guide-layout">
      <!-- 目录 -->
      <aside class="guide-toc" aria-label="指南目录">
        <p class="toc-title">本页目录</p>
        <a href="#about">01 · 平台能做什么</a>
        <a href="#roles">02 · 角色与演示账号</a>
        <a href="#workflow">03 · 一条完整流程</a>
        <a href="#map">04 · 功能地图</a>
        <a href="#faq">05 · 常见问题</a>
        <a href="#deploy">06 · 部署与开发</a>
      </aside>

      <main class="guide-content">
        <!-- 01 -->
        <section id="about" class="guide-section">
          <header class="section-head">
            <span class="section-index">01</span>
            <div>
              <h2>平台能做什么</h2>
              <p>围绕“园林数字资产的权属与分发”，把四件事串成一条证据链。</p>
            </div>
          </header>

          <div class="capability-grid">
            <article class="capability">
              <span class="capability-mark">水</span>
              <h3>数字水印</h3>
              <p>把资产唯一标识写进影像频域或矢量坐标。JPEG 压缩、缩放与噪声后仍可提取，用于判断“这张图来自哪件资产”。</p>
            </article>
            <article class="capability">
              <span class="capability-mark">链</span>
              <h3>区块链存证</h3>
              <p>文件哈希、水印标识与权利人信息写入联盟链，生成存证证书。任何改动都会导致哈希不一致。</p>
            </article>
            <article class="capability">
              <span class="capability-mark">审</span>
              <h3>双重审批授权</h3>
              <p>使用申请先由一级审批员核验材料，再由二级审批员复核。通过后生成授权记录，下载行为持续回流台账。</p>
            </article>
            <article class="capability">
              <span class="capability-mark">溯</span>
              <h3>全链路溯源</h3>
              <p>上传图片即可提取水印、定位资产、关联存证与授权记录；公开溯源页无需登录也能使用。</p>
            </article>
          </div>
        </section>

        <!-- 02 -->
        <section id="roles" class="guide-section">
          <header class="section-head">
            <span class="section-index">02</span>
            <div>
              <h2>角色与演示账号</h2>
              <p>不同角色看到的后台入口不同。演示库已准备好账号与样例数据。</p>
            </div>
          </header>

          <div class="role-table-wrap">
            <table class="role-table">
              <thead>
                <tr>
                  <th>角色</th>
                  <th>可以做什么</th>
                  <th>演示账号</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in roleRows" :key="item.role">
                  <td>{{ item.role }}</td>
                  <td>{{ item.description }}</td>
                  <td class="mono">
                    <template v-if="isDev">{{ item.account }}</template>
                    <span v-else class="account-hidden">仅开发环境显示</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="guide-note">
            {{ isDev
              ? '演示账号只在开发模式显示；正式部署前请删除或修改这些账号。'
              : '正式环境不展示演示账号。部署时请删除种子账号或修改默认密码。' }}
          </p>
        </section>

        <!-- 03 -->
        <section id="workflow" class="guide-section">
          <header class="section-head">
            <span class="section-index">03</span>
            <div>
              <h2>一条完整流程</h2>
              <p>按下面顺序操作，可以在 5–10 分钟内走完整个闭环。</p>
            </div>
          </header>

          <ol class="workflow-list">
            <li v-for="(step, index) in workflow" :key="step.title" class="workflow-item">
              <span class="workflow-index">{{ String(index + 1).padStart(2, '0') }}</span>
              <div class="workflow-body">
                <div class="workflow-title-row">
                  <h3>{{ step.title }}</h3>
                  <span class="workflow-role">{{ step.role }}</span>
                </div>
                <p>{{ step.description }}</p>
                <router-link v-if="step.to" :to="step.to" class="workflow-link">
                  {{ step.linkText || '打开对应页面' }} →
                </router-link>
              </div>
            </li>
          </ol>
        </section>

        <!-- 04 -->
        <section id="map" class="guide-section">
          <header class="section-head">
            <span class="section-index">04</span>
            <div>
              <h2>功能地图</h2>
              <p>不知道从哪里开始？按你要做的事直接进入。</p>
            </div>
          </header>

          <div class="map-grid">
            <router-link to="/assets" class="map-card">
              <span class="map-kicker">找资产</span>
              <h3>资产档案</h3>
              <p>按园林、类型、状态筛选已发布资产，查看详情与授权入口。</p>
            </router-link>
            <router-link to="/trace" class="map-card">
              <span class="map-kicker">查来源</span>
              <h3>溯源查询</h3>
              <p>上传一张图片，提取水印并核对链上存证；也可以直接输入水印 ID。</p>
            </router-link>
            <router-link to="/license/my" class="map-card">
              <span class="map-kicker">看进度</span>
              <h3>我的授权</h3>
              <p>查看审批中的申请、已生效的授权、有效期与合同信息。</p>
            </router-link>
            <router-link to="/my-assets" class="map-card">
              <span class="map-kicker">管作品</span>
              <h3>我的资产与收藏</h3>
              <p>处理草稿、驳回与待审资产，或查看收藏过的园林影像。</p>
            </router-link>
            <router-link to="/collections" class="map-card">
              <span class="map-kicker">做策展</span>
              <h3>我的合集</h3>
              <p>按主题把多件资产组织成合集，可在资产详情一键加入。</p>
            </router-link>
            <router-link to="/downloads" class="map-card">
              <span class="map-kicker">查台账</span>
              <h3>下载记录</h3>
              <p>查看授权下载过的资产、对应授权编号与下载时间。</p>
            </router-link>
            <router-link to="/admin" class="map-card">
              <span class="map-kicker">做管理</span>
              <h3>管理后台</h3>
              <p>仪表盘、资产审核、水印与存证管理、双重审批、园林档案与用户管理。</p>
            </router-link>
          </div>
        </section>

        <!-- 05 -->
        <section id="faq" class="guide-section">
          <header class="section-head">
            <span class="section-index">05</span>
            <div>
              <h2>常见问题</h2>
              <p>这些是最容易卡住的地方。</p>
            </div>
          </header>

          <el-collapse class="faq-collapse">
            <el-collapse-item title="为什么“上链存证”按钮是灰的？" name="1">
              <p>上链前必须先完成水印嵌入。先在右侧面板点击“嵌入水印”，状态变为“已嵌入”后，上链按钮才会启用。</p>
            </el-collapse-item>
            <el-collapse-item title="为什么资产列表里看不到我刚上传的文件？" name="2">
              <p>新上传的资产是“草稿”，只有上传者和管理员可见。完成水印与上链后点击“提交发布”，经资产管理员审核通过才会出现在公开列表。</p>
            </el-collapse-item>
            <el-collapse-item title="水印图片被裁剪或截图后还能溯源吗？" name="3">
              <p>水印可以抵抗 JPEG 压缩、噪声与常见缩放；大幅裁剪会破坏嵌入区域，此时需要结合区块链存证、授权记录和人工核验判断权属。</p>
            </el-collapse-item>
            <el-collapse-item title="申请授权后多久能审批？" name="4">
              <p>流程是“一级审批 → 二级审批”。演示环境可分别用 adm1 和 adm2 登录后台完成两级审批；审批通过后“我的授权”会出现生效记录。</p>
            </el-collapse-item>
            <el-collapse-item title="如何把资产发给外部人员核验？" name="5">
              <p>资产所有者或管理员在资产详情点击“分享核验”，可生成免登录链接，并设置有效期、访问码、是否允许下载与下载次数上限。外部人员打开后会看到资产信息与完整证据链；分享链接可随时撤销。</p>
            </el-collapse-item>
            <el-collapse-item title="顶栏铃铛里的待办点过之后还会亮吗？" name="6">
              <p>不会。点击待办或“全部已读”后，已读状态会保存到你的账号；业务状态再次变化时会重新变为未读。</p>
            </el-collapse-item>
            <el-collapse-item title="收藏和合集有什么区别？" name="7">
              <p>收藏是“我关注这件资产”，一件资产只有收藏/未收藏两种状态；合集是“我按主题组织一组资产”，一件资产可以同时出现在多个合集里，还可以设为公开供他人浏览。</p>
            </el-collapse-item>
            <el-collapse-item title="如何替换资产文件或回退旧版本？" name="8">
              <p>资产所有者或管理员在资产详情“版本历史”上传新版本，填写变更说明即可。系统保留旧版本并更新当前文件，水印状态会重置；恢复旧版本会生成一个新版本，不会删除历史。历史链上存证仍对应旧文件，证据链会标注“当前文件已更新”。</p>
            </el-collapse-item>
            <el-collapse-item title="AI 分析和智能问答为什么提示不可用？" name="5">
              <p>AI 能力需要单独配置模型与 API Key，默认关闭。关闭时接口会明确返回 503，而不是伪造分析结果。配置方式见 README 的 AI 章节。</p>
            </el-collapse-item>
            <el-collapse-item title="页面里的园林照片是真实数据吗？" name="6">
              <p>演示库使用 16 张来自 Wikimedia Commons 的苏州园林实景照片，授权信息记录在本地 <code>ATTRIBUTION.md</code>。照片只用于本地演示，不进入代码仓库；生产环境应替换为已获授权的馆藏影像。</p>
            </el-collapse-item>
          </el-collapse>
        </section>

        <!-- 06 -->
        <section id="deploy" class="guide-section">
          <header class="section-head">
            <span class="section-index">06</span>
            <div>
              <h2>部署与开发</h2>
              <p>前后端分离，默认本地磁盘存储，可选 PostgreSQL、Redis 与 FISCO BCOS。</p>
            </div>
          </header>

          <div class="deploy-grid">
            <div class="deploy-card">
              <h3>本地启动</h3>
              <pre><code>cd backend && pip install -r requirements.txt
python scripts/init_db.py
python run.py

cd frontend && npm install
npm run dev</code></pre>
              <p>访问 http://localhost:5173，后端健康检查在 http://localhost:5000/health。</p>
            </div>
            <div class="deploy-card">
              <h3>Docker 一键部署</h3>
              <pre><code>cp .env.example .env
docker-compose up -d
docker exec garden-backend python scripts/init_db.py</code></pre>
              <p>Nginx 暴露前端与 API；PostgreSQL、Redis、MinIO 均在 compose 中定义，MinIO 当前为可选组件。</p>
            </div>
          </div>

          <div class="guide-links">
            <a href="https://github.com/sijie-Z/ChainAuth_WatermarkAI" target="_blank" rel="noopener">
              GitHub 仓库与 README
            </a>
            <router-link to="/trace">先试试溯源码</router-link>
            <router-link to="/login">用演示账号登录</router-link>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<script setup>
import { reactive, onMounted } from 'vue'
import { gardenApi, publicApi } from '@/api/modules'

const isDev = import.meta.env.DEV

const roleRows = [
  { role: '普通用户', description: '浏览已发布资产、申请授权、查看自己的授权与申请', account: 'user1 / 123456' },
  { role: '一级审批员', description: '审批授权申请的第一级；可审核资产发布', account: 'adm1 / 123456' },
  { role: '二级审批员', description: '复核一级已通过的申请，通过后生成授权', account: 'adm2 / 123456' },
  { role: '资产管理员', description: '管理资产、嵌入水印、上链存证', account: 'asset_mgr / 123456' },
  { role: '授权管理员', description: '查看授权台账、处理审批与合同', account: 'license_mgr / 123456' },
  { role: '超级管理员', description: '全部后台功能', account: 'admin / admin123' }
]

const stats = reactive({
  assets: '—',
  gardens: '—',
  watermarked: '—',
  chained: '—'
})

const workflow = [
  {
    title: '登录并认识自己的角色',
    role: '所有角色',
    description: '用 user1 登录可以看到普通用户视角：资产档案、我的授权与申请入口。管理员登录后会多出“管理后台”。',
    to: '/login',
    linkText: '去登录'
  },
  {
    title: '上传一件资产',
    role: '普通用户 / 资产管理员',
    description: '在资产档案右上角点击“上传资产”。系统会校验文件类型、计算哈希并自动生成列表缩略图。新资产默认是草稿。',
    to: '/assets/upload',
    linkText: '打开上传页'
  },
  {
    title: '嵌入水印',
    role: '上传者 / 资产管理员',
    description: '进入资产详情，点击“嵌入水印”。系统会写入资产唯一标识并记录水印 ID；这是上链的前提。',
    to: '/assets',
    linkText: '挑选一件资产'
  },
  {
    title: '上链存证',
    role: '上传者 / 资产管理员',
    description: '水印状态变为“已嵌入”后，“上链存证”按钮启用。成功后生成交易哈希与存证证书，可在证书页查看。',
    to: '/admin/blockchain',
    linkText: '查看存证管理'
  },
  {
    title: '提交发布并由管理员审核',
    role: '上传者 → 资产管理员',
    description: '草稿在完成水印与上链后可以“提交发布”。资产管理员在后台“资产管理”中通过审核，资产才会出现在公开列表。',
    to: '/admin/assets',
    linkText: '去后台审核'
  },
  {
    title: '申请授权',
    role: '普通用户',
    description: '在资产详情点击“申请授权”，选择授权类型、使用目的和期限。提交后可在“我的授权 → 审批中”查看进度。',
    to: '/license/my',
    linkText: '查看我的申请'
  },
  {
    title: '完成双重审批',
    role: 'adm1 → adm2',
    description: 'adm1 在“待审批”完成一级审核；adm2 再复核。二级通过后系统自动生成授权记录，申请人即可在有效期内下载。',
    to: '/admin/license/pending',
    linkText: '进入待审批'
  },
  {
    title: '下载与溯源',
    role: '被授权用户 / 任何人',
    description: '获得授权后可在资产页下载；对外分发后，任何人把图片上传到“溯源查询”即可提取水印并核对存证。',
    to: '/trace',
    linkText: '打开溯源查询'
  }
]

onMounted(async () => {
  try {
    const [statsResponse, gardensResponse] = await Promise.all([
      publicApi.getStats(),
      gardenApi.getList()
    ])
    const data = statsResponse.data?.data
    if (data) {
      stats.assets = data.total_assets ?? '—'
      stats.watermarked = data.watermarked_assets ?? '—'
      stats.chained = data.chained_assets ?? '—'
    }
    const gardens = gardensResponse.data?.data
    if (Array.isArray(gardens)) {
      stats.gardens = gardens.length
    }
  } catch {
    // 统计失败时保留占位符，不影响指南内容
  }
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.guide-page {
  min-height: 100vh;
  background: $bg-primary;
  padding-bottom: $spacing-4xl;
}

// ========== 封面 ==========
.guide-hero {
  background: $bg-card;
  border-bottom: 1px solid $border-light;
}

.guide-hero-inner {
  max-width: 1180px;
  margin: 0 auto;
  padding: 56px 40px 36px;
}

.guide-kicker {
  margin-bottom: 22px;
}

.guide-title {
  font-family: $font-display;
  font-size: clamp(27px, 7vw, 44px);
  line-height: 1.35;
  font-weight: 600;
  letter-spacing: 0.01em;
  color: $text-primary;
  margin-bottom: 18px;
}

.guide-lead {
  max-width: 46em;
  font-size: 15px;
  line-height: 1.95;
  color: $text-secondary;

  strong {
    color: $primary-dark;
    font-weight: 500;
  }
}

.guide-hero-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 28px;
}

.guide-btn {
  display: inline-flex;
  align-items: center;
  padding: 10px 20px;
  border: 1px solid $border-dark;
  border-radius: $radius-sm;
  font-size: 14px;
  color: $text-primary;
  background: transparent;

  &:hover {
    border-color: $primary-color;
    color: $primary-dark;
  }

  &-primary {
    background: $primary-color;
    border-color: $primary-dark;
    color: #fcfdfb;

    &:hover {
      background: $primary-dark;
      color: #fcfdfb;
    }
  }
}

.guide-link-inline {
  font-size: 13px;
  color: $text-secondary;

  &:hover {
    color: $primary-dark;
  }
}

.guide-facts {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0;
  max-width: 760px;
  margin-top: 40px;
  border-top: 1px solid $border-light;

  > div {
    padding: 18px 20px 0 0;
    border-right: 1px solid $border-light;

    &:last-child {
      border-right: none;
    }
  }

  dt {
    font-size: 12px;
    letter-spacing: 0.1em;
    color: $text-placeholder;
    margin-bottom: 4px;
  }

  dd {
    font-family: $font-display;
    font-size: 28px;
    font-weight: 600;
    color: $text-primary;
    font-variant-numeric: tabular-nums;
  }
}

// ========== 布局 ==========
.guide-layout {
  max-width: 1180px;
  margin: 0 auto;
  padding: 48px 40px 0;
  display: grid;
  grid-template-columns: 200px minmax(0, 1fr);
  gap: 56px;
  align-items: start;
}

.guide-toc {
  position: sticky;
  top: 86px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-left: 14px;
  border-left: 1px solid $border-light;

  .toc-title {
    font-size: 12px;
    letter-spacing: 0.12em;
    color: $text-placeholder;
    margin-bottom: 10px;
  }

  a {
    padding: 6px 0;
    font-size: 13px;
    color: $text-secondary;

    &:hover {
      color: $primary-dark;
    }
  }
}

.guide-content {
  min-width: 0;
}

.guide-section {
  scroll-margin-top: 90px;

  & + .guide-section {
    margin-top: 64px;
    padding-top: 52px;
    border-top: 1px solid $border-light;
  }
}

.section-head {
  display: flex;
  gap: 18px;
  margin-bottom: 28px;

  .section-index {
    flex-shrink: 0;
    font-family: $font-mono;
    font-size: 12px;
    letter-spacing: 0.08em;
    color: $accent-color;
    padding-top: 6px;
  }

  h2 {
    font-family: $font-display;
    font-size: 25px;
    font-weight: 600;
    color: $text-primary;
    margin-bottom: 6px;
  }

  p {
    font-size: 14px;
    line-height: 1.7;
    color: $text-secondary;
  }
}

// ========== 能力 ==========
.capability-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.capability {
  padding: 22px;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-md;

  .capability-mark {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    margin-bottom: 14px;
    border: 1px solid rgba($accent-color, 0.45);
    border-radius: $radius-xs;
    font-family: $font-display;
    font-size: 15px;
    color: $accent-color;
  }

  h3 {
    font-family: $font-display;
    font-size: 17px;
    font-weight: 600;
    color: $text-primary;
    margin-bottom: 8px;
  }

  p {
    font-size: 13px;
    line-height: 1.8;
    color: $text-secondary;
  }
}

// ========== 角色 ==========
.role-table-wrap {
  overflow-x: auto;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-md;
}

.role-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 620px;

  th,
  td {
    padding: 13px 16px;
    text-align: left;
    border-bottom: 1px solid $border-light;
    font-size: 13px;
  }

  th {
    background: $bg-secondary;
    font-weight: $font-weight-medium;
    color: $text-secondary;
    letter-spacing: 0.02em;
  }

  td {
    color: $text-primary;
    line-height: 1.6;

    &.mono {
      font-family: $font-mono;
      font-size: 12px;
      color: $text-secondary;
      white-space: nowrap;
    }
  }

  tbody tr:last-child td {
    border-bottom: none;
  }
}

.guide-note {
  margin-top: 10px;
  font-size: 12px;
  line-height: 1.7;
  color: $text-placeholder;
}

.account-hidden {
  font-family: $font-family;
  font-size: 12px;
  color: $text-placeholder;
  white-space: normal;
}

// ========== 流程 ==========
.workflow-list {
  list-style: none;
  border-left: 1px solid $border-color;
  margin-left: 12px;
}

.workflow-item {
  position: relative;
  padding: 0 0 28px 30px;

  &::before {
    content: '';
    position: absolute;
    left: -5px;
    top: 6px;
    width: 9px;
    height: 9px;
    background: $bg-card;
    border: 2px solid $primary-color;
    border-radius: 50%;
  }

  &:last-child {
    padding-bottom: 0;
  }
}

.workflow-index {
  font-family: $font-mono;
  font-size: 11px;
  letter-spacing: 0.1em;
  color: $accent-color;
}

.workflow-body {
  margin-top: 4px;

  .workflow-title-row {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 6px;
  }

  h3 {
    font-family: $font-display;
    font-size: 17px;
    font-weight: 600;
    color: $text-primary;
  }

  p {
    font-size: 13px;
    line-height: 1.8;
    color: $text-secondary;
    max-width: 52em;
  }
}

.workflow-role {
  padding: 1px 8px;
  border: 1px solid $border-color;
  border-radius: $radius-xs;
  font-size: 11px;
  color: $text-placeholder;
  white-space: nowrap;
}

.workflow-link {
  display: inline-block;
  margin-top: 8px;
  font-size: 12px;
  color: $primary-color;

  &:hover {
    color: $primary-dark;
  }
}

// ========== 功能地图 ==========
.map-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.map-card {
  display: block;
  padding: 22px;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  color: $text-primary;
  transition: border-color $transition-fast, box-shadow $transition-fast;

  &:hover {
    border-color: $primary-color;
    box-shadow: $shadow-md;
    color: $text-primary;
  }

  .map-kicker {
    font-size: 11px;
    letter-spacing: 0.12em;
    color: $accent-color;
  }

  h3 {
    font-family: $font-display;
    font-size: 18px;
    margin: 6px 0 8px;
  }

  p {
    font-size: 13px;
    line-height: 1.75;
    color: $text-secondary;
  }
}

// ========== FAQ ==========
.faq-collapse {
  border-top: 1px solid $border-light;
  border-bottom: 1px solid $border-light;

  :deep(.el-collapse-item__header) {
    font-family: $font-display;
    font-size: 15px;
    color: $text-primary;
    background: transparent;
    height: 52px;
  }

  :deep(.el-collapse-item__wrap) {
    background: transparent;
  }

  :deep(.el-collapse-item__content) {
    padding-bottom: 18px;
    font-size: 13px;
    line-height: 1.8;
    color: $text-secondary;

    code {
      padding: 2px 6px;
      background: $bg-secondary;
      border-radius: $radius-xs;
      font-family: $font-mono;
      font-size: 12px;
    }
  }
}

// ========== 部署 ==========
.deploy-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.deploy-card {
  padding: 22px;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-md;

  h3 {
    font-family: $font-display;
    font-size: 17px;
    margin-bottom: 12px;
  }

  pre {
    margin: 0 0 12px;
    padding: 14px;
    background: $ink-band;
    border-radius: $radius-sm;
    overflow-x: auto;

    code {
      font-family: $font-mono;
      font-size: 12px;
      line-height: 1.7;
      color: rgba(252, 253, 251, 0.86);
      white-space: pre;
    }
  }

  p {
    font-size: 12px;
    line-height: 1.7;
    color: $text-secondary;
  }
}

.guide-links {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  margin-top: 22px;
  font-size: 13px;

  a {
    color: $primary-color;
  }
}

// ========== 响应式 ==========
@media (max-width: 960px) {
  .guide-layout {
    grid-template-columns: 1fr;
    gap: 28px;
    padding: 32px 20px 0;
  }

  .guide-toc {
    position: static;
    flex-direction: row;
    flex-wrap: wrap;
    gap: 4px 14px;
    padding: 12px 0;
    border-left: none;
    border-top: 1px solid $border-light;
    border-bottom: 1px solid $border-light;

    .toc-title {
      width: 100%;
      margin-bottom: 4px;
    }

    a {
      padding: 4px 0;
    }
  }

  .guide-hero-inner {
    padding: 40px 20px 28px;
  }

  .capability-grid,
  .map-grid,
  .deploy-grid {
    grid-template-columns: 1fr;
  }

  .guide-facts {
    grid-template-columns: repeat(2, minmax(0, 1fr));

    > div {
      padding: 14px 12px 0 0;

      &:nth-child(2) {
        border-right: none;
      }
    }
  }
}
</style>
