import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000
})

// Request interceptor to add token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const isLoginPage = window.location.pathname === '/login'
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      if (!isLoginPage) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export const login = async (username, password) => {
  const formData = new FormData()
  formData.append('username', username)
  formData.append('password', password)
  const response = await api.post('/auth/login', formData)
  return response.data
}

export const getMe = async () => {
  const response = await api.get('/auth/me')
  return response.data
}

export const getUsers = async () => {
  const response = await api.get('/users/')
  return response.data
}

export const createUser = async (data) => {
  const response = await api.post('/users/', data)
  return response.data
}

export const updateUser = async (userId, data) => {
  const response = await api.put(`/users/${userId}`, data)
  return response.data
}

export const deleteUser = async (userId) => {
  const response = await api.delete(`/users/${userId}`)
  return response.data
}

export const scrape = async (data) => {
  const response = await api.post('/scrape/', data)
  return response.data
}

export const scrapeAsync = async (data) => {
  const response = await api.post('/scrape/async', data)
  return response.data
}

export const scrapeBatch = async (data) => {
  const response = await api.post('/scrape/batch', data)
  return response.data
}

export const testProxy = async (data) => {
  const response = await api.post('/scrape/test-proxy', data)
  return response.data
}

export const getTask = async (taskId) => {
  const response = await api.get(`/tasks/${taskId}`)
  return response.data
}

export const getTasks = async (params) => {
  const response = await api.get('/tasks/', { params })
  return response.data
}

export const deleteTask = async (taskId) => {
  const response = await api.delete(`/tasks/${taskId}`)
  return response.data
}

export const deleteTasksBatch = async (taskIds) => {
  const response = await api.delete('/tasks/batch', { data: { task_ids: taskIds } })
  return response.data
}

export const retryTask = async (taskId, agentModelId, agentParallelEnabled = null, agentParallelBatchSize = null) => {
  const response = await api.post(`/tasks/${taskId}/retry`, null, {
    params: {
      agent_model_id: agentModelId,
      agent_parallel_enabled: agentParallelEnabled,
      agent_parallel_batch_size: agentParallelBatchSize
    }
  })
  return response.data
}

export const getStats = async () => {
  const response = await api.get('/stats/')
  return response.data
}

export const getConfigs = async () => {
  const response = await api.get('/configs/')
  return response.data
}

export const getConfigSchema = async () => {
  const response = await api.get('/configs/schema')
  return response.data
}

export const restartSystem = async () => {
  const response = await api.post('/configs/restart')
  return response.data
}

export const createConfig = async (data) => {
  const response = await api.post('/configs/', data)
  return response.data
}

export const updateConfig = async (key, data) => {
  const response = await api.put(`/configs/${key}`, data)
  return response.data
}

export const deleteConfig = async (key) => {
  const response = await api.delete(`/configs/${key}`)
  return response.data
}

// Node management
export const getNodes = async () => {
  const response = await api.get('/nodes/')
  return response.data
}

export const createNode = async (data) => {
  const response = await api.post('/nodes/', data)
  return response.data
}

export const updateNode = async (nodeId, data) => {
  const response = await api.put(`/nodes/${nodeId}`, data)
  return response.data
}

export const startNode = async (nodeId) => {
  const response = await api.post(`/nodes/${nodeId}/start`)
  return response.data
}

export const stopNode = async (nodeId) => {
  const response = await api.post(`/nodes/${nodeId}/stop`)
  return response.data
}

export const deleteNode = async (nodeId) => {
  const response = await api.delete(`/nodes/${nodeId}`)
  return response.data
}

export const getNodeLogs = (nodeId, params) => {
  return api.get(`/nodes/${nodeId}/logs`, { params, responseType: 'text' })
}

// LLM Models API
export const getLLMModels = async (params) => {
  const response = await api.get('/llm/models', { params })
  return response.data
}

export const getLLMModel = async (modelId) => {
  const response = await api.get(`/llm/models/${modelId}`)
  return response.data
}

export const createLLMModel = async (data) => {
  const response = await api.post('/llm/models', data)
  return response.data
}

export const updateLLMModel = async (modelId, data) => {
  const response = await api.put(`/llm/models/${modelId}`, data)
  return response.data
}

export const deleteLLMModel = async (modelId) => {
  const response = await api.delete(`/llm/models/${modelId}`)
  return response.data
}

export const testLLMModel = async (modelId) => {
  const response = await api.post(`/llm/models/${modelId}/test`)
  return response.data
}

// Prompt Templates API
export const getPromptTemplates = async (params) => {
  const response = await api.get('/prompt-templates', { params })
  return response.data
}

export const getPromptTemplate = async (templateId) => {
  const response = await api.get(`/prompt-templates/${templateId}`)
  return response.data
}

export const createPromptTemplate = async (data) => {
  const response = await api.post('/prompt-templates', data)
  return response.data
}

export const updatePromptTemplate = async (templateId, data) => {
  const response = await api.put(`/prompt-templates/${templateId}`, data)
  return response.data
}

export const deletePromptTemplate = async (templateId) => {
  const response = await api.delete(`/prompt-templates/${templateId}`)
  return response.data
}

// Proxies API
export const getProxies = async (params) => {
  const response = await api.get('/proxies', { params })
  return response.data
}

export const createProxy = async (data) => {
  const response = await api.post('/proxies', data)
  return response.data
}

export const updateProxy = async (proxyId, data) => {
  const response = await api.put(`/proxies/${proxyId}`, data)
  return response.data
}

export const deleteProxy = async (proxyId) => {
  const response = await api.delete(`/proxies/${proxyId}`)
  return response.data
}

export const testStoredProxy = async (proxyId) => {
  const response = await api.post(`/proxies/${proxyId}/test`)
  return response.data
}

// Skills API
export const getSkills = async (params) => {
  const response = await api.get('/skills/', { params })
  return response.data
}

export const getBuiltInSkills = async () => {
  const response = await api.get('/skills/built-in')
  return response.data
}

export const getSkill = async (skillId) => {
  const response = await api.get(`/skills/${skillId}`)
  return response.data
}

export const createSkill = async (data) => {
  const response = await api.post('/skills/', data)
  return response.data
}

export const updateSkill = async (skillId, data) => {
  const response = await api.put(`/skills/${skillId}`, data)
  return response.data
}

export const deleteSkill = async (skillId) => {
  const response = await api.delete(`/skills/${skillId}`)
  return response.data
}

// Skill Bundles API
export const getSkillBundles = async (params) => {
  const response = await api.get('/skill-bundles/', { params })
  return response.data
}

export const getSkillBundle = async (bundleId) => {
  const response = await api.get(`/skill-bundles/${bundleId}`)
  return response.data
}

export const createSkillBundle = async (data) => {
  const response = await api.post('/skill-bundles/', data)
  return response.data
}

export const updateSkillBundle = async (bundleId, data) => {
  const response = await api.put(`/skill-bundles/${bundleId}`, data)
  return response.data
}

export const deleteSkillBundle = async (bundleId) => {
  const response = await api.delete(`/skill-bundles/${bundleId}`)
  return response.data
}
