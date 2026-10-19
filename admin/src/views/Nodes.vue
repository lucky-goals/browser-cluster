<template>
  <div class="nodes-container">
    <div class="page-header">
      <div class="header-left">
        <h2>{{ $t('nodes.title') }}</h2>
        <p class="subtitle">{{ $t('nodes.subtitle') }}</p>
      </div>
      <el-button type="primary" @click="handleAdd">
        <el-icon><Plus /></el-icon>{{ $t('nodes.addNode') }}
      </el-button>
    </div>

    <el-card shadow="never" class="table-card">
      <el-table :data="nodes" v-loading="loading" style="width: 100%">
        <el-table-column prop="node_id" :label="$t('nodes.nodeId')" min-width="120" />
        <el-table-column prop="queue_name" :label="$t('nodes.queueName')" min-width="120" />
        <el-table-column prop="max_concurrent" :label="$t('nodes.maxConcurrent')" width="100" align="center" />
        <el-table-column prop="task_count" :label="$t('nodes.taskCount')" width="100" align="center">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ row.task_count || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('nodes.status')" width="120">
          <template #default="{ row }">
            <el-tag 
              :type="row.status === 'running' ? 'success' : (row.status === 'offline' ? 'danger' : 'info')" 
              effect="dark"
            >
              {{ row.status === 'running' ? '运行中' : (row.status === 'offline' ? '已离线' : '已停止') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_seen" :label="$t('nodes.lastSeen')" width="180">
          <template #default="{ row }">
            {{ row.last_seen ? formatTime(row.last_seen) : '-' }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('nodes.actions')" width="250" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button 
                v-if="row.status !== 'running'"
                type="success" 
                size="small" 
                @click="handleStart(row)"
              >{{ $t('nodes.start') }}</el-button>
              <el-button 
                v-else
                type="warning" 
                size="small" 
                @click="handleStop(row)"
              >{{ $t('nodes.stop') }}</el-button>
              <el-button type="primary" size="small" @click="handleEdit(row)">{{ $t('nodes.edit') }}</el-button>
              <el-button type="info" size="small" @click="handleViewLogs(row)">{{ $t('nodes.logs') }}</el-button>
              <el-button type="danger" size="small" @click="handleDelete(row)">{{ $t('nodes.delete') }}</el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Log Viewer Drawer -->
    <el-drawer
      v-model="logDrawerVisible"
      :title="`${$t('nodes.logTitle')}: ${currentLogNodeId}`"
      size="60%"
      direction="rtl"
      destroy-on-close
      @close="stopLogStream"
    >
      <div class="log-toolbar">
        <div class="toolbar-left">
          <el-select
            v-model="selectedLogDate"
            placeholder="实时日志"
            size="small"
            style="width: 140px; margin-right: 10px;"
            clearable
            @change="handleLogDateChange"
          >
            <el-option
              v-for="date in availableLogDates"
              :key="date"
              :label="date"
              :value="date"
            />
          </el-select>
          <el-checkbox v-model="autoScroll" :disabled="!!selectedLogDate">自动滚动</el-checkbox>
        </div>
        <div class="toolbar-right">
          <el-button size="small" @click="logContent = ''">清空屏幕</el-button>
          <el-button size="small" type="primary" @click="startLogStream" :disabled="!!selectedLogDate">重新连接</el-button>
          <el-button size="small" type="success" @click="downloadLog">
            <el-icon style="margin-right: 4px;"><Download /></el-icon>导出
          </el-button>
        </div>
      </div>
      <div 
        ref="logContainer" 
        class="log-viewer" 
        @scroll="handleScroll"
      >
        <div v-if="loadingMore" class="loading-more">正在加载历史日志...</div>
        <div v-if="noMoreLogs" class="no-more">已加载全部历史日志</div>
        <pre v-if="logContent">{{ logContent }}</pre>
        <el-empty v-else :description="$t('nodes.noLogs')" />
      </div>
      <template #footer>
        <div class="drawer-footer">
          <el-button @click="logDrawerVisible = false">{{ $t('common.cancel') }}</el-button>
        </div>
      </template>
    </el-drawer>

    <!-- Add/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? $t('nodes.editNode') : $t('nodes.addNode')"
      width="500px"
    >
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <el-form-item :label="$t('nodes.nodeId')" prop="node_id">
          <el-input v-model="form.node_id" :disabled="isEdit" :placeholder="$t('nodes.nodeIdPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('nodes.queueName')" prop="queue_name">
          <el-input v-model="form.queue_name" :placeholder="$t('nodes.queuePlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('nodes.maxConcurrent')" prop="max_concurrent">
          <el-input-number v-model="form.max_concurrent" :min="1" :max="20" />
          <div v-if="isEdit && form.status === 'running'" class="form-tip warning-tip">
            <el-icon><Warning /></el-icon> {{ $t('nodes.restartWarning') }}
          </div>
          <div v-else class="form-tip">{{ $t('nodes.stopAdvice') }}</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">{{ $t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, Warning, Download } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getNodes, createNode, updateNode, deleteNode, startNode, stopNode } from '../api'
import dayjs from 'dayjs'
import { useStatsStore } from '../stores/stats'

const { t } = useI18n()
const statsStore = useStatsStore()
const nodes = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref(null)

// 日志相关状态
const logDrawerVisible = ref(false)
const currentLogNodeId = ref('')
const logContent = ref('')
const autoScroll = ref(true)
const logContainer = ref(null)
const selectedLogDate = ref('')
const availableLogDates = ref([])
const loadingMore = ref(false)
const noMoreLogs = ref(false)
let currentOffset = ref(0)
let logAbortController = null
const PAGE_SIZE = 100

const fetchAvailableLogDates = async (nodeId) => {
  availableLogDates.value = [] // 重置日期列表，确保不共用
  try {
    const token = localStorage.getItem('token')
    const headers = {}
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    
    const response = await fetch(`/api/v1/nodes/${nodeId}/logs/dates`, { headers })
    if (response.ok) {
      availableLogDates.value = await response.json()
    }
  } catch (error) {
    console.error('Failed to fetch node log dates:', error)
  }
}

const form = ref({
  node_id: '',
  queue_name: 'task_queue',
  max_concurrent: 1
})

const rules = {
  node_id: [{ required: true, message: t('nodes.nodeIdPlaceholder'), trigger: 'blur' }],
  queue_name: [{ required: true, message: t('nodes.queuePlaceholder'), trigger: 'blur' }]
}

const fetchNodes = async () => {
  loading.value = true
  try {
    const data = await getNodes()
    nodes.value = data
  } catch (error) {
    ElMessage.error(t('nodes.getNodesFailed'))
  } finally {
    loading.value = false
  }
}

const handleAdd = () => {
  isEdit.value = false
  form.value = {
    node_id: '',
    queue_name: 'task_queue',
    max_concurrent: 1
  }
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  form.value = { ...row }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      try {
        if (isEdit.value) {
          await updateNode(form.value.node_id, form.value)
          ElMessage.success(t('nodes.updateSuccess'))
        } else {
          await createNode(form.value)
          ElMessage.success(t('nodes.addSuccess'))
        }
        dialogVisible.value = false
        fetchNodes()
        statsStore.fetchStats()
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || t('nodes.operationFailed'))
      } finally {
        submitting.value = false
      }
    }
  })
}

