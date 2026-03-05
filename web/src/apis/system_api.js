import { apiGet, apiPost, apiAdminGet, apiAdminPost, apiSuperAdminPost, apiSuperAdminGet, apiSuperAdminDelete } from './base'

/**
 * 系统管理API模块
 * 包含系统配置、健康检查、信息管理等功能
 */



// =============================================================================
// === 健康检查分组 ===
// =============================================================================

export const healthApi = {
  /**
   * 系统健康检查（公开接口）
   * @returns {Promise} - 健康检查结果
   */
  checkHealth: () => apiGet('/api/system/health', {}, false),

  /**
   * OCR服务健康检查
   * @returns {Promise} - OCR服务健康状态
   */
  checkOcrHealth: async () => apiAdminGet('/api/system/ocr/health')
}

// =============================================================================
// === 配置管理分组 ===
// =============================================================================

export const configApi = {
  /**
   * 获取系统配置
   * @returns {Promise} - 系统配置
   */
  getConfig: async () => apiAdminGet('/api/system/config'),

  /**
   * 更新单个配置项
   * @param {string} key - 配置键
   * @param {any} value - 配置值
   * @returns {Promise} - 更新结果
   */
  updateConfig: async (key, value) => apiAdminPost('/api/system/config', { key, value }),

  /**
   * 批量更新配置项
   * @param {Object} items - 配置项对象
   * @returns {Promise} - 更新结果
   */
  updateConfigBatch: async (items) => apiAdminPost('/api/system/config/update', items),

  /**
   * 重启系统（仅超级管理员）
   * @returns {Promise} - 重启结果
   */
  restartSystem: async () => apiSuperAdminPost('/api/system/restart', {}),

  /**
   * 获取系统日志
   * @returns {Promise} - 系统日志
   */
  getLogs: async () => apiAdminGet('/api/system/logs')
}

// =============================================================================
// === 信息管理分组 ===
// =============================================================================

export const brandApi = {
  /**
   * 获取系统信息配置（公开接口）
   * @returns {Promise} - 系统信息配置
   */
  getInfoConfig: () => apiGet('/api/system/info', {}, false),

  /**
   * 重新加载信息配置
   * @returns {Promise} - 重新加载结果
   */
  reloadInfoConfig: async () => apiAdminPost('/api/system/info/reload', {})
}

// =============================================================================
// === OCR服务分组 ===
// =============================================================================

export const ocrApi = {
  /**
   * 获取OCR服务统计信息
   * @returns {Promise} - OCR统计信息
   */
  getStats: async () => apiAdminGet('/api/system/ocr/stats'),

  /**
   * 获取OCR服务健康状态
   * @returns {Promise} - OCR健康状态
   */
  getHealth: async () => apiAdminGet('/api/system/ocr/health')
}

// =============================================================================
// === 聊天模型状态检查分组 ===
// =============================================================================

export const chatModelApi = {
  /**
   * 获取指定聊天模型的状态
   * @param {string} provider - 模型提供商
   * @param {string} modelName - 模型名称
   * @returns {Promise} - 模型状态
   */
  getModelStatus: async (provider, modelName) => {
    return apiAdminGet(`/api/system/chat-models/status?provider=${encodeURIComponent(provider)}&model_name=${encodeURIComponent(modelName)}`)
  },

  /**
   * 获取所有聊天模型的状态
   * @returns {Promise} - 所有模型状态
   */
  getAllModelsStatus: async () => {
    return apiAdminGet('/api/system/chat-models/all/status')
  }
}

// =============================================================================
// === 大坝异常配置分组 ===
// =============================================================================

export const damExceptionApi = {
  /**
   * 获取大坝异常配置
   * @returns {Promise} - 大坝异常配置
   */
  getConfig: async () => apiAdminGet('/api/system/dam-exception/config'),

  /**
   * 更新大坝异常配置
   * @param {Object} config - 配置对象
   * @returns {Promise} - 更新结果
   */
  updateConfig: async (config) => apiAdminPost('/api/system/dam-exception/config', config),

  /**
   * 获取可用的知识库列表
   * @returns {Promise} - 知识库列表
   */
  getKnowledgeBases: async () => apiAdminGet('/api/system/dam-exception/knowledge-bases'),

  /**
   * 获取可用的知识图谱列表
   * @returns {Promise} - 图谱列表
   */
  getGraphs: async () => apiAdminGet('/api/system/dam-exception/graphs')
}

export const damExceptionQaApi = {
  /**
   * 异常问答（供前端与其他系统复用）
   * @param {Object} payload - 请求体
   * @returns {Promise} - 问答结果
   */
  ask: async (payload) => apiPost('/api/system/dam-exception/qa', payload, {}, false),

  /**
   * 获取异常问答调用记录（登录后）
   * @param {number} limit - 记录条数
   * @returns {Promise} - 调用记录
   */
  getRecords: async (limit = 20) => apiGet(`/api/system/dam-exception/qa/records?limit=${limit}`)
}

// =============================================================================
// === 模型配置管理分组 ===
// =============================================================================

export const modelConfigApi = {
  /**
   * 获取所有模型配置（超级管理员）
   * @returns {Promise} - 模型配置
   */
  getConfig: async () => apiSuperAdminGet('/api/system/model-config'),

  /**
   * 添加或更新聊天模型提供商
   * @param {Object} providerData - 提供商数据
   * @returns {Promise} - 更新结果
   */
  updateProvider: async (providerData) =>
    apiSuperAdminPost('/api/system/model-config/provider', providerData),

  /**
   * 删除聊天模型提供商
   * @param {string} providerId - 提供商ID
   * @returns {Promise} - 删除结果
   */
  deleteProvider: async (providerId) =>
    apiSuperAdminDelete(`/api/system/model-config/provider/${encodeURIComponent(providerId)}`),

  /**
   * 添加或更新Embedding模型
   * @param {Object} modelData - 模型数据
   * @returns {Promise} - 更新结果
   */
  updateEmbedModel: async (modelData) =>
    apiSuperAdminPost('/api/system/model-config/embed-model', modelData),

  /**
   * 删除Embedding模型
   * @param {string} modelId - 模型ID
   * @returns {Promise} - 删除结果
   */
  deleteEmbedModel: async (modelId) =>
    apiSuperAdminDelete(`/api/system/model-config/embed-model/${encodeURIComponent(modelId)}`),

  /**
   * 添加或更新Reranker模型
   * @param {Object} modelData - 模型数据
   * @returns {Promise} - 更新结果
   */
  updateReranker: async (modelData) =>
    apiSuperAdminPost('/api/system/model-config/reranker', modelData),

  /**
   * 删除Reranker模型
   * @param {string} modelId - 模型ID
   * @returns {Promise} - 删除结果
   */
  deleteReranker: async (modelId) =>
    apiSuperAdminDelete(`/api/system/model-config/reranker/${encodeURIComponent(modelId)}`)
}
