<template>
  <div class="sigma-graph-container" ref="rootEl">
    <div class="sigma-canvas" ref="container"></div>
    <div class="slots">
      <div v-if="$slots.top" class="overlay top">
        <slot name="top" />
      </div>
      <div class="content">
        <slot name="content" />
      </div>
      <div v-if="$slots.bottom" class="overlay bottom">
        <slot name="bottom" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch, nextTick } from 'vue'
import Graph from 'graphology'
import Sigma from 'sigma'
import { buildNodeColorMap, filterByDimensions, getDimensionColor } from '@/utils/nodeColorMapper'

// 手动实现随机布局，使用更大的距离避免重叠
function applyRandomLayout(graph) {
  const nodes = graph.nodes()
  const nodeCount = nodes.length
  const scale = Math.sqrt(nodeCount) * 150 // 大幅增加分布范围，避免初始就重叠
  
  nodes.forEach(node => {
    graph.setNodeAttribute(node, 'x', (Math.random() - 0.5) * scale)
    graph.setNodeAttribute(node, 'y', (Math.random() - 0.5) * scale)
  })
}

// 简单的力导向布局，使节点分散且不重叠
function applySimpleForceLayout(graph, iterations = 50) {
  const nodes = graph.nodes()
  const nodeCount = nodes.length
  
  if (nodeCount === 0) return
  
  const repulsionStrength = 1000 // 大幅增加排斥力强度，使节点保持更大距离
  const attractionStrength = 0.001 // 进一步减小吸引力强度
  const damping = 0.9 // 调整阻尼系数使节点更快稳定
  
  // 初始化速度
  const velocities = new Map()
  nodes.forEach(node => velocities.set(node, { vx: 0, vy: 0 }))
  
  // 大幅增加迭代次数以确保节点充分分散
  for (let iter = 0; iter < iterations * 4; iter++) {
    // 计算排斥力（让节点相互排斥）
    for (let i = 0; i < nodeCount; i++) {
      const nodeA = nodes[i]
      const posA = { x: graph.getNodeAttribute(nodeA, 'x'), y: graph.getNodeAttribute(nodeA, 'y') }
      const vel = velocities.get(nodeA)
      
      for (let j = i + 1; j < nodeCount; j++) {
        const nodeB = nodes[j]
        const posB = { x: graph.getNodeAttribute(nodeB, 'x'), y: graph.getNodeAttribute(nodeB, 'y') }
        
        const dx = posB.x - posA.x
        const dy = posB.y - posA.y
        const distance = Math.sqrt(dx * dx + dy * dy) || 1
        
        // 排斥力 - 使用更强的排斥力，并设置最小距离阈值
        const minDistance = 100 // 设置最小距离阈值
        const force = repulsionStrength / Math.max(distance * distance, minDistance)
        const fx = (dx / distance) * force
        const fy = (dy / distance) * force
        
        vel.vx -= fx
        vel.vy -= fy
        
        const velB = velocities.get(nodeB)
        velB.vx += fx
        velB.vy += fy
      }
    }
    
    // 计算吸引力（让连接的节点相互靠近）
    graph.forEachEdge((edge, attrs, source, target) => {
      const posA = { x: graph.getNodeAttribute(source, 'x'), y: graph.getNodeAttribute(source, 'y') }
      const posB = { x: graph.getNodeAttribute(target, 'x'), y: graph.getNodeAttribute(target, 'y') }
      
      const dx = posB.x - posA.x
      const dy = posB.y - posA.y
      const distance = Math.sqrt(dx * dx + dy * dy) || 1
      
      const force = distance * attractionStrength
      const fx = (dx / distance) * force
      const fy = (dy / distance) * force
      
      const velA = velocities.get(source)
      const velB = velocities.get(target)
      
      velA.vx += fx
      velA.vy += fy
      velB.vx -= fx
      velB.vy -= fy
    })
    
    // 更新位置
    nodes.forEach(node => {
      const vel = velocities.get(node)
      const pos = { x: graph.getNodeAttribute(node, 'x'), y: graph.getNodeAttribute(node, 'y') }
      
      pos.x += vel.vx
      pos.y += vel.vy
      
      graph.setNodeAttribute(node, 'x', pos.x)
      graph.setNodeAttribute(node, 'y', pos.y)
      
      // 应用阻尼
      vel.vx *= damping
      vel.vy *= damping
    })
  }
}

