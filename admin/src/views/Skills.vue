<template>
  <div class="skills-container">
    <el-card class="skills-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="title">技能管理</span>
            <span class="subtitle">管理和扩展浏览器交互及提取技能</span>
          </div>
          <div class="header-actions">
            <el-button type="primary" @click="handleAddSkill">
              <el-icon><Plus /></el-icon> 新增技能
            </el-button>
            <el-button @click="loadSkills" :loading="loading">
              <el-icon><Refresh /></el-icon> 刷新
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="skills" v-loading="loading" border stripe style="width: 100%">
        <el-table-column prop="display_name" label="技能名称" min-width="150" />
        <el-table-column prop="name" label="标识符" width="180">
          <template #default="{ row }">
            <code>{{ row.name }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.type === 'extraction' ? 'success' : 'info'">
              {{ row.type === 'extraction' ? '数据提取' : '交互操作' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="is_builtin" label="属性" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_builtin" type="warning" size="small">内置</el-tag>
            <el-tag v-else type="primary" size="small">自定义</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_enabled" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.is_enabled" @change="toggleSkillStatus(row)" :disabled="row.is_builtin" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEditSkill(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDeleteSkill(row)" :disabled="row.is_builtin">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 技能编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑技能' : '新增技能'"
      width="85%"
      destroy-on-close
    >
      <el-form :model="skillForm" label-width="100px" label-position="top">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="名称 (标识符)" required>
              <el-input v-model="skillForm.name" placeholder="例如: extract_prices" :disabled="isEdit" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="显示名称" required>
              <el-input v-model="skillForm.display_name" placeholder="例如: 提取价格" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="技能类型">
              <el-select v-model="skillForm.type" style="width: 100%">
                <el-option label="交互操作 (Interaction)" value="interaction" />
                <el-option label="数据提取 (Extraction)" value="extraction" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="启用状态">
              <el-switch v-model="skillForm.is_enabled" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="描述">
          <el-input v-model="skillForm.description" type="textarea" :rows="2" placeholder="简要描述技能用途..." />
        </el-form-item>

        <el-form-item label="JavaScript 代码" required class="code-item">
          <div class="code-editor-outer">
            <codemirror
              v-model="skillForm.js_code"
              placeholder="// JavaScript 代码...
// 如果是提取类型，最后必须 return 一个值
// 示例：
// return { title: document.title, url: window.location.href };"
              :style="{ height: '400px', width: '100%' }"
              :autofocus="true"
              :indent-with-tab="true"
              :tab-size="2"
              :extensions="extensions"
            />
            <div class="form-util-bar">
              <div class="form-tip">
                <el-icon><InfoFilled /></el-icon>
                代码将在浏览器环境中执行，可以使用 `document`, `window` 等对象。如果是采集类技能，请确保最后使用 `return` 返回结果。
              </div>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitSkill" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, InfoFilled, Pointer } from '@element-plus/icons-vue'
import { getSkills, createSkill, updateSkill, deleteSkill } from '../api'

// CodeMirror imports
import { Codemirror } from 'vue-codemirror'
import { javascript } from '@codemirror/lang-javascript'
import { oneDark } from '@codemirror/theme-one-dark'

const extensions = [javascript(), oneDark]

const loading = ref(false)
const submitting = ref(false)
const skills = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const skillForm = ref({
  name: '',
  display_name: '',
  type: 'interaction',
  description: '',
  js_code: '',
  is_enabled: true
})

const loadSkills = async () => {
  loading.value = true
  try {
    const data = await getSkills()
    skills.value = data
  } catch (error) {
    ElMessage.error('加载技能列表失败')
  } finally {
    loading.value = false
  }
}

const handleAddSkill = () => {
  isEdit.value = false
  skillForm.value = {
    name: '',
    display_name: '',
    type: 'interaction',
    description: '',
    js_code: '',
    is_enabled: true
  }
  dialogVisible.value = true
}

const handleEditSkill = (row) => {
  isEdit.value = true
  skillForm.value = { ...row }
  dialogVisible.value = true
}

const submitSkill = async () => {
  if (!skillForm.value.name || !skillForm.value.display_name || !skillForm.value.js_code) {
    ElMessage.warning('请填写必填项')
    return
  }

  submitting.value = true
  try {
    if (isEdit.value) {
      const skillId = skillForm.value._id || skillForm.value.id
      await updateSkill(skillId, skillForm.value)
      ElMessage.success('更新成功')
    } else {
      await createSkill(skillForm.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadSkills()
  } catch (error) {
    ElMessage.error('保存失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    submitting.value = false
  }
}

const toggleSkillStatus = async (row) => {
  try {
    const skillId = row._id || row.id
    await updateSkill(skillId, { is_enabled: row.is_enabled })
    ElMessage.success('状态更新成功')
  } catch (error) {
    row.is_enabled = !row.is_enabled
    ElMessage.error('更新状态失败')
  }
}

const handleDeleteSkill = (row) => {
  ElMessageBox.confirm('确定删除该技能吗？', '提示', {
    type: 'warning'
  }).then(async () => {
    try {
      const skillId = row._id || row.id
      await deleteSkill(skillId)
      ElMessage.success('删除成功')
      loadSkills()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
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
