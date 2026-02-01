<template>
  <div class="llm-models-container">
    <el-card class="llm-models-card" :body-style="{ padding: '0' }">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="title">{{ $t('llmModels.title') }}</span>
            <span class="subtitle">{{ $t('llmModels.subtitle') }}</span>
          </div>
          <div class="header-actions">
            <el-button type="primary" @click="showCreateDialog">
              <el-icon><Plus /></el-icon> {{ $t('llmModels.addModel') }}
            </el-button>
            <el-button @click="loadModels" :loading="loading">
              <el-icon><Refresh /></el-icon> {{ $t('llmModels.refresh') }}
            </el-button>
          </div>
        </div>
      </template>

      <el-table 
        :data="models" 
        v-loading="loading" 
        style="width: 100%" 
        class="models-table" 
        border 
        stripe
      >
        <el-table-column prop="name" :label="$t('llmModels.columns.name')" width="350">
          <template #default="{ row }">
            <div class="model-name-cell">
              <el-tag :type="getProviderType(row.provider)" effect="plain" size="small">
                {{ getProviderLabel(row.provider) }}
              </el-tag>
              <span class="model-name">{{ row.name }}</span>
              <el-tag v-if="row.is_default" type="warning" size="small" effect="dark">{{ $t('llmModels.isDefault') }}</el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="model_name" :label="$t('llmModels.columns.id')" width="300">
          <template #default="{ row }">
            <code class="model-id">{{ row.model_name }}</code>
          </template>
        </el-table-column>

        <el-table-column prop="base_url" :label="$t('llmModels.columns.baseUrl')">
          <template #default="{ row }">
            <el-tooltip :content="row.base_url" placement="top">
              <span class="url-text">{{ row.base_url }}</span>
            </el-tooltip>
          </template>
        </el-table-column>

        <el-table-column prop="temperature" label="Temperature" width="120" align="center">
          <template #default="{ row }">
            <el-tag type="info" effect="plain" size="small">{{ row.temperature }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="supports_vision" :label="$t('llmModels.columns.vision')" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.supports_vision ? 'success' : 'info'" effect="plain" size="small">
              {{ row.supports_vision ? $t('llmModels.vision.yes') : $t('llmModels.vision.no') }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="supports_stream" :label="$t('llmModels.columns.stream')" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.supports_stream ? 'success' : 'info'" effect="plain" size="small">
              {{ row.supports_stream ? $t('llmModels.stream.yes') : $t('llmModels.stream.no') }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="max_retries" :label="$t('llmModels.columns.retries')" width="100" align="center">
          <template #default="{ row }">
            <el-tag type="info" effect="plain" size="small">{{ row.max_retries ?? 3 }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="is_enabled" :label="$t('llmModels.columns.status')" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_enabled ? 'success' : 'info'" effect="dark" size="default">
              {{ row.is_enabled ? $t('llmModels.status.enabled') : $t('llmModels.status.disabled') }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column :label="$t('llmModels.columns.actions')" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip :content="$t('llmModels.tooltips.test')" placement="top">
                <el-button circle size="small" type="success" :icon="Connection" @click="testModel(row)" :loading="testingId === row._id" />
              </el-tooltip>
              <el-tooltip :content="$t('llmModels.tooltips.edit')" placement="top">
                <el-button circle size="small" type="primary" :icon="Edit" @click="showEditDialog(row)" />
              </el-tooltip>
              <el-tooltip :content="$t('llmModels.tooltips.delete')" placement="top">
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
          @size-change="loadModels"
          @current-change="loadModels"
        />
      </div>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog 
      v-model="showDialog" 
      :title="isEdit ? $t('llmModels.dialog.editTitle') : $t('llmModels.dialog.createTitle')" 
      width="600px" 
      destroy-on-close
      class="bento-dialog"
    >
      <el-form :model="form" label-width="100px" label-position="top">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item :label="$t('llmModels.dialog.name')" required>
              <el-input v-model="form.name" :placeholder="$t('llmModels.dialog.namePlaceholder')" clearable />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('llmModels.dialog.provider')" required>
              <el-select v-model="form.provider" style="width: 100%">
                <el-option label="OpenAI" value="openai" />
                <el-option label="Anthropic" value="anthropic" />
                <el-option label="Google" value="google" />
                <el-option label="Ollama" value="ollama" />
                <el-option :label="$t('common.custom')" value="custom" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item :label="$t('llmModels.dialog.id')" required>
          <el-input v-model="form.model_name" :placeholder="$t('llmModels.dialog.idPlaceholder')" clearable />
        </el-form-item>

        <el-form-item :label="$t('llmModels.dialog.baseUrl')" required>
          <el-input v-model="form.base_url" :placeholder="getBaseUrlPlaceholder(form.provider)" clearable>
            <template #prefix><el-icon><Link /></el-icon></template>
          </el-input>
        </el-form-item>

        <el-form-item :label="$t('llmModels.dialog.apiKey')">
          <el-input v-model="form.api_key" type="password" :placeholder="$t('llmModels.dialog.apiKeyPlaceholder')" show-password clearable>
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="Temperature">
              <el-slider v-model="form.temperature" :min="0" :max="2" :step="0.1" show-input :show-input-controls="false" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="Max Tokens">
              <el-input-number v-model="form.max_tokens" :min="100" :max="128000" :step="1000" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="$t('llmModels.dialog.retries')">
              <el-input-number v-model="form.max_retries" :min="0" :max="10" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="6">
            <el-form-item :label="$t('llmModels.dialog.vision')">
              <el-switch v-model="form.supports_vision" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item :label="$t('llmModels.dialog.stream')">
              <el-switch v-model="form.supports_stream" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item :label="$t('llmModels.dialog.isDefault')">
              <el-switch v-model="form.is_default" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item :label="$t('llmModels.dialog.isEnabled')">
              <el-switch v-model="form.is_enabled" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showDialog = false" round>{{ $t('tasks.createDialog.cancel') }}</el-button>
          <el-button type="primary" @click="submitForm" :loading="submitting" round>
            {{ isEdit ? $t('llmModels.dialog.save') : $t('llmModels.dialog.create') }}
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
import { Plus, Refresh, Edit, Delete, Connection, Link, Lock } from '@element-plus/icons-vue'
import { getLLMModels, createLLMModel, updateLLMModel, deleteLLMModel, testLLMModel } from '../api'

const { t } = useI18n()

const loading = ref(false)
const submitting = ref(false)
const testingId = ref(null)
const models = ref([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

const showDialog = ref(false)
const isEdit = ref(false)
const editId = ref(null)

const defaultForm = {
  name: '',
  provider: 'openai',
  model_name: '',
  base_url: 'https://api.openai.com/v1',
  api_key: '',
  temperature: 0.7,
  max_tokens: 4096,
  supports_vision: false,
  supports_stream: false,
  max_retries: 3,
  is_default: false,
  is_enabled: true
}

const form = ref({ ...defaultForm })

const getProviderType = (provider) => {
  const types = {
    openai: 'success',
    anthropic: 'warning',
    google: 'primary',
    ollama: 'info',
    custom: ''
  }
  return types[provider] || 'info'
}

const getProviderLabel = (provider) => {
  const labels = {
    openai: 'OpenAI',
    anthropic: 'Anthropic',
    google: 'Google',
    ollama: 'Ollama',
    custom: t('common.custom') || '自定义'
  }
  return labels[provider] || provider
}

const getBaseUrlPlaceholder = (provider) => {
  const placeholders = {
    openai: 'https://api.openai.com/v1',
    anthropic: 'https://api.anthropic.com',
    google: 'https://generativelanguage.googleapis.com/v1beta',
    ollama: 'http://localhost:11434',
    custom: 'https://your-api-endpoint.com'
  }
  return placeholders[provider] || 'https://api.example.com'
}

const loadModels = async () => {
  loading.value = true
  try {
    const params = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value
    }
    const data = await getLLMModels(params)
    models.value = data.items
    total.value = data.total
  } catch (error) {
    ElMessage.error(t('llmModels.messages.loadFailed') + (error.response?.data?.detail || error.message))
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
    provider: row.provider,
    model_name: row.model_name,
    base_url: row.base_url,
    api_key: '', // 不回显 API Key
    temperature: row.temperature,
    max_tokens: row.max_tokens,
    supports_vision: row.supports_vision || false,
    supports_stream: row.supports_stream || false,
    max_retries: row.max_retries ?? 3,
    is_default: row.is_default,
    is_enabled: row.is_enabled
  }
  showDialog.value = true
}

const submitForm = async () => {
  if (!form.value.name || !form.value.model_name || !form.value.base_url) {
    ElMessage.warning(t('llmModels.messages.fillRequired'))
    return
  }

  submitting.value = true
  try {
    const submitData = { ...form.value }
    // 如果 API Key 为空且是编辑模式，不提交该字段
    if (!submitData.api_key && isEdit.value) {
      delete submitData.api_key
    }

    if (isEdit.value) {
      await updateLLMModel(editId.value, submitData)
      ElMessage.success(t('llmModels.messages.updateSuccess'))
    } else {
      await createLLMModel(submitData)
      ElMessage.success(t('llmModels.messages.createSuccess'))
    }
    
    showDialog.value = false
    loadModels()
  } catch (error) {
    ElMessage.error(t('llmModels.messages.operationFailed') + (error.response?.data?.detail || error.message))
  } finally {
    submitting.value = false
  }
}

const confirmDelete = (row) => {
  ElMessageBox.confirm(
    t('llmModels.messages.deleteConfirm', { name: row.name }),
    t('llmModels.messages.deleteTitle'),
    {
      confirmButtonText: t('common.delete'),
      cancelButtonText: t('common.cancel'),
      type: 'error',
      icon: Delete
    }
  ).then(async () => {
    try {
      await deleteLLMModel(row._id)
      ElMessage.success(t('llmModels.messages.deleteSuccess'))
      loadModels()
    } catch (error) {
      ElMessage.error(t('llmModels.messages.deleteFailed') + (error.response?.data?.detail || error.message))
    }
  }).catch(() => {})
}

const testModel = async (row) => {
  testingId.value = row._id
  try {
    const result = await testLLMModel(row._id)
    if (result.success) {
      ElMessage.success(t('llmModels.messages.testSuccess', { latency: result.latency_ms }))
    } else {
      ElMessage.error(t('llmModels.messages.testFailed', { message: result.message }))
    }
  } catch (error) {
    ElMessage.error(t('llmModels.messages.testCallFailed') + (error.response?.data?.detail || error.message))
  } finally {
    testingId.value = null
  }
}

onMounted(() => {
  loadModels()
})
</script>

<style scoped>
.llm-models-container {
  padding: 0;
}

.llm-models-card {
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
  gap: 10px;
}

.model-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.model-name {
  font-weight: 500;
}

.model-id {
  background: #f5f7fa;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 13px;
  color: #606266;
}

.url-text {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: inline-block;
  color: #409eff;
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