// 将节点标签绘制在节点内部并根据可用空间换行
function drawLabelInsideNode(context, data, settings) {
  if (!data.label) return

  const size = settings.labelSize
  const font = settings.labelFont
  const weight = settings.labelWeight
  const color = settings.labelColor.attribute
    ? data[settings.labelColor.attribute] || settings.labelColor.color || '#000'
    : settings.labelColor.color

  context.fillStyle = color
  context.font = `${weight} ${size}px ${font}`
  context.textAlign = 'center'
  context.textBaseline = 'middle'

  const diameter = Math.max(16, (data.size || 1) * 2)
  const maxWidth = diameter * 0.85
  const lineHeight = size + 2
  const rawLines = []
  const text = String(data.label)
  let currentLine = ''

  for (const char of text) {
    const testLine = currentLine + char
    if (context.measureText(testLine).width <= maxWidth || !currentLine) {
      currentLine = testLine
    } else {
      rawLines.push(currentLine)
      currentLine = char
    }
  }
  if (currentLine) rawLines.push(currentLine)

  const maxLines = Math.max(1, Math.floor((diameter * 0.8) / lineHeight))
  const lines = rawLines.slice(0, maxLines)
  if (rawLines.length > maxLines && lines.length > 0) {
    let lastLine = lines[lines.length - 1] || ''
    const ellipsis = '...'
    while (lastLine && context.measureText(lastLine + ellipsis).width > maxWidth) {
      lastLine = lastLine.slice(0, -1)
    }
    lines[lines.length - 1] = `${lastLine}${ellipsis}`
  }

  const totalHeight = lines.length * lineHeight
  const startY = data.y - totalHeight / 2 + lineHeight / 2
  lines.forEach((line, index) => {
    context.fillText(line, data.x, startY + index * lineHeight)
  })
}

const props = defineProps({
  graphData: {
    type: Object,
    required: true,
    default: () => ({ nodes: [], edges: [] })
  },
  labelField: { type: String, default: 'name' },
  autoFit: { type: Boolean, default: true },
  autoResize: { type: Boolean, default: true },
  layoutOptions: { type: Object, default: () => ({}) },
  nodeStyleOptions: { type: Object, default: () => ({}) },
  edgeStyleOptions: { type: Object, default: () => ({}) },
  enableFocusNeighbor: { type: Boolean, default: true },
  sizeByDegree: { type: Boolean, default: true },
  highlightKeywords: { type: Array, default: () => [] },
  hiddenDimensions: { type: Array, default: () => [] }
})

const emit = defineEmits(['ready', 'node-click', 'edge-click', 'canvas-click', 'data-rendered'])

const container = ref(null)
const rootEl = ref(null)
let graph = null
let sigmaInstance = null
let resizeObserver = null
let focusedNode = null

// 初始化图实例
function initGraph() {
  if (!container.value) return
  
  const width = container.value.offsetWidth
  const height = container.value.offsetHeight
  
  if (width === 0 || height === 0) {
    setTimeout(initGraph, 200)
    return
  }
  
  // 销毁旧实例
  if (sigmaInstance) {
    try { sigmaInstance.kill() } catch (e) {}
    sigmaInstance = null
  }
  
  // 创建 graphology 图
  graph = new Graph()
  
  // 创建 Sigma 实例
  sigmaInstance = new Sigma(graph, container.value, {
    allowInvalidContainer: true,
    renderLabels: true,  // 启用Sigma默认标签渲染
    labelRenderer: drawLabelInsideNode,
    renderEdgeLabels: true,
    labelFont: 'Microsoft YaHei, sans-serif',
    labelSize: 12,  // 标签字体大小
    labelColor: { color: '#ffffff' },  // 白色字体
    labelWeight: 'bold',  // 加粗
    labelRenderedSizeThreshold: 0,  // 始终显示标签
    edgeLabelSize: 10,
    edgeLabelColor: { color: '#cbd5e1' },
    edgeLabelWeight: 'normal',
    defaultNodeColor: '#f59e0b',
    defaultEdgeColor: '#64b5f6',
    defaultEdgeType: 'arrow',
    minCameraRatio: 0.1,
    maxCameraRatio: 10,
    nodeProgramClasses: {},
    edgeProgramClasses: {},
    nodeReducer: (node, data) => {
      const res = { ...data }
      
      // 处理高亮状态
      if (focusedNode) {
        if (node === focusedNode || graph.hasEdge(node, focusedNode) || graph.hasEdge(focusedNode, node)) {
          res.highlighted = true
        } else {
          res.color = '#e2e8f0'
          res.label = ''
        }
      }
      
      // 处理搜索高亮
      if (props.highlightKeywords.length > 0) {
        const label = data.label || ''
        const isMatch = props.highlightKeywords.some(kw => 
          kw && label.toLowerCase().includes(kw.toLowerCase())
        )
        if (isMatch) {
          res.highlighted = true
          res.color = '#ef4444'
          res.size = (data.size || 10) * 1.5
        }
      }
      
      return res
    },
    edgeReducer: (edge, data) => {
      const res = { ...data }
      
      if (focusedNode) {
        const [source, target] = graph.extremities(edge)
        if (source !== focusedNode && target !== focusedNode) {
          // 使用半透明而非完全隐藏，保持图谱结构可见
          res.color = '#334155'
          res.size = 0.5
        } else {
          // 高亮与聚焦节点相连的边
          res.color = '#60a5fa'
          res.size = 3
        }
      }
      
      return res
    }
  })
  
  // 绑定事件
  bindEvents()
  
  emit('ready', { graph, sigma: sigmaInstance })
}

