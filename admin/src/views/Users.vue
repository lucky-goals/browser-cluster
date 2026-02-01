<template>
  <div class="users-container">
    <div class="page-header">
      <div class="header-title">
        <h2>{{ $t('users.title') }}</h2>
        <p>{{ $t('users.subtitle') }}</p>
      </div>
      <el-button type="primary" @click="handleAdd">
        <el-icon><Plus /></el-icon>{{ $t('users.addUser') }}
      </el-button>
    </div>

    <el-card class="table-card">
      <el-table :data="users" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" :label="$t('users.username')" min-width="150" />
        <el-table-column prop="role" :label="$t('users.role')" width="120">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'info'">
              {{ row.role === 'admin' ? $t('users.admin') : $t('users.user') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" :label="$t('users.createdAt')" min-width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" :label="$t('users.updatedAt')" min-width="180">
          <template #default="{ row }">
            {{ formatTime(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('users.actions')" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :icon="Edit" @click="handleEdit(row)">{{ $t('users.edit') }}</el-button>
            <el-button 
              link 
              type="danger" 
              :icon="Delete" 
              @click="handleDelete(row)"
              :disabled="row.username === currentUser.username"
            >{{ $t('users.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 用户表单弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? $t('users.editUser') : $t('users.addUser')"
      width="450px"
      destroy-on-close
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item :label="$t('users.username')" prop="username">
          <el-input v-model="form.username" :placeholder="$t('users.usernamePlaceholder')" :disabled="isEdit" />
        </el-form-item>
        <el-form-item :label="$t('users.password')" :prop="isEdit ? '' : 'password'">
          <el-input 
            v-model="form.password" 
            type="password" 
            :placeholder="$t('users.passwordPlaceholder')" 
            show-password
          />
          <p v-if="isEdit" class="form-tip">{{ $t('users.passwordTip') }}</p>
        </el-form-item>
        <el-form-item :label="$t('users.role')" prop="role">
          <el-select v-model="form.role" :placeholder="$t('users.rolePlaceholder')" style="width: 100%">
            <el-option :label="$t('users.admin')" value="admin" />
            <el-option :label="$t('users.user')" value="user" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">{{ $t('common.confirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { Plus, Edit, Delete } from '@element-plus/icons-vue'
import { getUsers, createUser, updateUser, deleteUser } from '../api'
import { useAuthStore } from '../stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useI18n } from 'vue-i18n'
import dayjs from 'dayjs'

const { t } = useI18n()

const authStore = useAuthStore()
const currentUser = computed(() => authStore.user || {})

const users = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitLoading = ref(false)
const formRef = ref(null)

const form = ref({
  id: null,
  username: '',
  password: '',
  role: 'admin'
})

const rules = {
  username: [{ required: true, message: t('users.usernamePlaceholder'), trigger: 'blur' }],
  password: [{ required: true, message: t('users.passwordPlaceholder'), trigger: 'blur' }],
  role: [{ required: true, message: t('users.rolePlaceholder'), trigger: 'change' }]
}

const formatTime = (time) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

const fetchUsers = async () => {
  loading.value = true
  try {
    users.value = await getUsers()
  } catch (error) {
    ElMessage.error(t('users.getUsersFailed'))
  } finally {
    loading.value = false
  }
}

const handleAdd = () => {
  isEdit.value = false
  form.value = {
    id: null,
    username: '',
    password: '',
    role: 'admin'
  }
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  form.value = {
    id: row.id,
    username: row.username,
    password: '',
    role: row.role
  }
  dialogVisible.value = true
}

const handleDelete = (row) => {
  ElMessageBox.confirm(
    t('users.deleteConfirm', { username: row.username }),
    t('common.tip'),
    {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      type: 'warning',
    }
  ).then(async () => {
    try {
      await deleteUser(row.id)
      ElMessage.success(t('users.deleteSuccess'))
      fetchUsers()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || t('users.deleteFailed'))
    }
  })
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true
      try {
        if (isEdit.value) {
          await updateUser(form.value.id, {
            username: form.value.username,
            password: form.value.password || undefined,
            role: form.value.role
          })
          ElMessage.success(t('users.updateSuccess'))
        } else {
          await createUser({
            username: form.value.username,
            password: form.value.password,
            role: form.value.role
          })
          ElMessage.success(t('users.createSuccess'))
        }
        dialogVisible.value = false
        fetchUsers()
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || t('users.operationFailed'))
      } finally {
        submitLoading.value = false
      }
    }
  })
}

onMounted(() => {
  fetchUsers()
})
</script>

<style scoped>
.users-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-title h2 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.header-title p {
  margin: 4px 0 0;
  color: #909399;
  font-size: 14px;
}

.table-card {
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.form-tip {
  margin: 4px 0 0;
  font-size: 12px;
  color: #909399;
  line-height: 1;
}

:deep(.el-table__header) {
  background-color: #f5f7fa;
}
</style>
