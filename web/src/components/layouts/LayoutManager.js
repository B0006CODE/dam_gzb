/**
 * 布局管理器 - 统一管理知识图谱的各种布局算法
 * 提供布局接口、切换、动画等功能
 */

import * as d3 from 'd3'

export class LayoutManager {
  constructor() {
    this.layouts = new Map()
    this.currentLayout = null
    this.animationDuration = 1000
    this.transitionProgress = 0

    // 注册内置布局
    this.registerBuiltinLayouts()
  }

  /**
   * 注册内置布局算法
   */
  registerBuiltinLayouts() {
    // 力导向布局
    this.layouts.set('force', {
      name: '力导向布局',
      description: '基于 D3 力导向算法的 2D 布局',
      type: '2d',
      execute: (graph, options = {}) => this.forceLayout(graph, options),
      animate: true
    })

    // 环形布局
    this.layouts.set('radial', {
      name: '环形布局',
      description: '以中心节点为核心的环形分布',
      type: '2d',
      execute: (graph, options = {}) => this.radialLayout(graph, options),
      animate: true
    })

    // 3D 球形布局
    this.layouts.set('sphere3d', {
      name: '3D球形布局',
      description: '在球面上分布节点的3D布局',
      type: '3d',
      execute: (graph, options = {}) => this.sphere3DLayout(graph, options),
      animate: true
    })

    // 3D 螺旋布局
    this.layouts.set('spiral3d', {
      name: '3D螺旋布局',
      description: '螺旋状分布的3D布局',
      type: '3d',
      execute: (graph, options = {}) => this.spiral3DLayout(graph, options),
      animate: true
    })
  }

  /**
   * 力导向布局
   */
  forceLayout(graph, options = {}) {
    const nodes = graph.nodes()
    const edges = graph.edges()

    const width = options.width || 800
    const height = options.height || 600
    const centerNode = options.centerNode || null

    // 初始化位置
    const simulation = d3.forceSimulation(nodes.map(nodeId => ({
      id: nodeId,
      x: Math.random() * width,
      y: Math.random() * height
    })))

    // 定义力
    simulation
      .force('charge', d3.forceManyBody().strength(-300))
      .force('link', d3.forceLink(edges.map(edge => ({
        source: edge.source,
        target: edge.target
      })))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(20))

    // 如果有中心节点，添加向心力
    if (centerNode) {
      simulation.force('centerNode', d3.forceCenter(
        width / 2, height / 2
      ).strength(options.centerStrength || 0.8))
    }

    return new Promise((resolve) => {
      simulation.stop()

      // 运行模拟
      for (let i = 0; i < 300; i++) {
        simulation.tick()
      }

      const positions = {}
      simulation.nodes().forEach(node => {
        positions[node.id] = {
          x: node.x,
          y: node.y,
          z: 0
        }
      })

      resolve(positions)
    })
  }

  /**
   * 环形布局
   */
  radialLayout(graph, options = {}) {
    const nodes = graph.nodes()
    const edges = graph.edges()
    const width = options.width || 800
    const height = options.height || 600
    const centerNode = options.centerNode || null

    if (!centerNode && nodes.length > 0) {
      centerNode = nodes[0] // 默认第一个节点为中心
    }

    // 构建邻接表
    const adjacency = new Map()
    nodes.forEach(node => adjacency.set(node, []))
    edges.forEach(edge => {
      adjacency.get(edge.source).push(edge.target)
      adjacency.get(edge.target).push(edge.source)
    })

    // BFS 分层
    const levels = new Map()
    const visited = new Set()
    const queue = centerNode ? [centerNode] : nodes.slice()

    if (centerNode) {
      levels.set(centerNode, 0)
      visited.add(centerNode)
    }

    while (queue.length > 0) {
      const current = queue.shift()
      const currentLevel = levels.get(current) || 0

      const neighbors = adjacency.get(current) || []
      neighbors.forEach(neighbor => {
        if (!visited.has(neighbor)) {
          visited.add(neighbor)
          levels.set(neighbor, currentLevel + 1)
          queue.push(neighbor)
        }
      })
    }

    // 按层级分组
    const levelGroups = new Map()
    levels.forEach((level, node) => {
      if (!levelGroups.has(level)) {
        levelGroups.set(level, [])
      }
      levelGroups.get(level).push(node)
    })

    // 计算位置
    const positions = {}
    const centerX = width / 2
    const centerY = height / 2
    const baseRadius = Math.min(width, height) * 0.15

    levelGroups.forEach((nodesInLevel, level) => {
      const radius = baseRadius + (level * 80)
      const angleStep = (2 * Math.PI) / nodesInLevel.length

      nodesInLevel.forEach((node, index) => {
        const angle = index * angleStep
        positions[node] = {
          x: centerX + radius * Math.cos(angle),
          y: centerY + radius * Math.sin(angle),
          z: level * 20 // 添加深度层次
        }
      })
    })

    return Promise.resolve(positions)
  }