// 绑定事件
function bindEvents() {
  if (!sigmaInstance) return
  
  // 节点点击
  sigmaInstance.on('clickNode', ({ node }) => {
    emit('node-click', { id: node, data: graph.getNodeAttributes(node) })
    
    if (props.enableFocusNeighbor) {
      if (focusedNode === node) {
        focusedNode = null
      } else {
        focusedNode = node
      }
      sigmaInstance.refresh()
    }
  })
  
  // 画布点击
  sigmaInstance.on('clickStage', () => {
    emit('canvas-click')
    if (focusedNode) {
      focusedNode = null
      sigmaInstance.refresh()
    }
  })
  
  // 边点击
  sigmaInstance.on('clickEdge', ({ edge }) => {
    emit('edge-click', { id: edge, data: graph.getEdgeAttributes(edge) })
  })
  
  // 节点拖拽支持 - 完全重写以确保正常工作
  let draggedNode = null
  let isDragging = false
  
  // 鼠标按下节点时开始拖拽
  sigmaInstance.on('downNode', (e) => {
    isDragging = true
    draggedNode = e.node
    graph.setNodeAttribute(draggedNode, 'highlighted', true)
    sigmaInstance.getGraph().setNodeAttribute(draggedNode, 'fixed', true)
  })
  
  // 鼠标移动时更新节点位置
  sigmaInstance.getMouseCaptor().on('mousemovebody', (e) => {
    if (!isDragging || !draggedNode) return
    
    // 获取鼠标在图空间中的坐标
    const pos = sigmaInstance.viewportToGraph(e)
    
    // 更新节点位置
    graph.setNodeAttribute(draggedNode, 'x', pos.x)
    graph.setNodeAttribute(draggedNode, 'y', pos.y)
    
    // 阻止默认行为并刷新
    e.preventSigmaDefault()
    e.original.preventDefault()
    e.original.stopPropagation()
  })
  
  // 鼠标释放时结束拖拽
  const endDrag = () => {
    if (draggedNode) {
      graph.removeNodeAttribute(draggedNode, 'highlighted')
      graph.removeNodeAttribute(draggedNode, 'fixed')
      draggedNode = null
    }
    isDragging = false
  }
  
  // 绑定mouseup事件到body，确保在任何位置释放都能结束拖拽
  sigmaInstance.getMouseCaptor().on('mouseup', endDrag)
  
  // 点击画布时也结束拖拽
  sigmaInstance.on('clickStage', () => {
    if (isDragging) {
      endDrag()
    }
  })
}

// 设置图数据
function setGraphData() {
  if (!graph) {
    initGraph()
  }
  if (!graph) return
  
  // 清空现有数据
  graph.clear()
  
  // 过滤隐藏的维度
  const { nodes, edges } = filterByDimensions(
    props.graphData.nodes || [],
    props.graphData.edges || [],
    props.hiddenDimensions
  )
  
  if (nodes.length === 0) {
    if (sigmaInstance) sigmaInstance.refresh()
    return
  }
  
  // 构建颜色映射
  const colorMap = buildNodeColorMap(nodes, edges)
  
  // 计算度数
  const degrees = new Map()
  for (const n of nodes) {
    degrees.set(String(n.id), 0)
  }
  for (const e of edges) {
    const s = String(e.source_id)
    const t = String(e.target_id)
    degrees.set(s, (degrees.get(s) || 0) + 1)
    degrees.set(t, (degrees.get(t) || 0) + 1)
  }
  
  // 添加节点
  for (const node of nodes) {
    const nodeId = String(node.id)
    const degree = degrees.get(nodeId) || 0
    const colorInfo = colorMap.get(nodeId) || { color: '#f59e0b', dimension: 'default' }
    
    // 计算节点大小 - 增大基础大小以容纳标签
    let size = 15  // 增大基础大小
    if (props.sizeByDegree) {
      size = Math.min(15 + degree * 3, 50)  // 增大节点以容纳标签
    }
    
    graph.addNode(nodeId, {
      label: node[props.labelField] || node.name || nodeId,
      size,
      color: colorInfo.color,
      dimension: colorInfo.dimension,
      x: Math.random(),
      y: Math.random(),
    })
  }
  
  // 添加边
  for (let i = 0; i < edges.length; i++) {
    const edge = edges[i]
    const sourceId = String(edge.source_id)
    const targetId = String(edge.target_id)
    
    if (graph.hasNode(sourceId) && graph.hasNode(targetId)) {
      try {
        graph.addEdge(sourceId, targetId, {
          label: edge.type || '',
          size: 2,
          color: '#ffffff',
        })
      } catch (e) {
        // 忽略重复边
      }
    }
  }
  
  // 应用布局
  applyLayout()
  
  // 刷新渲染
  if (sigmaInstance) {
    sigmaInstance.refresh()
  }
  
  emit('data-rendered')
}