const handleStart = async (row) => {
  try {
    await startNode(row.node_id)
    ElMessage.success(t('nodes.startSuccess', { id: row.node_id }))
    fetchNodes()
    statsStore.fetchStats()
  } catch (error) {
    ElMessage.error(t('nodes.startFailed'))
  }
}

const handleStop = async (row) => {
  try {
    await stopNode(row.node_id)
    ElMessage.success(t('nodes.stopSuccess', { id: row.node_id }))
    fetchNodes()
    statsStore.fetchStats()
  } catch (error) {
    ElMessage.error(t('nodes.stopFailed'))
  }
}

const handleViewLogs = (row) => {
  currentLogNodeId.value = row.node_id
  logContent.value = ''
  selectedLogDate.value = ''
  currentOffset.value = 0
  noMoreLogs.value = false
  logDrawerVisible.value = true
  fetchAvailableLogDates(row.node_id)
  startLogStream()
}

const handleLogDateChange = (val) => {
  logContent.value = ''
  currentOffset.value = 0
  noMoreLogs.value = false
  startLogStream()
}

const handleScroll = async (e) => {
  if (autoScroll.value) {
    const { scrollTop, scrollHeight, clientHeight } = e.target
    if (scrollTop + clientHeight < scrollHeight - 50) {
      autoScroll.value = false
    }
  }

  if (e.target.scrollTop === 0 && !loadingMore.value && !noMoreLogs.value) {
    await loadMoreLogs()
  }
}

