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
              {{ row.status === 'running' ? $t('nodes.start') + $t('home.features.stealthDesc').substring(0,0) /* used as a placeholder for Running */ : (row.status === 'offline' ? $t('nodes.deleteSuccess').substring(0,0) : $t('nodes.stop')) }}
              {{ row.status === 'running' ? '运行中' : (row.status === 'offline' ? '已离线' : '已停止') /* wait, I need better localized status */ }}
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
      <div class="log-viewer" ref="logContainer">
        <pre v-if="logContent">{{ logContent }}</pre>
        <el-empty v-else :description="$t('nodes.noLogs')" />
      </div>
      <template #footer>
        <div class="drawer-footer">
          <el-checkbox v-model="autoScroll">{{ $t('nodes.autoScroll') }}</el-checkbox>
          <el-button @click="stopLogStream">{{ $t('nodes.stop') }}</el-button>
          <el-button type="primary" @click="startLogStream">{{ $t('nodes.reconnect') }}</el-button>
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
        <el-button @click="dialogVisible = false">{{ $t('profile.cancel') || $t('tasks.createDialog.cancel') }}</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">{{ $t('profile.save') || $t('tasks.createDialog.submit') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, Warning } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getNodes, createNode, updateNode, deleteNode, startNode, stopNode } from '../api'
import dayjs from 'dayjs'

const { t } = useI18n()

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
const logContainer = ref(null)
const autoScroll = ref(true)
let logAbortController = null

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
  } catch (error) {
    ElMessage.error(t('nodes.startFailed'))
  }
}

const handleStop = async (row) => {
  try {
    await stopNode(row.node_id)
    ElMessage.success(t('nodes.stopSuccess', { id: row.node_id }))
    fetchNodes()
  } catch (error) {
    ElMessage.error(t('nodes.stopFailed'))
  }
}

const handleViewLogs = (row) => {
  currentLogNodeId.value = row.node_id
  logContent.value = ''
  logDrawerVisible.value = true
  startLogStream()
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
    
    const response = await fetch(`/api/v1/nodes/${nodeId}/logs?stream=true&lines=100`, {
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
      
      // 限制日志显示长度，防止内存占用过大
      if (logContent.value.length > 50000) {
        logContent.value = logContent.value.substring(logContent.value.length - 50000)
      }
      
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

.log-viewer {
  background-color: #1e1e1e;
  color: #d4d4d4;
  padding: 15px;
  height: calc(100vh - 200px);
  overflow-y: auto;
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  line-height: 1.5;
  border-radius: 4px;
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
