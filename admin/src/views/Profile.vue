<template>
  <div class="profile-container">
    <el-card class="profile-card">
      <template #header>
        <div class="card-header">
          <span>{{ $t('profile.title') }}</span>
        </div>
      </template>
      
      <el-form :model="profileForm" label-width="100px" class="profile-form">
        <el-form-item :label="$t('profile.username')">
          <el-input v-model="profileForm.username" disabled />
        </el-form-item>
        
        <el-form-item :label="$t('profile.role')">
          <el-tag :type="profileForm.role === 'admin' ? 'danger' : 'success'">
            {{ profileForm.role }}
          </el-tag>
        </el-form-item>
        
        <el-form-item :label="$t('profile.language')">
          <el-select v-model="profileForm.language" class="language-select">
            <el-option label="简体中文" value="zh-CN" />
            <el-option label="繁體中文" value="zh-TW" />
            <el-option label="English" value="en" />
            <el-option label="日本語" value="ja" />
          </el-select>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="handleSave">
            {{ $t('profile.save') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'

const authStore = useAuthStore()
const { t } = useI18n()
const saving = ref(false)

const profileForm = ref({
  username: '',
  role: '',
  language: 'zh-CN'
})

onMounted(() => {
  if (authStore.user) {
    profileForm.value.username = authStore.user.username
    profileForm.value.role = authStore.user.role || 'admin'
    profileForm.value.language = authStore.user.language || 'zh-CN'
  }
})

const handleSave = async () => {
  saving.value = true
  try {
    await authStore.updateProfile({
      language: profileForm.value.language
    })
    ElMessage.success(t('profile.saveSuccess'))
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || 'Update failed')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.profile-container {
  display: flex;
  justify-content: center;
  padding-top: 40px;
}

.profile-card {
  width: 100%;
  max-width: 600px;
}

.card-header {
  font-weight: bold;
  font-size: 18px;
}

.profile-form {
  margin-top: 20px;
}

.language-select {
  width: 100%;
}
</style>
