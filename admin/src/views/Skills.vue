<template>
  <div class="skills-container">
    <el-card class="skills-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="title">{{ $t('skills.title') }}</span>
            <span class="subtitle">{{ $t('skills.subtitle') }}</span>
          </div>
          <div class="header-actions">
            <el-button type="primary" @click="showCreateDialog">
              <el-icon><Plus /></el-icon> {{ $t('skills.addSkill') }}
            </el-button>
            <el-button @click="loadSkills" :loading="loading">
              <el-icon><Refresh /></el-icon> {{ $t('skills.refresh') }}
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="skills" v-loading="loading" stripe>
        <el-table-column prop="name" :label="$t('skills.columns.name')" min-width="150">
          <template #default="{ row }">
            <div class="skill-name-cell">
              <span class="skill-name">{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="skill_id" :label="$t('skills.columns.id')" width="180">
          <template #default="{ row }">
            <code class="skill-id">{{ row.skill_id }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="type" :label="$t('skills.columns.type')" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.type === 'extraction' ? 'warning' : 'success'" size="small">
              {{ row.type === 'extraction' ? $t('skills.types.extraction') : $t('skills.types.interaction') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_builtin" :label="$t('skills.columns.attr')" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_builtin ? 'info' : 'primary'" effect="plain" size="small">
              {{ row.is_builtin ? $t('skills.attrs.builtin') : $t('skills.attrs.custom') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_enabled" :label="$t('skills.columns.status')" width="100" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_enabled"
              @change="toggleSkillStatus(row)"
              :disabled="row.is_builtin"
            />
          </template>
        </el-table-column>
        <el-table-column :label="$t('skills.columns.actions')" width="180" align="center" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="showEditDialog(row)" :icon="Edit">{{ $t('skills.actions.edit') }}</el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="confirmDelete(row)" 
              :icon="Delete"
              :disabled="row.is_builtin"
            >{{ $t('skills.actions.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 技能编辑对话框 -->
    <el-dialog 
      v-model="showDialog" 
      :title="isEdit ? $t('skills.dialog.editTitle') : $t('skills.dialog.createTitle')" 
      width="800px" 
      top="10vh" 
      destroy-on-close 
      class="skill-dialog"
    >
      <el-form :model="form" label-width="120px" label-position="top">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item :label="$t('skills.dialog.id')" required>
              <el-input v-model="form.skill_id" :placeholder="$t('skills.dialog.idPlaceholder')" :disabled="isEdit" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('skills.dialog.name')" required>
              <el-input v-model="form.name" :placeholder="$t('skills.dialog.namePlaceholder')" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item :label="$t('skills.dialog.type')" required>
              <el-radio-group v-model="form.type">
                <el-radio-button label="interaction">{{ $t('skills.dialog.interaction') }}</el-radio-button>
                <el-radio-button label="extraction">{{ $t('skills.dialog.extraction') }}</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('skills.dialog.isEnabled')">
              <el-switch v-model="form.is_enabled" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item :label="$t('skills.dialog.description')">
          <el-input v-model="form.description" type="textarea" :rows="2" :placeholder="$t('skills.dialog.descriptionPlaceholder')" />
        </el-form-item>

        <el-form-item :label="$t('skills.dialog.jsCode')" required>
          <el-input
            v-model="form.code"
            type="textarea"
            :rows="12"
            :placeholder="$t('skills.dialog.jsPlaceholder')"
            class="code-editor"
          />
          <div class="code-tip">
            {{ $t('skills.dialog.tip') }}
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">{{ $t('skills.dialog.confirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, InfoFilled, Pointer, Edit, Delete } from '@element-plus/icons-vue'
import { getSkills, createSkill, updateSkill, deleteSkill, toggleSkill } from '../api'

const { t } = useI18n()

// CodeMirror imports
import { Codemirror } from 'vue-codemirror'
import { javascript } from '@codemirror/lang-javascript'
import { oneDark } from '@codemirror/theme-one-dark'

const extensions = [javascript(), oneDark]

const loading = ref(false)
const submitting = ref(false)
const skills = ref([])
const showDialog = ref(false)
const isEdit = ref(false)
const form = ref({
  skill_id: '',
  name: '',
  type: 'interaction',
  description: '',
  code: '',
  is_enabled: true
})
const editId = ref(null)

const loadSkills = async () => {
  loading.value = true
  try {
    const data = await getSkills()
    skills.value = data.items
  } catch (error) {
    ElMessage.error(t('skills.messages.loadFailed'))
  } finally {
    loading.value = false
  }
}

const showCreateDialog = () => {
  isEdit.value = false
  form.value = {
    skill_id: '',
    name: '',
    type: 'interaction',
    description: '',
    code: '',
    is_enabled: true
  }
  showDialog.value = true
}

const showEditDialog = (row) => {
  isEdit.value = true
  editId.value = row._id
  form.value = {
    skill_id: row.skill_id,
    name: row.name,
    type: row.type,
    description: row.description,
    code: row.code,
    is_enabled: row.is_enabled
  }
  showDialog.value = true
}

const submitForm = async () => {
  if (!form.value.skill_id || !form.value.name || !form.value.code) {
    ElMessage.warning(t('skills.messages.fillRequired'))
    return
  }

  submitting.value = true
  try {
    if (isEdit.value) {
      await updateSkill(editId.value, form.value)
      ElMessage.success(t('skills.messages.updateSuccess'))
    } else {
      await createSkill(form.value)
      ElMessage.success(t('skills.messages.createSuccess'))
    }
    showDialog.value = false
    loadSkills()
  } catch (error) {
    ElMessage.error(t('skills.messages.saveFailed') + (error.response?.data?.detail || error.message))
  } finally {
    submitting.value = false
  }
}

const toggleSkillStatus = async (row) => {
  try {
    await toggleSkill(row._id, row.is_enabled)
    ElMessage.success(t('skills.messages.toggleSuccess'))
  } catch (error) {
    ElMessage.error(t('skills.messages.toggleFailed'))
    row.is_enabled = !row.is_enabled
  }
}

const confirmDelete = (row) => {
  ElMessageBox.confirm(
    t('skills.messages.deleteConfirm'),
    t('skills.messages.deleteConfirmTitle'),
    {
      confirmButtonText: t('common.delete'),
      cancelButtonText: t('common.cancel'),
      type: 'warning'
    }
  ).then(async () => {
    try {
      await deleteSkill(row._id)
      ElMessage.success(t('skills.messages.deleteSuccess'))
      loadSkills()
    } catch (error) {
      ElMessage.error(t('skills.messages.deleteFailed'))
    }
  }).catch(() => {})
}

onMounted(() => {
  loadSkills()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-left .title {
  font-size: 18px;
  font-weight: bold;
}
.header-left .subtitle {
  font-size: 13px;
  color: #909399;
  margin-left: 10px;
}
.code-editor-outer {
  width: 100%;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
}

.code-editor-outer :deep(.cm-editor) {
  font-size: 14px;
}

.form-util-bar {
  background-color: #2c313a;
  padding: 8px 12px;
  border-top: 1px solid #181a1f;
}

.form-tip {
  font-size: 13px;
  color: #abb2bf;
  display: flex;
  align-items: center;
  gap: 6px;
  line-height: 1.4;
}

.form-tip .el-icon {
  color: #61afef;
}

.code-item :deep(.el-form-item__content) {
  display: block;
}
</style>