  /**
   * 3D 球形布局
   */
  sphere3DLayout(graph, options = {}) {
    const nodes = graph.nodes()
    const width = options.width || 800
    const height = options.height || 600
    const radius = Math.min(width, height) * 0.3

    const positions = {}

    // 使用斐波那契螺旋在球面上分布节点
    nodes.forEach((node, index) => {
      const y = 1 - (index / (nodes.length - 1)) * 2 // y 从 -1 到 1
      const radiusAtY = Math.sqrt(1 - y * y)

      const theta = Math.PI * (3 - Math.sqrt(5)) * index // 黄金角

      const x = Math.cos(theta) * radiusAtY
      const z = Math.sin(theta) * radiusAtY

      positions[node] = {
        x: width/2 + x * radius,
        y: height/2 + y * radius,
        z: z * radius
      }
    })

    return Promise.resolve(positions)
  }

  /**
   * 3D 螺旋布局
   */
  spiral3DLayout(graph, options = {}) {
    const nodes = graph.nodes()
    const width = options.width || 800
    const height = options.height || 600

    const positions = {}
    const centerX = width / 2
    const centerY = height / 2
    const maxRadius = Math.min(width, height) * 0.35
    const maxHeight = height * 0.3

    nodes.forEach((node, index) => {
      const t = index / (nodes.length - 1) // 0 到 1 的进度

      // 螺旋参数
      const angle = t * Math.PI * 6 // 旋转3圈
      const radius = maxRadius * t // 半径从0线性增长
      const heightOffset = maxHeight * (t - 0.5) // 高度从中心到顶部

      positions[node] = {
        x: centerX + radius * Math.cos(angle),
        y: centerY + heightOffset,
        z: radius * Math.sin(angle)
      }
    })

    return Promise.resolve(positions)
  }

  /**
   * 获取可用布局列表
   */
  getAvailableLayouts() {
    return Array.from(this.layouts.entries()).map(([key, layout]) => ({
      key,
      ...layout
    }))
  }

  /**
   * 切换布局
   */
  async switchLayout(layoutKey, graph, options = {}) {
    const layout = this.layouts.get(layoutKey)
    if (!layout) {
      throw new Error(`未找到布局: ${layoutKey}`)
    }

    const previousPositions = this.currentLayout ?
      await this.currentLayout.execute(graph, options) : {}

    const newPositions = await layout.execute(graph, options)

    this.currentLayout = layout

    return {
      positions: newPositions,
      previousPositions,
      layout: layout,
      shouldAnimate: layout.animate
    }
  }

  /**
   * 动画过渡函数
   */
  animateTransition(fromPositions, toPositions, duration = this.animationDuration, onProgress = null) {
    return new Promise((resolve) => {
      const startTime = performance.now()

      const animate = (currentTime) => {
        const elapsed = currentTime - startTime
        const progress = Math.min(elapsed / duration, 1)

        // 使用缓动函数
        const easeProgress = this.easeInOutCubic(progress)

        const currentPositions = {}
        for (const nodeId in toPositions) {
          const from = fromPositions[nodeId] || { x: 0, y: 0, z: 0 }
          const to = toPositions[nodeId]

          currentPositions[nodeId] = {
            x: from.x + (to.x - from.x) * easeProgress,
            y: from.y + (to.y - from.y) * easeProgress,
            z: from.z + (to.z - from.z) * easeProgress
          }
        }

        if (onProgress) {
          onProgress(currentPositions, progress)
        }

        if (progress < 1) {
          requestAnimationFrame(animate)
        } else {
          resolve(currentPositions)
        }
      }

      requestAnimationFrame(animate)
    })
  }

  /**
   * 缓动函数
   */
  easeInOutCubic(t) {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
  }

  /**
   * 注册自定义布局
   */
  registerLayout(key, layout) {
    this.layouts.set(key, layout)
  }

  /**
   * 销毁管理器
   */
  dispose() {
    this.layouts.clear()
    this.currentLayout = null
  }
}

// 单例模式
export const layoutManager = new LayoutManager()
