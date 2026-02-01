import { defineStore } from 'pinia'
import { login as loginApi, getMe, updateMe } from '../api'
import i18n from '../i18n'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null'),
    loading: false,
    error: null
  }),

  getters: {
    isAuthenticated: (state) => !!state.token,
    isAdmin: (state) => state.user?.role === 'admin'
  },

  actions: {
    async login(username, password) {
      this.loading = true
      this.error = null
      try {
        const data = await loginApi(username, password)

        this.token = data.access_token
        this.user = data.user

        localStorage.setItem('token', this.token)
        localStorage.setItem('user', JSON.stringify(this.user))

        return true
      } catch (error) {
        this.error = error.response?.data?.detail || '登录失败'
        throw error
      } finally {
        this.loading = false
      }
    },

    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    },

    async fetchCurrentUser() {
      if (!this.token) return

      try {
        const data = await getMe()
        this.user = data
        localStorage.setItem('user', JSON.stringify(this.user))

        // Update i18n locale
        if (data.language) {
          i18n.global.locale.value = data.language
        }
      } catch (error) {
        this.logout()
      }
    },

    async updateProfile(data) {
      try {
        const updatedUser = await updateMe(data)
        this.user = updatedUser
        localStorage.setItem('user', JSON.stringify(this.user))

        // Update i18n locale
        if (updatedUser.language) {
          i18n.global.locale.value = updatedUser.language
        }
        return true
      } catch (error) {
        console.error('Failed to update profile:', error)
        throw error
      }
    }
  }
})