// 应用布局
function applyLayout() {
  if (!graph || graph.order === 0) return

  // 先应用随机布局作为初始位置
  applyRandomLayout(graph)

  // 使用简单力导向布局，使节点分散并不重叠 - 增加迭代次数
  applySimpleForceLayout(graph, 100)
}

// 刷新图
function refreshGraph() {
  focusedNode = null
  setGraphData()
}

// 适应视图
function fitView() {
  if (sigmaInstance) {
    const camera = sigmaInstance.getCamera()
    camera.animatedReset({ duration: 300 })
  }
}

// 适应中心
function fitCenter() {
  fitView()
}

// 获取实例
function getInstance() {
  return { graph, sigma: sigmaInstance }
}

// 聚焦节点
async function focusNode(id) {
  if (!graph || !sigmaInstance) return
  
  const nodeId = String(id)
  if (!graph.hasNode(nodeId)) return
  
  focusedNode = nodeId
  sigmaInstance.refresh()
  
  // 移动相机到节点
  const nodePos = sigmaInstance.getNodeDisplayData(nodeId)
  if (nodePos) {
    const camera = sigmaInstance.getCamera()
    camera.animate({ x: nodePos.x, y: nodePos.y, ratio: 0.5 }, { duration: 300 })
  }
}

// 清除聚焦
async function clearFocus() {
  focusedNode = null
  if (sigmaInstance) {
    sigmaInstance.refresh()
  }
}

// 应用关键词高亮
function applyHighlightKeywords() {
  if (sigmaInstance) {
    sigmaInstance.refresh()
  }
}

// 清除高亮
function clearHighlights() {
  if (sigmaInstance) {
    sigmaInstance.refresh()
  }
}

// 监听数据变化
watch(() => props.graphData, () => {
  nextTick(() => setGraphData())
}, { deep: true })

// 监听隐藏维度变化
watch(() => props.hiddenDimensions, () => {
  nextTick(() => setGraphData())
}, { deep: true })

// 监听布局变化
watch(() => props.layoutOptions, () => {
  nextTick(() => {
    applyLayout()
    if (sigmaInstance) sigmaInstance.refresh()
  })
}, { deep: true })

// 监听高亮关键词变化
watch(() => props.highlightKeywords, () => {
  if (sigmaInstance) sigmaInstance.refresh()
}, { deep: true })

onMounted(() => {
  // ResizeObserver
  if (window.ResizeObserver) {
    resizeObserver = new ResizeObserver(() => {
      if (sigmaInstance && container.value) {
        sigmaInstance.refresh()
      }
    })
    if (container.value) resizeObserver.observe(container.value)
  }
  
  nextTick(() => {
    initGraph()
    setGraphData()
  })
})

onUnmounted(() => {
  if (resizeObserver && container.value) {
    resizeObserver.unobserve(container.value)
  }
  if (sigmaInstance) {
    try { sigmaInstance.kill() } catch (e) {}
    sigmaInstance = null
  }
  graph = null
})

// 暴露方法
defineExpose({
  refreshGraph,
  fitView,
  fitCenter,
  getInstance,
  focusNode,
  clearFocus,
  setData: setGraphData,
  applyHighlightKeywords,
  clearHighlights
})
</script>

<style lang="less" scoped>
.sigma-graph-container {
  position: relative;
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  
  .sigma-canvas {
    width: 100%;
    height: 100%;
  }
  
  .slots {
    pointer-events: none;
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    z-index: 10;
    
    .overlay {
      width: 100%;
      flex-shrink: 0;
      flex-grow: 0;
      pointer-events: auto;
      
      &.top { top: 0; }
      &.bottom { bottom: 0; }
    }
    
    .content {
      pointer-events: none;
      flex: 1;
    }
    
    .content * {
      pointer-events: none;
    }
  }
}
</style>

// �ڵ����鵯����ʽ
.node-detail {
  padding: 8px 0;
  
  .detail-row {
    display: flex;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid #f0f0f0;
    
    &:last-child {
      border-bottom: none;
    }
  }
  
  .detail-label {
    font-weight: 600;
    color: var(--text-primary);
    min-width: 80px;
    margin-right: 12px;
  }
  
  .detail-value {
    color: var(--text-secondary);
    flex: 1;
    word-break: break-all;
  }
  
  .detail-color {
    width: 30px;
    height: 30px;
    border-radius: 4px;
    border: 1px solid #d9d9d9;
  }
}
