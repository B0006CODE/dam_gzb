<template>
  <div class="setting-view">
    <HeaderComponent title="设置" class="setting-header">

      <template #actions>
        <a-button :type="isNeedRestart ? 'primary' : 'default'" @click="sendRestart" :icon="h(ReloadOutlined)">
          {{ isNeedRestart ? '需要刷新' : '重新加载' }}
        </a-button>
      </template>
    </HeaderComponent>
    <div class="setting-container layout-container">
      <div class="sider" v-if="state.windowWidth > 520">
        <a-button type="text" v-if="userStore.isSuperAdmin" :class="{ activesec: state.section === 'base'}" @click="state.section='base'" :icon="h(SettingOutlined)"> 基本设置 </a-button>
        <a-button type="text" :class="{ activesec: state.section === 'user'}" @click="state.section='user'" :icon="h(UserOutlined)" v-if="userStore.isAdmin"> 用户管理 </a-button>
      </div>
      <div class="setting" v-if="(state.windowWidth <= 520 || state.section === 'base') && userStore.isSuperAdmin">
        <h3>检索配置</h3>
        <div class="section">
          <div class="card card-select">
            <span class="label">{{ items?.default_model?.des || '默认对话模型' }}</span>
            <ModelSelectorComponent
              @select-model="handleChatModelSelect"
              :model_spec="configStore.config?.default_model"
              placeholder="请选择默认模型"
            />
          </div>
          <div class="card card-select">
            <span class="label">{{ items?.fast_model.des }}</span>
            <ModelSelectorComponent
              @select-model="handleFastModelSelect"
              :model_spec="configStore.config?.fast_model"
              placeholder="请选择模型"
            />
          </div>
          <div class="card card-select">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span class="label">{{ items?.embed_model.des }}</span>
              <!-- <a-button
                size="small"
                :loading="state.checkingStatus"
                @click="checkAllModelStatus"
                :disabled="state.checkingStatus"
              >
                检查状态
              </a-button> -->
            </div>
            <a-select style="width: 320px"
              :value="configStore.config?.embed_model"
              @change="handleChange('embed_model', $event)"
              @dropdownVisibleChange="checkAllModelStatus"
            >
              <a-select-option
                v-for="(name, idx) in items?.embed_model.choices" :key="idx"
                :value="name"
              >
                <div style="display: flex; align-items: center; gap: 8px; min-width: 0;">
                  <span style="flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    {{ name }}
                  </span>
                  <span
                    :style="{
                      color: getModelStatusColor(name),
                      fontSize: '11px',
                      fontWeight: 'bold',
                      flexShrink: 0,
                      padding: '2px 4px',
                      borderRadius: '3px',
                    }"
                    :title="getModelStatusTooltip(name)"
                  >
                    {{ getModelStatusIcon(name) }}
                  </span>
                </div>
              </a-select-option>
            </a-select>
          </div>
          <div class="card card-select">
            <span class="label">{{ items?.reranker.des }}</span>
            <a-select style="width: 320px"
              :value="configStore.config?.reranker"
              @change="handleChange('reranker', $event)"
            >
              <a-select-option
                v-for="(name, idx) in items?.reranker.choices" :key="idx"
                :value="name">{{ name }}
              </a-select-option>
            </a-select>
          </div>
          <div class="card card-select">
            <span class="label">{{ items?.rerank_top_k?.des || '重排序返回结果数量' }}</span>
            <a-input-number
              style="width: 120px"
              :value="configStore.config?.rerank_top_k"
              :min="1"
              :max="50"
              @change="handleChange('rerank_top_k', $event)"
            />
          </div>
        </div>

        <!-- 服务链接部分 -->
        <div v-if="userStore.isAdmin">
          <h3>服务链接</h3>
          <p>快速访问系统相关的外部服务。</p>
          <div class="services-grid">
            <div class="service-link-card">
              <div class="service-info">
                <h4>Neo4j 浏览器</h4>
                <p>图数据库管理界面</p>
              </div>
                            <a-button type="default" @click="openLink('http://localhost:7474/')" :icon="h(GlobalOutlined)">
                访问
              </a-button>
            </div>

            <div class="service-link-card">
              <div class="service-info">
                <h4>API 接口文档</h4>
                <p>系统接口文档和调试工具</p>
              </div>
              <a-button type="default" @click="openLink('http://localhost:5050/docs')" :icon="h(GlobalOutlined)">
                访问
              </a-button>
            </div>

            <div class="service-link-card">
              <div class="service-info">
                <h4>MinIO 对象存储</h4>
                <p>文件存储管理控制台</p>
              </div>
              <a-button type="default" @click="openLink('http://localhost:9001')" :icon="h(GlobalOutlined)">
                访问
              </a-button>
            </div>

            <div class="service-link-card">
              <div class="service-info">
                <h4>Milvus WebUI</h4>
                <p>向量数据库管理界面</p>
              </div>
              <a-button type="default" @click="openLink('http://localhost:9091/webui/')" :icon="h(GlobalOutlined)">
                访问
              </a-button>
            </div>
          </div>
        </div>

        <!-- 大坝异常配置部分 -->
        <div v-if="userStore.isAdmin">
          <h3>大坝异常配置</h3>
          <p>配置大坝异常问答接口的默认知识库、图谱和API设置。</p>
          <div class="section">
            <div class="card card-select">
              <span class="label">知识库白名单</span>
              <a-select
                style="width: 320px"
                mode="multiple"
                placeholder="选择知识库（可多选）"
                :value="damConfig.kb_whitelist"
                :loading="damConfigLoading"
                @change="(val) => updateDamConfig('kb_whitelist', val)"
              >
                <a-select-option
                  v-for="kb in availableKnowledgeBases"
                  :key="kb.id"
                  :value="kb.id"
                >{{ kb.name }}</a-select-option>
              </a-select>
            </div>
            <div class="card card-select">
              <span class="label">默认知识图谱</span>
              <a-select
                style="width: 320px"
                placeholder="选择图谱"
                :value="damConfig.graph_name"
                :loading="damConfigLoading"
                @change="(val) => updateDamConfig('graph_name', val)"
              >
                <a-select-option
                  v-for="graph in availableGraphs"
                  :key="graph.id"
                  :value="graph.id"
                >{{ graph.name }}</a-select-option>
              </a-select>
            </div>
            <div class="card card-select">
              <span class="label">异常数据API地址</span>
              <a-input
                style="width: 320px"
                placeholder="输入API地址"
                :value="damConfig.exception_api_url"
                @change="(e) => updateDamConfig('exception_api_url', e.target.value)"
              />
            </div>
            <div class="card card-select">
              <span class="label">默认包含修复建议</span>
              <a-switch
                :checked="damConfig.include_repair_suggestions"
                @change="(val) => updateDamConfig('include_repair_suggestions', val)"
              />
            </div>
            <div class="card" style="justify-content: flex-end;">
              <a-button type="primary" :loading="damConfigSaving" @click="saveDamConfig">
                保存配置
              </a-button>
            </div>
          </div>
        </div>

        <!-- 模型配置管理部分 -->
        <div v-if="userStore.isSuperAdmin">
          <h3>模型配置管理</h3>
          <p>配置聊天模型提供商、Embedding模型和Reranker模型的地址和参数。</p>
          
          <!-- 聊天模型提供商 -->
          <div class="section model-config-section">
            <div class="section-header">
              <span class="section-title">聊天模型提供商</span>
              <a-button size="small" type="primary" @click="showProviderModal()" :icon="h(PlusOutlined)">添加</a-button>
            </div>
            <a-collapse v-model:activeKey="modelConfigState.expandedProviders" :bordered="false">
              <a-collapse-panel v-for="(provider, providerId) in modelConfig.providers" :key="providerId" :header="provider.name || providerId">
                <template #extra>
                  <a-space @click.stop>
                    <a-button size="small" @click.stop="showProviderModal(providerId, provider)" :icon="h(EditOutlined)">编辑</a-button>
                    <a-popconfirm title="确定删除该提供商？" @confirm="deleteProvider(providerId)">
                      <a-button size="small" danger :icon="h(DeleteOutlined)">删除</a-button>
                    </a-popconfirm>
                  </a-space>
                </template>
                <div class="provider-detail">
                  <p><strong>ID:</strong> {{ providerId }}</p>
                  <p><strong>Base URL:</strong> {{ provider.base_url }}</p>
                  <p><strong>默认模型:</strong> {{ provider.default }}</p>
                  <p><strong>环境变量:</strong> {{ provider.env }}</p>
                  <p><strong>模型列表:</strong> {{ provider.models?.join(', ') || '无' }}</p>
                </div>
              </a-collapse-panel>
            </a-collapse>
          </div>
          
          <!-- Embedding模型 -->
          <div class="section model-config-section">
            <div class="section-header">
              <span class="section-title">Embedding模型</span>
              <a-button size="small" type="primary" @click="showEmbedModal()" :icon="h(PlusOutlined)">添加</a-button>
            </div>
            <a-collapse v-model:activeKey="modelConfigState.expandedEmbeds" :bordered="false">
              <a-collapse-panel v-for="(model, modelId) in modelConfig.embed_models" :key="modelId" :header="model.name || modelId">
                <template #extra>
                  <a-space @click.stop>
                    <a-button size="small" @click.stop="showEmbedModal(modelId, model)" :icon="h(EditOutlined)">编辑</a-button>
                    <a-popconfirm title="确定删除该模型？" @confirm="deleteEmbedModel(modelId)">
                      <a-button size="small" danger :icon="h(DeleteOutlined)">删除</a-button>
                    </a-popconfirm>
                  </a-space>
                </template>
                <div class="provider-detail">
                  <p><strong>ID:</strong> {{ modelId }}</p>
                  <p><strong>Base URL:</strong> {{ model.base_url }}</p>
                  <p><strong>维度:</strong> {{ model.dimension }}</p>
                  <p><strong>API Key变量:</strong> {{ model.api_key }}</p>
                </div>
              </a-collapse-panel>
            </a-collapse>
          </div>
          
          <!-- Reranker模型 -->
          <div class="section model-config-section">
            <div class="section-header">
              <span class="section-title">Reranker模型</span>
              <a-button size="small" type="primary" @click="showRerankerModal()" :icon="h(PlusOutlined)">添加</a-button>
            </div>
            <a-collapse v-model:activeKey="modelConfigState.expandedRerankers" :bordered="false">
              <a-collapse-panel v-for="(model, modelId) in modelConfig.rerankers" :key="modelId" :header="model.name || modelId">
                <template #extra>
                  <a-space @click.stop>
                    <a-button size="small" @click.stop="showRerankerModal(modelId, model)" :icon="h(EditOutlined)">编辑</a-button>
                    <a-popconfirm title="确定删除该模型？" @confirm="deleteReranker(modelId)">
                      <a-button size="small" danger :icon="h(DeleteOutlined)">删除</a-button>
                    </a-popconfirm>
                  </a-space>
                </template>
                <div class="provider-detail">
                  <p><strong>ID:</strong> {{ modelId }}</p>
                  <p><strong>Base URL:</strong> {{ model.base_url }}</p>
                  <p><strong>API Key变量:</strong> {{ model.api_key }}</p>
                </div>
              </a-collapse-panel>
            </a-collapse>
          </div>
        </div>
      </div>


      <div class="setting" v-if="(state.windowWidth <= 520 || state.section === 'user') && userStore.isAdmin">
         <UserManagementComponent />
      </div>
    </div>
  </div>
