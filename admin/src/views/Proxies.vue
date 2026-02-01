<template>
  <div class="proxies-container">
    <el-card class="proxies-card" :body-style="{ padding: '0' }">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="title">{{ $t('proxies.title') }}</span>
            <span class="subtitle">{{ $t('proxies.subtitle') }}</span>
          </div>
          <div class="header-actions">
            <el-input
              v-model="searchQuery"
              :placeholder="$t('proxies.searchPlaceholder')"
              clearable
              prefix-icon="Search"
              style="width: 250px"
              @clear="loadProxies"
              @keyup.enter="loadProxies"
            />
            <el-button type="primary" @click="showCreateDialog">
              <el-icon><Plus /></el-icon> {{ $t('proxies.addProxy') }}
            </el-button>
            <el-button @click="loadProxies" :loading="loading">
              <el-icon><Refresh /></el-icon> {{ $t('proxies.refresh') }}
            </el-button>
          </div>
        </div>
      </template>

      <el-table 
        :data="proxies" 
        v-loading="loading" 
        style="width: 100%" 
        class="proxies-table" 
        border 
        stripe
      >
        <el-table-column prop="name" :label="$t('proxies.name')" min-width="160">
          <template #default="{ row }">
            <div class="proxy-name-cell">
              <el-tag :type="row.protocol === 'socks5' ? 'warning' : 'success'" size="small" effect="plain">
                {{ row.protocol.toUpperCase() }}
              </el-tag>
              <span class="proxy-name">{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="server" :label="$t('proxies.server')" min-width="200">
          <template #default="{ row }">
            <code class="server-code">{{ row.server }}</code>
          </template>
        </el-table-column>

        <el-table-column prop="location" :label="$t('proxies.location')" width="150" align="center">
          <template #default="{ row }">
            <span v-if="row.location">{{ row.location }}</span>
            <span v-else style="color: #909399; font-style: italic;">{{ $t('proxies.unknownLocation') }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="session_type" :label="$t('proxies.sessionType')" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.session_type === 'sticky' ? 'primary' : 'info'" size="small" effect="light">
              {{ row.session_type === 'sticky' ? $t('proxies.stickyIP') : $t('proxies.randomIP') }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="is_enabled" :label="$t('proxies.isEnabled')" width="80" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.is_enabled" @change="(val) => handleToggleStatus(row, val)" />
          </template>
        </el-table-column>

        <el-table-column :label="$t('proxies.actions')" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip :content="$t('proxies.test')" placement="top">
                <el-button circle size="small" type="success" :icon="Connection" @click="testProxy(row)" :loading="testingId === row._id" />
              </el-tooltip>
              <el-tooltip :content="$t('proxies.edit')" placement="top">
                <el-button circle size="small" type="primary" :icon="Edit" @click="showEditDialog(row)" />
              </el-tooltip>
              <el-tooltip :content="$t('proxies.delete')" placement="top">
                <el-button circle size="small" type="danger" :icon="Delete" @click="confirmDelete(row)" />
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container" v-if="total > pageSize">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @size-change="loadProxies"
          @current-change="loadProxies"
        />
      </div>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog 
      v-model="showDialog" 
      :title="isEdit ? $t('proxies.editProxy') : $t('proxies.addProxy')" 
      width="600px" 
      destroy-on-close
      class="bento-dialog"
    >
      <el-form :model="form" label-width="100px" label-position="top">
        <el-row :gutter="20">
          <el-col :span="16">
            <el-form-item :label="$t('proxies.name')" required>
              <el-input v-model="form.name" :placeholder="$t('proxies.namePlaceholder')" clearable />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="$t('proxies.protocol')" required>
              <el-select v-model="form.protocol" style="width: 100%">
                <el-option label="HTTP" value="http" />
                <el-option label="SOCKS5" value="socks5" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item :label="$t('proxies.server')" required>
          <el-input v-model="form.server" placeholder="us.arxlabs.io:3010" clearable>
            <template #prefix><el-icon><Link /></el-icon></template>
          </el-input>
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item :label="$t('proxies.username')">
              <el-input v-model="form.username" :placeholder="$t('proxies.authPlaceholder')" clearable>
                <template #prefix><el-icon><User /></el-icon></template>
              </el-input>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('proxies.password')">
              <el-input v-model="form.password" type="password" :placeholder="$t('proxies.passwordPlaceholder')" show-password clearable>
                <template #prefix><el-icon><Lock /></el-icon></template>
              </el-input>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item :label="$t('proxies.location')">
              <el-input v-model="form.location" :placeholder="$t('proxies.locationPlaceholder')" clearable />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('proxies.sessionType')">
              <el-radio-group v-model="form.session_type" size="default">
                <el-radio-button label="random">{{ $t('proxies.randomIP') }}</el-radio-button>
                <el-radio-button label="sticky">{{ $t('proxies.stickyIP') }}</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item :label="$t('proxies.isEnabled')">
          <el-switch v-model="form.is_enabled" />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showDialog = false" round>{{ $t('tasks.createDialog.cancel') }}</el-button>
          <el-button type="primary" @click="submitForm" :loading="submitting" round>
            {{ isEdit ? $t('proxies.save') : $t('proxies.create') }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Edit, Delete, Connection, Link, Lock, User, Search } from '@element-plus/icons-vue'
import { getProxies, createProxy, updateProxy, deleteProxy, testStoredProxy } from '../api'

const { t } = useI18n()

const loading = ref(false)
const submitting = ref(false)
const testingId = ref(null)
const proxies = ref([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const searchQuery = ref('')

const showDialog = ref(false)
const isEdit = ref(false)
const editId = ref(null)

const defaultForm = {
  name: '',
  protocol: 'http',
  server: '',
  username: '',
  password: '',
  session_type: 'random',
  location: '',
  is_enabled: true
}

const form = ref({ ...defaultForm })

const loadProxies = async () => {
  loading.value = true
  try {
    const params = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
      search: searchQuery.value || undefined
    }
    const data = await getProxies(params)
    proxies.value = data.items
    total.value = data.total
  } catch (error) {
    ElMessage.error(t('proxies.getProxiesFailed') + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const showCreateDialog = () => {
  isEdit.value = false
  editId.value = null
  form.value = { ...defaultForm }
  showDialog.value = true
}

const showEditDialog = (row) => {
  isEdit.value = true
  editId.value = row._id
  form.value = {
    name: row.name,
    protocol: row.protocol,
    server: row.server,
    username: row.username || '',
    password: '', // 不回显密码原文
    session_type: row.session_type,
    location: row.location || '',
    is_enabled: row.is_enabled
  }
  showDialog.value = true
}

const submitForm = async () => {
  if (!form.value.name || !form.value.server) {
    ElMessage.warning(t('proxies.fillRequired'))
    return
  }

  submitting.value = true
  try {
    const submitData = { ...form.value }
    if (!submitData.password && isEdit.value) {
      delete submitData.password
    }

    if (isEdit.value) {
      await updateProxy(editId.value, submitData)
      ElMessage.success(t('proxies.updateSuccess'))
    } else {
      await createProxy(submitData)
      ElMessage.success(t('proxies.createSuccess'))
    }
    
    showDialog.value = false
    loadProxies()
  } catch (error) {
    ElMessage.error(t('proxies.operationFailed') + (error.response?.data?.detail || error.message))
  } finally {
    submitting.value = false
  }
}

const handleToggleStatus = async (row, val) => {
  try {
    await updateProxy(row._id, { is_enabled: val })
    ElMessage.success(t('proxies.toggleSuccess', { name: row.name, status: val ? t('proxies.enabled') : t('proxies.disabled') }))
  } catch (error) {
    row.is_enabled = !val // 恢复状态
    ElMessage.error(t('proxies.toggleFailed'))
  }
}

const confirmDelete = (row) => {
  ElMessageBox.confirm(
    t('proxies.deleteConfirm', { name: row.name }),
    t('proxies.deleteConfirmTitle'),
    {
      confirmButtonText: t('proxies.deleteBtn'),
      cancelButtonText: t('tasks.createDialog.cancel'),
      type: 'error',
      icon: Delete
    }
  ).then(async () => {
    try {
      await deleteProxy(row._id)
      ElMessage.success(t('proxies.deleteSuccess'))
      loadProxies()
    } catch (error) {
      ElMessage.error(t('proxies.deleteFailed') + (error.response?.data?.detail || error.message))
    }
  }).catch(() => {})
}

const testProxy = async (row) => {
  testingId.value = row._id
  try {
    const result = await testStoredProxy(row._id)
    if (result.status === 'success') {
      ElMessage.success(t('proxies.testSuccess', { latency: result.latency, code: result.status_code }))
    } else {
      ElMessage.error(t('proxies.testFailed', { message: result.message }))
    }
  } catch (error) {
    ElMessage.error(t('proxies.testCallFailed'))
  } finally {
    testingId.value = null
  }
}

onMounted(() => {
  loadProxies()
})
</script>

<style scoped>
.proxies-container {
  padding: 0;
}

.proxies-card {
  border-radius: 12px;
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.header-left .title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.header-left .subtitle {
  font-size: 13px;
  color: #909399;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.proxy-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.proxy-name {
  font-weight: 500;
}

.server-code {
  background: #f5f7fa;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 13px;
  color: #606266;
}

.action-buttons {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.pagination-container {
  padding: 20px;
  display: flex;
  justify-content: flex-end;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
