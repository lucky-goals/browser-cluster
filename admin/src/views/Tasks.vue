<template>
  <div class="tasks-container">
    <el-card class="tasks-card" :body-style="{ padding: '0' }">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="title">{{ $t('tasks.title') }}</span>
            <span class="subtitle">{{ $t('tasks.subtitle') }}</span>
          </div>
          <div class="header-actions">
            <el-button 
              type="danger" 
              plain 
              :disabled="selectedTasks.length === 0"
              @click="confirmBatchDelete"
            >
              <el-icon><DeleteFilled /></el-icon> {{ $t('tasks.batchDelete') }} ({{ selectedTasks.length }})
            </el-button>
            <el-button type="primary" @click="showScrapeDialog = true">
              <el-icon><Plus /></el-icon> {{ $t('tasks.createTask') }}
            </el-button>
            <el-button @click="loadTasks" :loading="loading">
              <el-icon><Refresh /></el-icon> {{ $t('tasks.refresh') }}
            </el-button>
          </div>
        </div>
      </template>

      <div class="filter-bar">
        <el-form :inline="true" :model="filterForm" class="filter-form">
          <el-form-item :label="$t('tasks.columns.status')">
            <el-radio-group v-model="filterForm.status" @change="handleFilter" size="default">
              <el-radio-button label="">{{ $t('tasks.status.all') }}</el-radio-button>
              <el-radio-button label="pending">{{ $t('tasks.status.pending') }}</el-radio-button>
              <el-radio-button label="processing">{{ $t('tasks.status.running') }}</el-radio-button>
              <el-radio-button label="success">{{ $t('tasks.status.success') }}</el-radio-button>
              <el-radio-button label="failed">{{ $t('tasks.status.failed') }}</el-radio-button>
            </el-radio-group>
          </el-form-item>
          
          <el-form-item :label="$t('tasks.search.keyword')">
            <el-input 
              v-model="filterForm.url" 
              :placeholder="$t('tasks.searchPlaceholder')" 
              clearable 
              style="width: 280px"
              @keyup.enter="handleFilter"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-form-item>
          
          <el-form-item>
            <el-button type="primary" @click="handleFilter">{{ $t('tasks.search.query') }}</el-button>
            <el-button @click="resetFilter">{{ $t('tasks.search.reset') }}</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-table 
        :data="tasks" 
        v-loading="loading" 
        style="width: 100%" 
        class="tasks-table" 
        border 
        stripe
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="40" align="center" />
        <el-table-column prop="task_id" :label="$t('tasks.columns.id')" width="250">
          <template #default="{ row }">
            <div class="task-id-row">
              <el-tag size="small"  effect="plain" class="id-tag-simple">
                {{ row.task_id }}
              </el-tag>
              <el-button link type="primary" :icon="CopyDocument" @click="copyToClipboard(row.task_id)" class="copy-btn-mini" />
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="url" :label="$t('tasks.columns.target')" min-width="250">
          <template #default="{ row }">
            <div class="task-url-row">
              <el-tooltip :content="row.url" placement="top" :show-after="500">
                <el-link :href="row.url" target="_blank" class="url-link-bold" :underline="false">
                  <el-icon><Link /></el-icon>
                  <span>{{ row.url }}</span>
                </el-link>
              </el-tooltip>
              <!-- 显示重定向后的实际 URL -->
              <div v-if="row.result?.metadata?.actual_url && row.result.metadata.actual_url !== row.url" class="actual-url-info">
                <el-tooltip :content="$t('tasks.columns.actualUrl') + ': ' + row.result.metadata.actual_url" placement="bottom">
                  <span class="actual-url-text">
                    <el-icon><Right /></el-icon>
                    {{ row.result.metadata.actual_url }}
                  </span>
                </el-tooltip>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="status" :label="$t('tasks.columns.status')" width="140" align="center">
          <template #default="{ row }">
            <div class="status-container">
              <el-tag :type="getStatusType(row.status)" size="default" effect="dark" class="status-tag">
                <div class="status-content">
                  <span class="status-dot-mini" :class="row.status"></span>
                  {{ getStatusText(row.status) }}
                </div>
              </el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column :label="$t('tasks.columns.stats')" width="220">
          <template #default="{ row }">
            <div class="stats-group">
              <div class="stat-item timing-row">
                <el-icon><Timer /></el-icon>
                <span class="label">{{ $t('tasks.stats.duration') }}</span>
                <div class="timing-tags">
                  <el-tooltip :content="$t('tasks.stats.totalDuration')" placement="top">
                    <el-tag size="small" effect="dark" class="time-tag total">
                      {{ row.duration ? row.duration.toFixed(1) + 's' : '-' }}
                    </el-tag>
                  </el-tooltip>
                  <el-tooltip v-if="row.result?.metadata?.load_time" :content="$t('tasks.stats.loadDuration')" placement="top">
                    <el-tag size="small" effect="plain" type="warning" class="time-tag load">
                      <el-icon class="mini-icon"><Loading /></el-icon>
                      {{ row.result.metadata.load_time.toFixed(1) }}s
                    </el-tag>
                  </el-tooltip>
                </div>
              </div>
              <div class="stat-item">
                <el-icon><Cpu /></el-icon>
                <span class="label">{{ $t('tasks.stats.cache') }}</span>
                <el-tag :type="row.cached ? 'success' : 'info'" size="small" effect="light" class="cache-tag">
                  <div class="cache-tag-content">
                    <span>{{ row.cached ? $t('tasks.stats.cacheHit') : $t('tasks.stats.cacheSkip') }}</span>
                    <div v-if="row.cached" class="cache-split-mini">
                      <span v-if="row.html_cached" class="split-dot html" :title="$t('tasks.stats.htmlHit')">H</span>
                      <span v-if="row.agent_cached" class="split-dot ai" :title="$t('tasks.stats.aiHit')">A</span>
                      <span v-else-if="row.result?.agent_result?.cache_hits > 0" class="split-dot partial" :title="`${$t('tasks.stats.partialHit')}: ${row.result.agent_result.cache_hits}/${row.result.agent_result.total_chunks}`">P</span>
                    </div>
                  </div>
                </el-tag>
              </div>
              <div class="stat-item">
                <el-icon><Monitor /></el-icon>
                <span class="label">{{ $t('tasks.stats.node') }}</span>
                <el-tag v-if="row.node_id" :type="getNodeColor(row.node_id)" size="small" effect="light" class="node-tag">
                  {{ row.node_id }}
                </el-tag>
                <span v-else class="empty-text">-</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column :label="$t('tasks.columns.timeline')" width="180">
          <template #default="{ row }">
            <div class="timeline-mini">
              <div class="time-row">
                <span class="dot create"></span>
                <span class="label">{{ $t('tasks.stats.created') }}</span>
                <span class="time">{{ formatTimeOnly(row.created_at) }}</span>
              </div>
              <div class="time-row" v-if="row.completed_at">
                <span class="dot complete"></span>
                <span class="label">{{ $t('tasks.stats.completed') }}</span>
                <span class="time">{{ formatTimeOnly(row.completed_at) }}</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column :label="$t('tasks.columns.actions')" width="160" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip :content="$t('tasks.detail.title')" placement="top">
                <el-button circle size="small" :icon="View" @click="viewTask(row)" />
              </el-tooltip>
              
              <el-tooltip :content="$t('tasks.messages.retryConfirm')" placement="top">
                <el-button 
                  circle 
                  size="small" 
                  type="warning" 
                  :icon="VideoPlay" 
                  @click="confirmRetry(row)"
                  :disabled="row.status === 'pending' || row.status === 'processing'"
                />
              </el-tooltip>

              <el-tooltip :content="$t('common.delete')" placement="top">
                <el-button 
                  circle 
                  size="small" 
                  type="danger" 
                  :icon="DeleteFilled" 
                  @click="confirmDelete(row.task_id)"
                />
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadTasks"
          @current-change="loadTasks"
        />
      </div>
    </el-card>

    <!-- 新建任务对话框 -->
    <el-dialog 
      v-model="showScrapeDialog" 
      :title="$t('tasks.createDialog.title')" 
      width="1000px" 
      destroy-on-close 
      top="3vh"
      class="bento-dialog task-create-dialog"
    >
      <el-form :model="scrapeForm" label-width="100px" label-position="top">
        <!-- 顶部固定区域：基础配置 -->
        <el-card shadow="never" class="basic-config-card">
          <el-row :gutter="20">
            <el-col :span="18">
              <el-form-item :label="$t('tasks.createDialog.targetUrl')" required class="mb-0">
                <el-input v-model="scrapeForm.url" placeholder="https://example.com" clearable>
                  <template #prefix><el-icon><Connection /></el-icon></template>
                </el-input>
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item :label="$t('tasks.createDialog.priority')" class="mb-0">
                <el-select v-model="scrapeForm.priority" style="width: 100%">
                  <el-option :label="$t('tasks.createDialog.priorityHigh')" :value="10" />
                  <el-option :label="$t('tasks.createDialog.priorityNormal')" :value="5" />
                  <el-option :label="$t('tasks.createDialog.priorityLow')" :value="1" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20" style="margin-top: 10px;">
            <el-col :span="8">
              <el-form-item :label="$t('tasks.createDialog.cache')" class="mb-0">
                <div class="compact-switch-wrapper">
                  <el-switch v-model="scrapeForm.cache.enabled" />
                  <span class="status-text">{{ scrapeForm.cache.enabled ? $t('tasks.createDialog.cacheEnabled') : $t('tasks.createDialog.cacheDisabled') }}</span>
                </div>
              </el-form-item>
            </el-col>
            <el-col :span="16" v-if="scrapeForm.cache.enabled">
              <el-form-item :label="$t('tasks.createDialog.cacheTTL')" class="mb-0">
                <el-input-number v-model="scrapeForm.cache.ttl" :min="60" :step="60" style="width: 200px" />
              </el-form-item>
            </el-col>
          </el-row>
        </el-card>

        <!-- 底部 Tab 区域 -->
        <div class="scrape-tabs-container">
          <el-tabs v-model="scrapeActiveTab" type="border-card">
            <!-- Tab 1: 浏览器配置 -->
            <el-tab-pane name="browser">
              <template #label>
                <div class="tab-label">
                  <el-icon><Monitor /></el-icon>
                  <span>{{ $t('tasks.createDialog.tabs.browser') }}</span>
                </div>
              </template>
              
              <div class="tab-content-grid">
                <!-- 加载策略 -->
                <div class="config-section">
                  <div class="section-title">{{ $t('tasks.createDialog.browser.strategy') }}</div>
                  <el-form-item :label="$t('tasks.createDialog.browser.waitFor')">
                    <el-select v-model="scrapeForm.params.wait_for" style="width: 100%" :teleported="false">
                      <el-option label="Network Idle" value="networkidle" />
                      <el-option label="Page Load" value="load" />
                      <el-option label="DOM Ready" value="domcontentloaded" />
                    </el-select>
                  </el-form-item>
                  <el-row :gutter="15">
                    <el-col :span="12">
                      <el-form-item :label="$t('tasks.createDialog.browser.timeout')">
                        <el-input-number v-model="scrapeForm.params.timeout" :min="5000" :step="5000" style="width: 100%" controls-position="right" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item :label="$t('tasks.createDialog.browser.waitTime')">
                        <el-input-number v-model="scrapeForm.params.wait_time" :min="0" :step="500" style="width: 100%" controls-position="right" />
                      </el-form-item>
                    </el-col>
                  </el-row>
                </div>

                <!-- 环境模拟 -->
                <div class="config-section">
                  <div class="section-title">{{ $t('tasks.createDialog.browser.emulation') }}</div>
                  <el-form-item :label="$t('tasks.createDialog.browser.viewport')">
                    <div class="viewport-group">
                      <el-input-number v-model="scrapeForm.params.viewport.width" :min="320" controls-position="right" />
                      <span class="v-sep">×</span>
                      <el-input-number v-model="scrapeForm.params.viewport.height" :min="240" controls-position="right" />
                    </div>
                  </el-form-item>
                  <div class="feature-grid mini">
                    <div class="feature-cell">
                      <span class="label">{{ $t('tasks.createDialog.browser.stealth') }}</span>
                      <el-switch v-model="scrapeForm.params.stealth" size="small" />
                    </div>
                    <div class="feature-cell">
                      <span class="label">{{ $t('tasks.createDialog.browser.screenshot') }}</span>
                      <el-switch v-model="scrapeForm.params.screenshot" size="small" />
                    </div>
                    <div class="feature-cell" v-if="scrapeForm.params.screenshot">
                      <span class="label">{{ $t('tasks.createDialog.browser.fullPage') }}</span>
                      <el-switch v-model="scrapeForm.params.is_fullscreen" size="small" />
                    </div>
                    <div class="feature-cell">
                      <span class="label">{{ $t('tasks.createDialog.browser.noImage') }}</span>
                      <el-switch v-model="scrapeForm.params.block_images" size="small" />
                    </div>
                  </div>
                </div>
              </div>
            </el-tab-pane>

            <!-- Tab 2: 高级选项 -->
            <el-tab-pane name="proxy">
              <template #label>
                <div class="tab-label">
                  <el-icon><Lock /></el-icon>
                  <span>{{ $t('tasks.createDialog.tabs.advanced') }}</span>
                </div>
              </template>
              
              <div class="tab-content-flex">
                <div class="config-section">
                  <div class="section-title">{{ $t('tasks.createDialog.advanced.proxy') }}</div>
                  <el-form-item :label="$t('tasks.createDialog.advanced.proxy') + ' (' + $t('tasks.createDialog.advanced.optional') + ')'" label-position="top">
                    <div style="display: flex; gap: 12px; width: 100%;">
                      <el-input v-model="scrapeForm.params.proxy.server" :placeholder="$t('tasks.createDialog.advanced.proxyPlaceholder')" clearable style="flex: 1" />
                      <el-button 
                        type="primary" 
                        plain 
                        :icon="Refresh" 
                        :loading="testingProxy"
                        @click="handleTestProxy"
                        style="width: 100px"
                      >
                        {{ $t('tasks.createDialog.advanced.test') }}
                      </el-button>
                      <el-button 
                        type="info" 
                        plain 
                        :icon="Connection" 
                        @click="showProxySelector"
                        style="width: 120px"
                      >
                        {{ $t('tasks.createDialog.advanced.pool') }}
                      </el-button>
                    </div>
                  </el-form-item>
                  <el-row :gutter="15" style="margin-top: 5px;">
                    <el-col :span="18">
                      <el-form-item :label="$t('tasks.createDialog.advanced.username')">
                        <el-input v-model="scrapeForm.params.proxy.username" :placeholder="$t('tasks.createDialog.advanced.optional')" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="6">
                      <el-form-item :label="$t('tasks.createDialog.advanced.password')">
                        <el-input v-model="scrapeForm.params.proxy.password" type="password" :placeholder="$t('tasks.createDialog.advanced.optional')" show-password />
                      </el-form-item>
                    </el-col>
                  </el-row>
                </div>
 
                <div class="config-section">
                  <div class="section-title">{{ $t('tasks.createDialog.advanced.interceptor') }}</div>
                  <el-form-item :label="$t('tasks.createDialog.advanced.pattern')">
                    <el-select
                      v-model="scrapeForm.params.intercept_apis"
                      multiple
                      filterable
                      allow-create
                      collapse-tags
                      :placeholder="$t('tasks.createDialog.advanced.patternPlaceholder')"
                      style="width: 100%"
                    />
                  </el-form-item>
                  <div class="form-tip">{{ $t('tasks.createDialog.advanced.patternTip') }}</div>
                </div>
              </div>
            </el-tab-pane>

            <!-- Tab 3: Agent AI -->
            <el-tab-pane name="agent">
              <template #label>
                <div class="tab-label">
                  <el-icon><MagicStick /></el-icon>
                  <span>{{ $t('tasks.createDialog.tabs.agent') }}</span>
                </div>
              </template>
              
              <div class="agent-tab-content">
                <div class="agent-header-row">
                  <div class="section-title">{{ $t('tasks.createDialog.agent.title') }}</div>
                  <div class="agent-enable-switch">
                    <span class="switch-label">{{ $t('tasks.createDialog.agent.enable') }}</span>
                    <el-switch v-model="scrapeForm.params.agent_enabled" />
                  </div>
                </div>

                <div v-if="scrapeForm.params.agent_enabled" class="agent-config-body">
                  <el-row :gutter="20">
                    <el-col :span="8">
                      <el-form-item :label="$t('tasks.createDialog.agent.model')" required>
                        <el-select v-model="scrapeForm.params.agent_model_id" style="width: 100%" :placeholder="$t('tasks.createDialog.agent.model')">
                          <el-option
                            v-for="model in llmModels"
                            :key="model._id"
                            :label="model.name"
                            :value="model._id"
                          >
                            <div style="display: flex; align-items: center; gap: 8px;">
                              <el-tag size="small" type="info" effect="plain">{{ model.provider }}</el-tag>
                              <span>{{ model.name }}</span>
                              <el-tag v-if="model.supports_vision" size="small" type="success" effect="plain">视觉</el-tag>
                            </div>
                          </el-option>
                        </el-select>
                      </el-form-item>
                    </el-col>
                    <el-col :span="8">
                      <el-form-item :label="$t('tasks.createDialog.agent.parallel')">
                        <div style="display: flex; align-items: center; gap: 10px;">
                          <el-switch v-model="scrapeForm.params.agent_parallel_enabled" />
                          <el-input-number 
                            v-if="scrapeForm.params.agent_parallel_enabled" 
                            v-model="scrapeForm.params.agent_parallel_batch_size" 
                            :min="1" 
                            :max="50" 
                            size="small" 
                            style="width: 100px" 
                          />
                        </div>
                      </el-form-item>
                    </el-col>
                    <el-col :span="8">
                      <el-form-item :label="$t('tasks.createDialog.agent.template')">
                        <div class="template-select-row">
                          <el-select
                            v-model="selectedTemplateId"
                            filterable
                            clearable
                            :filter-method="filterTemplates"
                            :loading="templateLoading"
                            :placeholder="$t('tasks.createDialog.agent.templatePlaceholder')"
                            popper-class="template-select-dropdown"
                            style="flex: 1; margin-right: 8px;"
                            @change="applyTemplate"
                            @visible-change="handleTemplateDropdownVisible"
                          >
                            <el-option
                              v-for="tpl in filteredTemplates"
                              :key="tpl._id"
                              :label="tpl.name"
                              :value="tpl._id"
                            >
                              <div class="template-option">
                                <span class="template-option-name">{{ tpl.name }}</span>
                                <span class="template-option-preview">{{ tpl.content.substring(0, 30) }}...</span>
                              </div>
                            </el-option>
                          </el-select>
                          <el-button size="default" @click="loadAllTemplates" :icon="Refresh" circle />
                        </div>
                      </el-form-item>
                    </el-col>
                  </el-row>
                  
                  <el-form-item :label="$t('tasks.createDialog.agent.systemPrompt')">
                    <el-input
                      v-model="scrapeForm.params.agent_system_prompt"
                      type="textarea"
                      :rows="4"
                      :placeholder="$t('tasks.createDialog.agent.systemPromptPlaceholder')"
                    />
                  </el-form-item>
 
                  <el-form-item :label="$t('tasks.createDialog.agent.prompt')" required>
                    <el-input
                      v-model="scrapeForm.params.agent_prompt"
                      type="textarea"
                      :rows="6"
                      :placeholder="$t('tasks.createDialog.agent.promptPlaceholder')"
                    />
                  </el-form-item>
                </div>
                
                <div v-else class="agent-disabled-placeholder">
                  <el-icon><InfoFilled /></el-icon>
                  <p>{{ $t('tasks.createDialog.agent.disabledDesc') }}</p>
                  <el-button type="primary" plain @click="scrapeForm.params.agent_enabled = true">{{ $t('tasks.createDialog.agent.enableBtn') }}</el-button>
                </div>
              </div>
            </el-tab-pane>
            <!-- Tab 4: 交互步骤 (Skills) -->
            <el-tab-pane name="skills">
              <template #label>
                <div class="tab-label">
                  <el-icon><Pointer /></el-icon>
                  <span>{{ $t('tasks.createDialog.tabs.skills') }}</span>
                </div>
              </template>
              
              <div class="skills-tab-content">
                <div class="agent-header-row">
                  <div class="section-title">{{ $t('tasks.createDialog.skills.title') }}</div>
                  <div class="header-right-actions">
                    <el-select
                      v-model="selectedBundleId"
                      :placeholder="$t('tasks.createDialog.skills.applyBundle')"
                      size="small"
                      style="width: 180px; margin-right: 12px;"
                      @change="applySkillBundle"
                    >
                      <el-option
                        v-for="bundle in skillBundles"
                        :key="bundle._id || bundle.id"
                        :label="bundle.name"
                        :value="bundle._id || bundle.id"
                      />
                    </el-select>
                    <el-button type="primary" link @click="addInteractionStep">
                      <el-icon><Plus /></el-icon> {{ $t('tasks.createDialog.skills.addStep') }}
                    </el-button>
                  </div>
                </div>

                <div v-if="scrapeForm.params.interaction_steps?.length" class="skills-list">
                  <div v-for="(step, index) in scrapeForm.params.interaction_steps" :key="index" class="skill-step-item">
                    <div class="step-index">{{ index + 1 }}</div>
                    
                    <el-select v-model="step.action" :placeholder="$t('tasks.createDialog.advanced.optional')" style="width: 140px" @change="resetStepParams(index)">
                      <el-option
                         v-for="skill in builtInSkills"
                         :key="skill.name"
                         :label="skill.display_name"
                         :value="skill.name"
                       />
                       <el-divider v-if="customSkills.length" content-position="center">{{ $t('common.tip') }}</el-divider>
                       <el-option
                         v-for="skill in customSkills"
                         :key="skill.name"
                         :label="`${skill.display_name} (${skill.name})`"
                         :value="skill.name"
                       />
                     </el-select>

                    <div class="step-params-config">
                      <!-- 基础滚动参数 -->
                      <template v-if="step.action === 'scroll'">
                        <el-input v-model="step.params.selector" :placeholder="$t('tasks.createDialog.skills.params.container')" size="small" style="width: 180px" />
                        <el-input-number v-model="step.params.distance" :step="100" :placeholder="$t('tasks.createDialog.skills.params.distance')" size="small" style="width: 100px" />
                      </template>
 
                      <!-- 流式滚动参数 -->
                      <template v-if="step.action === 'infinite_scroll'">
                        <el-input v-model="step.params.selector" :placeholder="$t('tasks.createDialog.skills.params.container')" size="small" style="width: 180px" />
                        <el-input-number v-model="step.params.max_scrolls" :min="1" :max="50" :placeholder="$t('tasks.createDialog.skills.params.maxScrolls')" size="small" style="width: 100px" />
                        <el-input-number v-model="step.params.delay" :min="500" :step="500" :placeholder="$t('tasks.createDialog.skills.params.delay')" size="small" style="width: 110px" />
                      </template>
 
                      <!-- 点击参数 -->
                      <template v-if="step.action === 'click'">
                        <el-input v-model="step.params.selector" :placeholder="$t('tasks.createDialog.skills.params.selector')" size="small" style="width: 250px" />
                      </template>
 
                      <!-- 翻页参数 -->
                      <template v-if="step.action === 'pagination'">
                        <el-select v-model="step.params.action" size="small" style="width: 100px">
                          <el-option :label="$t('tasks.createDialog.skills.params.next')" value="next" />
                          <el-option :label="$t('tasks.createDialog.skills.params.prev')" value="prev" />
                        </el-select>
                        <el-input v-model="step.params.selector" :placeholder="$t('tasks.createDialog.skills.params.btnSelector')" size="small" style="width: 180px" />
                      </template>
 
                      <!-- 填充参数 -->
                      <template v-if="step.action === 'fill'">
                        <el-button type="info" plain size="small" @click="addFillPair(index)">{{ $t('tasks.createDialog.skills.params.addField') }}</el-button>
                        <div v-if="Object.keys(step.params.data || {}).length" class="fill-data-preview">
                          {{ $t('tasks.createDialog.skills.params.fieldsCount', { n: Object.keys(step.params.data).length }) }}
                        </div>
                      </template>
 
                      <!-- 缩放参数 -->
                      <template v-if="step.action === 'zoom'">
                        <el-input v-model="step.params.selector" :placeholder="$t('tasks.createDialog.skills.params.selector')" size="small" style="width: 150px" />
                        <el-select v-model="step.params.direction" size="small" style="width: 80px">
                          <el-option :label="$t('tasks.createDialog.skills.params.in')" value="in" />
                          <el-option :label="$t('tasks.createDialog.skills.params.out')" value="out" />
                        </el-select>
                        <el-input-number v-model="step.params.times" :min="1" :max="10" size="small" style="width: 90px" />
                      </template>

                      <!-- 等待参数 -->
                       <template v-if="step.action === 'wait'">
                         <el-input-number v-model="step.params.duration" :min="100" :step="500" placeholder="ms" size="small" style="width: 120px" />
                       </template>

                       <!-- 提取配置技能 -->
                       <template v-if="step.action === 'block_container'">
                         <el-input v-model="step.params.selector" :placeholder="$t('tasks.createDialog.skills.params.blockSelector')" size="small" style="width: 250px" />
                       </template>
                       <template v-if="step.action === 'exclude_elements'">
                         <el-input v-model="step.params.selectors" :placeholder="$t('tasks.createDialog.skills.params.excludeSelectors')" size="small" style="width: 350px" />
                       </template>
                     </div>

                    <el-button type="danger" link @click="removeInteractionStep(index)">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                </div>

                <div v-else class="agent-disabled-placeholder mini">
                  <p>{{ $t('tasks.createDialog.skills.desc') }}</p>
                  <el-button type="primary" plain size="small" @click="addInteractionStep">{{ $t('tasks.createDialog.skills.firstStep') }}</el-button>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </el-form>
 
      <template #footer>
        <div class="bento-footer">
          <el-button @click="showScrapeDialog = false" round>{{ $t('tasks.createDialog.cancel') }}</el-button>
          <el-button type="primary" @click="submitTask" :loading="loading" class="bento-submit" round>
            <el-icon><Promotion /></el-icon>
            <span>{{ $t('tasks.createDialog.submit') }}</span>
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 任务详情对话框 -->
    <el-dialog v-model="showTaskDialog" :title="$t('tasks.detail.title')" width="900px" top="5vh">
      <div v-if="currentTask" class="task-details">
        <el-tabs v-model="activeTab">
          <el-tab-pane :label="$t('tasks.detail.tabs.info')" name="info">
            <el-descriptions :column="2" border size="default" class="detail-descriptions">
              <el-descriptions-item :label="$t('tasks.detail.info.id')">{{ currentTask.task_id }}</el-descriptions-item>
              <el-descriptions-item :label="$t('tasks.detail.info.status')">
                <el-tag :type="getStatusType(currentTask.status)" size="default">{{ getStatusText(currentTask.status) }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item :label="$t('tasks.detail.info.url')" :span="2">
                <el-link :href="currentTask.url" target="_blank" type="primary" class="detail-url-link">{{ currentTask.url }}</el-link>
              </el-descriptions-item>
              <el-descriptions-item :label="$t('tasks.detail.info.created')">{{ formatDate(currentTask.created_at) }}</el-descriptions-item>
              <el-descriptions-item :label="$t('tasks.detail.info.completed')">{{ formatDate(currentTask.completed_at) || '-' }}</el-descriptions-item>
              <el-descriptions-item :label="$t('tasks.detail.info.cache')">
                <div class="cache-info-detail">
                  <el-tag :type="currentTask.cached ? 'success' : 'info'" size="default">
                    {{ currentTask.cached ? $t('tasks.detail.info.hit') : $t('tasks.detail.info.miss') }}
                  </el-tag>
                  <div v-if="currentTask.cached" class="cache-split-details">
                    <el-tag v-if="currentTask.html_cached" type="success" size="small" effect="plain" class="split-tag">
                      {{ $t('tasks.stats.htmlHit') }}
                    </el-tag>
                    <el-tag v-if="currentTask.agent_cached" type="success" size="small" effect="plain" class="split-tag">
                      {{ $t('tasks.stats.aiHit') }}
                    </el-tag>
                    <el-tooltip v-else-if="currentTask.result?.agent_result?.cache_hits > 0" 
                                :content="`${$t('tasks.stats.partialHit')}: ${currentTask.result.agent_result.cache_hits}/${currentTask.result.agent_result.total_chunks}`" 
                                placement="top">
                      <el-tag type="warning" size="small" effect="plain" class="split-tag">
                        {{ $t('tasks.stats.partialHit') }}
                      </el-tag>
                    </el-tooltip>
                  </div>
                </div>
              </el-descriptions-item>
              <el-descriptions-item :label="$t('tasks.detail.info.node')">{{ currentTask.node_id || '-' }}</el-descriptions-item>
              <el-descriptions-item :label="$t('tasks.detail.info.proxy')" v-if="currentTask.params?.proxy" :span="2">
                <div class="proxy-info-detail">
                  <div class="proxy-line">
                    <span class="p-label">{{ $t('tasks.detail.info.server') }}</span>
                    <el-tag type="warning" effect="plain" size="small">
                      <el-icon><Connection /></el-icon> {{ currentTask.params.proxy.server }}
                    </el-tag>
                  </div>
                  <div class="proxy-line" v-if="currentTask.params.proxy.username">
                    <span class="p-label">{{ $t('tasks.detail.info.user') }}</span>
                    <code class="p-user">{{ currentTask.params.proxy.username }}</code>
                  </div>
                </div>
              </el-descriptions-item>
            </el-descriptions>
 
            <div v-if="currentTask.result" class="metadata-section">
              <el-divider content-position="left">{{ $t('tasks.detail.metadata.title') }}</el-divider>
              <el-descriptions :column="2" border size="default" class="detail-descriptions">
                <el-descriptions-item :label="$t('tasks.detail.metadata.pageTitle')" :span="2" width="120px">{{ currentTask.result.metadata?.title || '-' }}</el-descriptions-item>
                <el-descriptions-item :label="$t('tasks.detail.metadata.actualUrl')" :span="2" v-if="currentTask.result.metadata?.actual_url">
                  <el-link :href="currentTask.result.metadata.actual_url" target="_blank" type="success" class="detail-url-link">
                    {{ currentTask.result.metadata.actual_url }}
                  </el-link>
                </el-descriptions-item>
                <el-descriptions-item :label="$t('tasks.detail.metadata.loadTime')">
                  <el-tag type="warning" effect="plain" size="default">
                    {{ currentTask.result.metadata?.load_time?.toFixed(2) }}s
                  </el-tag>
                </el-descriptions-item>
              </el-descriptions>
            </div>
 
            <div v-if="currentTask.error" class="error-section">
              <el-divider content-position="left">{{ $t('tasks.detail.error') }}</el-divider>
              <el-alert :title="currentTask.error.message" type="error" :closable="false" show-icon>
                <template #default>
                  <pre class="error-stack">{{ currentTask.error.stack }}</pre>
                </template>
              </el-alert>
            </div>
          </el-tab-pane>
 
          <el-tab-pane :label="$t('tasks.detail.tabs.intercept')" name="intercept" v-if="currentTask.result?.intercepted_apis">
            <div v-for="(requests, pattern) in currentTask.result.intercepted_apis" :key="pattern" class="intercept-group">
              <div class="pattern-header">
                <el-tag size="small">{{ $t('tasks.detail.intercept.pattern', { pattern: pattern }) }}</el-tag>
                <span class="count">{{ $t('tasks.detail.intercept.count', { count: requests.length }) }}</span>
              </div>
              <el-collapse>
                <el-collapse-item v-for="(req, index) in requests" :key="index" :title="`${req.method} ${req.url.substring(0, 80)}...`">
                  <div class="req-detail">
                    <p><strong>{{ $t('tasks.detail.intercept.fullUrl') }}</strong> {{ req.url }}</p>
                    <p><strong>{{ $t('tasks.detail.intercept.status') }}</strong> <el-tag :type="req.status < 400 ? 'success' : 'danger'" size="small">{{ req.status }}</el-tag></p>
                    <div class json-box>
                      <strong>{{ $t('tasks.detail.intercept.content') }}</strong>
                      <pre>{{ formatJSON(req.content) }}</pre>
                    </div>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </el-tab-pane>
 
          <el-tab-pane :label="$t('tasks.detail.tabs.screenshot')" name="screenshot" v-if="currentTask.result?.screenshot">
            <div class="screenshot-container">
              <el-image 
                :src="'data:image/png;base64,' + currentTask.result.screenshot" 
                :preview-src-list="['data:image/png;base64,' + currentTask.result.screenshot]"
                fit="contain"
              >
                <template #error>
                  <div class="image-slot">
                    <el-icon><picture /></el-icon>
                  </div>
                </template>
              </el-image>
            </div>
          </el-tab-pane>
 
          <el-tab-pane :label="$t('tasks.detail.tabs.html')" name="html" v-if="currentTask.result?.html">
            <div class="html-container">
              <pre><code>{{ currentTask.result.html }}</code></pre>
            </div>
          </el-tab-pane>
 
          <el-tab-pane :label="$t('tasks.detail.tabs.agent')" name="agent" v-if="currentTask.result?.agent_result">
            <div class="agent-result-section">
              <!-- 状态概览 -->
              <el-descriptions :column="3" border size="small" class="agent-status-desc">
                <el-descriptions-item :label="$t('tasks.detail.agent.status')">
                  <el-tag :type="getAgentStatusType(currentTask.result.agent_result.status)" effect="dark">
                    {{ getAgentStatusText(currentTask.result.agent_result.status) }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item :label="$t('tasks.detail.agent.model')">
                  <span v-if="currentTask.result.agent_result.model_name">{{ currentTask.result.agent_result.model_name }}</span>
                  <code v-else-if="currentTask.result.agent_result.model_id" style="font-size: 12px; color: #64748b;">{{ currentTask.result.agent_result.model_id }}</code>
                  <span v-else>-</span>
                </el-descriptions-item>
                <el-descriptions-item :label="$t('tasks.detail.agent.duration')">
                  <el-tag type="warning" effect="plain" v-if="currentTask.result.agent_result.processing_time">
                    {{ currentTask.result.agent_result.processing_time.toFixed(2) }}s
                  </el-tag>
                  <span v-else>-</span>
                </el-descriptions-item>
                <el-descriptions-item :label="$t('tasks.detail.agent.parallel')" v-if="currentTask.result.agent_result.parallel_info">
                  <el-tag type="success" size="small" effect="plain">
                    {{ $t('tasks.detail.agent.chunks', { n: currentTask.result.agent_result.parallel_info.chunks }) }}
                    ({{ $t('tasks.detail.agent.batch', { n: currentTask.result.agent_result.parallel_info.batch_size }) }})
                  </el-tag>
                </el-descriptions-item>
              </el-descriptions>
 
              <!-- Token 使用量 -->
              <div v-if="currentTask.result.agent_result.token_usage" class="token-usage-row">
                <el-tag type="info" effect="plain" size="small">
                  Prompt: {{ currentTask.result.agent_result.token_usage.prompt_tokens || 0 }}
                </el-tag>
                <el-tag type="info" effect="plain" size="small">
                  Completion: {{ currentTask.result.agent_result.token_usage.completion_tokens || 0 }}
                </el-tag>
                <el-tag type="primary" effect="plain" size="small">
                  {{ $t('tasks.detail.agent.tokens') }}: {{ currentTask.result.agent_result.token_usage.total_tokens || 0 }} tokens
                </el-tag>
              </div>

              <!-- 错误信息 -->
              <el-alert 
                v-if="currentTask.result.agent_result.error" 
                :title="currentTask.result.agent_result.error" 
                type="error" 
                :closable="false" 
                show-icon
                style="margin-top: 15px;"
              />

              <!-- 提取结果表格 -->
              <div v-if="currentTask.result.agent_result.extracted_items?.length" class="extracted-results">
                <el-divider content-position="left">
                  <el-icon><Grid /></el-icon> 提取结果 ({{ currentTask.result.agent_result.extracted_items.length }} 条)
                </el-divider>
                <el-table :data="currentTask.result.agent_result.extracted_items" border stripe max-height="300" size="small">
                  <el-table-column 
                    v-for="(value, key) in currentTask.result.agent_result.extracted_items[0]" 
                    :key="key" 
                    :prop="key" 
                    :label="key"
                    min-width="120"
                    show-overflow-tooltip
                  />
                </el-table>
                
                <div class="agent-actions">
                  <el-button size="small" type="primary" @click="copyAgentJSON" :icon="DocumentCopy">
                    复制 JSON
                  </el-button>
                  <el-button size="small" type="success" @click="exportAgentExcel" :icon="Download">
                    导出 Excel
                  </el-button>
                </div>
              </div>

              <!-- 提示词折叠区域 -->
              <el-collapse v-model="activeCollapsePrompt" class="prompt-collapse" style="margin-top: 15px;">
                <!-- 系统提示词 -->
                <el-collapse-item name="system" v-if="currentTask.result.agent_result.system_prompt">
                  <template #title>
                    <div class="collapse-title">
                      <el-icon><Monitor /></el-icon>
                      <span>系统提示词</span>
                    </div>
                  </template>
                  <div class="prompt-content system">
                    <pre>{{ currentTask.result.agent_result.system_prompt }}</pre>
                  </div>
                </el-collapse-item>

                <!-- 提取要求（用户提示词） -->
                <el-collapse-item name="user" v-if="currentTask.result.agent_result.user_prompt">
                  <template #title>
                    <div class="collapse-title">
                      <el-icon><EditPen /></el-icon>
                      <span>提取要求 (用户提示词)</span>
                    </div>
                  </template>
                  <div class="prompt-content">
                    <pre>{{ currentTask.result.agent_result.user_prompt }}</pre>
                  </div>
                  <el-button 
                    size="small" 
                    type="warning" 
                    @click.stop="showSaveTemplateDialog"
                    style="margin-top: 10px;"
                  >
                    <el-icon><Collection /></el-icon> 保存为模板
                  </el-button>
                </el-collapse-item>
              </el-collapse>

              <!-- 原始响应 -->
              <el-collapse v-if="currentTask.result.agent_result.raw_response" style="margin-top: 15px;">
                <el-collapse-item title="原始响应" name="raw">
                  <pre class="raw-response">{{ currentTask.result.agent_result.raw_response }}</pre>
                </el-collapse-item>
              </el-collapse>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>

    <!-- 保存为模板对话框 -->
    <el-dialog v-model="showSaveTemplateDialogVisible" title="保存为模板" width="500px">
      <el-form :model="saveTemplateForm" label-width="80px">
        <el-form-item label="模板名称" required>
          <el-input v-model="saveTemplateForm.name" placeholder="请输入模板名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input 
            v-model="saveTemplateForm.description" 
            type="textarea" 
            :rows="2" 
            placeholder="可选：简要描述此模板的用途" 
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSaveTemplateDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmSaveTemplate">保存</el-button>
      </template>
    </el-dialog>

    <!-- 重试任务对话框 -->
    <el-dialog v-model="showRetryDialog" title="重试任务" width="500px">
      <el-form :model="retryForm" label-width="120px">
        <el-form-item label="当前任务">
          <div class="task-info-mini">
            <div class="id-row">ID: <code>{{ retryForm.taskId }}</code></div>
            <div class="url-row" :title="retryForm.url">URL: {{ retryForm.url }}</div>
          </div>
        </el-form-item>
        
        <el-form-item label="Agent 模型" v-if="retryForm.agentEnabled">
          <el-select v-model="retryForm.agentModelId" style="width: 100%" placeholder="更改使用的模型 (可选)">
            <el-option
              v-for="model in llmModels"
              :key="model._id"
              :label="model.name"
              :value="model._id"
            >
              <div style="display: flex; align-items: center; gap: 8px;">
                <el-tag size="small" type="info" effect="plain">{{ model.provider }}</el-tag>
                <span>{{ model.name }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="块状并行" v-if="retryForm.agentEnabled">
          <div style="display: flex; align-items: center; gap: 10px;">
            <el-switch v-model="retryForm.agentParallelEnabled" />
            <el-input-number 
              v-if="retryForm.agentParallelEnabled" 
              v-model="retryForm.agentParallelBatchSize" 
              :min="1" 
              :max="50" 
              size="small" 
              style="width: 100px" 
            />
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRetryDialog = false">取消</el-button>
        <el-button type="primary" @click="handleRetry">确定重试</el-button>
      </template>
    </el-dialog>

    <!-- 代理选择对话框 -->
    <el-dialog
      v-model="proxyDialogVisible"
      title="从代理池选择"
      width="800px"
      class="proxy-selector-dialog"
      destroy-on-close
    >
      <div class="selector-header" style="margin-bottom: 20px; display: flex; gap: 10px;">
        <el-input
          v-model="proxySearch"
          placeholder="搜索名称、服务器、城市..."
          clearable
          prefix-icon="Search"
          style="width: 300px"
          @clear="loadProxyPool"
          @keyup.enter="loadProxyPool"
        />
        <el-button type="primary" :icon="Search" @click="loadProxyPool">查询</el-button>
      </div>

      <el-table :data="proxyPool" v-loading="proxyLoading" border stripe size="small">
        <el-table-column prop="name" label="代理名称" min-width="120" />
        <el-table-column prop="server" label="服务器地址" min-width="180">
          <template #default="{ row }">
            <code>{{ row.server }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="location" label="地理位置" width="150" />
        <el-table-column prop="session_type" label="会话" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.session_type === 'sticky' ? '粘性' : '随机' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleSelectProxy(row)">选择</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container" style="margin-top: 20px; display: flex; justify-content: flex-end;">
        <el-pagination
          v-model:current-page="proxyPage"
          v-model:page-size="proxyPageSize"
          :total="proxyTotal"
          layout="total, prev, pager, next"
          @current-change="loadProxyPool"
        />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { 
  Plus, 
  Refresh, 
  Search, 
  DeleteFilled, 
  View, 
  VideoPlay, 
  CopyDocument, 
  Link, 
  Right, 
  Timer, 
  Loading, 
  Cpu, 
  Monitor, 
  InfoFilled, 
  Pointer, 
  Promotion,
  Picture, WarningFilled, Setting, Connection, MagicStick, Download, DocumentCopy, Grid, EditPen, Collection
} from '@element-plus/icons-vue'
import { getTasks, deleteTask as deleteTaskApi, getTask, scrapeAsync, retryTask, deleteTasksBatch, getLLMModels, getPromptTemplates, createPromptTemplate, testProxy, getProxies, getSkillBundles, getSkills as getCustomSkills, getBuiltInSkills } from '../api'
import dayjs from 'dayjs'

const { t } = useI18n()
const router = useRouter()

const loading = ref(false)
const tasks = ref([])
const llmModels = ref([])
const selectedTasks = ref([])
const testingProxy = ref(false)
const builtInSkills = ref([])
const customSkills = ref([])

const handleTestProxy = async () => {
  if (!scrapeForm.value.params.proxy.server) {
    ElMessage.warning('请先输入代理服务器地址')
    return
  }

  testingProxy.value = true
  try {
    const result = await testProxy({
      proxy: scrapeForm.value.params.proxy
    })
    
    if (result.status === 'success') {
      ElMessage({
        message: `代理测试成功！(耗时: ${result.latency}s, 状态码: ${result.status_code})`,
        type: 'success',
        duration: 5000
      })
    } else {
      ElMessageBox.alert(result.message, '代理测试失败', {
        confirmButtonText: '确定',
        type: 'error',
        dangerouslyUseHTMLString: true
      })
    }
  } catch (error) {
    ElMessage.error('测试接口调用失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    testingProxy.value = false
  }
}
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const activeTab = ref('info')
const scrapeActiveTab = ref('browser') // 新建任务对话框的当前 Tab
const activeCollapsePrompt = ref([]) // 任务详情中提示词的折叠状态

// Prompt Templates
const promptTemplates = ref([])
const filteredTemplates = ref([])
const selectedTemplateId = ref(null)
const templateLoading = ref(false)

// Skill Bundles
const skillBundles = ref([])
const bundleLoading = ref(false)
const selectedBundleId = ref(null)

const showSaveTemplateDialogVisible = ref(false)
const saveTemplateForm = ref({ name: '', description: '' })

const filterForm = ref({
  status: '',
  url: ''
})

const handleFilter = () => {
  currentPage.value = 1
  loadTasks()
}

const handleSelectionChange = (val) => {
  selectedTasks.value = val
}

// Proxy Pool Selector
const proxyDialogVisible = ref(false)
const proxyLoading = ref(false)
const proxyPool = ref([])
const proxyTotal = ref(0)
const proxyPage = ref(1)
const proxyPageSize = ref(10)
const proxySearch = ref('')

const loadProxyPool = async () => {
  proxyLoading.value = true
  try {
    const params = {
      skip: (proxyPage.value - 1) * proxyPageSize.value,
      limit: proxyPageSize.value,
      search: proxySearch.value || undefined
    }
    const data = await getProxies(params)
    proxyPool.value = data.items
    proxyTotal.value = data.total
  } catch (error) {
    ElMessage.error('加载代理池失败')
  } finally {
    proxyLoading.value = false
  }
}

const showProxySelector = () => {
  proxyDialogVisible.value = true
  loadProxyPool()
}

const handleSelectProxy = (proxy) => {
  scrapeForm.value.params.proxy = {
    server: proxy.server,
    username: proxy.username || '',
    password: proxy.password || ''
  }
  proxyDialogVisible.value = false
  ElMessage.success(`已选择代理: ${proxy.name}`)
}

const confirmBatchDelete = () => {
  const taskIds = selectedTasks.value.map(task => task.task_id)
  ElMessageBox.confirm(
    `确定要删除选中的 ${taskIds.length} 个任务吗？此操作不可恢复。`,
    '批量删除确认',
    {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'error',
      icon: DeleteFilled,
      buttonSize: 'default'
    }
  ).then(async () => {
    try {
      loading.value = true
      await deleteTasksBatch(taskIds)
      ElMessage.success(`成功删除 ${taskIds.length} 个任务`)
      selectedTasks.value = []
      loadTasks()
    } catch (error) {
      ElMessage.error('批量删除失败: ' + (error.response?.data?.detail || error.message))
    } finally {
      loading.value = false
    }
  }).catch(() => {})
}

const resetFilter = () => {
  filterForm.value = {
    status: '',
    url: ''
  }
  handleFilter()
}

const showScrapeDialog = ref(false)
const showTaskDialog = ref(false)
const showRetryDialog = ref(false)
const retryForm = ref({
  taskId: '',
  url: '',
  agentEnabled: false,
  agentModelId: null,
  agentParallelEnabled: false,
  agentParallelBatchSize: 10
})
const scrapeForm = ref({
  url: '',
  params: {
    wait_for: 'networkidle',
    wait_time: 3000,
    timeout: 30000,
    selector: '',
    screenshot: true,
    is_fullscreen: false,
    block_images: false,
    block_media: false,
    user_agent: '',
    viewport: {
      width: 1920,
      height: 1080
    },
    proxy: {
      server: '',
      username: '',
      password: ''
    },
    stealth: true,
    intercept_apis: [],
    intercept_continue: false,
    agent_enabled: false,
    agent_model_id: null,
    agent_system_prompt: '',
    agent_prompt: '',
    agent_parallel_enabled: false,
    agent_parallel_batch_size: 10
  },
  cache: {
    enabled: true,
    ttl: 3600
  },
  priority: 1
})

const currentTask = ref(null)

// 根据节点名称生成固定颜色
const getNodeColor = (nodeId) => {
  if (!nodeId) return 'info'
  const colors = ['success', 'warning', 'danger', 'primary', '']
  let hash = 0
  for (let i = 0; i < nodeId.length; i++) {
    hash = nodeId.charCodeAt(i) + ((hash << 5) - hash)
  }
  const index = Math.abs(hash) % colors.length
  return colors[index]
}

const loadTasks = async () => {
  loading.value = true
  try {
    const params = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value
    }
    if (filterForm.value.status) {
      params.status = filterForm.value.status
    }
    if (filterForm.value.url) {
      params.url = filterForm.value.url
    }
    
    const data = await getTasks(params)
    tasks.value = data.tasks
    total.value = data.total
  } catch (error) {
    ElMessage.error('获取任务列表失败')
  } finally {
    loading.value = false
  }
}

const confirmDelete = (taskId) => {
  ElMessageBox.confirm(
    '确定要删除该任务吗？此操作不可恢复。',
    '提示',
    {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'error',
      icon: DeleteFilled,
      buttonSize: 'default'
    }
  ).then(() => {
    deleteTask(taskId)
  }).catch(() => {})
}

const deleteTask = async (taskId) => {
  try {
    await deleteTaskApi(taskId)
    ElMessage.success('删除成功')
    loadTasks()
  } catch (error) {
    ElMessage.error('删除失败: ' + (error.response?.data?.detail || error.message))
  }
}

const confirmRetry = (row) => {
  retryForm.value = {
    taskId: row.task_id,
    url: row.url,
    agentEnabled: !!row.params?.agent_enabled,
    agentModelId: row.params?.agent_model_id || null,
    agentParallelEnabled: !!row.params?.agent_parallel_enabled,
    agentParallelBatchSize: row.params?.agent_parallel_batch_size || 10
  }
  showRetryDialog.value = true
}

const handleRetry = async () => {
  try {
    showRetryDialog.value = false
    loading.value = true
    await retryTask(
      retryForm.value.taskId, 
      retryForm.value.agentModelId,
      retryForm.value.agentParallelEnabled,
      retryForm.value.agentParallelBatchSize
    )
    ElMessage.success('已重新提交任务')
    loadTasks()
  } catch (error) {
    ElMessage.error('重试失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const viewTask = async (task) => {
  try {
    const data = await getTask(task.task_id)
    currentTask.value = data
    activeTab.value = 'info'
    showTaskDialog.value = true
  } catch (error) {
    ElMessage.error('获取任务详情失败')
  }
}

const submitTask = async () => {
  if (!scrapeForm.value.url) {
    ElMessage.warning('请输入目标 URL')
    return
  }

  loading.value = true
  try {
    // 深度克隆表单数据，避免修改原始数据
    const submitData = JSON.parse(JSON.stringify(scrapeForm.value))
    
    // 处理可选参数：如果为空则设置为 null，以匹配后端 Optional 类型
    if (!submitData.params.user_agent) {
      submitData.params.user_agent = null
    }
    if (!submitData.params.selector) {
      submitData.params.selector = null
    }
    
    // 代理配置处理
    if (!submitData.params.proxy || !submitData.params.proxy.server) {
      submitData.params.proxy = null
    } else {
      // 如果 server 存在但用户名/密码为空，也清理一下
      if (!submitData.params.proxy.username) delete submitData.params.proxy.username
      if (!submitData.params.proxy.password) delete submitData.params.proxy.password
    }
    
    // 拦截配置处理
    if (!submitData.params.intercept_apis || submitData.params.intercept_apis.length === 0) {
      submitData.params.intercept_apis = null
    }
    
    // 视口配置处理：如果宽高为 0 或无效，则设为 null 使用默认值
    if (!submitData.params.viewport || !submitData.params.viewport.width || !submitData.params.viewport.height) {
      submitData.params.viewport = null
    }

    // 交互步骤处理：如果为空则设为 null
    if (!submitData.params.interaction_steps || submitData.params.interaction_steps.length === 0) {
      submitData.params.interaction_steps = null
    }
    
    await scrapeAsync(submitData)
    ElMessage.success('任务提交成功 (异步)')
    showScrapeDialog.value = false
    loadTasks()
    
    // 重置表单
    resetForm()
  } catch (error) {
    ElMessage.error('任务提交失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  scrapeForm.value = {
    url: '',
    params: {
      wait_for: 'networkidle',
      wait_time: 3000,
      timeout: 30000,
      selector: '',
      screenshot: true,
      block_images: false,
      block_media: false,
      user_agent: '',
      viewport: {
        width: 1280,
        height: 720
      },
      proxy: {
        server: '',
        username: '',
        password: ''
      },
      stealth: true,
      intercept_apis: [],
      intercept_continue: false,
      agent_enabled: false,
      agent_model_id: null,
      agent_system_prompt: '',
      agent_prompt: '',
      interaction_steps: []
    },
    cache: {
      enabled: true,
      ttl: 3600
    },
    priority: 1
  }
}

const getStatusType = (status) => {
  const types = {
    pending: 'info',
    processing: 'warning',
    success: 'success',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    'pending': t('tasks.status.pending'),
    'processing': t('tasks.status.running'),
    'success': t('tasks.status.success'),
    'failed': t('tasks.status.failed')
  }
  return texts[status] || status
}

const formatDate = (date) => {
  if (!date) return ''
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

const formatTimeOnly = (date) => {
  if (!date) return ''
  return dayjs(date).format('HH:mm:ss')
}

const copyToClipboard = (text) => {
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

const formatJSON = (content) => {
  if (typeof content === 'string') {
    try {
      return JSON.stringify(JSON.parse(content), null, 2)
    } catch (e) {
      return content
    }
  }
  return JSON.stringify(content, null, 2)
}

const loadLLMModels = async () => {
  try {
    const data = await getLLMModels({ is_enabled: true, limit: 100 })
    llmModels.value = data.items
  } catch (error) {
    console.error('Failed to load LLM models:', error)
  }
}

const getAgentStatusType = (status) => {
  const types = {
    pending: 'info',
    processing: 'warning',
    success: 'success',
    failed: 'danger',
    skipped: 'info'
  }
  return types[status] || 'info'
}

const getAgentStatusText = (status) => {
  const map = {
    pending: '等待处理',
    processing: '处理中',
    success: '识别成功',
    failed: '识别失败',
    skipped: '已跳过'
  }
  return map[status] || status
}

const copyAgentJSON = () => {
  if (currentTask.value?.result?.agent_result?.extracted_items) {
    const json = JSON.stringify(currentTask.value.result.agent_result.extracted_items, null, 2)
    navigator.clipboard.writeText(json).then(() => {
      ElMessage.success('JSON 已复制到剪贴板')
    }).catch(() => {
      ElMessage.error('复制失败')
    })
  }
}

const exportAgentExcel = () => {
  if (!currentTask.value?.result?.agent_result?.extracted_items?.length) return
  
  const items = currentTask.value.result.agent_result.extracted_items
  const headers = Object.keys(items[0])
  
  // 简单的 CSV 导出
  let csv = headers.join(',') + '\n'
  items.forEach(item => {
    csv += headers.map(h => {
      const val = item[h] ?? ''
      return typeof val === 'string' && val.includes(',') ? `"${val}"` : val
    }).join(',') + '\n'
  })
  
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `agent_extract_${currentTask.value.task_id}.csv`
  link.click()
  URL.revokeObjectURL(url)
  ElMessage.success('已导出为 CSV 文件')
}

// ===== Prompt Template Functions =====
const loadAllTemplates = async () => {
  templateLoading.value = true
  try {
    const data = await getPromptTemplates({ limit: 100 })
    promptTemplates.value = data.items
    filteredTemplates.value = data.items  // 初始显示全部
  } catch (error) {
    console.error('Failed to load templates:', error)
  } finally {
    templateLoading.value = false
  }
}

// 本地过滤方法
const filterTemplates = (query) => {
  if (!query) {
    filteredTemplates.value = promptTemplates.value
    return
  }
  const lowerQuery = query.toLowerCase()
  filteredTemplates.value = promptTemplates.value.filter(tpl => 
    tpl.name.toLowerCase().includes(lowerQuery) || 
    tpl.content.toLowerCase().includes(lowerQuery)
  )
}

// 下拉框展开时确保加载数据
const handleTemplateDropdownVisible = (visible) => {
  if (visible && promptTemplates.value.length === 0) {
    loadAllTemplates()
  } else if (visible) {
    // 重置过滤，显示全部
    filteredTemplates.value = promptTemplates.value
  }
}

const applyTemplate = (templateId) => {
  if (!templateId) return
  const tpl = promptTemplates.value.find(t => t._id === templateId)
  if (tpl) {
    scrapeForm.value.params.agent_system_prompt = tpl.system_content || ''
    scrapeForm.value.params.agent_prompt = tpl.content
    ElMessage.success(`已应用模板: ${tpl.name}`)
  }
}

const showSaveTemplateDialog = () => {
  saveTemplateForm.value = { name: '', description: '' }
  showSaveTemplateDialogVisible.value = true
}

const confirmSaveTemplate = async () => {
  if (!saveTemplateForm.value.name.trim()) {
    ElMessage.warning('请输入模板名称')
    return
  }
  const promptContent = currentTask.value?.result?.agent_result?.user_prompt
  if (!promptContent) {
    ElMessage.warning('没有可保存的提示词')
    return
  }
  
  try {
    await createPromptTemplate({
      name: saveTemplateForm.value.name,
      content: promptContent,
      description: saveTemplateForm.value.description
    })
    ElMessage.success('模板保存成功')
    showSaveTemplateDialogVisible.value = false
    await loadAllTemplates()
  } catch (error) {
    ElMessage.error('保存模板失败: ' + (error.response?.data?.detail || error.message))
  }
}

const addInteractionStep = () => {
  if (!scrapeForm.value.params.interaction_steps) {
    scrapeForm.value.params.interaction_steps = []
  }
  scrapeForm.value.params.interaction_steps.push({
    action: 'scroll',
    params: { distance: 500, selector: 'window' }
  })
}

const removeInteractionStep = (index) => {
  scrapeForm.value.params.interaction_steps.splice(index, 1)
}

const resetStepParams = (index) => {
  const step = scrapeForm.value.params.interaction_steps[index]
  const defaults = {
    scroll: { distance: 500, selector: 'window' },
    infinite_scroll: { max_scrolls: 10, delay: 1500, selector: 'window' },
    pagination: { action: 'next', selector: '' },
    zoom: { direction: 'in', times: 1, selector: '' },
    fill: { data: {} },
    click: { selector: '' },
    wait: { duration: 1000 },
    extract_coordinates: {},
    block_container: { selector: '' },
    exclude_elements: { selectors: '' }
  }
  step.params = JSON.parse(JSON.stringify(defaults[step.action] || {}))
}

const loadSkillBundles = async () => {
  bundleLoading.value = true
  try {
    const data = await getSkillBundles()
    skillBundles.value = data
  } catch (error) {
    console.error('Failed to load skill bundles:', error)
  } finally {
    bundleLoading.value = false
  }
}

const applySkillBundle = (bundleId) => {
  if (!bundleId) return
  const bundle = skillBundles.value.find(b => (b._id || b.id) === bundleId)
  if (bundle && bundle.steps) {
    if (!scrapeForm.value.params.interaction_steps) {
      scrapeForm.value.params.interaction_steps = []
    }
    // 将技能包中的步骤追加到当前步骤中
    const newSteps = JSON.parse(JSON.stringify(bundle.steps))
    scrapeForm.value.params.interaction_steps.push(...newSteps)
    ElMessage.success(`已应用技能包: ${bundle.name}`)
    selectedBundleId.value = null // 重置选择器
  }
}

const addFillPair = (index) => {
  const step = scrapeForm.value.params.interaction_steps[index]
  ElMessageBox.prompt('请输入字段选择器和内容 (格式: selector=value)', '添加表单字段', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
  }).then(({ value }) => {
    if (value && value.includes('=')) {
      const [k, v] = value.split('=')
      if (!step.params.data) step.params.data = {}
      step.params.data[k.trim()] = v.trim()
    } else {
      ElMessage.warning('格式错误，请使用 selector=value')
    }
  }).catch(() => {})
}

const loadSkills = async () => {
  try {
    const [builtIn, custom] = await Promise.all([
      getBuiltInSkills(),
      getCustomSkills({ is_enabled: true })
    ])
    builtInSkills.value = builtIn
    customSkills.value = custom
  } catch (err) {
    console.error('Failed to load skills:', err)
  }
}

onMounted(() => {
  loadTasks()
  loadLLMModels()
  loadAllTemplates()
  loadProxyPool()
  loadSkills()
  loadSkillBundles()
})
</script>

<style scoped>
/* 列表 UI 优化 */
.task-info-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.id-tag-simple {
  font-size: 14px;
  color: #64748b;
  background-color: #f1f5f9;
  border: none;
  padding: 0 5px;
}

.task-id-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.copy-btn-mini {
  padding: 0;
  height: auto;
  font-size: 12px;
}

.task-url-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.actual-url-info {
  margin-top: 2px;
}

.actual-url-text {
  font-size: 12px;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 4px;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.actual-url-text .el-icon {
  font-size: 14px;
  color: #3b82f6;
}

.url-link-bold {
  font-size: 14px;
  font-weight: 600;
  color: #328ee4;
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  transition: color 0.2s;
}

.url-link-bold:hover {
  color: #3b82f6;
}

.url-link-bold span {
  display: inline-block;
  max-width: 550px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}

.url-link-bold .el-icon {
  color: #3b82f6;
  font-size: 15px;
  padding: 0 2px;
}

.status-tag {
  border: none;
  min-width: 90px;
  border-radius: 20px;
}

.status-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.status-dot-mini {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #fff;
}

.status-dot-mini.processing {
  animation: blink 1.5s infinite;
}

.stats-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #475569;
}

.stat-item .el-icon {
  font-size: 15px;
  color: #64748b;
}

.stat-item .label {
  color: #94a3b8;
  font-size: 14px;
  min-width: 35px;
}

.timing-row {
  align-items: flex-start !important;
  padding-top: 2px;
}

.timing-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.time-tag {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  font-size: 12px !important;
  border: none;
  height: 26px;
  line-height: 26px;
}

.time-tag.total {
  background: linear-gradient(135deg, #73d494 0%, #47b66c 100%);
}

.time-tag.load {
  background-color: #fffbeb;
  border: 1px solid #fde68a;
  color: #b45309;
}

.cache-tag {
  font-size: 12px !important;
  height: 24px;
  line-height: 24px;
}

.mini-icon {
  font-size: 10px;
  margin-right: 2px;
}

.timeline-mini {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.time-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #64748b;
}

.time-row .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.time-row .dot.create { background-color: #3b82f6; }
.time-row .dot.complete { background-color: #22c55e; }

.time-row .label {
  color: #94a3b8;
  min-width: 30px;
}

.time-row .time {
  font-family: monospace;
}

/* 原有样式保持或替换 */
.tasks-container {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: calc(100vh - 60px);
}

.tasks-card {
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left .title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.header-left .subtitle {
  font-size: 13px;
  color: #909399;
  margin-left: 12px;
}

.filter-bar {
  padding: 20px;
  background-color: #fff;
  border-bottom: 1px solid #ebeef5;
}

/* 新建任务对话框重构样式 */
.bento-dialog :deep(.el-dialog__body) {
  padding: 0;
  background-color: #f8fafc;
}

.basic-config-card {
  margin: 15px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: #fff;
}

.scrape-tabs-container {
  margin: 0 15px 15px 15px;
}

.scrape-tabs-container :deep(.el-tabs--border-card) {
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.tab-content-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  padding: 10px 5px;
}

.tab-content-flex {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 10px 5px;
}

.config-section {
  background: #fff;
  padding: 15px;
  border-radius: 10px;
  border: 1px solid #f1f5f9;
}

.section-title {
  font-size: 14px;
  font-weight: 700;
  color: #334155;
  margin-bottom: 15px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.section-title::before {
  content: "";
  width: 3px;
  height: 14px;
  background: #3b82f6;
  border-radius: 2px;
}

.mb-0 { margin-bottom: 0 !important; }

.compact-switch-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 32px;
}

.feature-grid.mini {
  grid-template-columns: repeat(2, 1fr);
  margin-top: 15px;
}

.feature-cell {
  background-color: #f8fafc;
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid #f1f5f9;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.feature-cell .label {
  font-size: 12px;
  color: #475569;
}

.bento-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 10px 0;
}

.bento-submit {
  padding-left: 24px;
  padding-right: 24px;
  font-weight: 600;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  border: none;
}

.bento-submit:hover {
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
}

.agent-tab-content {
  padding: 5px;
}

.agent-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px dashed #e2e8f0;
}

.agent-enable-switch {
  display: flex;
  align-items: center;
  gap: 10px;
}

.switch-label {
  font-size: 13px;
  color: #64748b;
}

.template-select-row {
  display: flex;
  align-items: center;
}

.agent-disabled-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
  color: #94a3b8;
}

.agent-disabled-placeholder .el-icon {
  font-size: 48px;
  margin-bottom: 15px;
  color: #e2e8f0;
}

.agent-disabled-placeholder p {
  margin-bottom: 20px;
  font-size: 14px;
}

.bento-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 15px 20px;
  background: #fff;
  border-top: 1px solid #f1f5f9;
}

/* 下拉选项样式 */
.option-item {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.option-label {
  font-weight: 600;
  color: #1e293b;
  font-size: 14px;
}

.option-desc {
  font-size: 12px;
  color: #64748b;
}

:deep(.el-select-dropdown__item) {
    height: auto !important;
    padding: 12px !important;
    line-height: 1.2 !important;
    white-space: normal !important;
  }
 
 :deep(.el-select-dropdown__item.selected) {
   background-color: #eff6ff;
 }
 
 :deep(.el-select-dropdown__wrap) {
   max-height: 400px !important;
 }

/* 详情页样式 */
.task-details {
  padding: 10px;
}

.detail-descriptions :deep(.el-descriptions__label) {
  font-size: 14px;
  font-weight: 600;
  color: #475569;
  background-color: #f8fafc !important;
}

.detail-descriptions :deep(.el-descriptions__content) {
  font-size: 14px;
  color: #1e293b;
}

.detail-url-link {
  font-size: 14px;
  word-break: break-all;
}

.metadata-section, .error-section {
  margin-top: 20px;
}

.error-stack {
  margin-top: 10px;
  padding: 12px;
  background: #fef0f0;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  color: #f56c6c;
}

.intercept-group {
  margin-bottom: 20px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}

.pattern-header {
  padding: 10px;
  background: #f5f7fa;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #ebeef5;
}

.count {
  font-size: 12px;
  color: #909399;
}

.node-tag {
  font-weight: bold;
  font-size: 12px;
}

.req-detail {
  padding: 10px;
}

.json-box {
  margin-top: 10px;
}

.json-box pre {
  margin-top: 5px;
  padding: 10px;
  background: #282c34;
  color: #abb2bf;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 12px;
  max-height: 300px;
}

.screenshot-container {
  display: flex;
  justify-content: center;
  background: #f5f7fa;
  padding: 20px;
  border-radius: 4px;
  min-height: 400px;
}

.html-container pre {
  padding: 15px;
  background: #000000;
  color: #d6d6d6;
  border-radius: 4px;
  font-family: monospace;
  font-size: 14px;
  overflow-x: auto;
  max-height: 500px;
}

.id-cell, .url-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.truncated-id {
  font-family: monospace;
  font-size: 12px;
}

.url-text {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 8px;
  display: inline-block;
}

.status-dot.pending { background-color: #909399; }
.status-dot.processing { background-color: #409eff; animation: blink 1.5s infinite; }
.status-dot.success { background-color: #67c23a; }
.status-dot.failed { background-color: #f56c6c; }

@keyframes blink {
  0% { opacity: 1; }
  50% { opacity: 0.4; }
  100% { opacity: 1; }
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 8px;
}

.pagination-container {
  padding: 20px;
  display: flex;
  justify-content: flex-end;
}

/* 代理信息展示样式 */
.proxy-info-detail {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 4px 0;
}

.proxy-line {
  display: flex;
  align-items: center;
  gap: 12px;
  white-space: nowrap;
}

.p-label {
  font-size: 12px;
  color: #909399;
  min-width: 50px;
  flex-shrink: 0;
}

.proxy-line :deep(.el-tag__content) {
  display: flex;
  align-items: center;
  gap: 4px;
}

.p-user {
  background: #fdf6ec;
  color: #e6a23c;
  padding: 2px 8px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 13px;
  border: 1px solid #faecd8;
  word-break: break-all;
}

/* 交互步骤 (Skills) 样式 */
.skills-tab-content {
  padding: 5px;
}

.skills-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 400px;
  overflow-y: auto;
  padding-right: 5px;
}

.skill-step-item {
  display: flex;
  align-items: center;
  gap: 12px;
  background: white;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  transition: all 0.2s;
}

.skill-step-item:hover {
  border-color: #3b82f6;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

.step-index {
  width: 24px;
  height: 24px;
  background: #f1f5f9;
  color: #64748b;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
}

.step-params-config {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.agent-disabled-placeholder.mini {
  padding: 20px 0;
}

.fill-data-preview {
  font-size: 12px;
  color: #67c23a;
  background: #f0f9eb;
  padding: 2px 8px;
  border-radius: 10px;
}

/* Agent 配置样式 */
.header-icon-box.agent {
  background: linear-gradient(135deg, #a855f7 0%, #6366f1 100%);
}

.agent-disabled-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #909399;
  font-size: 13px;
  padding: 20px;
  background: #fafafa;
  border-radius: 6px;
}

.agent-result-section {
  padding: 10px 0;
}

.agent-status-desc {
  margin-bottom: 15px;
}

.token-usage-row {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

.extracted-results {
  margin-top: 10px;
}

.agent-actions {
  display: flex;
  gap: 10px;
  margin-top: 15px;
  justify-content: flex-end;
}

.raw-response {
  margin: 0;
  padding: 12px;
  background: #282c34;
  color: #abb2bf;
  border-radius: 4px;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
  overflow: auto;
}

.prompt-collapse {
  border: 1px solid #f1f5f9;
  border-radius: 8px;
  overflow: hidden;
  background: white;
}

.collapse-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #475569;
  padding-left: 5px;
}

.prompt-content {
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 12px;
}

.prompt-content.system {
  background: #f0f7ff;
  border-color: #d1e9ff;
}

.prompt-content pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  color: #606266;
}

.template-option {
  display: flex;
  flex-direction: column;
  max-width: 280px;
}

.template-option-name {
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.template-option-preview {
  font-size: 12px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-create-dialog :deep(.el-dialog__body) {
  max-height: 75vh;
  overflow-y: auto;
  padding: 15px 25px;
}

.task-info-mini {
  background: #f8fafc;
  padding: 10px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  width: 100%;
  box-sizing: border-box;
  overflow: hidden;
}

.task-info-mini .id-row {
  font-size: 11px;
  color: #64748b;
  margin-bottom: 4px;
  font-family: monospace;
}

.task-info-mini .url-row {
  font-size: 13px;
  color: #1e293b;
  width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

/* 缓存分拆样式 */
.cache-tag-content {
  display: flex;
  align-items: center;
  gap: 4px;
}

.cache-split-mini {
  display: flex;
  gap: 2px;
  margin-left: 2px;
}

.split-dot {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  font-size: 9px;
  font-weight: bold;
  color: white;
  line-height: 1;
}

.split-dot.html { background-color: #10b981; }
.split-dot.ai   { background-color: #3b82f6; }
.split-dot.partial { background-color: #f59e0b; }

.cache-info-detail {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cache-split-details {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.split-tag {
  font-size: 11px;
}
</style>

<style>
/* 全局样式：模板下拉框宽度限制 */
.template-select-dropdown {
  max-width: 350px !important;
}

/* 紧凑型弹窗样式 */
.task-create-dialog .el-dialog__body {
  padding: 10px 25px !important; 
}
.task-create-dialog .el-form-item {
  margin-bottom: 8px;
}
.task-create-dialog .el-form-item__label {
  padding-bottom: 2px !important;
  margin-bottom: 2px !important;
}
.task-create-dialog .el-card__body {
  padding: 12px;
}
.task-create-dialog .config-section {
  margin-bottom: 15px;
}
.task-create-dialog .section-title {
  margin-bottom: 8px;
  font-size: 14px;
}
.task-create-dialog .el-divider--horizontal {
  margin: 15px 0;
}
</style>