</template>

<script setup>
import { message } from 'ant-design-vue';
import { computed, reactive, ref, h, watch, onMounted, onUnmounted } from 'vue'
import { useConfigStore } from '@/stores/config';
import { useUserStore } from '@/stores/user'
import {
  ReloadOutlined,
  SettingOutlined,
  FolderOutlined,
  UserOutlined,
  GlobalOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined
} from '@ant-design/icons-vue';
import HeaderComponent from '@/components/HeaderComponent.vue';
import UserManagementComponent from '@/components/UserManagementComponent.vue';
import { notification, Button, Modal, Input, InputNumber } from 'ant-design-vue';
import { configApi, damExceptionApi, modelConfigApi } from '@/apis/system_api'
import { embeddingApi } from '@/apis/knowledge_api'
import ModelSelectorComponent from '@/components/ModelSelectorComponent.vue';

const configStore = useConfigStore()
const userStore = useUserStore()
const items = computed(() => configStore.config._config_items)
const isNeedRestart = ref(false)
const state = reactive({
  loading: false,
  section: 'base',
  windowWidth: window?.innerWidth || 0,
  modelStatuses: {}, // 存储embedding模型状态
  checkingStatus: false // 是否正在检查状态
})

// 大坝异常配置相关
const damConfig = reactive({
  kb_whitelist: [],
  graph_name: 'neo4j',
  exception_api_url: '',
  exception_api_params: {},
  include_repair_suggestions: true
})
const damConfigLoading = ref(false)
const damConfigSaving = ref(false)
const availableKnowledgeBases = ref([])
const availableGraphs = ref([])

