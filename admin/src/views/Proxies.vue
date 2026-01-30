<template>
  <div class="proxies-container">
    <el-card class="proxies-card" :body-style="{ padding: '0' }">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="title">代理池管理</span>
            <span class="subtitle">管理代理服务器集群，支持账号密码认证与连接拨测</span>
          </div>
          <div class="header-actions">
            <el-input
              v-model="searchQuery"
              placeholder="搜索名称、服务器或位置..."
              clearable
              prefix-icon="Search"
              style="width: 250px"
              @clear="loadProxies"
              @keyup.enter="loadProxies"
            />
            <el-button type="primary" @click="showCreateDialog">
              <el-icon><Plus /></el-icon> 新增代理
            </el-button>
            <el-button @click="loadProxies" :loading="loading">
              <el-icon><Refresh /></el-icon> 刷新
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
        <el-table-column prop="name" label="名称/标识" min-width="160">
          <template #default="{ row }">
            <div class="proxy-name-cell">
              <el-tag :type="row.protocol === 'socks5' ? 'warning' : 'success'" size="small" effect="plain">
                {{ row.protocol.toUpperCase() }}
              </el-tag>
              <span class="proxy-name">{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="server" label="服务器地址" min-width="200">
          <template #default="{ row }">
            <code class="server-code">{{ row.server }}</code>
          </template>
        </el-table-column>

        <el-table-column prop="location" label="国家/城市" width="150" align="center">
          <template #default="{ row }">
            <span v-if="row.location">{{ row.location }}</span>
            <span v-else style="color: #909399; font-style: italic;">未知</span>
          </template>
        </el-table-column>

        <el-table-column prop="session_type" label="会话方式" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.session_type === 'sticky' ? 'primary' : 'info'" size="small" effect="light">
              {{ row.session_type === 'sticky' ? '粘性 IP' : '随机 IP' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="is_enabled" label="可用" width="80" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.is_enabled" @change="(val) => handleToggleStatus(row, val)" />
          </template>
        </el-table-column>

        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip content="连接测试" placement="top">
                <el-button circle size="small" type="success" :icon="Connection" @click="testProxy(row)" :loading="testingId === row._id" />
              </el-tooltip>
              <el-tooltip content="编辑" placement="top">
                <el-button circle size="small" type="primary" :icon="Edit" @click="showEditDialog(row)" />
              </el-tooltip>
              <el-tooltip content="删除" placement="top">
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
      :title="isEdit ? '编辑代理配置' : '新增代理配置'" 
      width="600px" 
      destroy-on-close
      class="bento-dialog"
    >
      <el-form :model="form" label-width="100px" label-position="top">
        <el-row :gutter="20">
          <el-col :span="16">
            <el-form-item label="名称" required>
              <el-input v-model="form.name" placeholder="如：美国-洛杉矶-01" clearable />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="协议" required>
              <el-select v-model="form.protocol" style="width: 100%">
                <el-option label="HTTP" value="http" />
                <el-option label="SOCKS5" value="socks5" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="服务器地址" required>
          <el-input v-model="form.server" placeholder="us.arxlabs.io:3010" clearable>
            <template #prefix><el-icon><Link /></el-icon></template>
          </el-input>
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="用户名 (可选)">
              <el-input v-model="form.username" placeholder="为空则不使用认证" clearable>
                <template #prefix><el-icon><User /></el-icon></template>
              </el-input>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="密码 (可选)">
              <el-input v-model="form.password" type="password" placeholder="留空则不更新" show-password clearable>
                <template #prefix><el-icon><Lock /></el-icon></template>
              </el-input>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="国家/城市 (可选)">
              <el-input v-model="form.location" placeholder="如：美国 加利福尼亚" clearable />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="会话方式">
              <el-radio-group v-model="form.session_type" size="default">
                <el-radio-button label="random">随机 IP</el-radio-button>
                <el-radio-button label="sticky">粘性 IP</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="启用状态">
          <el-switch v-model="form.is_enabled" />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showDialog = false" round>取消</el-button>
          <el-button type="primary" @click="submitForm" :loading="submitting" round>
            {{ isEdit ? '保存' : '创建' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Edit, Delete, Connection, Link, Lock, User, Search } from '@element-plus/icons-vue'
import { getProxies, createProxy, updateProxy, deleteProxy, testStoredProxy } from '../api'

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
    ElMessage.error('获取代理列表失败: ' + (error.response?.data?.detail || error.message))
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
    ElMessage.warning('请填写必选字段（名称和服务器地址）')
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
      ElMessage.success('代理配置已更新')
    } else {
      await createProxy(submitData)
      ElMessage.success('代理配置已创建')
    }
    
    showDialog.value = false
    loadProxies()
  } catch (error) {
    ElMessage.error('操作失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    submitting.value = false
  }
}

const handleToggleStatus = async (row, val) => {
  try {
    await updateProxy(row._id, { is_enabled: val })
    ElMessage.success(`${row.name} 已${val ? '启用' : '禁用'}`)
  } catch (error) {
    row.is_enabled = !val // 恢复状态
    ElMessage.error('更新状态失败')
  }
}

const confirmDelete = (row) => {
  ElMessageBox.confirm(
    `确定要删除代理 "${row.name}" 吗？此操作不可恢复。`,
    '删除确认',
    {
      confirmButtonText: '删除按钮',
      cancelButtonText: '取消',
      type: 'error',
      icon: Delete
    }
  ).then(async () => {
    try {
      await deleteProxy(row._id)
      ElMessage.success('删除成功')
      loadProxies()
    } catch (error) {
      ElMessage.error('删除失败: ' + (error.response?.data?.detail || error.message))
    }
  }).catch(() => {})
}

const testProxy = async (row) => {
  testingId.value = row._id
  try {
    const result = await testStoredProxy(row._id)
    if (result.status === 'success') {
      ElMessage.success(`测试通过！响应延迟: ${result.latency}s, 状态码: ${result.status_code}`)
    } else {
      ElMessage.error(`测试失败: ${result.message}`)
    }
  } catch (error) {
    ElMessage.error('测试接口调用失败')
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
