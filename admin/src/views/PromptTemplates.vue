<template>
  <div class="prompt-templates-container">
    <el-card class="templates-card">
      <template #header>
        <div class="card-header">
          <span class="title">{{ $t('promptTemplates.title') }}</span>
          <el-button type="primary" @click="showCreateDialog">
            <el-icon><Plus /></el-icon> {{ $t('promptTemplates.addTemplate') }}
          </el-button>
        </div>
      </template>

      <!-- 搜索栏 -->
      <div class="search-bar">
        <el-input
          v-model="searchQuery"
          :placeholder="$t('promptTemplates.searchPlaceholder')"
          clearable
          @input="handleSearch"
          style="width: 300px;"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button @click="loadTemplates" :icon="Refresh">{{ $t('promptTemplates.refresh') }}</el-button>
      </div>

      <!-- 模板列表 -->
      <el-table :data="templates" v-loading="loading" stripe>
        <el-table-column prop="name" :label="$t('promptTemplates.columns.name')" min-width="150">
          <template #default="{ row }">
            <span class="template-name">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="content" :label="$t('promptTemplates.columns.preview')" min-width="300">
          <template #default="{ row }">
            <el-tooltip :content="row.content" placement="top" :show-after="500">
              <span class="content-preview">{{ row.content.substring(0, 80) }}{{ row.content.length > 80 ? '...' : '' }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="description" :label="$t('promptTemplates.columns.description')" width="180">
          <template #default="{ row }">
            <span class="description-text">{{ row.description || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="username" :label="$t('promptTemplates.columns.creator')" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ row.username }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" :label="$t('promptTemplates.columns.updatedAt')" width="160" align="center">
          <template #default="{ row }">
            {{ formatDate(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('promptTemplates.columns.actions')" width="180" align="center" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="showEditDialog(row)" :icon="Edit">{{ $t('promptTemplates.actions.edit') }}</el-button>
            <el-button size="small" type="danger" @click="confirmDelete(row)" :icon="Delete">{{ $t('promptTemplates.actions.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @size-change="loadTemplates"
          @current-change="loadTemplates"
        />
      </div>
    </el-card>

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="showDialog" :title="isEdit ? $t('promptTemplates.dialog.editTitle') : $t('promptTemplates.dialog.createTitle')" width="1000px" top="15vh" destroy-on-close class="template-dialog">
      <el-form :model="form" label-width="100px" :rules="formRules" ref="formRef">
        <el-form-item :label="$t('promptTemplates.dialog.name')" prop="name">
          <el-input v-model="form.name" :placeholder="$t('promptTemplates.dialog.namePlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('promptTemplates.dialog.description')">
          <el-input v-model="form.description" :placeholder="$t('promptTemplates.dialog.descriptionPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('promptTemplates.dialog.systemRole')">
          <template #label>
            <div style="display: flex; align-items: center; gap: 4px;">
              <span>{{ $t('promptTemplates.dialog.systemRole') }}</span>
              <el-tooltip :content="$t('promptTemplates.dialog.systemRoleTip')" placement="top">
                <el-icon><InfoFilled /></el-icon>
              </el-tooltip>
            </div>
          </template>
          <el-input
            v-model="form.system_content"
            type="textarea"
            :rows="6"
            :placeholder="$t('promptTemplates.dialog.systemRolePlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="$t('promptTemplates.dialog.extractRequest')" prop="content">
          <template #label>
            <div style="display: flex; align-items: center; gap: 4px;">
              <span>{{ $t('promptTemplates.dialog.extractRequest') }}</span>
              <el-tooltip :content="$t('promptTemplates.dialog.extractRequestTip')" placement="top">
                <el-icon><InfoFilled /></el-icon>
              </el-tooltip>
            </div>
          </template>
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="12"
            :placeholder="$t('promptTemplates.dialog.extractRequestPlaceholder')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">{{ $t('promptTemplates.dialog.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh, Edit, Delete, InfoFilled } from '@element-plus/icons-vue'
import { getPromptTemplates, createPromptTemplate, updatePromptTemplate, deletePromptTemplate } from '../api'
import dayjs from 'dayjs'

const { t } = useI18n()

const loading = ref(false)
const submitting = ref(false)
const templates = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const searchQuery = ref('')

const showDialog = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const formRef = ref(null)
const form = ref({
  name: '',
  description: '',
  system_content: '',
  content: ''
})

const formRules = computed(() => ({
  name: [{ required: true, message: t('promptTemplates.messages.nameRequired'), trigger: 'blur' }],
  content: [{ required: true, message: t('promptTemplates.messages.contentRequired'), trigger: 'blur' }]
}))

const formatDate = (date) => {
  if (!date) return '-'
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

const loadTemplates = async () => {
  loading.value = true
  try {
    const params = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value
    }
    if (searchQuery.value) {
      params.search = searchQuery.value
    }
    const data = await getPromptTemplates(params)
    templates.value = data.items
    total.value = data.total
  } catch (error) {
    ElMessage.error(t('promptTemplates.messages.loadFailed'))
  } finally {
    loading.value = false
  }
}

let searchTimer = null
const handleSearch = () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    currentPage.value = 1
    loadTemplates()
  }, 300)
}

const showCreateDialog = () => {
  isEdit.value = false
  editId.value = null
  form.value = { name: '', description: '', system_content: '', content: '' }
  showDialog.value = true
}

const showEditDialog = (row) => {
  isEdit.value = true
  editId.value = row._id
  form.value = {
    name: row.name,
    description: row.description || '',
    system_content: row.system_content || '',
    content: row.content
  }
  showDialog.value = true
}

const submitForm = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    submitting.value = true
    try {
      if (isEdit.value) {
        await updatePromptTemplate(editId.value, form.value)
        ElMessage.success(t('promptTemplates.messages.updateSuccess'))
      } else {
        await createPromptTemplate(form.value)
        ElMessage.success(t('promptTemplates.messages.createSuccess'))
      }
      showDialog.value = false
      loadTemplates()
    } catch (error) {
      const msg = isEdit.value ? t('promptTemplates.messages.updateFailed') : t('promptTemplates.messages.createFailed')
      ElMessage.error(msg + (error.response?.data?.detail || error.message))
    } finally {
      submitting.value = false
    }
  })
}

const confirmDelete = (row) => {
  ElMessageBox.confirm(
    t('promptTemplates.messages.deleteConfirm', { name: row.name }),
    t('promptTemplates.messages.deleteTitle'),
    {
      confirmButtonText: t('common.delete'),
      cancelButtonText: t('common.cancel'),
      type: 'error'
    }
  ).then(async () => {
    try {
      await deletePromptTemplate(row._id)
      ElMessage.success(t('promptTemplates.messages.deleteSuccess'))
      loadTemplates()
    } catch (error) {
      ElMessage.error(t('promptTemplates.messages.deleteFailed') + (error.response?.data?.detail || error.message))
    }
  }).catch(() => {})
}

onMounted(() => {
  loadTemplates()
})
</script>

<style scoped>
.prompt-templates-container {
  padding: 20px;
}

.templates-card {
  border-radius: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header .title {
  font-size: 18px;
  font-weight: 600;
}

.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.template-name {
  font-weight: 500;
  color: #303133;
}

.content-preview {
  color: #606266;
  font-size: 13px;
}

.description-text {
  color: #909399;
  font-size: 12px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.template-dialog :deep(.el-dialog__body) {
  max-height: 75vh;
  padding-top: 10px;
}

.template-dialog :deep(.el-textarea__inner) {
  max-height: 50vh;
  overflow-y: auto;
}
</style>