const handleModelLocalPathsUpdate = (config) => {
  handleChange('model_local_paths', config)
}

const preHandleChange = (key, e) => {

  if (key == 'enable_reranker'
    || key == 'embed_model'
    || key == 'reranker'
    || key == 'rerank_top_k'
    || key == 'model_local_paths') {
    isNeedRestart.value = true
    notification.info({
      message: '需要重新加载模型',
      description: '请点击右下角按钮重新加载模型',
      placement: 'topLeft',
      duration: 0,
      btn: h(Button, { type: 'primary', onClick: sendRestart }, '立即重新加载')
    })
  }
  return true
}

const handleChange = (key, e) => {
  if (!preHandleChange(key, e)) {
    return
  }
  configStore.setConfigValue(key, e)
}

const handleChanges = (items) => {
  for (const key in items) {
    if (!preHandleChange(key, items[key])) {
      return
    }
  }
  configStore.setConfigValues(items)
}

const updateWindowWidth = () => {
  state.windowWidth = window?.innerWidth || 0
}

const handleChatModelSelect = (spec) => {
  if (typeof spec === 'string' && spec) {
    configStore.setConfigValue('default_model', spec)
  }
}

const handleFastModelSelect = (spec) => {
  if (typeof spec === 'string' && spec) {
    configStore.setConfigValue('fast_model', spec)
  }
}

