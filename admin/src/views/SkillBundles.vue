<template>
  <div class="skill-bundles-container">
    <el-card class="bundles-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="title">{{ $t('skillBundles.title') }}</span>
            <span class="subtitle">{{ $t('skillBundles.subtitle') }}</span>
          </div>
          <div class="header-actions">
            <el-button type="primary" @click="handleAddBundle">
              <el-icon><Plus /></el-icon> {{ $t('skillBundles.addBundle') }}
            </el-button>
            <el-button @click="loadBundles" :loading="loading">
              <el-icon><Refresh /></el-icon> {{ $t('skillBundles.refresh') }}
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="bundles" v-loading="loading" border stripe style="width: 100%">
        <el-table-column prop="name" :label="$t('skillBundles.columns.name')" min-width="150" />
        <el-table-column prop="description" :label="$t('skillBundles.columns.description')" min-width="200" show-overflow-tooltip />
        <el-table-column :label="$t('skillBundles.columns.steps')" width="120" align="center">
          <template #default="{ row }">
            <el-tag type="info">{{ $t('skillBundles.stepsCount', { n: row.steps?.length || 0 }) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" :label="$t('skillBundles.columns.createdAt')" width="180" align="center">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('skillBundles.columns.actions')" width="180" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEditBundle(row)">{{ $t('skillBundles.actions.edit') }}</el-button>
            <el-button link type="danger" @click="handleDeleteBundle(row)">{{ $t('skillBundles.actions.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 技能包编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? $t('skillBundles.dialog.editTitle') : $t('skillBundles.dialog.createTitle')"
      width="900px"
      destroy-on-close
    >
      <el-form :model="bundleForm" label-width="100px" label-position="top">
        <el-form-item :label="$t('skillBundles.dialog.name')" required>
          <el-input v-model="bundleForm.name" :placeholder="$t('skillBundles.dialog.namePlaceholder')" />
        </el-form-item>
        
        <el-form-item :label="$t('skillBundles.dialog.description')">
          <el-input v-model="bundleForm.description" type="textarea" :rows="2" :placeholder="$t('skillBundles.dialog.descriptionPlaceholder')" />
        </el-form-item>

        <div class="steps-section">
          <div class="section-header">
            <span class="section-title">{{ $t('skillBundles.dialog.stepsConfig') }}</span>
            <el-button type="primary" link @click="addStep" :icon="Plus">
               {{ $t('skillBundles.dialog.addStep') }}
            </el-button>
          </div>

          <div v-if="bundleForm.steps.length" class="steps-list">
            <div v-for="(step, index) in bundleForm.steps" :key="index" class="step-item">
              <div class="step-header">
                <span class="step-index">{{ $t('skillBundles.dialog.stepIndex', { n: index + 1 }) }}</span>
                <el-button type="danger" link @click="removeStep(index)">
                  <el-icon><Delete /></el-icon> {{ $t('skillBundles.dialog.remove') }}
                </el-button>
              </div>
              
              <el-row :gutter="20">
                <el-col :span="6">
                  <el-form-item :label="$t('skillBundles.dialog.actionType')">
                    <el-select v-model="step.action" @change="resetStepParams(index)" style="width: 100%">
                      <el-option
                         v-for="skill in builtInSkills"
                         :key="skill.name"
                         :label="skill.display_name"
                         :value="skill.name"
                       />
                       <el-divider v-if="customSkills.length" content-position="center">{{ $t('skills.attrs.custom') }}</el-divider>
                       <el-option 
                         v-for="skill in customSkills" 
                         :key="skill.name" 
                         :label="`${skill.display_name} (${skill.name})`" 
                         :value="skill.name" 
                       />
                    </el-select>
                  </el-form-item>
                </el-col>
                
                <el-col :span="18">
                  <div class="params-editor">
                    <!-- 等待参数 -->
                    <template v-if="step.action === 'wait'">
                      <el-form-item :label="$t('skillBundles.dialog.wait.duration')">
                        <el-input-number v-model="step.params.duration" :min="100" :step="500" />
                      </el-form-item>
                    </template>

                    <!-- 滚动参数 -->
                    <template v-else-if="step.action === 'scroll'">
                      <el-row :gutter="10">
                        <el-col :span="16">
                          <el-form-item :label="$t('skillBundles.dialog.scroll.container')">
                            <el-input v-model="step.params.selector" :placeholder="$t('skillBundles.dialog.scroll.containerPlaceholder')" />
                          </el-form-item>
                        </el-col>
                        <el-col :span="8">
                          <el-form-item :label="$t('skillBundles.dialog.scroll.distance')">
                            <el-input-number v-model="step.params.distance" :step="100" />
                          </el-form-item>
                        </el-col>
                      </el-row>
                    </template>

                    <!-- 点击参数 -->
                    <template v-else-if="step.action === 'click'">
                      <el-form-item :label="$t('skillBundles.dialog.click.target')" required>
                        <el-input v-model="step.params.selector" :placeholder="$t('skillBundles.dialog.click.targetPlaceholder')" />
                      </el-form-item>
                    </template>

                    <!-- 流式滚动参数 -->
                    <template v-else-if="step.action === 'infinite_scroll'">
                      <el-row :gutter="10">
                        <el-col :span="10">
                          <el-form-item :label="$t('skillBundles.dialog.infiniteScroll.container')">
                            <el-input v-model="step.params.selector" :placeholder="$t('skillBundles.dialog.infiniteScroll.containerPlaceholder')" />
                          </el-form-item>
                        </el-col>
                        <el-col :span="7">
                          <el-form-item :label="$t('skillBundles.dialog.infiniteScroll.maxScrolls')">
                            <el-input-number v-model="step.params.max_scrolls" :min="1" :max="50" style="width: 100%" />
                          </el-form-item>
                        </el-col>
                        <el-col :span="7">
                          <el-form-item :label="$t('skillBundles.dialog.infiniteScroll.delay')">
                            <el-input-number v-model="step.params.delay" :min="500" :step="500" style="width: 100%" />
                          </el-form-item>
                        </el-col>
                      </el-row>
                    </template>

                    <!-- 翻页参数 -->
                    <template v-else-if="step.action === 'pagination'">
                      <el-row :gutter="10">
                        <el-col :span="8">
                          <el-form-item :label="$t('skillBundles.dialog.pagination.action')">
                            <el-select v-model="step.params.action" style="width: 100%">
                              <el-option :label="$t('skillBundles.dialog.pagination.next')" value="next" />
                              <el-option :label="$t('skillBundles.dialog.pagination.prev')" value="prev" />
                            </el-select>
                          </el-form-item>
                        </el-col>
                        <el-col :span="16">
                          <el-form-item :label="$t('skillBundles.dialog.click.target')">
                            <el-input v-model="step.params.selector" :placeholder="$t('skillBundles.dialog.pagination.btnPlaceholder')" />
                          </el-form-item>
                        </el-col>
                      </el-row>
                    </template>

                    <!-- 缩放参数 -->
                    <template v-else-if="step.action === 'zoom'">
                      <el-row :gutter="10">
                        <el-col :span="10">
                          <el-form-item :label="$t('skillBundles.dialog.zoom.container')">
                            <el-input v-model="step.params.selector" :placeholder="$t('skillBundles.dialog.zoom.containerPlaceholder')" />
                          </el-form-item>
                        </el-col>
                        <el-col :span="7">
                          <el-form-item :label="$t('skillBundles.dialog.zoom.direction')">
                            <el-select v-model="step.params.direction" style="width: 100%">
                              <el-option :label="$t('skillBundles.dialog.zoom.in')" value="in" />
                              <el-option :label="$t('skillBundles.dialog.zoom.out')" value="out" />
                            </el-select>
                          </el-form-item>
                        </el-col>
                        <el-col :span="7">
                          <el-form-item :label="$t('skillBundles.dialog.zoom.times')">
                            <el-input-number v-model="step.params.times" :min="1" :max="10" style="width: 100%" />
                          </el-form-item>
                        </el-col>
                      </el-row>
                    </template>

                    <!-- 填充参数 -->
                    <template v-else-if="step.action === 'fill'">
                      <div class="fill-params-header" style="margin-bottom: 10px;">
                        <el-button type="info" plain size="small" @click="addFillPair(index)">{{ $t('skillBundles.dialog.fill.addField') }}</el-button>
                        <span v-if="Object.keys(step.params.data || {}).length" style="margin-left: 10px; color: #909399; font-size: 13px;">
                          {{ $t('skillBundles.dialog.fill.fieldsCount', { n: Object.keys(step.params.data).length }) }}
                        </span>
                      </div>
                      <div v-if="Object.keys(step.params.data || {}).length" class="fill-data-tags" style="display: flex; flex-wrap: wrap; gap: 5px;">
                        <el-tag 
                          v-for="(val, key) in step.params.data" 
                          :key="key" 
                          closable 
                          size="small"
                          @close="removeFillPair(index, key)"
                        >
                          {{ key }}: {{ val }}
                        </el-tag>
                      </div>
                    </template>

                     <template v-else-if="step.action === 'extract_coordinates'">
                       <div class="no-params-tip" style="color: #909399; font-size: 13px; padding: 10px;">
                         {{ $t('skillBundles.dialog.extractCoordinates.noParams') }}
                       </div>
                     </template>

                     <!-- 块状容器参数 -->
                     <template v-else-if="step.action === 'block_container'">
                       <el-form-item :label="$t('skillBundles.dialog.blockContainer.title')" required>
                         <el-input v-model="step.params.selector" :placeholder="$t('skillBundles.dialog.blockContainer.placeholder')" />
                       </el-form-item>
                     </template>

                     <!-- 排除元素参数 -->
                     <template v-else-if="step.action === 'exclude_elements'">
                       <el-form-item :label="$t('skillBundles.dialog.excludeElements.title')" required>
                         <el-input v-model="step.params.selectors" :placeholder="$t('skillBundles.dialog.excludeElements.placeholder')" />
                       </el-form-item>
                     </template>

                     <!-- 动态加载其它技能的参数：显示一个通用的 JSON 编辑器或简单的 Key-Value -->
                    <template v-else>
                      <el-form-item :label="$t('skillBundles.dialog.advanced.json')">
                        <el-input 
                          v-model="step.params_json" 
                          type="textarea" 
                          :rows="2" 
                          placeholder='{"selector": ".item", "count": 5}'
                          @blur="validateParamsJson(index)"
                        />
                      </el-form-item>
                    </template>
                  </div>
                </el-col>
              </el-row>
            </div>
          </div>
          
          <el-empty v-else :description="$t('skillBundles.dialog.empty')" :image-size="60" />
        </div>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submitBundle" :loading="submitting">{{ $t('skillBundles.dialog.confirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Delete } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const { t } = useI18n()
import { 
  getSkillBundles, createSkillBundle, updateSkillBundle, deleteSkillBundle,
  getSkills, getBuiltInSkills
} from '../api'

const loading = ref(false)
const submitting = ref(false)
const bundles = ref([])
const builtInSkills = ref([])
const customSkills = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)

const bundleForm = ref({
  name: '',
  description: '',
  steps: []
})

const loadBundles = async () => {
  loading.value = true
  try {
    const data = await getSkillBundles()
    bundles.value = data
  } catch (error) {
    ElMessage.error(t('skillBundles.messages.loadFailed'))
  } finally {
    loading.value = false
  }
}

const loadSkills = async () => {
  try {
    const [builtIn, custom] = await Promise.all([
      getBuiltInSkills(),
      getSkills({ is_enabled: true })
    ])
    builtInSkills.value = builtIn
    customSkills.value = custom
  } catch (error) {
    console.error('Failed to load skills:', error)
  }
}

const handleAddBundle = () => {
  isEdit.value = false
  bundleForm.value = {
    name: '',
    description: '',
    steps: []
  }
  dialogVisible.value = true
}

const handleEditBundle = (row) => {
  isEdit.value = true
  // 处理步骤中的 params 转换
  const steps = (row.steps || []).map(step => ({
    ...step,
    params_json: JSON.stringify(step.params || {})
  }))
  bundleForm.value = { ...row, steps }
  dialogVisible.value = true
}

const addStep = () => {
  bundleForm.value.steps.push({
    action: 'wait',
    params: { duration: 1000 },
    params_json: '{"duration": 1000}'
  })
}

const removeStep = (index) => {
  bundleForm.value.steps.splice(index, 1)
}

const resetStepParams = (index) => {
  const step = bundleForm.value.steps[index]
  const defaults = {
    wait: { duration: 1000 },
    scroll: { distance: 500, selector: 'window' },
    infinite_scroll: { max_scrolls: 10, delay: 1500, selector: 'window' },
    click: { selector: '' },
    pagination: { action: 'next', selector: '' },
    fill: { data: {} },
    zoom: { direction: 'in', times: 1, selector: '' },
    extract_coordinates: {},
    block_container: { selector: '' },
    exclude_elements: { selectors: '' }
  }
  step.params = JSON.parse(JSON.stringify(defaults[step.action] || {}))
  step.params_json = JSON.stringify(step.params)
}

const validateParamsJson = (index) => {
  const step = bundleForm.value.steps[index]
  // 只有非专用 UI 的动作才需要从 JSON 验证
  const dedicatedActions = ['wait', 'scroll', 'infinite_scroll', 'click', 'pagination', 'fill', 'zoom', 'extract_coordinates', 'block_container', 'exclude_elements']
  if (dedicatedActions.includes(step.action)) return

  try {
    step.params = JSON.parse(step.params_json || '{}')
  } catch (e) {
    ElMessage.warning(t('skillBundles.messages.jsonError', { n: index + 1 }))
  }
}

const addFillPair = (index) => {
  const step = bundleForm.value.steps[index]
  ElMessageBox.prompt(t('skillBundles.messages.promptPayload'), t('skillBundles.messages.addFieldTitle'), {
    confirmButtonText: t('common.confirm'),
    cancelButtonText: t('common.cancel'),
  }).then(({ value }) => {
    if (value && value.includes('=')) {
      const parts = value.split('=')
      const k = parts[0].trim()
      const v = parts.slice(1).join('=').trim()
      if (!step.params.data) step.params.data = {}
      step.params.data[k] = v
    } else {
      ElMessage.warning(t('skillBundles.messages.formatError'))
    }
  }).catch(() => {})
}

const removeFillPair = (index, key) => {
  const step = bundleForm.value.steps[index]
  if (step.params.data) {
    delete step.params.data[key]
  }
}

const submitBundle = async () => {
  if (!bundleForm.value.name) {
    ElMessage.warning(t('skillBundles.messages.nameRequired'))
    return
  }

  // 同步所有 params
  bundleForm.value.steps.forEach((_, idx) => validateParamsJson(idx))

  submitting.value = true
  try {
    const payload = {
      name: bundleForm.value.name,
      description: bundleForm.value.description,
      steps: bundleForm.value.steps.map(s => ({ action: s.action, params: s.params }))
    }

    if (isEdit.value) {
      const id = bundleForm.value._id || bundleForm.value.id
      await updateSkillBundle(id, payload)
      ElMessage.success(t('skillBundles.messages.updateSuccess'))
    } else {
      await createSkillBundle(payload)
      ElMessage.success(t('skillBundles.messages.createSuccess'))
    }
    dialogVisible.value = false
    loadBundles()
  } catch (error) {
    ElMessage.error(t('skillBundles.messages.saveFailed'))
  } finally {
    submitting.value = false
  }
}

const handleDeleteBundle = (row) => {
  ElMessageBox.confirm(t('skillBundles.messages.deleteConfirm'), t('skillBundles.messages.deleteConfirmTitle'), {
    type: 'warning'
  }).then(async () => {
    try {
      const id = row._id || row.id
      await deleteSkillBundle(id)
      ElMessage.success(t('skillBundles.messages.deleteSuccess'))
      loadBundles()
    } catch (error) {
      ElMessage.error(t('skillBundles.messages.deleteFailed'))
    }
  })
}

const formatDate = (date) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

onMounted(() => {
  loadBundles()
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

.steps-section {
  margin-top: 20px;
  border-top: 1px solid #ebeef5;
  padding-top: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.step-item {
  background-color: #f8f9fb;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 15px;
  position: relative;
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.step-index {
  font-weight: bold;
  color: #409eff;
}

.params-editor {
  background-color: #fff;
  padding: 10px;
  border-radius: 4px;
}
</style>
