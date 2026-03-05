import { useUserStore, checkAdminPermission, checkSuperAdminPermission } from '@/stores/user'
import { message } from 'ant-design-vue'

/**
 * 基础API请求封装
 * 提供统一的请求方法，自动处理认证头和错误
 */

/**
 * 发送API请求的基础函数
 * @param {string} url - API端点
 * @param {Object} options - 请求选项
 * @param {boolean} requiresAuth - 是否需要认证头
 * @param {string} responseType - 响应类型: 'json' | 'text' | 'blob'
 * @returns {Promise} - 请求结果
 */
export async function apiRequest(url, options = {}, requiresAuth = true, responseType = 'json') {
  try {
    const hasBody = Object.prototype.hasOwnProperty.call(options, 'body') && options.body !== undefined && options.body !== null
    const isFormDataBody = hasBody && typeof FormData !== 'undefined' && options.body instanceof FormData

    // 默认请求配置
    const headers = {
      ...(options.headers || {}),
    }

    // 仅在非 FormData 请求体、且未显式指定 Content-Type 时设置 JSON 默认值
    if (!isFormDataBody) {
      const hasContentType =
        Object.prototype.hasOwnProperty.call(headers, 'Content-Type') ||
        Object.prototype.hasOwnProperty.call(headers, 'content-type')
      if (!hasContentType) {
        headers['Content-Type'] = 'application/json'
      }
    } else {
      // FormData 需要让浏览器自动补 boundary，避免手动设置导致服务端解析失败
      delete headers['Content-Type']
      delete headers['content-type']
    }

    const requestOptions = {
      ...options,
      headers,
    }

    // 如果需要认证，添加认证头
    if (requiresAuth) {
      const userStore = useUserStore()
      if (!userStore.isLoggedIn) {
        throw new Error('用户未登录')
      }

      Object.assign(requestOptions.headers, userStore.getAuthHeaders())
    }

    // 发送请求
    const response = await fetch(url, requestOptions)

    // 处理API返回的错误
    if (!response.ok) {
      // 尝试解析错误信息
      let errorMessage = `请求失败: ${response.status}, ${response.statusText}`
      let errorData = null


      try {
        errorData = await response.json()
        errorMessage = errorData.detail || errorData.message || errorMessage
      } catch (e) {
        // 如果无法解析JSON，使用默认错误信息
      }

      // 特殊处理401和403错误
      if (response.status === 401) {
        // 如果是认证失败，可能需要重新登录
        const userStore = useUserStore()

        // 检查是否是token过期
        const isTokenExpired = errorData &&
          (errorData.detail?.includes('令牌已过期') ||
           errorData.detail?.includes('token expired') ||
           errorMessage?.includes('令牌已过期') ||
           errorMessage?.includes('token expired'))

        message.error(isTokenExpired ? '登录已过期，请重新登录' : '认证失败，请重新登录')

        // 如果用户当前认为自己已登录，则登出
        if (userStore.isLoggedIn) {
          userStore.logout()
        }

        // 使用setTimeout确保消息显示后再跳转
        setTimeout(() => {
          window.location.href = '/login'
        }, 1500)

        throw new Error('未授权，请先登录')
      } else if (response.status === 403) {
        throw new Error('没有权限执行此操作')
      } else if (response.status === 500) {
        throw new Error('Server 500 Error, please check the log use `docker logs api-dev`')
      }

      throw new Error(errorMessage)
    }

    // 根据responseType处理响应
    if (responseType === 'blob') {
      return response
    } else if (responseType === 'json') {
      // 检查Content-Type以确定如何处理响应
      const contentType = response.headers.get('Content-Type')
      if (contentType && contentType.includes('application/json')) {
        return await response.json()
      }
      return await response.text()
    } else if (responseType === 'text') {
      return await response.text()
    } else {
      return response
    }
  } catch (error) {
    console.error('API请求错误:', error)
    throw error
  }
}