onMounted(() => {
  updateWindowWidth()
  window.addEventListener('resize', updateWindowWidth)
  state.section = userStore.isSuperAdmin ? 'base' : 'user'

  checkAllModelStatus()
  
  // 加载大坝异常配置
  if (userStore.isAdmin) {
    loadDamConfig()
  }
  
  // 加载模型配置
  if (userStore.isSuperAdmin) {
    loadModelConfig()
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', updateWindowWidth)
})

// 加载大坝异常配置
const loadDamConfig = async () => {
  damConfigLoading.value = true
  try {
    // 并行加载配置和可用选项
    const [configRes, kbRes, graphRes] = await Promise.all([
      damExceptionApi.getConfig(),
      damExceptionApi.getKnowledgeBases(),
      damExceptionApi.getGraphs()
    ])
    
    if (configRes.data) {
      Object.assign(damConfig, configRes.data)
    }
    if (kbRes.knowledge_bases) {
      availableKnowledgeBases.value = kbRes.knowledge_bases
    }
    if (graphRes.graphs) {
      availableGraphs.value = graphRes.graphs
    }
  } catch (error) {
    console.error('加载大坝配置失败:', error)
    message.error('加载大坝配置失败')
  } finally {
    damConfigLoading.value = false
  }
}

// 更新大坝配置项（本地）
const updateDamConfig = (key, value) => {
  damConfig[key] = value
}

// 保存大坝异常配置
const saveDamConfig = async () => {
  damConfigSaving.value = true
  try {
    const result = await damExceptionApi.updateConfig({
      kb_whitelist: damConfig.kb_whitelist,
      graph_name: damConfig.graph_name,
      exception_api_url: damConfig.exception_api_url,
      exception_api_params: damConfig.exception_api_params,
      include_repair_suggestions: damConfig.include_repair_suggestions
    })
    if (result.success) {
      message.success('大坝异常配置保存成功')
    } else {
      message.error('保存失败')
    }
  } catch (error) {
    console.error('保存大坝配置失败:', error)
    message.error('保存大坝配置失败')
  } finally {
    damConfigSaving.value = false
  }
}

// =============================================================================
// === 模型配置管理相关 ===
// =============================================================================

const modelConfig = reactive({
  providers: {},
  embed_models: {},
  rerankers: {}
})

const modelConfigState = reactive({
  loading: false,
  expandedProviders: [],
  expandedEmbeds: [],
  expandedRerankers: []
})

// 加载模型配置
const loadModelConfig = async () => {
  if (!userStore.isSuperAdmin) return
  
  modelConfigState.loading = true
  try {
    const res = await modelConfigApi.getConfig()
    if (res.success && res.data) {
      modelConfig.providers = res.data.providers || {}
      modelConfig.embed_models = res.data.embed_models || {}
      modelConfig.rerankers = res.data.rerankers || {}
    }
  } catch (error) {
    console.error('加载模型配置失败:', error)
    message.error('加载模型配置失败')
  } finally {
    modelConfigState.loading = false
  }
}

// Provider模态框处理
const showProviderModal = (providerId = null, providerData = null) => {
  const isEdit = !!providerId
  const formData = reactive({
    provider_id: providerId || '',
    name: providerData?.name || '',
    base_url: providerData?.base_url || '',
    default: providerData?.default || '',
    env: providerData?.env || 'NO_API_KEY',
    models: providerData?.models?.join('\n') || '',
    url: providerData?.url || ''
  })
  
  const modal = Modal.confirm({
    title: isEdit ? '编辑模型提供商' : '添加模型提供商',
    width: 520,
    icon: null,
    content: h('div', { class: 'model-form' }, [
      h('div', { class: 'form-item' }, [
        h('label', '提供商ID *'),
        h(Input, { 
          value: formData.provider_id, 
          disabled: isEdit,
          placeholder: '如: openai, deepseek',
          onChange: e => formData.provider_id = e.target.value 
        })
      ]),
      h('div', { class: 'form-item' }, [
        h('label', '显示名称 *'),
        h(Input, { 
          value: formData.name, 
          placeholder: '如: OpenAI',
          onChange: e => formData.name = e.target.value 
        })
      ]),
      h('div', { class: 'form-item' }, [
        h('label', 'Base URL *'),
        h(Input, { 
          value: formData.base_url, 
          placeholder: '如: https://api.openai.com/v1',
          onChange: e => formData.base_url = e.target.value 
        })
      ]),
      h('div', { class: 'form-item' }, [
        h('label', '默认模型'),
        h(Input, { 
          value: formData.default, 
          placeholder: '如: gpt-4o-mini',
          onChange: e => formData.default = e.target.value 
        })
      ]),
      h('div', { class: 'form-item' }, [
        h('label', 'API Key环境变量'),
        h(Input, { 
          value: formData.env, 
          placeholder: '如: OPENAI_API_KEY',
          onChange: e => formData.env = e.target.value 
        })
      ]),
      h('div', { class: 'form-item' }, [
        h('label', '模型列表（每行一个）'),
        h(Input.TextArea, { 
          value: formData.models, 
          rows: 4,
          placeholder: '每行一个模型名，如:\ngpt-4\ngpt-4o\ngpt-4o-mini',
          onChange: e => formData.models = e.target.value 
        })
      ])
    ]),
    okText: '保存',
    cancelText: '取消',
    onOk: async () => {
      if (!formData.provider_id || !formData.name || !formData.base_url) {
        message.error('请填写必填项')
        return Promise.reject()
      }
      try {
        const models = formData.models.split('\n').filter(m => m.trim())
        await modelConfigApi.updateProvider({
          provider_id: formData.provider_id,
          name: formData.name,
          base_url: formData.base_url,
          default: formData.default || models[0] || '',
          env: formData.env || 'NO_API_KEY',
          models: models,
          url: formData.url
        })
        message.success('保存成功')
        await loadModelConfig()
      } catch (error) {
        message.error('保存失败: ' + error.message)
        return Promise.reject()
      }
    }
  })
}

// 删除Provider
const deleteProvider = async (providerId) => {
  try {
    await modelConfigApi.deleteProvider(providerId)
    message.success('删除成功')
    await loadModelConfig()
  } catch (error) {
    message.error('删除失败: ' + error.message)
  }
}

// Embed模型模态框处理
const showEmbedModal = (modelId = null, modelData = null) => {
  const isEdit = !!modelId
  const formData = reactive({
    model_id: modelId || '',
    name: modelData?.name || '',
    dimension: modelData?.dimension || 1024,
    base_url: modelData?.base_url || '',
    api_key: modelData?.api_key || 'NO_API_KEY'
  })
  
  Modal.confirm({
    title: isEdit ? '编辑Embedding模型' : '添加Embedding模型',
    width: 480,
    icon: null,
    content: h('div', { class: 'model-form' }, [
      h('div', { class: 'form-item' }, [
        h('label', '模型ID *'),
        h(Input, { 
          value: formData.model_id, 
          disabled: isEdit,
          placeholder: '如: siliconflow/BAAI/bge-m3',
          onChange: e => formData.model_id = e.target.value 
        })
      ]),
      h('div', { class: 'form-item' }, [
        h('label', '模型名称 *'),
        h(Input, { 
          value: formData.name, 
          placeholder: '如: BAAI/bge-m3',
          onChange: e => formData.name = e.target.value 
        })
      ]),
      h('div', { class: 'form-item' }, [
        h('label', '向量维度'),
        h(InputNumber, { 
          value: formData.dimension,
          min: 1,
          max: 8192,
          onChange: v => formData.dimension = v 
        })
      ]),
      h('div', { class: 'form-item' }, [
        h('label', 'Base URL *'),
        h(Input, { 
          value: formData.base_url, 
          placeholder: '如: https://api.siliconflow.cn/v1/embeddings',
          onChange: e => formData.base_url = e.target.value 
        })
      ]),
      h('div', { class: 'form-item' }, [
        h('label', 'API Key环境变量'),
        h(Input, { 
          value: formData.api_key, 
          placeholder: '如: SILICONFLOW_API_KEY',
          onChange: e => formData.api_key = e.target.value 
        })
      ])
    ]),
    okText: '保存',
    cancelText: '取消',
    onOk: async () => {
      if (!formData.model_id || !formData.name || !formData.base_url) {
        message.error('请填写必填项')
        return Promise.reject()
      }
      try {
        await modelConfigApi.updateEmbedModel({
          model_id: formData.model_id,
          name: formData.name,
          dimension: formData.dimension,
          base_url: formData.base_url,
          api_key: formData.api_key || 'NO_API_KEY'
        })
        message.success('保存成功')
        await loadModelConfig()
      } catch (error) {
        message.error('保存失败: ' + error.message)
        return Promise.reject()
      }
    }
  })
}

// 删除Embed模型
const deleteEmbedModel = async (modelId) => {
  try {
    await modelConfigApi.deleteEmbedModel(modelId)
    message.success('删除成功')
    await loadModelConfig()
  } catch (error) {
    message.error('删除失败: ' + error.message)
  }
}

// Reranker模态框处理
const showRerankerModal = (modelId = null, modelData = null) => {
  const isEdit = !!modelId
  const formData = reactive({
    model_id: modelId || '',
    name: modelData?.name || '',
    base_url: modelData?.base_url || '',
    api_key: modelData?.api_key || 'NO_API_KEY'
  })
  
  Modal.confirm({
    title: isEdit ? '编辑Reranker模型' : '添加Reranker模型',
    width: 480,
    icon: null,
    content: h('div', { class: 'model-form' }, [
      h('div', { class: 'form-item' }, [
        h('label', '模型ID *'),
        h(Input, { 
          value: formData.model_id, 
          disabled: isEdit,
          placeholder: '如: siliconflow/BAAI/bge-reranker-v2-m3',
          onChange: e => formData.model_id = e.target.value 
        })
      ]),
      h('div', { class: 'form-item' }, [
        h('label', '模型名称 *'),
        h(Input, { 
          value: formData.name, 
          placeholder: '如: BAAI/bge-reranker-v2-m3',
          onChange: e => formData.name = e.target.value 
        })
      ]),
      h('div', { class: 'form-item' }, [
        h('label', 'Base URL *'),
        h(Input, { 
          value: formData.base_url, 
          placeholder: '如: https://api.siliconflow.cn/v1/rerank',
          onChange: e => formData.base_url = e.target.value 
        })
      ]),
      h('div', { class: 'form-item' }, [
        h('label', 'API Key环境变量'),
        h(Input, { 
          value: formData.api_key, 
          placeholder: '如: SILICONFLOW_API_KEY',
          onChange: e => formData.api_key = e.target.value 
        })
      ])
    ]),
    okText: '保存',
    cancelText: '取消',
    onOk: async () => {
      if (!formData.model_id || !formData.name || !formData.base_url) {
        message.error('请填写必填项')
        return Promise.reject()
      }
      try {
        await modelConfigApi.updateReranker({
          model_id: formData.model_id,
          name: formData.name,
          base_url: formData.base_url,
          api_key: formData.api_key || 'NO_API_KEY'
        })
        message.success('保存成功')
        await loadModelConfig()
      } catch (error) {
        message.error('保存失败: ' + error.message)
        return Promise.reject()
      }
    }
  })
}

// 删除Reranker
const deleteReranker = async (modelId) => {
  try {
    await modelConfigApi.deleteReranker(modelId)
    message.success('删除成功')
    await loadModelConfig()
  } catch (error) {
    message.error('删除失败: ' + error.message)
  }
}

const sendRestart = () => {

  configApi.restartSystem()
    .then(() => {
      setTimeout(() => {
        window.location.reload()
      }, 200)
    })
    .catch(error => {
      console.error('重启服务失败:', error)
      message.error({ content: `重启失败: ${error.message}`, key: "restart", duration: 2 });
    });
}


// 检查所有embedding模型状态
const checkAllModelStatus = async () => {
  try {
    state.checkingStatus = true
    const response = await embeddingApi.getAllModelsStatus()
    if (response.status.models) {
      state.modelStatuses = response.status.models
    }
  } catch (error) {
    console.error('检查所有模型状态失败:', error)
    message.error('获取模型状态失败')
  } finally {
    state.checkingStatus = false
  }
}

// 获取模型状态图标
const getModelStatusIcon = (modelId) => {
  const status = state.modelStatuses[modelId]
  if (!status) return '○'
  if (status.status === 'available') return '✓'
  if (status.status === 'unavailable') return '✗'
  if (status.status === 'error') return '⚠'
  return '○'
}

// 获取模型状态颜色
const getModelStatusColor = (modelId) => {
  const status = state.modelStatuses[modelId]
  if (!status) return '#999'
  if (status.status === 'available') return '#52c41a'
  if (status.status === 'unavailable') return '#ff4d4f'
  if (status.status === 'error') return '#faad14'
  return '#999'
}
// 获取模型状态提示文本
const getModelStatusTooltip = (modelId) => {
  const status = state.modelStatuses[modelId]
  if (!status) return '状态未知'

  let statusText = ''
  if (status.status === 'available') statusText = '可用'
  else if (status.status === 'unavailable') statusText = '不可用'
  else if (status.status === 'error') statusText = '错误'

  const message = status.message || '无详细信息'
  return `${statusText}: ${message}`
}

const openLink = (url) => {
  window.open(url, '_blank')
}
</script>

<style lang="less" scoped>

.setting-container {
  --setting-header-height: 55px;
  max-width: 1054px;
}

.setting-header {
  height: var(--setting-header-height);
}

.setting-header p {
  margin: 8px 0 0;
}

.setting-container {
  padding: 0;
  box-sizing: border-box;
  display: flex;
  position: relative;
  min-height: calc(100vh - var(--setting-header-height));
}

.sider {
  width: 180px;
  height: 100%;
  padding: 0 20px;
  position: sticky;
  top: var(--setting-header-height);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding-top: 20px;


  & > * {
    width: 100%;
    height: auto;
    padding: 6px 16px;
    cursor: pointer;
    transition: all 0.1s;
    text-align: left;
    font-size: 15px;
    border-radius: 8px;
    color: var(--gray-700);

    &:hover {
      background: rgba(6, 182, 212, 0.1);
    }

    &.activesec {
      background: rgba(6, 182, 212, 0.15);
      color: var(--main-color);
    }
  }
}

.setting {
  width: 100%;
  flex: 1;
  margin: 0 auto;
  height: 100%;
  padding: 0 20px;
  margin-bottom: 40px;

  h3:not(:first-child) {
    margin-top: 30px;
  }
  h3:first-child {
    margin-top: 20px;
  }

  .section {
    margin-top: 10px;
    background-color: var(--glass-bg);
    padding: 12px 16px;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    border: var(--glass-border);
  }

  .card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    // padding: 12px 0;

    .label {
      margin-right: 20px;
      font-weight: 500;
      color: var(--gray-800);

      button {
        margin-left: 10px;
        height: 24px;
        padding: 0 8px;
        font-size: smaller;
      }
    }
  }

  .services-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 12px;
    margin-top: 20px;
  }

  .service-link-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border: var(--glass-border);
    border-radius: 8px;
    background: rgba(30, 41, 59, 0.35);
    transition: all 0.2s;
    min-height: 60px;

    &:hover {
      box-shadow: var(--shadow-md);
    }

    .service-info {
      flex: 1;
      margin-right: 16px;

      h4 {
        margin: 0 0 4px 0;
        color: var(--gray-900);
        font-size: 15px;
        font-weight: 600;
      }

      p {
        margin: 0;
        color: var(--gray-600);
        font-size: 13px;
        line-height: 1.4;
      }
    }
  }

  // 模型配置管理样式
  .model-config-section {
    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
      
      .section-title {
        font-weight: 600;
        font-size: 14px;
        color: var(--gray-800);
      }
    }
    
    .provider-detail {
      p {
        margin: 4px 0;
        font-size: 13px;
        color: var(--gray-600);
        
        strong {
          color: var(--gray-800);
          margin-right: 8px;
        }
      }
    }
    
    :deep(.ant-collapse) {
      background: transparent;
      
      .ant-collapse-item {
        margin-bottom: 8px;
        border-radius: 6px;
        overflow: hidden;
        background: rgba(30, 41, 59, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
      }
      
      .ant-collapse-header {
        padding: 10px 12px;
        color: var(--gray-800);
        font-weight: 500;
      }
      
      .ant-collapse-content-box {
        padding: 12px;
      }
    }
  }
}

@media (max-width: 520px) {
  .setting-container {
    flex-direction: column;
  }

  .card.card-select {
    gap: 0.75rem;
    align-items: flex-start;
    flex-direction: column;
  }

  .services-grid {
    gap: 12px;
  }

  .service-link-card {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
    min-height: auto;
    padding: 12px;

    .service-info {
      text-align: left;
      margin-bottom: 4px;
      margin-right: 0;
    }
  }
}
</style>

<style lang="less">
// 添加全局样式以确保滚动功能在dropdown内正常工作
.ant-dropdown-menu {
  &.scrollable-menu {
    max-height: 300px;
    overflow-y: auto;
  }
}

// 模型配置表单样式（全局）
.model-form {
  .form-item {
    margin-bottom: 16px;
    
    label {
      display: block;
      margin-bottom: 6px;
      font-weight: 500;
      color: var(--gray-700);
    }
    
    .ant-input,
    .ant-input-number,
    .ant-input-textarea {
      width: 100%;
    }
  }
}
</style>

