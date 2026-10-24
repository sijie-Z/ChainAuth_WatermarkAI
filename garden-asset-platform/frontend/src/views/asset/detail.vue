<template>
  <div class="asset-detail-container">
    <header class="page-bar">
      <router-link to="/assets" class="page-back">
        <el-icon><ArrowLeft /></el-icon>
        返回资产档案
      </router-link>
      <h1 class="page-title">资产详情</h1>
      <span v-if="asset.asset_code" class="page-meta">{{ asset.asset_code }}</span>
      <div class="page-actions">
        <el-button
          text
          :loading="favoriteLoading"
          :title="favorited ? '取消收藏' : '收藏资产'"
          @click="toggleFavorite"
        >
          <el-icon><StarFilled v-if="favorited" /><Star v-else /></el-icon>
          {{ favorited ? '已收藏' : '收藏' }}
        </el-button>
        <el-button text title="复制当前页面链接" @click="shareAsset">
          <el-icon><Share /></el-icon>
          复制链接
        </el-button>
        <el-button
          v-if="asset.status === 'published'"
          text
          title="把资产加入自己的合集"
          @click="openCollectionDialog"
        >
          <el-icon><Collection /></el-icon>
          加入合集
        </el-button>
        <el-button
          v-if="canManage && asset.status === 'published'"
          text
          title="生成可对外核验的分享链接"
          @click="openShareDialog"
        >
          <el-icon><Link /></el-icon>
          分享核验
        </el-button>
      </div>
    </header>

    <!-- 加载骨架屏 -->
    <el-skeleton :loading="loading" animated>
      <template #template>
        <div class="detail-grid">
          <div class="skeleton-sheet">
            <el-skeleton-item variant="text" style="width: 40%; height: 26px" />
            <el-skeleton-item variant="image" style="width: 100%; aspect-ratio: 16 / 10; margin-top: 20px" />
            <el-skeleton :rows="4" animated style="margin-top: 20px" />
          </div>
          <div class="skeleton-side">
            <el-skeleton :rows="5" animated />
            <el-skeleton :rows="3" animated style="margin-top: 32px" />
          </div>
        </div>
      </template>

      <template #default>
        <!-- 错误状态 -->
        <el-card v-if="loadError" class="error-card">
          <el-empty description="资产加载失败">
            <el-button type="primary" @click="loadAsset">重试</el-button>
            <el-button @click="goBack">返回列表</el-button>
          </el-empty>
        </el-card>

        <!-- 正常内容 -->
        <div v-else class="detail-grid">
          <!-- 左侧：资产图版与著录信息 -->
          <article class="asset-sheet">
            <header class="sheet-head">
              <div class="sheet-title-group">
                <p class="sheet-kicker">{{ asset.garden_name || '苏州园林' }} · 数字资产</p>
                <h2 class="sheet-title">{{ asset.title }}</h2>
              </div>
              <StatusTag :status="asset.status" kind="asset" />
            </header>

            <!-- 当前用户在这件资产上的授权/申请状态 -->
            <div v-if="assetState" class="asset-state" :class="assetState.tone">
              <div class="asset-state-text">
                <strong>{{ assetState.title }}</strong>
                <span>{{ assetState.description }}</span>
              </div>
              <router-link :to="assetState.link" class="asset-state-action">
                {{ assetState.action }} →
              </router-link>
            </div>

            <div v-if="asset.status === 'rejected' && asset.reject_reason" class="reject-banner">
              <strong>审核未通过</strong>
              <span>{{ asset.reject_reason }}</span>
            </div>

            <figure class="preview-area">
              <div v-if="previewLoading" class="preview-placeholder">
                <el-icon class="is-loading" :size="40"><Loading /></el-icon>
                <span>正在加载预览…</span>
              </div>
              <div v-else-if="previewDeferred && !previewError" class="preview-placeholder preview-deferred">
                <el-icon :size="44"><Document /></el-icon>
                <span>文件约 {{ formatSize(asset.file_size) }}，加载预览会消耗相应流量</span>
                <el-button size="small" type="primary" plain @click="loadPreviewFile">加载预览</el-button>
              </div>
              <video
                v-else-if="asset.asset_type === 'video' && previewUrl"
                class="asset-video"
                :src="previewUrl"
                controls
                preload="metadata"
              ></video>
              <iframe
                v-else-if="asset.asset_type === 'document' && isPdfAsset && previewUrl"
                class="asset-pdf"
                :src="previewUrl"
                title="文档预览"
              ></iframe>
              <ModelViewer
                v-else-if="isModelAsset && previewUrl"
                :src="previewUrl"
                :format="modelFormat"
                class="asset-model"
                @error="previewError = true"
              />
              <el-image
                v-else-if="asset.asset_type === 'image' || asset.asset_type === 'vector'"
                class="asset-photo"
                :src="getAssetUrl(asset)"
                :preview-src-list="asset.asset_type === 'image' ? [getAssetUrl(asset)] : []"
                :preview-teleported="true"
                hide-on-click-modal
                fit="contain"
              >
                <template #error>
                  <div class="preview-placeholder">
                    <el-icon :size="48"><Picture /></el-icon>
                    <span>{{ typeLabel(asset.asset_type) }}预览暂不可用</span>
                  </div>
                </template>
              </el-image>
              <div v-else class="preview-placeholder">
                <el-icon :size="56"><Document /></el-icon>
                <span>{{ previewPlaceholderText }}</span>
              </div>
              <figcaption class="preview-caption">
                <span>{{ asset.garden_name || '未归类园林' }}</span>
                <span class="mono">{{ asset.asset_code }}</span>
              </figcaption>
            </figure>

            <dl class="spec-grid">
              <div class="spec-item">
                <dt>资产编码</dt>
                <dd class="mono">{{ asset.asset_code || '—' }}</dd>
              </div>
              <div class="spec-item">
                <dt>所属园林</dt>
                <dd>{{ asset.garden_name || '—' }}</dd>
              </div>
              <div class="spec-item">
                <dt>文件格式</dt>
                <dd>{{ (asset.file_format || '—').toUpperCase() }}</dd>
              </div>
              <div class="spec-item">
                <dt>文件大小</dt>
                <dd>{{ formatSize(asset.file_size) }}</dd>
              </div>
              <div class="spec-item">
                <dt>上传者</dt>
                <dd>{{ asset.uploader_name || asset.creator_name || '—' }}</dd>
              </div>
              <div class="spec-item">
                <dt>创建时间</dt>
                <dd>{{ formatDate(asset.created_at) }}</dd>
              </div>
              <div class="spec-item spec-span">
                <dt>著录说明</dt>
                <dd>{{ asset.description || '暂无描述' }}</dd>
              </div>
              <div v-if="tags.length" class="spec-item spec-span">
                <dt>标签</dt>
                <dd class="asset-tags">
                  <span v-for="tag in tags" :key="tag" class="asset-tag">{{ tag }}</span>
                </dd>
              </div>
            </dl>
          </article>

          <!-- 右侧：状态与操作 -->
          <aside class="side-panel">
            <section class="side-block">
              <header class="side-head">
                <span class="side-kicker">水印状态</span>
                <StatusTag :status="requiresWatermark ? (asset.watermark_status || 'none') : 'not_applicable'" kind="watermark" />
              </header>
              <dl class="side-meta">
                <div v-if="asset.watermark_id" class="side-row">
                  <dt>水印 ID</dt>
                  <dd class="mono">{{ asset.watermark_id }}</dd>
                </div>
                <div v-if="asset.vr_value != null" class="side-row">
                  <dt>鲁棒性值</dt>
                  <dd>{{ asset.vr_value?.toFixed(4) || '-' }}</dd>
                </div>
                <div v-if="!asset.watermark_id" class="side-row">
                  <dt>说明</dt>
                  <dd>尚未写入水印标识</dd>
                </div>
              </dl>
              <el-button
                v-if="canManage && requiresWatermark && !watermarkReady"
                type="primary"
                class="side-action"
                :loading="watermarking || asset.watermark_status === 'pending'"
                :disabled="asset.watermark_status === 'pending'"
                @click="embedWatermark"
              >
                {{ asset.watermark_status === 'pending' ? '水印处理中…' : '嵌入水印' }}
              </el-button>
              <el-button
                v-else-if="canManage && requiresWatermark"
                class="side-action"
                :loading="extracting"
                @click="extractWatermark"
              >
                提取并校验水印
              </el-button>
              <p v-if="!requiresWatermark" class="side-hint">
                该资产类型不适用盲水印，将使用文件哈希与版本记录存证。
              </p>
              <p v-if="asset.watermark_status === 'pending'" class="side-hint task-hint">
                后台水印任务处理中，可以离开此页，稍后回来查看结果。
              </p>
              <p v-if="asset.watermark_status === 'failed'" class="side-hint task-hint error">
                上次水印任务失败，可重新提交。
              </p>
              <p v-else-if="!canManage" class="side-hint">仅上传者或资产管理员可操作水印。</p>
            </section>

            <section class="side-block">
              <header class="side-head">
                <span class="side-kicker">区块链存证</span>
                <StatusTag :status="asset.chain_status || 'none'" kind="chain" />
              </header>
              <dl class="side-meta">
                <div v-if="asset.chain_tx_hash" class="side-row">
                  <dt>交易哈希</dt>
                  <dd class="mono">{{ asset.chain_tx_hash }}</dd>
                </div>
                <div v-if="asset.certificate_id" class="side-row">
                  <dt>证书编号</dt>
                  <dd class="mono">{{ asset.certificate_id }}</dd>
                </div>
                <div v-if="!asset.chain_tx_hash" class="side-row">
                  <dt>说明</dt>
                  <dd>尚未写入联盟链</dd>
                </div>
              </dl>
              <el-button
                v-if="canManage && asset.chain_status !== 'confirmed'"
                type="primary"
                class="side-action"
                :disabled="!chainReady || asset.chain_status === 'pending'"
                :loading="chaining || asset.chain_status === 'pending'"
                @click="registerChain"
              >
                {{ asset.chain_status === 'pending' ? '存证处理中…' : '上链存证' }}
              </el-button>
              <el-button v-else-if="canManage" class="side-action" @click="viewCertificate">
                查看存证证书
              </el-button>
              <p v-if="!canManage" class="side-hint">存证操作由上传者或资产管理员完成。</p>
              <p v-else-if="asset.chain_status !== 'confirmed' && !chainReady" class="side-hint">
                上链前需先完成水印嵌入
              </p>
              <p v-else-if="asset.chain_status === 'pending'" class="side-hint task-hint">
                后台存证任务处理中，完成后会自动签发当前版本证书。
              </p>
              <p v-else-if="asset.chain_status === 'failed'" class="side-hint task-hint error">
                上次存证任务失败，可重新提交。
              </p>
              <p
                v-if="canManage && !asset.certificate_id && hasHistoricalCertificates"
                class="side-hint"
              >
                当前版本未存证；历史版本证书可在“版本”页签查看。
              </p>
            </section>

            <section class="side-block side-actions">
              <header class="side-head">
                <span class="side-kicker">授权与分发</span>
              </header>
              <p class="side-note">下载与使用需经双重审批，授权记录会写入台账。</p>
              <div v-if="licenseStatusError" class="license-state-error">
                授权状态加载失败，暂时无法判断是否需要重新申请。
                <el-button link type="primary" size="small" @click="loadExtras">重试</el-button>
              </div>
              <el-button
                v-if="canSubmitPublish && (!requiresWatermark || watermarkReady)"
                type="primary"
                class="side-action"
                :loading="publishing"
                @click="publishAsset"
              >
                {{ asset.status === 'rejected' ? '重新提交发布' : '提交发布' }}
              </el-button>
              <p v-else-if="canSubmitPublish" class="side-hint">
                完成水印嵌入后才能提交发布
              </p>
              <el-skeleton
                v-if="extrasLoading"
                class="license-loading"
                animated
                :rows="1"
              />
              <template v-else>
                <el-button
                  v-if="canDownload"
                  type="primary"
                  class="side-action"
                  :loading="downloading"
                  @click="downloadAsset"
                >
                  <el-icon><Download /></el-icon>
                  下载资产
                </el-button>
                <el-button
                  v-else-if="pendingApplication"
                  class="side-action"
                  @click="goToMyLicenses"
                >
                  查看审批进度
                </el-button>
                <el-button
                  v-else
                  type="primary"
                  class="side-action"
                  :disabled="licenseStatusError"
                  @click="applyLicense"
                >
                  {{ rejectedApplication ? '重新申请授权' : '申请授权' }}
                </el-button>
              </template>
              <el-button class="side-action" @click="goBack">返回资产列表</el-button>
              <el-button v-if="canManage" text class="side-action" @click="openAssetLicenses">
                授权与下载记录
              </el-button>
              <el-button v-if="canManage" text class="side-action" @click="openEditDialog">
                编辑著录信息
              </el-button>
            </section>
          </aside>
        </div>

        <!-- 编辑著录信息 -->
        <el-dialog v-model="editVisible" title="编辑著录信息" width="min(560px, 92vw)">
          <el-form label-position="top">
            <el-form-item label="标题">
              <el-input v-model="editForm.title" maxlength="100" show-word-limit />
            </el-form-item>
            <el-form-item label="著录说明">
              <el-input v-model="editForm.description" type="textarea" :rows="5" maxlength="1000" show-word-limit />
            </el-form-item>
            <el-form-item label="标签">
              <el-select
                v-model="editForm.tags"
                multiple
                filterable
                allow-create
                default-first-option
                placeholder="输入标签后回车添加，最多 20 个"
                style="width: 100%"
              >
                <el-option v-for="tag in tags" :key="tag" :label="tag" :value="tag" />
              </el-select>
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="editVisible = false">取消</el-button>
            <el-button type="primary" :loading="editSaving" @click="saveEdit">保存</el-button>
          </template>
        </el-dialog>

        <!-- 授权与下载记录 -->
        <el-dialog
          v-model="assetLicenseDialogVisible"
          title="授权与下载记录"
          width="min(900px, 94vw)"
        >
          <p class="asset-license-caption">
            {{ asset.asset_code }} · {{ asset.title }}
          </p>
          <el-skeleton v-if="assetLicensesLoading" animated :rows="4" />
          <div v-else-if="assetLicensesError" class="evidence-error">
            <span>授权记录加载失败。</span>
            <el-button type="primary" link @click="loadAssetLicenses">重试</el-button>
          </div>
          <el-tabs v-else>
            <el-tab-pane :label="`授权记录（${assetLicenses.length}）`">
              <el-table :data="assetLicenses" stripe row-key="id" style="width: 100%">
                <el-table-column label="被授权方" min-width="120">
                  <template #default="{ row }">{{ row.licensee_name || '-' }}</template>
                </el-table-column>
                <el-table-column label="状态" width="90">
                  <template #default="{ row }">
                    <el-tag size="small" :type="licenseStatusType(row.status)">
                      {{ licenseStatusLabel(row.status) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="到期时间" width="120">
                  <template #default="{ row }">
                    {{ row.end_time ? formatDate(row.end_time) : '长期' }}
                  </template>
                </el-table-column>
                <el-table-column label="下载 / 配额" width="110">
                  <template #default="{ row }">
                    {{ row.download_count || 0 }} / {{ row.max_downloads ?? '不限' }}
                  </template>
                </el-table-column>
                <el-table-column label="用途 / 地域" min-width="180" show-overflow-tooltip>
                  <template #default="{ row }">
                    {{ row.usage_purpose_code || row.usage_scope || '-' }} · {{ row.territory || '不限地域' }}
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="130" fixed="right">
                  <template #default="{ row }">
                    <el-button
                      v-if="row.can_renew"
                      type="primary"
                      link
                      size="small"
                      @click="renewAssetLicense(row)"
                    >续期</el-button>
                    <el-button
                      v-if="row.can_revoke"
                      type="danger"
                      link
                      size="small"
                      @click="revokeAssetLicense(row)"
                    >撤销</el-button>
                  </template>
                </el-table-column>
              </el-table>
              <el-empty
                v-if="assetLicenses.length === 0"
                description="该资产暂无授权记录"
                :image-size="56"
              />
            </el-tab-pane>
            <el-tab-pane :label="`申请记录（${assetApplications.length}）`">
              <el-table :data="assetApplications" stripe row-key="id" style="width: 100%">
                <el-table-column label="申请人" min-width="120">
                  <template #default="{ row }">{{ row.applicant_name || '-' }}</template>
                </el-table-column>
                <el-table-column label="状态" width="100">
                  <template #default="{ row }">
                    <el-tag size="small" type="info">{{ applicationStatusLabel(row.status) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="申请时间" width="120">
                  <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
                </el-table-column>
                <el-table-column label="用途" min-width="220" show-overflow-tooltip>
                  <template #default="{ row }">
                    {{ row.usage_purpose || row.usage_scope || '-' }}
                  </template>
                </el-table-column>
              </el-table>
              <el-empty
                v-if="assetApplications.length === 0"
                description="该资产暂无申请记录"
                :image-size="56"
              />
            </el-tab-pane>
          </el-tabs>
        </el-dialog>

        <!-- 分享核验链接 -->
        <el-dialog v-model="shareVisible" title="分享核验" width="min(620px, 94vw)">
          <p class="share-dialog-note">
            生成一个免登录的核验页，外部人员无需注册即可查看资产信息与证据链。
            分享链接不会暴露文件存储路径。
          </p>
          <el-form label-position="top" class="share-form">
            <div class="share-form-grid">
              <el-form-item label="有效期">
                <el-select v-model="shareForm.expires_in_days" style="width: 100%">
                  <el-option label="7 天" :value="7" />
                  <el-option label="30 天" :value="30" />
                  <el-option label="90 天" :value="90" />
                  <el-option label="长期有效" :value="0" />
                </el-select>
              </el-form-item>
              <el-form-item label="访问码（可选）">
                <el-input
                  v-model="shareForm.access_code"
                  placeholder="4-32 位，留空则无需访问码"
                  maxlength="32"
                  show-password
                />
              </el-form-item>
            </div>
            <el-form-item label="下载权限">
              <div class="share-download-row">
                <el-switch v-model="shareForm.allow_download" active-text="允许下载" />
                <el-input
                  v-if="shareForm.allow_download"
                  v-model.number="shareForm.max_downloads"
                  type="number"
                  min="1"
                  max="1000"
                  placeholder="下载次数上限（留空不限）"
                  class="share-limit-input"
                />
              </div>
            </el-form-item>
          </el-form>

          <div class="share-create-row">
            <el-button type="primary" :loading="shareCreating" @click="createShareLink">
              生成分享链接
            </el-button>
            <span class="share-create-hint">仅已发布资产可分享</span>
          </div>

          <div v-if="createdShare" class="created-share">
            <span class="created-label">新链接</span>
            <code>{{ sharePageUrl(createdShare.token) }}</code>
            <el-button size="small" @click="copyShareUrl(createdShare.token)">
              <el-icon><CopyDocument /></el-icon>
              复制
            </el-button>
          </div>

          <div class="existing-shares">
            <div class="existing-head">
              <strong>已创建的链接</strong>
              <span v-if="shareListLoading">加载中…</span>
            </div>
            <el-empty
              v-if="!shareListLoading && shares.length === 0"
              description="还没有分享链接"
              :image-size="52"
            />
            <ul v-else class="share-list">
              <li v-for="share in shares" :key="share.id" class="share-item">
                <div class="share-item-main">
                  <span class="share-item-url">{{ sharePageUrl(share.token) }}</span>
                  <span class="share-item-meta">
                    {{ share.has_access_code ? '需要访问码' : '无需访问码' }}
                    · {{ share.allow_download ? `允许下载（${share.download_count}/${share.max_downloads || '不限'}）` : '仅查看' }}
                    · {{ share.expires_at ? `${formatDate(share.expires_at)} 到期` : '长期有效' }}
                  </span>
                </div>
                <div class="share-item-actions">
                  <el-button size="small" text @click="copyShareUrl(share.token)">复制</el-button>
                  <el-button
                    size="small"
                    text
                    type="danger"
                    :disabled="share.status !== 'active'"
                    @click="revokeShare(share)"
                  >
                    {{ share.status === 'active' ? '撤销' : '已失效' }}
                  </el-button>
                </div>
              </li>
            </ul>
          </div>
        </el-dialog>

        <!-- 加入合集 -->
        <el-dialog v-model="collectionDialogVisible" title="加入合集" width="min(520px, 92vw)">
          <p class="share-dialog-note">
            合集用于按主题组织资产。你可以同时加入多个合集；取消勾选会从对应合集中移出。
          </p>
          <el-skeleton v-if="collectionLoading" animated :rows="3" />
          <el-empty
            v-else-if="collectionOptions.length === 0"
            description="还没有合集"
            :image-size="60"
          >
            <el-button type="primary" @click="$router.push('/collections')">去新建合集</el-button>
          </el-empty>
          <el-checkbox-group v-else v-model="collectionChecked" class="collection-choices">
            <label
              v-for="item in collectionOptions"
              :key="item.id"
              class="collection-choice"
            >
              <el-checkbox :value="item.id" />
              <span class="choice-body">
                <strong>{{ item.name }}</strong>
                <small>{{ item.asset_count }} 件资产 · {{ item.is_public ? '公开' : '私有' }}</small>
              </span>
            </label>
          </el-checkbox-group>
          <template #footer>
            <el-button @click="collectionDialogVisible = false">取消</el-button>
            <el-button
              type="primary"
              :loading="collectionSaving"
              :disabled="collectionOptions.length === 0"
              @click="saveCollections"
            >
              保存
            </el-button>
          </template>
        </el-dialog>

        <!-- 下载范围声明 -->
        <el-dialog
          v-model="downloadDialogVisible"
          title="确认使用范围"
          width="min(480px, 92vw)"
        >
          <el-alert
            type="info"
            :closable="false"
            show-icon
            class="download-scope-alert"
            title="本次下载会记录申报用途与地域"
            description="申报范围必须与授权范围一致，超出范围会被拒绝并写入台账。"
          />
          <el-form label-width="90px" class="download-scope-form">
            <el-form-item label="使用目的">
              <el-select v-model="downloadForm.purpose" style="width: 100%">
                <el-option
                  v-for="item in downloadPurposeOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="使用地域">
              <el-select v-model="downloadForm.territory" style="width: 100%">
                <el-option
                  v-for="item in downloadTerritoryOptions"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </el-select>
            </el-form-item>
          </el-form>
          <div v-if="activeLicense" class="download-scope-summary">
            <p>{{ activeLicense.scope_summary || '按授权合同约定' }}</p>
            <p v-if="activeLicense.max_downloads">
              剩余下载次数：{{ activeLicense.download_remaining }} / {{ activeLicense.max_downloads }}
            </p>
            <p class="download-fingerprint-note">
              本次下载会生成带授权编号与账号的可见指纹副本，原盲水印仍保留。
            </p>
          </div>
          <template #footer>
            <el-button @click="downloadDialogVisible = false">取消</el-button>
            <el-button type="primary" :loading="downloading" @click="confirmDownload">
              确认下载
            </el-button>
          </template>
        </el-dialog>

        <!-- 上传新版本 -->
        <el-dialog
          v-model="versionDialogVisible"
          title="上传新版本"
          width="min(560px, 94vw)"
          :close-on-click-modal="false"
        >
          <el-alert type="warning" :closable="false" show-icon class="version-warning">
            新版本会替换当前文件并重置水印状态；已发布/待审资产会退回草稿，需要重新水印、提交发布并通过审核。
            历史存证仍对应旧版本，需要重新核验或存证。
          </el-alert>
          <el-upload
            drag
            :auto-upload="false"
            :limit="1"
            :on-change="handleVersionFile"
            :on-exceed="handleVersionExceed"
            :show-file-list="false"
            :accept="versionAccept"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              将新版本文件拖到此处，或 <em>点击选择</em>
            </div>
          </el-upload>
          <div v-if="versionFile" class="version-file">
            <el-icon><Document /></el-icon>
            <span>{{ versionFile.name }} · {{ formatSize(versionFile.size) }}</span>
          </div>
          <el-input
            v-model="versionNote"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            class="version-note-input"
            placeholder="变更说明（可选），例如：修正斗拱标注、替换为高清扫描件"
          />
          <el-progress
            v-if="versionUploading"
            :percentage="versionProgress"
            :stroke-width="4"
            class="version-progress"
          />
          <template #footer>
            <el-button :disabled="versionUploading" @click="versionDialogVisible = false">取消</el-button>
            <el-button
              type="primary"
              :loading="versionUploading"
              :disabled="!versionFile"
              @click="submitVersion"
            >
              上传并保存
            </el-button>
          </template>
        </el-dialog>

        <!-- 证据、标注、版本与讨论 -->
        <section class="collab-tabs-card">
          <el-tabs v-model="activeDetailTab" class="collab-tabs">
            <el-tab-pane label="证据链" name="evidence">
              <div class="collab-panel">
                <section class="evidence-section">
                  <header class="related-head">
                    <div>
                      <h2 class="related-title">溯源证据链</h2>
                      <p class="related-subtitle">上传登记、水印、链上存证与业务台账按时间排列</p>
                    </div>
                    <div class="evidence-actions">
                      <el-button
                        v-if="canManage && asset.status !== 'deleted'"
                        plain
                        size="small"
                        :loading="evidenceExporting"
                        @click="exportEvidencePackage"
                      >
                        导出证据包
                      </el-button>
                      <el-button
                        v-if="canManage && asset.status === 'published'"
                        type="primary"
                        plain
                        size="small"
                        @click="openShareDialog"
                      >
                        分享核验
                      </el-button>
                    </div>
                  </header>
                  <el-skeleton v-if="evidenceLoading" animated :rows="4" />
                  <div v-else-if="evidenceError" class="evidence-error">
                    <span>证据链加载失败，可能影响对资产状态的判断。</span>
                    <el-button type="primary" link @click="loadEvidence">重新加载</el-button>
                  </div>
                  <EvidenceChain
                    v-else
                    :items="evidence.items"
                    :summary="evidence.summary"
                  />
                </section>
              </div>
            </el-tab-pane>

            <el-tab-pane label="标注" name="annotations" lazy>
              <div class="collab-panel">
                <AnnotationBoard
                  v-if="['image', 'vector'].includes(asset.asset_type)"
                  :asset-id="asset.id"
                  :asset-type="asset.asset_type"
                  :image-url="getAssetUrl(asset)"
                  :version-id="currentVersionId"
                  :version-no="currentVersionNo"
                />
              </div>
            </el-tab-pane>

            <el-tab-pane label="版本" name="versions" lazy>
              <div class="collab-panel">
                <!-- 版本历史 -->
                <section class="version-section">
          <header class="related-head">
            <div>
              <h2 class="related-title">版本历史</h2>
              <p class="related-subtitle">
                {{ versions.length ? `共 ${versions.length} 个版本 · 当前 v${currentVersionNo}` : '文件修订与替换记录' }}
              </p>
            </div>
            <el-button
              v-if="canManage && asset.status !== 'deleted'"
              type="primary"
              plain
              size="small"
              @click="openVersionDialog"
            >
              上传新版本
            </el-button>
          </header>
          <el-skeleton v-if="versionsLoading" animated :rows="3" />
          <div v-else-if="versionsError" class="evidence-error">
            <span>版本历史加载失败。</span>
            <el-button type="primary" link @click="loadVersions">重新加载</el-button>
          </div>
          <div v-else-if="versions.length === 0" class="version-empty">
            暂无版本记录。旧资产会在执行初始化脚本后补齐 v1。
          </div>
          <div v-else class="version-list">
            <article
              v-for="version in versions"
              :key="version.id"
              class="version-item"
              :class="{ current: version.is_current }"
            >
              <div class="version-main">
                <div class="version-head">
                  <strong class="version-no">v{{ version.version_no }}</strong>
                  <el-tag v-if="version.is_current" size="small" type="success" effect="plain">当前版本</el-tag>
                  <span class="version-meta">
                    {{ (version.file_format || '文件').toUpperCase() }}
                    · {{ formatSize(version.file_size) }}
                    · {{ version.creator_name || '—' }}
                    · {{ formatDate(version.created_at) }}
                  </span>
                </div>
                <p class="version-note">{{ version.change_note || '无变更说明' }}</p>
                <p v-if="version.file_hash" class="version-hash" :title="version.file_hash">
                  SHA-256 {{ version.file_hash.slice(0, 16) }}…{{ version.file_hash.slice(-8) }}
                </p>
                <div v-if="version.certificate" class="version-proof">
                  <el-icon><Link /></el-icon>
                  <router-link
                    :to="`/certificate/${version.certificate.certificate_id}`"
                    class="version-proof-link"
                  >
                    {{ version.certificate.certificate_id }}
                  </router-link>
                  <el-tag
                    size="small"
                    :type="version.certificate.is_current ? 'success' : 'info'"
                    effect="plain"
                  >
                    {{ version.certificate.is_current ? '当前版本存证' : '历史版本存证' }}
                  </el-tag>
                </div>
                <p v-else class="version-proof muted">该版本未存证</p>
              </div>
              <div class="version-actions">
                <el-button
                  v-if="canManage"
                  size="small"
                  link
                  type="primary"
                  :loading="versionDownloadingId === version.id"
                  @click="downloadVersion(version)"
                >
                  下载
                </el-button>
                <el-button
                  v-if="canManage && !version.is_current"
                  size="small"
                  link
                  type="warning"
                  :loading="versionRestoringId === version.id"
                  @click="restoreVersion(version)"
                >
                  恢复为此版本
                </el-button>
              </div>
            </article>
          </div>
                </section>
              </div>
            </el-tab-pane>

            <el-tab-pane label="讨论" name="comments" lazy>
              <div class="collab-panel">
                <CommentSection :asset-id="asset.id" />
              </div>
            </el-tab-pane>
          </el-tabs>
        </section>

        <!-- 同园林相关资产 -->
        <section v-if="related.length" class="related-section">
          <header class="related-head">
            <div>
              <h2 class="related-title">同园林资产</h2>
              <p class="related-subtitle">{{ asset.garden_name || '本园林' }} · 继续浏览</p>
            </div>
            <router-link to="/assets" class="related-more">查看全部 →</router-link>
          </header>
          <div class="related-grid">
            <router-link
              v-for="item in related"
              :key="item.id"
              :to="`/assets/${item.id}`"
              class="related-card"
            >
              <div class="related-thumb">
                <img :src="getCardUrl(item)" :alt="item.title" loading="lazy" @error="onRelatedImageError" />
              </div>
              <div class="related-body">
                <h3>{{ item.title }}</h3>
                <p class="mono">{{ item.asset_code }}</p>
              </div>
            </router-link>
          </div>
        </section>
      </template>
    </el-skeleton>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft, Collection, CopyDocument, Document, Link, Picture, Star, StarFilled, Share,
  Download, UploadFilled, Loading
} from '@element-plus/icons-vue'
import { assetApi, collectionApi, licenseApi, watermarkApi, blockchainApi, taskApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'
import { copyToClipboard, parseBackendDate } from '@/utils'
import EvidenceChain from '@/components/common/EvidenceChain.vue'
import AnnotationBoard from '@/components/asset/AnnotationBoard.vue'
import CommentSection from '@/components/asset/CommentSection.vue'
import ModelViewer from '@/components/ModelViewer.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const asset = ref({})
const loading = ref(true)
const loadError = ref(false)
const watermarking = ref(false)
const extracting = ref(false)
const chaining = ref(false)
const downloading = ref(false)
const publishing = ref(false)
const editVisible = ref(false)
const editSaving = ref(false)
const editForm = ref({ title: '', description: '', tags: [] })
const favorited = ref(false)
const favoriteLoading = ref(false)
const tags = ref([])
const related = ref([])
const myLicenses = ref([])
const extrasLoading = ref(true)
const assetLicenseDialogVisible = ref(false)
const assetLicenses = ref([])
const assetApplications = ref([])
const assetLicensesLoading = ref(false)
const assetLicensesError = ref(false)
const myApplications = ref([])
const activeDetailTab = ref('evidence')
const evidence = ref({ items: [], summary: null })
const evidenceLoading = ref(false)
const evidenceError = ref(false)
const evidenceExporting = ref(false)
const licenseStatusError = ref(false)
const shareVisible = ref(false)
const shareCreating = ref(false)
const shareListLoading = ref(false)
const shares = ref([])
const createdShare = ref(null)
const shareForm = reactive({
  expires_in_days: 7,
  access_code: '',
  allow_download: false,
  max_downloads: null
})
const collectionDialogVisible = ref(false)
const collectionOptions = ref([])
const collectionChecked = ref([])
const collectionLoading = ref(false)
const collectionSaving = ref(false)
const versions = ref([])
const versionsLoading = ref(false)
const versionsError = ref(false)
const versionsLoaded = ref(false)
const versionDialogVisible = ref(false)
const versionFile = ref(null)
const versionNote = ref('')
const versionUploading = ref(false)
const versionProgress = ref(0)
const versionDownloadingId = ref(null)
const versionRestoringId = ref(null)
const activeTask = ref(null)
const previewUrl = ref('')
const previewLoading = ref(false)
const previewError = ref(false)
const downloadDialogVisible = ref(false)
const downloadForm = reactive({
  purpose: 'personal_learning',
  territory: '中国大陆'
})
const downloadPurposeOptions = [
  { value: 'personal_learning', label: '个人学习' },
  { value: 'teaching_research', label: '教学科研' },
  { value: 'commercial_marketing', label: '商业宣传' },
  { value: 'publication', label: '出版发行' },
  { value: 'exhibition', label: '公开展览' },
  { value: 'derivative', label: '衍生创作' },
  { value: 'other', label: '其他' }
]
const downloadTerritoryOptions = ['中国大陆', '中国港澳台', '全球', '海外']
let taskPollTimer = null

const VERSION_ACCEPT = {
  image: 'image/*',
  vector: '.shp,.geojson,.kml,.kmz,.zip',
  document: '.pdf,.doc,.docx,.dwg,.dxf',
  video: '.mp4,.mov,.avi,.mkv',
  model: '.obj,.fbx,.gltf,.glb,.stl'
}
const versionAccept = computed(() => VERSION_ACCEPT[asset.value.asset_type] || '')
const currentVersionNo = computed(() => {
  const current = versions.value.find(item => item.is_current)
  return current?.version_no || versions.value[0]?.version_no || 1
})
const currentVersionId = computed(() => {
  const current = versions.value.find(item => item.is_current)
  return current?.id || versions.value[0]?.id || null
})
const watermarkReady = computed(() =>
  ['embedded', 'verified'].includes(asset.value.watermark_status)
)
const hasHistoricalCertificates = computed(() =>
  versions.value.some(version => Boolean(version.certificate))
)
const requiresWatermark = computed(() =>
  ['image', 'vector'].includes(asset.value.asset_type)
)
const chainReady = computed(() => watermarkReady.value || !requiresWatermark.value)
const isOwner = computed(() => {
  const userId = userStore.user?.id
  return Boolean(userId) && [asset.value.creator_id, asset.value.owner_id, asset.value.uploader_id].includes(userId)
})
const canManage = computed(() => {
  const role = userStore.userRole
  return ['admin', 'asset_admin'].includes(role) || isOwner.value
})
const activeLicense = computed(() => myLicenses.value.find(license => {
  if (license.status !== 'active') return false
  if (!license.end_time) return true
  return new Date(license.end_time).getTime() > Date.now()
}) || null)
const pendingApplication = computed(() => myApplications.value.find(application =>
  ['pending', 'adm1_approved'].includes(application.status)
) || null)
const rejectedApplication = computed(() => myApplications.value.find(application =>
  application.status === 'rejected'
) || null)
const canDownload = computed(() => Boolean(canManage.value || activeLicense.value))
const isPdfAsset = computed(() =>
  asset.value.asset_type === 'document'
  && ['pdf'].includes((asset.value.file_format || '').toLowerCase())
)
const modelFormat = computed(() => (asset.value.file_format || '').toLowerCase())
const isModelAsset = computed(() =>
  asset.value.asset_type === 'model'
  && ['glb', 'gltf', 'stl', 'obj'].includes(modelFormat.value)
)
const previewSupported = computed(() =>
  asset.value.asset_type === 'video' || isPdfAsset.value || isModelAsset.value
)
// 大文件不自动拉取预览，避免打开详情页就开始消耗大量流量
const PREVIEW_AUTO_LOAD_LIMIT = 25 * 1024 * 1024
const previewDeferred = computed(() =>
  previewSupported.value
  && canDownload.value
  && !previewUrl.value
  && !previewLoading.value
  && Number(asset.value.file_size || 0) > PREVIEW_AUTO_LOAD_LIMIT
)
const previewPlaceholderText = computed(() => {
  if (previewSupported.value) {
    if (!canDownload.value) return '获得授权后可在线预览'
    if (previewError.value) return '预览加载失败，可下载后查看'
    return '预览加载中…'
  }
  if (asset.value.asset_type === 'model') {
    return '该模型格式暂不支持在线预览，可下载后查看'
  }
  if (asset.value.asset_type === 'document') {
    return '该文档格式暂不支持在线预览，可下载后查看'
  }
  return `${typeLabel(asset.value.asset_type)}预览暂不可用`
})
const canSubmitPublish = computed(() =>
  isOwner.value && ['draft', 'rejected'].includes(asset.value.status)
)
const assetState = computed(() => {
  if (activeLicense.value) {
    const end = activeLicense.value.end_time
      ? new Date(activeLicense.value.end_time).toLocaleDateString('zh-CN')
      : '长期有效'
    return {
      tone: 'success',
      title: '你已获得该资产的使用授权',
      description: `${activeLicense.value.license_code} · 有效期至 ${end}`,
      action: '查看我的授权',
      link: '/license/my'
    }
  }
  if (pendingApplication.value) {
    const stage = pendingApplication.value.status === 'adm1_approved'
      ? '一级审批已通过，等待二级复核'
      : '已提交，等待一级审批'
    return {
      tone: 'info',
      title: '授权申请正在审批中',
      description: stage,
      action: '查看审批进度',
      link: '/license/my?tab=pending'
    }
  }
  if (rejectedApplication.value) {
    return {
      tone: 'warning',
      title: '上次授权申请未通过',
      description: rejectedApplication.value.adm2_review_comment
        || rejectedApplication.value.adm1_review_comment
        || '可以补充材料后重新申请',
      action: '重新申请',
      link: `/license/apply?asset_id=${asset.value.id}`
    }
  }
  return null
})

async function loadAsset() {
  loading.value = true
  loadError.value = false
  try {
    const response = await assetApi.getDetail(route.params.id)
    if (response.data.code === 200) {
      asset.value = response.data.data
      loadExtras()
      loadEvidence()
      if (activeDetailTab.value === 'versions') {
        loadVersions()
      }
    } else {
      loadError.value = true
    }
  } catch (error) {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

async function loadExtras() {
  const id = route.params.id
  extrasLoading.value = true
  const results = await Promise.allSettled([
    assetApi.getFavorite(id),
    assetApi.getTags(id),
    assetApi.getRelated(id),
    licenseApi.getMyLicenses({ asset_id: id, per_page: 20 }),
    licenseApi.myApplications({ asset_id: id, per_page: 20 })
  ])

  if (results[0].status === 'fulfilled' && results[0].value.data?.code === 200) {
    favorited.value = Boolean(results[0].value.data.data?.favorited)
  }
  if (results[1].status === 'fulfilled' && results[1].value.data?.code === 200) {
    tags.value = (results[1].value.data.data || []).map(tag => tag.name).filter(Boolean)
  }
  if (results[2].status === 'fulfilled' && results[2].value.data?.code === 200) {
    related.value = results[2].value.data.data || []
  }
  if (results[3].status === 'fulfilled' && results[3].value.data?.code === 200) {
    myLicenses.value = results[3].value.data.data?.items || []
  }
  if (results[4].status === 'fulfilled' && results[4].value.data?.code === 200) {
    myApplications.value = results[4].value.data.data?.items || []
  }
  // 授权/申请状态未知时不能贸然让用户再次申请，避免重复提交
  licenseStatusError.value = [results[3], results[4]].some(
    result => result.status !== 'fulfilled' || result.value.data?.code !== 200
  )
  extrasLoading.value = false
}

async function openAssetLicenses() {
  assetLicenseDialogVisible.value = true
  await loadAssetLicenses()
}

async function loadAssetLicenses() {
  if (!asset.value.id) return
  assetLicensesLoading.value = true
  assetLicensesError.value = false
  try {
    const response = await assetApi.getLicenses(asset.value.id)
    if (response.data?.code === 200) {
      assetLicenses.value = response.data.data?.licenses || []
      assetApplications.value = response.data.data?.applications || []
    } else {
      assetLicensesError.value = true
    }
  } catch {
    assetLicensesError.value = true
  } finally {
    assetLicensesLoading.value = false
  }
}

function licenseStatusLabel(status) {
  return { active: '生效中', expired: '已过期', revoked: '已撤销' }[status] || status
}

function licenseStatusType(status) {
  return { active: 'success', expired: 'info', revoked: 'danger' }[status] || 'info'
}

function applicationStatusLabel(status) {
  return {
    pending: '待一级审批',
    adm1_approved: '待二级审批',
    approved: '已通过',
    rejected: '已驳回',
    cancelled: '已撤回'
  }[status] || status
}

async function renewAssetLicense(row) {
  let endDate
  try {
    const result = await ElMessageBox.prompt(
      '请输入新的到期日期（YYYY-MM-DD）',
      '授权续期',
      {
        inputValue: row.end_time ? row.end_time.slice(0, 10) : '',
        inputPattern: /^\d{4}-\d{2}-\d{2}$/,
        inputErrorMessage: '日期格式为 YYYY-MM-DD',
        confirmButtonText: '续期',
        cancelButtonText: '取消'
      }
    )
    endDate = result.value
  } catch {
    return
  }
  try {
    await licenseApi.renew(row.id, { end_time: `${endDate}T23:59:59` })
    ElMessage.success('授权已续期')
    await loadAssetLicenses()
    loadExtras()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '续期失败')
  }
}

async function revokeAssetLicense(row) {
  let reason = ''
  try {
    const result = await ElMessageBox.prompt(
      '撤销后对方将立即无法继续下载，历史下载记录仍保留。可填写原因：',
      '撤销授权',
      {
        inputPlaceholder: '撤销原因（可选）',
        confirmButtonText: '撤销',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    reason = result.value || ''
  } catch {
    return
  }
  try {
    await licenseApi.revoke(row.id, { reason })
    ElMessage.success('授权已撤销')
    await loadAssetLicenses()
    loadExtras()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '撤销失败')
  }
}

async function loadEvidence() {  if (!asset.value.id) return
  evidenceLoading.value = true
  evidenceError.value = false
  try {
    const response = await assetApi.getEvidence(asset.value.id)
    if (response.data?.code === 200) {
      evidence.value = response.data.data || { items: [], summary: null }
    } else {
      evidenceError.value = true
    }
  } catch {
    evidenceError.value = true
  } finally {
    evidenceLoading.value = false
  }
}

async function exportEvidencePackage() {
  if (!asset.value.id || evidenceExporting.value) return

  try {
    await ElMessageBox.confirm(
      '将打包当前版本原文件与水印副本（超过服务端大小限制时只含清单与证书）、证据链、各版本证书与 SHA-256 校验清单。历史版本只保留记录，不包含文件。',
      '导出证据包',
      { type: 'info', confirmButtonText: '生成并下载', cancelButtonText: '取消' }
    )
  } catch {
    return
  }

  evidenceExporting.value = true
  try {
    const response = await assetApi.exportEvidencePackage(asset.value.id)
    const omitted = response.headers?.['x-evidence-package-omitted'] === '1'
    const url = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.download = `${asset.value.asset_code}-evidence.zip`
    document.body.appendChild(link)
    link.click()
    link.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
    ElMessage.success(
      omitted
        ? '证据包已生成：文件超出大小限制，仅包含清单、证书与证据链'
        : '证据包已生成并开始下载'
    )
  } catch (error) {
    let message = '证据包导出失败'
    const data = error.response?.data
    if (data instanceof Blob) {
      try {
        const parsed = JSON.parse(await data.text())
        message = parsed.message || message
      } catch {
        // 保留默认提示
      }
    } else if (data?.message) {
      message = data.message
    }
    ElMessage.error(message)
  } finally {
    evidenceExporting.value = false
  }
}

async function openShareDialog() {
  shareVisible.value = true
  createdShare.value = null
  await loadShares()
}

async function loadShares() {
  if (!asset.value.id) return
  shareListLoading.value = true
  try {
    const response = await assetApi.getShares(asset.value.id)
    if (response.data?.code === 200) {
      shares.value = response.data.data || []
    }
  } catch {
    ElMessage.error('分享链接加载失败')
  } finally {
    shareListLoading.value = false
  }
}

function sharePageUrl(token) {
  return `${window.location.origin}/share/${token}`
}

async function copyShareUrl(token) {
  const ok = await copyToClipboard(sharePageUrl(token))
  ElMessage[ok ? 'success' : 'error'](ok ? '分享链接已复制' : '复制失败，请手动选择')
}

async function createShareLink() {
  if (shareCreating.value) return
  const code = shareForm.access_code.trim()
  if (code && (code.length < 4 || code.length > 32)) {
    ElMessage.warning('访问码长度需为 4-32 位')
    return
  }
  if (shareForm.allow_download && shareForm.max_downloads) {
    const limit = Number(shareForm.max_downloads)
    if (!Number.isInteger(limit) || limit < 1 || limit > 1000) {
      ElMessage.warning('下载次数上限需在 1-1000 之间')
      return
    }
  }

  shareCreating.value = true
  try {
    const response = await assetApi.createShare(asset.value.id, {
      expires_in_days: shareForm.expires_in_days,
      access_code: code || undefined,
      allow_download: shareForm.allow_download,
      max_downloads: shareForm.allow_download ? (shareForm.max_downloads || undefined) : undefined
    })
    if (response.data?.code === 200) {
      createdShare.value = response.data.data
      ElMessage.success('分享链接已生成')
      await loadShares()
    } else {
      ElMessage.error(response.data?.message || '创建分享失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '创建分享失败')
  } finally {
    shareCreating.value = false
  }
}

async function revokeShare(share) {
  try {
    await ElMessageBox.confirm(
      '撤销后该链接立即失效，已经拿到链接的人将无法继续查看。',
      '撤销分享链接',
      { type: 'warning', confirmButtonText: '撤销', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    const response = await assetApi.revokeShare(share.id)
    if (response.data?.code === 200) {
      ElMessage.success('分享链接已撤销')
      if (createdShare.value?.id === share.id) createdShare.value = null
      await loadShares()
    } else {
      ElMessage.error(response.data?.message || '撤销失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '撤销失败')
  }
}

async function openCollectionDialog() {
  collectionDialogVisible.value = true
  collectionLoading.value = true
  try {
    const response = await collectionApi.getList({ asset_id: asset.value.id })
    if (response.data?.code === 200) {
      collectionOptions.value = response.data.data || []
      collectionChecked.value = collectionOptions.value
        .filter(item => item.contains)
        .map(item => item.id)
    } else {
      ElMessage.error(response.data?.message || '合集加载失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '合集加载失败')
  } finally {
    collectionLoading.value = false
  }
}

async function saveCollections() {
  if (collectionSaving.value) return
  const selected = new Set(collectionChecked.value)
  const tasks = []
  for (const item of collectionOptions.value) {
    const shouldContain = selected.has(item.id)
    if (shouldContain && !item.contains) {
      tasks.push(collectionApi.addAssets(item.id, [asset.value.id]))
    } else if (!shouldContain && item.contains) {
      tasks.push(collectionApi.removeAsset(item.id, asset.value.id))
    }
  }

  if (tasks.length === 0) {
    collectionDialogVisible.value = false
    return
  }

  collectionSaving.value = true
  try {
    const results = await Promise.allSettled(tasks)
    const failed = results.filter(result => result.status === 'rejected').length
    if (failed) {
      ElMessage.warning(`已保存，${failed} 个合集操作失败`)
    } else {
      ElMessage.success('合集已更新')
    }
    collectionDialogVisible.value = false
  } finally {
    collectionSaving.value = false
  }
}

async function loadVersions() {
  if (!asset.value.id) return
  versionsLoading.value = true
  versionsError.value = false
  try {
    const response = await assetApi.getVersions(asset.value.id)
    if (response.data?.code === 200) {
      versions.value = response.data.data?.items || []
      versionsLoaded.value = true
    } else {
      versionsError.value = true
    }
  } catch {
    versionsError.value = true
  } finally {
    versionsLoading.value = false
  }
}

function openVersionDialog() {
  versionFile.value = null
  versionNote.value = ''
  versionProgress.value = 0
  versionDialogVisible.value = true
}

function handleVersionFile(uploadFile) {
  const raw = uploadFile.raw
  if (!raw) return
  if (raw.size > 500 * 1024 * 1024) {
    ElMessage.error('文件超过 500MB 限制')
    versionFile.value = null
    return
  }
  versionFile.value = raw
}

function handleVersionExceed(files) {
  const raw = files?.[0]
  if (!raw) return
  if (raw.size > 500 * 1024 * 1024) {
    ElMessage.error('文件超过 500MB 限制')
    return
  }
  versionFile.value = raw
}

async function submitVersion() {
  if (!versionFile.value || versionUploading.value) return
  versionUploading.value = true
  versionProgress.value = 0
  try {
    const formData = new FormData()
    formData.append('file', versionFile.value)
    formData.append('change_note', versionNote.value.trim())
    const response = await assetApi.uploadVersion(asset.value.id, formData, {
      onUploadProgress: (event) => {
        if (!event.total) return
        versionProgress.value = Math.min(95, Math.round((event.loaded / event.total) * 95))
      }
    })
    if (response.data?.code === 200) {
      versionProgress.value = 100
      asset.value = response.data.data.asset || asset.value
      ElMessage.success('新版本已保存，水印状态已重置')
      versionDialogVisible.value = false
      await Promise.all([loadVersions(), loadEvidence()])
    } else {
      ElMessage.error(response.data?.message || '版本上传失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '版本上传失败')
  } finally {
    versionUploading.value = false
  }
}

async function downloadVersion(version) {
  if (versionDownloadingId.value) return
  versionDownloadingId.value = version.id
  try {
    const response = await assetApi.downloadVersion(asset.value.id, version.id)
    const url = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    const ext = version.file_format ? `.${version.file_format.toLowerCase()}` : ''
    link.href = url
    link.download = `${asset.value.asset_code}-v${version.version_no}${ext}`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  } catch (error) {
    let message = '版本下载失败'
    const data = error.response?.data
    if (data instanceof Blob) {
      try {
        const parsed = JSON.parse(await data.text())
        message = parsed.message || message
      } catch {
        // 保留默认提示
      }
    } else if (data?.message) {
      message = data.message
    }
    ElMessage.error(message)
  } finally {
    versionDownloadingId.value = null
  }
}

async function restoreVersion(version) {
  if (versionRestoringId.value) return
  try {
    await ElMessageBox.confirm(
      `恢复 v${version.version_no} 会把该版本复制为新的当前版本，并重置水印；历史版本不会删除。`,
      '恢复历史版本',
      { type: 'warning', confirmButtonText: '恢复', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  versionRestoringId.value = version.id
  try {
    const response = await assetApi.restoreVersion(asset.value.id, version.id)
    if (response.data?.code === 200) {
      asset.value = response.data.data.asset || asset.value
      ElMessage.success(`已恢复 v${version.version_no} 并生成新版本`)
      await Promise.all([loadVersions(), loadEvidence()])
    } else {
      ElMessage.error(response.data?.message || '恢复失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '恢复失败')
  } finally {
    versionRestoringId.value = null
  }
}

async function toggleFavorite() {
  if (favoriteLoading.value) return
  favoriteLoading.value = true
  try {
    if (favorited.value) {
      await assetApi.removeFavorite(asset.value.id)
      favorited.value = false
      ElMessage.success('已取消收藏')
    } else {
      await assetApi.addFavorite(asset.value.id)
      favorited.value = true
      ElMessage.success('已加入收藏')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '收藏操作失败')
  } finally {
    favoriteLoading.value = false
  }
}

async function shareAsset() {
  try {
    await navigator.clipboard.writeText(window.location.href)
    ElMessage.success('资产链接已复制')
  } catch {
    ElMessage.warning('浏览器未允许复制，请从地址栏复制链接')
  }
}

function downloadAsset() {
  if (downloading.value) return
  // 所有者与管理员下载自己管理的资产，不受授权范围限制
  if (canManage.value) {
    performDownload({})
    return
  }
  if (!activeLicense.value) {
    ElMessage.warning('无有效授权，请先申请授权')
    return
  }
  downloadForm.purpose = activeLicense.value.usage_purpose_code || 'personal_learning'
  downloadForm.territory = downloadTerritoryOptions.includes(activeLicense.value.territory)
    ? activeLicense.value.territory
    : '中国大陆'
  downloadDialogVisible.value = true
}

async function confirmDownload() {
  downloadDialogVisible.value = false
  await performDownload({
    purpose: downloadForm.purpose,
    territory: downloadForm.territory
  })
}

async function performDownload(params) {
  if (downloading.value) return
  downloading.value = true
  try {
    const response = await assetApi.download(asset.value.id, params)
    const url = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.download = `${asset.value.asset_code}.${(asset.value.file_format || 'bin').toLowerCase()}`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
    const fingerprint = response.headers?.['x-download-fingerprint']
    ElMessage.success(
      fingerprint ? `下载已开始，指纹 ${fingerprint}` : '下载已开始'
    )
    loadExtras()
  } catch (error) {
    let message = '下载失败'
    const data = error.response?.data
    if (data instanceof Blob) {
      try {
        const parsed = JSON.parse(await data.text())
        message = parsed.message || message
      } catch {
        // 保留默认提示
      }
    } else if (data?.message) {
      message = data.message
    }
    ElMessage.error(message)
  } finally {
    downloading.value = false
  }
}

async function publishAsset() {
  if (publishing.value) return
  publishing.value = true
  try {
    const response = await assetApi.publish(asset.value.id)
    if (response.data?.code === 200) {
      ElMessage.success('已提交发布，等待管理员审核')
      loadAsset()
    } else {
      ElMessage.error(response.data?.message || '提交发布失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '提交发布失败')
  } finally {
    publishing.value = false
  }
}

function openEditDialog() {
  editForm.value = {
    title: asset.value.title || '',
    description: asset.value.description || '',
    tags: [...tags.value]
  }
  editVisible.value = true
}

async function saveEdit() {
  if (!editForm.value.title.trim()) {
    ElMessage.warning('标题不能为空')
    return
  }
  const normalizedTags = [...new Set(
    editForm.value.tags.map(tag => String(tag).trim()).filter(Boolean)
  )].slice(0, 20)
  editSaving.value = true
  try {
    const response = await assetApi.update(asset.value.id, {
      title: editForm.value.title.trim(),
      description: editForm.value.description,
      tags: normalizedTags
    })
    if (response.data?.code === 200) {
      asset.value = { ...asset.value, ...response.data.data }
      tags.value = normalizedTags
      editVisible.value = false
      ElMessage.success('著录信息已更新')
    } else {
      ElMessage.error(response.data?.message || '保存失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '保存失败')
  } finally {
    editSaving.value = false
  }
}

function goToMyLicenses() {
  router.push('/license/my?tab=pending')
}

function getCardUrl(item) {
  return item.id ? `/api/assets/${item.id}/thumbnail?size=card&v=2` : placeholderImage(item.asset_type)
}

function onRelatedImageError(event) {
  const img = event?.target
  if (!img || img.dataset.fallbackApplied) return
  img.dataset.fallbackApplied = '1'
  img.src = placeholderImage('image')
}

function stopTaskPolling() {
  if (taskPollTimer) {
    clearTimeout(taskPollTimer)
    taskPollTimer = null
  }
}

function pollTask(taskId, { interval = 1500, timeout = 120000 } = {}) {
  return new Promise((resolve) => {
    const startedAt = Date.now()
    const tick = async () => {
      if (Date.now() - startedAt > timeout) {
        stopTaskPolling()
        resolve(activeTask.value || { status: 'timeout' })
        return
      }
      try {
        const response = await taskApi.get(taskId)
        const task = response.data?.data
        if (task) {
          activeTask.value = task
          if (['succeeded', 'failed', 'cancelled'].includes(task.status)) {
            stopTaskPolling()
            resolve(task)
            return
          }
        }
      } catch {
        // 网络抖动时继续轮询，最终由超时兜底
      }
      taskPollTimer = setTimeout(tick, interval)
    }
    tick()
  })
}

async function refreshAssetState() {
  if (!asset.value.id) return
  try {
    const response = await assetApi.getDetail(asset.value.id)
    if (response.data?.code === 200) {
      asset.value = response.data.data
    }
  } catch {
    // 保留当前展示，证据链与版本列表仍会尝试刷新
  }
  await Promise.all([loadVersions(), loadEvidence()])
}

async function awaitAcceptedTask(response, startMessage) {
  const payload = response.data?.data || {}
  if (!payload.task) return
  activeTask.value = payload.task
  ElMessage.success(startMessage)
  if (!payload.worker_enabled) {
    ElMessage.warning('任务已排队，但后台 worker 未启用；请运行 flask tasks run')
    return
  }
  const task = await pollTask(payload.task.id)
  await refreshAssetState()
  if (task.status === 'succeeded') {
    ElMessage.success('后台任务已完成')
  } else if (task.status === 'timeout') {
    ElMessage.info('任务仍在处理，可以稍后刷新查看')
  } else {
    ElMessage.error(task.error_message || '后台任务失败')
  }
}

async function embedWatermark() {
  watermarking.value = true
  try {
    const response = await watermarkApi.embed(asset.value.id, { async: true })
    if (response.data.code === 202) {
      asset.value.watermark_status = 'pending'
      await awaitAcceptedTask(response, '水印任务已提交')
    } else if (response.data.code === 200) {
      ElMessage.success('水印嵌入成功')
      loadAsset()
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '水印嵌入失败')
  } finally {
    watermarking.value = false
  }
}

async function extractWatermark() {
  extracting.value = true
  try {
    const response = await watermarkApi.extract(asset.value.id)
    if (response.data.code === 200) {
      ElMessage.success('水印提取成功，NC值: ' + response.data.data.nc_value)
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '水印提取失败')
  } finally {
    extracting.value = false
  }
}

async function registerChain() {
  chaining.value = true
  try {
    const response = await blockchainApi.register(asset.value.id, { async: true })
    if (response.data.code === 202) {
      asset.value.chain_status = 'pending'
      await awaitAcceptedTask(response, '存证任务已提交')
    } else if (response.data.code === 200) {
      ElMessage.success('存证成功')
      loadAsset()
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '存证失败')
  } finally {
    chaining.value = false
  }
}

function revokePreview() {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = ''
  }
}

async function loadPreviewFile() {
  if (
    !asset.value.id || !previewSupported.value || !canDownload.value
    || previewUrl.value || previewLoading.value
  ) return
  previewLoading.value = true
  previewError.value = false
  try {
    const response = await assetApi.preview(asset.value.id)
    revokePreview()
    previewUrl.value = URL.createObjectURL(response.data)
  } catch {
    previewError.value = true
  } finally {
    previewLoading.value = false
  }
}

watch(
  [canDownload, () => asset.value.id, previewSupported],
  () => {
    revokePreview()
    const isLargeFile = Number(asset.value.file_size || 0) > PREVIEW_AUTO_LOAD_LIMIT
    if (previewSupported.value && canDownload.value && !isLargeFile) loadPreviewFile()
  }
)

onBeforeUnmount(() => {
  stopTaskPolling()
  revokePreview()
})

function viewCertificate() {
  router.push(`/certificate/${asset.value.certificate_id}`)
}

function applyLicense() {
  router.push(`/license/apply?asset_id=${asset.value.id}`)
}

function goBack() {
  router.push('/assets')
}

const TYPE_LABELS = { image: '影像', vector: '矢量图', model: '三维模型', document: '文献', video: '视频' }

function typeLabel(type) {
  return TYPE_LABELS[type] || '文件'
}

function getAssetUrl(asset) {
  if (asset.id) {
    const current = versions.value.find(item => item.is_current)
    const token = current?.file_hash || asset.watermark_id || ''
    const suffix = token ? `?v=${String(token).slice(0, 10)}` : ''
    return `/api/assets/${asset.id}/thumbnail${suffix}`
  }
  return placeholderImage(asset.asset_type)
}

function placeholderImage(type) {
  const colors = { image: '#2f6b5a', vector: '#4c6e8a', model: '#6d5b7a', document: '#b07a2a', video: '#a6402f' }
  const color = (colors[type] || '#5b675f').replace('#', '')
  const label = (type || 'FILE').substring(0, 3).toUpperCase()
  return `data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="800" height="500"%3E%3Crect fill="%23${color}" width="800" height="500"/%3E%3Ctext x="400" y="260" text-anchor="middle" fill="white" font-size="42"%3E${label}%3C/text%3E%3C/svg%3E`
}

function formatSize(size) {
  if (!size) return '-'
  if (size < 1024) return size + ' B'
  if (size < 1024 * 1024) return (size / 1024).toFixed(2) + ' KB'
  return (size / 1024 / 1024).toFixed(2) + ' MB'
}

function formatDate(dateStr) {
  const date = parseBackendDate(dateStr)
  return date ? date.toLocaleDateString('zh-CN') : ''
}

onMounted(() => {
  const tab = route.query.tab
  if (['evidence', 'annotations', 'versions', 'comments'].includes(tab)) {
    activeDetailTab.value = tab
  }
  loadAsset()
})

watch(() => route.query.tab, tab => {
  if (['evidence', 'annotations', 'versions', 'comments'].includes(tab)) {
    activeDetailTab.value = tab
  }
})

// 版本列表只在用户真正打开“版本”页签时加载，避免详情首屏多打一次接口
watch(activeDetailTab, tab => {
  if (tab === 'versions' && asset.value.id && !versionsLoaded.value && !versionsLoading.value) {
    loadVersions()
  }
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.asset-detail-container {
  max-width: 1280px;
  margin: 0 auto;
  padding: $spacing-2xl $spacing-3xl $spacing-4xl;
  min-height: 100vh;
  background: $bg-primary;
}

// ========== 页眉 ==========
.page-bar {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: $spacing-md;
  padding-bottom: $spacing-md;
  margin-bottom: $spacing-xl;
  border-bottom: 1px solid $border-light;
}

.page-back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  align-self: center;
  font-size: $font-size-sm;
  color: $text-secondary;
  transition: color $transition-fast;

  &:hover {
    color: $primary-dark;
  }
}

.page-title {
  font-family: $font-display;
  font-size: 23px;
  font-weight: $font-weight-semibold;
  line-height: $line-height-tight;
  letter-spacing: 0.02em;
  color: $text-primary;
}

.page-meta {
  margin-left: auto;
  align-self: center;
  font-family: $font-mono;
  font-size: $font-size-xs;
  letter-spacing: 0.08em;
  color: $text-placeholder;
}

// ========== 版面 ==========
.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: $spacing-2xl;
  align-items: start;
}

.asset-sheet {
  min-width: 0;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  padding: $spacing-2xl;
  box-shadow: $shadow-sm;
}

.sheet-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: $spacing-lg;
  margin-bottom: $spacing-lg;
}

.sheet-kicker {
  font-size: $font-size-xs;
  letter-spacing: 0.14em;
  color: $text-secondary;
  margin-bottom: 6px;
}

.sheet-title {
  font-family: $font-display;
  font-size: 24px;
  line-height: 1.35;
  font-weight: $font-weight-semibold;
  color: $text-primary;
}

.preview-area {
  margin: 0 0 $spacing-xl;
}

.asset-photo {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 10;
  background: $bg-secondary;
  border: 1px solid $border-light;
  border-radius: $radius-md;
  overflow: hidden;
  cursor: zoom-in;

  :deep(.el-image__inner) {
    width: 100%;
    height: 100%;
    object-fit: contain;
  }
}

.asset-video,
.asset-pdf {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 10;
  background: #111;
  border: 1px solid $border-light;
  border-radius: $radius-md;
}

.asset-pdf {
  background: $bg-secondary;
}

.asset-model {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 10;
  border: 1px solid $border-light;
  border-radius: $radius-md;
}

.preview-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: $spacing-sm;
  width: 100%;
  aspect-ratio: 16 / 10;
  background: $bg-secondary;
  border: 1px solid $border-light;
  border-radius: $radius-md;
  color: $text-placeholder;
  font-size: $font-size-base;
}

.preview-caption {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: $spacing-md;
  padding-top: $spacing-sm;
  font-size: $font-size-xs;
  color: $text-placeholder;

  .mono {
    font-family: $font-mono;
    letter-spacing: 0.04em;
    overflow-wrap: anywhere;
    text-align: right;
  }
}

.spec-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  border-top: 1px solid $border-light;

  .spec-item {
    display: grid;
    grid-template-columns: 80px minmax(0, 1fr);
    gap: $spacing-sm;
    padding: $spacing-md 0;
    border-bottom: 1px solid $border-light;
    min-width: 0;

    &:nth-child(odd) {
      padding-right: $spacing-lg;
    }

    &:nth-child(even) {
      padding-left: $spacing-lg;
      border-left: 1px solid $border-light;
    }
  }

  .spec-span {
    grid-column: 1 / -1;

    &:nth-child(even) {
      border-left: none;
      padding-left: 0;
    }
  }

  dt {
    font-size: $font-size-xs;
    letter-spacing: 0.06em;
    color: $text-secondary;
    padding-top: 2px;
  }

  dd {
    font-size: $font-size-sm;
    color: $text-primary;
    line-height: 1.7;
    overflow-wrap: anywhere;
  }

  .mono {
    font-family: $font-mono;
    font-size: $font-size-xs;
  }
}

.page-actions {
  display: flex;
  align-items: center;
  gap: 2px;

  :deep(.el-button) {
    margin-left: 0;
    font-size: 13px;
    color: $text-secondary;

    &:hover {
      color: $primary-dark;
    }
  }
}

.reject-banner {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 10px 14px;
  margin-bottom: $spacing-lg;
  background: $error-bg;
  border-left: 3px solid $error-color;
  border-radius: $radius-sm;

  strong {
    font-size: 12px;
    color: $error-color;
  }

  span {
    font-size: 12px;
    line-height: 1.7;
    color: $text-secondary;
  }
}

// 当前用户的申请/授权状态
.asset-state {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-lg;
  padding: 12px 14px;
  margin-bottom: $spacing-lg;
  border: 1px solid $border-light;
  border-left-width: 3px;
  border-radius: $radius-sm;
  background: $bg-secondary;

  &.success {
    border-left-color: $success-color;
    background: $success-bg;
  }

  &.info {
    border-left-color: $info-color;
    background: $info-bg;
  }

  &.warning {
    border-left-color: $warning-color;
    background: $warning-bg;
  }

  .asset-state-text {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;

    strong {
      font-size: 13px;
      color: $text-primary;
    }

    span {
      font-size: 12px;
      color: $text-secondary;
      overflow-wrap: anywhere;
    }
  }

  .asset-state-action {
    flex-shrink: 0;
    font-size: 12px;
    color: $primary-dark;
  }
}

.asset-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.asset-tag {
  padding: 2px 8px;
  border: 1px solid $border-color;
  border-radius: $radius-xs;
  background: $bg-secondary;
  font-size: 12px;
  color: $text-secondary;
}

// ========== 证据 / 标注 / 版本 / 讨论 ==========
.collab-tabs-card {
  margin-top: $spacing-3xl;
  padding: 0 $spacing-xl $spacing-xl;
  border: 1px solid $border-light;
  border-radius: $radius-lg;
  background: $bg-card;
  box-shadow: $shadow-card;
}

.collab-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 0;
  }

  :deep(.el-tabs__nav-wrap::after) {
    height: 1px;
    background: $border-light;
  }

  :deep(.el-tabs__item) {
    font-size: 14px;
    color: $text-secondary;
  }

  :deep(.el-tabs__item.is-active) {
    color: $primary-color;
    font-weight: 600;
  }
}

.collab-panel {
  padding-top: $spacing-lg;

  :deep(.evidence-section),
  :deep(.annotation-section),
  :deep(.version-section),
  :deep(.comment-section) {
    margin-top: 0;
    padding: 0;
    border: none;
    border-radius: 0;
    background: transparent;
    box-shadow: none;
  }
}

// ========== 证据链 ==========
.evidence-section {
  margin-top: $spacing-3xl;
  padding: $spacing-xl;
  border: 1px solid $border-light;
  border-radius: $radius-lg;
  background: $bg-card;
  box-shadow: $shadow-card;
}

.evidence-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 20px;
  border: 1px dashed $border-color;
  border-radius: $radius-md;
  background: $bg-secondary;
  font-size: 13px;
  color: $text-secondary;
}

.license-loading {
  margin: 8px 0 12px;
}

.asset-license-caption {
  margin: -4px 0 14px;
  font-family: $font-mono;
  font-size: 12px;
  color: $text-placeholder;
}

.license-state-error {  margin: 8px 0 12px;
  padding: 8px 10px;
  border-radius: $radius-sm;
  background: $warning-bg;
  font-size: 12px;
  line-height: 1.6;
  color: $warning-color;
}

// ========== 分享弹窗 ==========
.download-scope-alert {
  margin-bottom: 16px;
}

.download-scope-form {
  margin-top: 4px;
}

.download-scope-summary {
  padding: 12px 14px;
  border-radius: $radius-sm;
  background: $bg-secondary;
  font-size: 12px;
  line-height: 1.7;
  color: $text-secondary;

  p {
    margin: 0;
  }

  .download-fingerprint-note {
    margin-top: 6px;
    color: $primary-dark;
  }
}

.share-dialog-note {
  margin: 0 0 16px;
  font-size: 13px;
  line-height: 1.7;
  color: $text-secondary;
}

.share-form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.share-download-row {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
}

.share-limit-input {
  max-width: 220px;
}

.share-create-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 0;
  border-top: 1px dashed $border-light;
  border-bottom: 1px dashed $border-light;
}

.share-create-hint {
  font-size: 12px;
  color: $text-placeholder;
}

.created-share {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
  padding: 10px 12px;
  border: 1px solid rgba(47, 107, 90, 0.25);
  border-radius: $radius-md;
  background: rgba(47, 107, 90, 0.06);

  .created-label {
    flex: 0 0 auto;
    font-size: 11px;
    letter-spacing: 0.1em;
    color: $primary-color;
  }

  code {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-family: $font-mono;
    font-size: 12px;
    color: $text-primary;
  }
}

.existing-shares {
  margin-top: 18px;
}

.existing-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 8px;
  font-size: 13px;
  color: $text-secondary;

  strong {
    font-weight: 600;
    color: $text-primary;
  }

  span {
    font-size: 12px;
    color: $text-placeholder;
  }
}

.share-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 260px;
  overflow-y: auto;
}

.share-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid $border-light;

  &:last-child { border-bottom: none; }
}

.share-item-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.share-item-url {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: $font-mono;
  font-size: 12px;
  color: $text-primary;
}

.share-item-meta {
  font-size: 11px;
  color: $text-placeholder;
}

.share-item-actions {
  flex: 0 0 auto;
  display: flex;
  gap: 2px;
}

.collection-choices {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 300px;
  overflow-y: auto;
}

.collection-choice {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid $border-light;
  border-radius: $radius-md;
  cursor: pointer;

  &:hover {
    border-color: $primary-light;
    background: $bg-hover;
  }
}

.choice-body {
  display: flex;
  flex-direction: column;
  gap: 2px;

  strong {
    font-size: 13px;
    color: $text-primary;
  }

  small {
    font-size: 11px;
    color: $text-placeholder;
  }
}

@media (max-width: 720px) {
  .share-form-grid {
    grid-template-columns: 1fr;
  }

  .share-download-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .share-limit-input {
    max-width: 100%;
  }

  .evidence-section {
    padding: 16px;
  }

  .related-head {
    flex-wrap: wrap;
  }

  .evidence-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .version-section {
    padding: 16px;
  }

  .collab-tabs-card {
    padding: 0 16px 16px;
  }

  .version-item {
    flex-direction: column;
    gap: 8px;
  }

  .version-actions {
    width: 100%;
    justify-content: flex-end;
  }
}

// ========== 版本历史 ==========
.version-section {
  margin-top: $spacing-3xl;
  padding: $spacing-xl;
  border: 1px solid $border-light;
  border-radius: $radius-lg;
  background: $bg-card;
  box-shadow: $shadow-card;
}

.version-empty {
  padding: 18px;
  border: 1px dashed $border-color;
  border-radius: $radius-md;
  background: $bg-secondary;
  font-size: 13px;
  color: $text-secondary;
}

.version-list {
  display: flex;
  flex-direction: column;
}

.version-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  padding: 12px 0;
  border-bottom: 1px solid $border-light;

  &:last-child { border-bottom: none; padding-bottom: 0; }

  &.current {
    background: rgba(47, 107, 90, 0.03);
    margin: 0 -12px;
    padding-left: 12px;
    padding-right: 12px;
    border-radius: $radius-sm;
  }
}

.version-main {
  flex: 1;
  min-width: 0;
}

.version-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.version-no {
  font-family: $font-mono;
  font-size: 14px;
  color: $text-primary;
}

.version-meta {
  font-size: 11px;
  color: $text-placeholder;
}

.version-note {
  margin: 4px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: $text-secondary;
}

.version-hash {
  margin: 3px 0 0;
  font-family: $font-mono;
  font-size: 10px;
  color: $text-placeholder;
}

.version-proof {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin: 8px 0 0;
  font-size: 11px;
  color: $text-secondary;

  .el-icon {
    color: $primary-color;
  }

  &.muted {
    margin: 6px 0 0;
    color: $text-placeholder;
  }
}

.version-proof-link {
  font-family: $font-mono;
  color: $primary-dark;
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
}

.version-actions {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 4px;
}

.version-warning {
  margin-bottom: 14px;
}

.version-file {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  padding: 8px 10px;
  border-radius: $radius-sm;
  background: $bg-secondary;
  font-size: 12px;
  color: $text-secondary;
}

.version-note-input {
  margin-top: 12px;
}

.version-progress {
  margin-top: 10px;
}

// ========== 相关资产 ==========
.related-section {
  margin-top: $spacing-3xl;
  padding-top: $spacing-xl;
  border-top: 1px solid $border-light;
}

.related-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: $spacing-lg;
  margin-bottom: $spacing-lg;

  .related-title {
    font-family: $font-display;
    font-size: 20px;
    font-weight: 600;
    color: $text-primary;
    margin-bottom: 4px;
  }

  .related-subtitle {
    font-size: 12px;
    color: $text-placeholder;
  }

  .related-more {
    font-size: 13px;
    color: $primary-color;
  }
}

.evidence-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.related-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: $spacing-lg;
}

.related-card {
  display: block;
  min-width: 0;
  overflow: hidden;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  background: $bg-card;
  color: $text-primary;
  transition: border-color $transition-fast, box-shadow $transition-fast;

  &:hover {
    border-color: $primary-color;
    box-shadow: $shadow-md;
    color: $text-primary;
  }

  .related-thumb {
    height: 104px;
    overflow: hidden;
    background: $bg-secondary;

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
  }

  .related-body {
    padding: 10px 12px 12px;

    h3 {
      font-size: 13px;
      font-weight: 500;
      line-height: 1.5;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      margin-bottom: 3px;
    }

    p {
      font-size: 11px;
      color: $text-placeholder;
    }
  }
}

// ========== 右侧面板 ==========
.side-panel {
  position: sticky;
  top: $spacing-xl;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  box-shadow: $shadow-sm;
  overflow: hidden;
  min-width: 0;
}

.side-block {
  padding: $spacing-xl;
  border-bottom: 1px solid $border-light;

  &:last-child {
    border-bottom: none;
  }
}

.side-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: $spacing-sm;
  margin-bottom: $spacing-md;
}

.side-kicker {
  font-family: $font-display;
  font-size: $font-size-base;
  font-weight: $font-weight-semibold;
  color: $text-primary;
}

.side-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.side-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;

  dt {
    font-size: $font-size-xs;
    color: $text-secondary;
    letter-spacing: 0.04em;
  }

  dd {
    font-size: $font-size-sm;
    color: $text-primary;
    line-height: 1.55;
    overflow-wrap: anywhere;
  }

  .mono {
    font-family: $font-mono;
    font-size: $font-size-xs;
  }
}

.side-action {
  width: 100%;
  margin-top: $spacing-md;
}

.side-hint,
.side-note {
  margin-top: $spacing-sm;
  font-size: $font-size-xs;
  line-height: 1.6;
  color: $text-placeholder;
}

.task-hint {
  color: $primary-dark;

  &.error {
    color: $accent-color;
  }
}

.side-actions {
  .side-action {
    margin-top: 10px;
  }
}

// 骨架
.skeleton-sheet,
.skeleton-side {
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  padding: $spacing-2xl;
}

.error-card {
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}

@media (max-width: $breakpoint-lg) {
  .detail-grid {
    grid-template-columns: minmax(0, 1fr) 300px;
  }
}

@media (max-width: $breakpoint-md) {
  .asset-detail-container {
    padding: $spacing-lg;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }

  .side-panel {
    position: static;
  }

  .asset-sheet {
    padding: $spacing-lg;
  }

  .spec-grid {
    grid-template-columns: 1fr;

    .spec-item {
      &:nth-child(odd) {
        padding-right: 0;
      }

      &:nth-child(even) {
        padding-left: 0;
        border-left: none;
      }
    }
  }

  .page-meta {
    width: 100%;
    margin-left: 0;
    text-align: left;
  }

  .page-actions {
    width: 100%;
  }

  .asset-state {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .related-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