/**
 * 发送GET请求
 * @param {string} url - API端点
 * @param {Object} options - 请求选项
 * @param {boolean} requiresAuth - 是否需要认证
 * @param {string} responseType - 响应类型: 'json' | 'text' | 'blob'
 * @returns {Promise} - 请求结果
 */
export function apiGet(url, options = {}, requiresAuth = true, responseType = 'json') {
  return apiRequest(url, { method: 'GET', ...options }, requiresAuth, responseType)
}

export function apiAdminGet(url, options = {}, responseType = 'json') {
  checkAdminPermission()
  return apiGet(url, options, true, responseType)
}

export function apiSuperAdminGet(url, options = {}, responseType = 'json') {
  checkSuperAdminPermission()
  return apiGet(url, options, true, responseType)
}

/**
 * 发送POST请求
 * @param {string} url - API端点
 * @param {Object} data - 请求体数据
 * @param {Object} options - 其他请求选项
 * @param {boolean} requiresAuth - 是否需要认证
 * @param {string} responseType - 响应类型: 'json' | 'text' | 'blob'
 * @returns {Promise} - 请求结果
 */
export function apiPost(url, data = {}, options = {}, requiresAuth = true, responseType = 'json') {
  const isFormData = typeof FormData !== 'undefined' && data instanceof FormData
  return apiRequest(
    url,
    {
      method: 'POST',
      ...(isFormData ? { body: data } : { body: JSON.stringify(data) }),
      ...options
    },
    requiresAuth,
    responseType
  )
}

export function apiAdminPost(url, data = {}, options = {}, responseType = 'json') {
  checkAdminPermission()
  return apiPost(url, data, options, true, responseType)
}

export function apiSuperAdminPost(url, data = {}, options = {}, responseType = 'json') {
  checkSuperAdminPermission()
  return apiPost(url, data, options, true, responseType)
}

/**
 * 发送PUT请求
 * @param {string} url - API端点
 * @param {Object} data - 请求体数据
 * @param {Object} options - 其他请求选项
 * @param {boolean} requiresAuth - 是否需要认证
 * @param {string} responseType - 响应类型: 'json' | 'text' | 'blob'
 * @returns {Promise} - 请求结果
 */
export function apiPut(url, data = {}, options = {}, requiresAuth = true, responseType = 'json') {
  const isFormData = typeof FormData !== 'undefined' && data instanceof FormData
  return apiRequest(
    url,
    {
      method: 'PUT',
      ...(isFormData ? { body: data } : { body: JSON.stringify(data) }),
      ...options
    },
    requiresAuth,
    responseType
  )
}

export function apiAdminPut(url, data = {}, options = {}, responseType = 'json') {
  checkAdminPermission()
  return apiPut(url, data, options, true, responseType)
}

export function apiSuperAdminPut(url, data = {}, options = {}, responseType = 'json') {
  checkSuperAdminPermission()
  return apiPut(url, data, options, true, responseType)
}

/**
 * 发送DELETE请求
 * @param {string} url - API端点
 * @param {Object} data - 请求体数据
 * @param {Object} options - 请求选项
 * @param {boolean} requiresAuth - 是否需要认证
 * @param {string} responseType - 响应类型: 'json' | 'text' | 'blob'
 * @returns {Promise} - 请求结果
 */
export function apiDelete(url, data = {}, options = {}, requiresAuth = true, responseType = 'json') {
  const hasBody = data !== undefined && data !== null
  return apiRequest(
    url,
    {
      method: 'DELETE',
      ...(hasBody ? { body: JSON.stringify(data) } : {}),
      ...options
    },
    requiresAuth,
    responseType
  )
}

export function apiAdminDelete(url, data = {}, options = {}) {
  checkAdminPermission()
  return apiDelete(url, data, options, true)
}

export function apiSuperAdminDelete(url, data = {}, options = {}) {
  checkSuperAdminPermission()
  return apiDelete(url, data, options, true)
}