const loadMoreLogs = async () => {
  if (loadingMore.value || noMoreLogs.value) return
  
  loadingMore.value = true
  const oldScrollHeight = logContainer.value.scrollHeight
  const nodeId = currentLogNodeId.value
  
  try {
    const token = localStorage.getItem('token')
    const headers = {}
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    
    currentOffset.value += PAGE_SIZE
    
    let url = `/api/v1/nodes/${nodeId}/logs?lines=${PAGE_SIZE}&offset=${currentOffset.value}`
    if (selectedLogDate.value) {
      url += `&date=${selectedLogDate.value}`
    }
    
    const response = await fetch(url, { headers })
    if (response.ok) {
      const text = await response.text()
      if (text.trim()) {
        logContent.value = text + logContent.value
        nextTick(() => {
          if (logContainer.value) {
            logContainer.value.scrollTop = logContainer.value.scrollHeight - oldScrollHeight
          }
        })
      } else {
        noMoreLogs.value = true
      }
    }
  } catch (error) {
    console.error('Failed to load more logs:', error)
  } finally {
    loadingMore.value = false
  }
}

const downloadLog = () => {
  const token = localStorage.getItem('token')
  const nodeId = currentLogNodeId.value
  const dateParam = selectedLogDate.value ? `&date=${selectedLogDate.value}` : ''
  const url = `/api/v1/nodes/${nodeId}/logs?download=true${dateParam}&token=${token}`
  
  const link = document.createElement('a')
  link.href = url
  link.target = '_blank'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

const startLogStream = async () => {
  if (logAbortController) {
    logAbortController.abort()
  }
  
  logAbortController = new AbortController()
  const nodeId = currentLogNodeId.value
  
  try {
    const token = localStorage.getItem('token')
    const headers = {}
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    
    // 构建 URL
    let url = `/api/v1/nodes/${nodeId}/logs?`
    if (selectedLogDate.value) {
      url += `date=${selectedLogDate.value}&lines=${PAGE_SIZE}&offset=0`
    } else {
      url += `stream=true&lines=${PAGE_SIZE}`
    }
    
    const response = await fetch(url, {
      headers,
      signal: logAbortController.signal
    })
    
    if (!response.ok) {
      const errorData = await response.json()
      logContent.value = `错误: ${errorData.detail || '无法获取日志'}`
      return
    }
    
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      
      const chunk = decoder.decode(value, { stream: true })
      logContent.value += chunk
      
      if (autoScroll.value) {
        scrollToBottom()
      }
    }
  } catch (error) {
    if (error.name === 'AbortError') {
      console.log('Log stream aborted')
    } else {
      logContent.value += `\n[连接中断: ${error.message}]`
    }
  }
}

const stopLogStream = () => {
  if (logAbortController) {
    logAbortController.abort()
    logAbortController = null
  }
}

const scrollToBottom = () => {
  setTimeout(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  }, 100)
}

const handleDelete = (row) => {
  ElMessageBox.confirm(
    t('nodes.deleteConfirm', { id: row.node_id }),
    t('proxies.deleteConfirmTitle'),
    { type: 'warning' }
  ).then(async () => {
    try {
      await deleteNode(row.node_id)
      ElMessage.success(t('nodes.deleteSuccess'))
      fetchNodes()
      statsStore.fetchStats()
    } catch (error) {
      ElMessage.error(t('nodes.deleteFailed'))
    }
  })
}

const formatTime = (time) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

onMounted(() => {
  fetchNodes()
})
</script>

<style scoped>
.nodes-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left h2 {
  margin: 0 0 4px 0;
  font-size: 24px;
  color: #303133;
}

.subtitle {
  margin: 0;
  font-size: 14px;
  color: #909399;
}

.table-card {
  border-radius: 8px;
}

.log-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 20px;
  background-color: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.toolbar-left, .toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.log-viewer {
  background-color: #1e1e1e;
  color: #d4d4d4;
  padding: 15px;
  height: calc(100vh - 210px);
  overflow-y: auto;
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  line-height: 1.5;
  border-radius: 4px;
  position: relative;
}

.loading-more, .no-more {
  text-align: center;
  padding: 10px;
  color: #888;
  font-size: 12px;
}

.log-viewer pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.drawer-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 15px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  display: flex;
  align-items: center;
}

.warning-tip {
  color: #e6a23c;
}
</style>
