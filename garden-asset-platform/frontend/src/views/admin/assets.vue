<template>
  <div class="admin-assets">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>资产管理</span>
          <el-button type="primary" size="small" @click="goToUpload">上传资产</el-button>
        </div>
      </template>

      <!-- 搜索 -->
      <el-form inline>
        <el-form-item>
          <el-input v-model="search.keyword" placeholder="搜索标题/编码" clearable />
        </el-form-item>
        <el-form-item>
          <el-select v-model="search.asset_type" placeholder="类型" clearable>
            <el-option label="影像" value="image" />
            <el-option label="模型" value="model" />
            <el-option label="矢量" value="vector" />
            <el-option label="文献" value="document" />
            <el-option label="视频" value="video" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-select v-model="search.watermark_status" placeholder="水印状态" clearable>
            <el-option label="已嵌入" value="embedded" />
            <el-option label="未嵌入" value="pending" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-select v-model="search.chain_status" placeholder="存证状态" clearable>
            <el-option label="已存证" value="confirmed" />
            <el-option label="未存证" value="pending" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
        </el-form-item>
      </el-form>

      <!-- 表格 -->
      <el-skeleton :loading="loading" animated :rows="8">
        <template #template>
          <div v-for="i in 8" :key="i" style="display: flex; gap: 16px; padding: 14px 0; border-bottom: 1px solid #e8ede9">
            <el-skeleton-item variant="text" style="width: 160px" />
            <el-skeleton-item variant="text" style="flex: 1" />
            <el-skeleton-item variant="text" style="width: 60px" />
            <el-skeleton-item variant="text" style="width: 60px" />
            <el-skeleton-item variant="text" style="width: 60px" />
            <el-skeleton-item variant="text" style="width: 80px" />
            <el-skeleton-item variant="text" style="width: 120px" />
          </div>
        </template>
        <template #default>
      <el-table :data="assets" stripe>
        <el-table-column prop="asset_code" label="编码" width="180" />
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="asset_type" label="类型" width="80">
          <template #default="{ row }">
            <el-tag size="small">{{ getTypeName(row.asset_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="watermark_status" label="水印" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="row.watermark_status === 'embedded' ? 'success' : 'info'">
              {{ row.watermark_status === 'embedded' ? '已嵌入' : '未嵌入' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="chain_status" label="存证" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="row.chain_status === 'confirmed' ? 'success' : 'info'">
              {{ row.chain_status === 'confirmed' ? '已存证' : '未存证' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="uploader" label="上传者" width="100">
          <template #default="{ row }">
            {{ row.uploader_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="140">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button size="small" @click="viewDetail(row.id)">查看</el-button>
              <el-button size="small" type="primary" @click="batchWatermark(row)" :disabled="row.watermark_status === 'embedded'">
                嵌水印
              </el-button>
              <el-button size="small" type="success" @click="batchChain(row)" :disabled="row.chain_status === 'confirmed' || row.watermark_status !== 'embedded'">
                上链
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
        </template>
      </el-skeleton>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="perPage"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadAssets"
        @current-change="loadAssets"
        style="margin-top: 20px; justify-content: center"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { assetApi, watermarkApi, blockchainApi } from '@/api/modules'

const router = useRouter()

const loading = ref(false)
const assets = ref([])
const page = ref(1)
const perPage = ref(20)
const total = ref(0)

const search = ref({
  keyword: '',
  asset_type: '',
  watermark_status: '',
  chain_status: ''
})

async function loadAssets() {
  loading.value = true
  try {
    const params = {
      page: page.value,
      per_page: perPage.value,
      ...search.value
    }
    const response = await assetApi.getList(params)
    if (response.data.code === 200) {
      assets.value = response.data.data.items
      total.value = response.data.data.total
    }
  } catch (error) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadAssets()
}

function goToUpload() {
  router.push('/admin/assets/upload')
}

function viewDetail(id) {
  router.push(`/assets/${id}`)
}

async function batchWatermark(row) {
  try {
    const response = await watermarkApi.embed(row.id)
    if (response.data.code === 200) {
      ElMessage.success('水印嵌入成功')
      loadAssets()
    }
  } catch (error) {
    ElMessage.error('水印嵌入失败')
  }
}

async function batchChain(row) {
  try {
    const response = await blockchainApi.register(row.id)
    if (response.data.code === 200) {
      ElMessage.success('上链存证成功')
      loadAssets()
    }
  } catch (error) {
    ElMessage.error('上链存证失败')
  }
}

function getTypeName(type) {
  const map = { image: '影像', model: '模型', vector: '矢量', document: '文献', video: '视频' }
  return map[type] || type
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadAssets()
})
</script>

<style scoped>
.admin-assets {
  padding: 0;
}
</style>