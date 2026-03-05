<template>
  <div class="radial-layout-container">
    <div ref="container" class="canvas-container"></div>

    <!-- 控制面板 -->
    <div class="control-panel">
      <div class="layout-controls">
        <a-select
          v-model:value="selectedCenterNode"
          placeholder="选择中心节点"
          style="width: 200px; margin-right: 8px"
          show-search
          :filter-option="filterOption"
        >
          <a-select-option
            v-for="node in availableNodes"
            :key="node.id"
            :value="node.id"
          >
            {{ getNodeLabel(node) }}
          </a-select-option>
        </a-select>

        <a-input-number
          v-model:value="radiusStep"
          :min="50"
          :max="200"
          :step="10"
          placeholder="半径步长"
          style="width: 100px; margin-right: 8px"
        />

        <a-button
          type="primary"
          @click="updateLayout"
          :loading="isUpdating"
          size="small"
        >
          重新布局
        </a-button>
      </div>

      <div class="zoom-controls">
        <a-button size="small" @click="zoomIn">
          <ZoomInOutlined />
        </a-button>
        <a-button size="small" @click="zoomOut">
          <ZoomOutOutlined />
        </a-button>
        <a-button size="small" @click="resetView">
          <HomeOutlined />
        </a-button>
      </div>
    </div>

    <!-- 节点详情面板 -->
    <div
      v-if="selectedNode"
      class="node-detail-panel"
      :style="{ transform: `translate(${detailPanelPosition.x}px, ${detailPanelPosition.y}px)` }"
    >
      <div class="panel-header">
        <h4>{{ getNodeLabel(selectedNode) }}</h4>
        <a-button type="text" size="small" @click="selectedNode = null">
          <CloseOutlined />
        </a-button>
      </div>
      <div class="panel-content">
        <div class="detail-item">
          <span class="label">类型:</span>
          <span class="value">{{ selectedNode.entity_type }}</span>
        </div>
        <div class="detail-item">
          <span class="label">连接数:</span>
          <span class="value">{{ getNodeDegree(selectedNode) }}</span>
        </div>
        <div v-if="selectedNode.description" class="detail-item">
          <span class="label">描述:</span>
          <span class="value">{{ selectedNode.description }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, watch, computed } from 'vue'
import { message } from 'ant-design-vue'
import { ZoomInOutlined, ZoomOutOutlined, HomeOutlined, CloseOutlined } from '@ant-design/icons-vue'
import * as d3 from 'd3'
import { layoutManager } from './LayoutManager.js'

const props = defineProps({
  graphData: {
    type: Object,
    required: true,
    default: () => ({ nodes: [], edges: [] })
  },
  width: {
    type: Number,
    default: 800
  },
  height: {
    type: Number,
    default: 600
  }
})

const emit = defineEmits(['node-click', 'edge-click', 'layout-changed'])

// 响应式数据
const container = ref(null)
const svg = ref(null)
const simulation = ref(null)
const selectedNode = ref(null)
const selectedEdge = ref(null)
const isUpdating = ref(false)
const selectedCenterNode = ref('')
const radiusStep = ref(80)
const detailPanelPosition = ref({ x: 10, y: 10 })

// 可用节点列表
const availableNodes = computed(() => {
  return props.graphData.nodes.map(node => ({
    id: node.id,
    name: node.name || node.properties?.entity_id || node.id,
    ...node
  }))
})

// 获取节点标签
const getNodeLabel = (node) => {
  return node.name || node.properties?.entity_id || node.id
}

// 获取节点度数
const getNodeDegree = (node) => {
  const nodeId = typeof node === 'string' ? node : node.id
  const connections = props.graphData.edges.filter(edge =>
    edge.source_id === nodeId || edge.target_id === nodeId
  )
  return connections.length
}

// 过滤选项
const filterOption = (input, option) => {
  const node = availableNodes.value.find(n => n.id === option.value)
  return node && getNodeLabel(node).toLowerCase().includes(input.toLowerCase())
}

// 初始化环形布局
const initRadialLayout = () => {
  if (!container.value || props.graphData.nodes.length === 0) return

  const width = container.value.clientWidth || props.width
  const height = container.value.clientHeight || props.height

  // 清空容器
  d3.select(container.value).selectAll('*').remove()

  // 创建SVG
  svg.value = d3.select(container.value)
    .append('svg')
    .attr('width', width)
    .attr('height', height)

  // 创建容器组
  const g = svg.value.append('g')

  // 添加缩放行为
  const zoom = d3.zoom()
    .scaleExtent([0.1, 4])
    .on('zoom', (event) => {
      g.attr('transform', event.transform)
    })

  svg.value.call(zoom)

  // 创建力导向模拟
  simulation.value = d3.forceSimulation(props.graphData.nodes)
    .force('charge', d3.forceManyBody().strength(-300))
    .force('link', d3.forceLink(props.graphData.edges)
      .id(d => d.id)
      .distance(d => {
        // 根据连接强度调整距离
        return d.strength ? 50 / d.strength : 100
      })
    )
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(25))

  // 应用环形布局约束
  applyRadialConstraints(width, height)

  // 绘制连线
  const links = g.append('g')
    .attr('class', 'links')
    .selectAll('line')
    .data(props.graphData.edges)
    .enter()
    .append('line')
    .attr('stroke', '#666')
    .attr('stroke-width', d => Math.sqrt(d.strength || 1))
    .attr('stroke-opacity', 0.6)

  // 绘制节点
  const nodes = g.append('g')
    .attr('class', 'nodes')
    .selectAll('circle')
    .data(props.graphData.nodes)
    .enter()
    .append('circle')
    .attr('r', d => {
      const degree = getNodeDegree(d)
      return Math.min(8 + degree * 2, 20)
    })
    .attr('fill', d => getNodeColor(d))
    .attr('stroke', '#fff')
    .attr('stroke-width', 2)
    .style('cursor', 'pointer')
    .call(d3.drag()
      .on('start', dragStarted)
      .on('drag', dragged)
      .on('end', dragEnded)
    )

  // 添加节点标签
  const labels = g.append('g')
    .attr('class', 'labels')
    .selectAll('text')
    .data(props.graphData.nodes)
    .enter()
    .append('text')
    .text(d => getNodeLabel(d))
    .attr('font-size', '12px')
    .attr('text-anchor', 'middle')
    .attr('dy', '.35em')
    .style('pointer-events', 'none')

  // 更新位置
  simulation.value.on('tick', () => {
    links
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y)

    nodes
      .attr('cx', d => d.x)
      .attr('cy', d => d.y)

    labels
      .attr('x', d => d.x)
      .attr('y', d => d.y)
  })

  // 添加交互事件
  nodes.on('click', (event, d) => {
    event.stopPropagation()
    selectedNode.value = d
    emit('node-click', d)
  })

  links.on('click', (event, d) => {
    event.stopPropagation()
    selectedEdge.value = d
    emit('edge-click', d)
  })

  svg.value.on('click', () => {
    selectedNode.value = null
    selectedEdge.value = null
  })
}

// 应用环形约束
const applyRadialConstraints = (width, height) => {
  const centerX = width / 2
  const centerY = height / 2
  const maxRadius = Math.min(width, height) * 0.4

  simulation.value.force('radial', d3.forceRadial(maxRadius, centerX, centerY)
    .strength(0.1)
  )

  // 如果指定了中心节点，为其添加向心力
  if (selectedCenterNode.value) {
    simulation.value.force('centerNode', (alpha) => {
      const centerNodeData = props.graphData.nodes.find(n => n.id === selectedCenterNode.value)
      if (centerNodeData) {
        centerNodeData.vx += (centerX - centerNodeData.x) * alpha * 0.8
        centerNodeData.vy += (centerY - centerNodeData.y) * alpha * 0.8
      }
    })
  }
}

// 获取节点颜色
const getNodeColor = (node) => {
  const colors = [
    '#60a5fa', '#34d399', '#f59e0b', '#f472b6', '#22d3ee',
    '#a78bfa', '#f97316', '#4ade80', '#f43f5e', '#2dd4bf'
  ]

  const type = node.entity_type || node.labels?.[0] || 'default'
  let hash = 0
  for (let i = 0; i < type.length; i++) {
    hash = type.charCodeAt(i) + ((hash << 5) - hash)
  }

  return colors[Math.abs(hash) % colors.length]
}

// 拖拽事件处理
const dragStarted = (event, d) => {
  if (!event.active) simulation.value.alphaTarget(0.3).restart()
  d.fx = d.x
  d.fy = d.y
}

const dragged = (event, d) => {
  d.fx = event.x
  d.fy = event.y
}

const dragEnded = (event, d) => {
  if (!event.active) simulation.value.alphaTarget(0)
  d.fx = null
  d.fy = null
}

// 更新布局
const updateLayout = async () => {
  if (!container.value) return

  isUpdating.value = true

  try {
    // 使用 layoutManager 执行环形布局
    const positions = await layoutManager.radialLayout(
      { nodes: props.graphData.nodes, edges: props.graphData.edges },
      {
        width: container.value.clientWidth,
        height: container.value.clientHeight,
        centerNode: selectedCenterNode.value,
        radiusStep: radiusStep.value
      }
    )

    // 应用新位置到图形
    applyPositionsToGraph(positions)

    emit('layout-changed', 'radial', positions)
  } catch (error) {
    console.error('布局更新失败:', error)
    message.error('布局更新失败')
  } finally {
    isUpdating.value = false
  }
}

// 应用位置到图形
const applyPositionsToGraph = (positions) => {
  const duration = 1000

  props.graphData.nodes.forEach(node => {
    const pos = positions[node.id]
    if (pos) {
      d3.select(`circle[data-id="${node.id}"]`)
        .transition()
        .duration(duration)
        .attr('cx', pos.x)
        .attr('cy', pos.y)

      d3.select(`text[data-id="${node.id}"]`)
        .transition()
        .duration(duration)
        .attr('x', pos.x)
        .attr('y', pos.y)
    }
  })

  props.graphData.edges.forEach(edge => {
    d3.select(`line[data-id="${edge.id}"]`)
      .transition()
      .duration(duration)
      .attr('x1', positions[edge.source_id]?.x || edge.source.x)
      .attr('y1', positions[edge.source_id]?.y || edge.source.y)
      .attr('x2', positions[edge.target_id]?.x || edge.target.x)
      .attr('y2', positions[edge.target_id]?.y || edge.target.y)
  })
}

// 缩放控制
const zoomIn = () => {
  svg.value.transition().duration(300).call(
    d3.zoom().transform,
    d3.zoomIdentity.scale(1.3)
  )
}

const zoomOut = () => {
  svg.value.transition().duration(300).call(
    d3.zoom().transform,
    d3.zoomIdentity.scale(0.7)
  )
}

const resetView = () => {
  svg.value.transition().duration(500).call(
    d3.zoom().transform,
    d3.zoomIdentity
  )
}

// 监听数据变化
watch(() => props.graphData, () => {
  if (props.graphData.nodes.length > 0) {
    initRadialLayout()
  }
}, { deep: true, immediate: true })

// 监听容器大小变化
const resizeObserver = new ResizeObserver(() => {
  if (container.value) {
    const width = container.value.clientWidth
    const height = container.value.clientHeight
    svg.value.attr('width', width).attr('height', height)
  }
})

onMounted(() => {
  if (props.graphData.nodes.length > 0) {
    initRadialLayout()
  }

  // 默认选择第一个节点作为中心节点
  if (props.graphData.nodes.length > 0) {
    selectedCenterNode.value = props.graphData.nodes[0].id
  }

  if (container.value) {
    resizeObserver.observe(container.value)
  }
})

onUnmounted(() => {
  if (simulation.value) {
    simulation.value.stop()
  }
  if (container.value) {
    resizeObserver.unobserve(container.value)
  }
})
</script>

<style lang="less" scoped>
.radial-layout-container {
  position: relative;
  width: 100%;
  height: 100%;
  background: #f8f9fa;
  border-radius: 8px;
  overflow: hidden;
}

.canvas-container {
  width: 100%;
  height: 100%;
}

.control-panel {
  position: absolute;
  top: 16px;
  left: 16px;
  background: var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  border: var(--glass-border);
  border-radius: 8px;
  padding: 12px;
  box-shadow: var(--shadow-md);
  display: flex;
  align-items: center;
  gap: 16px;
  z-index: 1000;

  .layout-controls {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .zoom-controls {
    display: flex;
    gap: 4px;

    button {
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
  }
}

.node-detail-panel {
  position: absolute;
  background: var(--glass-bg);
  border-radius: 8px;
  box-shadow: var(--shadow-lg);
  backdrop-filter: var(--glass-blur);
  width: 260px;
  min-height: 120px;
  z-index: 1001;
  border: var(--glass-border);

  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    border-bottom: var(--glass-border);
    background: rgba(15, 23, 42, 0.45);
    border-radius: 8px 8px 0 0;

    h4 {
      margin: 0;
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary);
    }
  }

  .panel-content {
    padding: 16px;

    .detail-item {
      display: flex;
      margin-bottom: 8px;
      align-items: flex-start;

      &:last-child {
        margin-bottom: 0;
      }

      .label {
        min-width: 60px;
        font-weight: 600;
        color: var(--text-tertiary);
        font-size: 12px;
        flex-shrink: 0;
      }

      .value {
        color: var(--text-primary);
        font-size: 12px;
        word-break: break-word;
        flex: 1;
      }
    }
  }
}

:deep(svg) {
  .links line {
    transition: stroke 0.2s ease;
  }

  .nodes circle {
    transition: all 0.2s ease;

    &:hover {
      stroke-width: 3;
      filter: brightness(1.2);
    }
  }

  .labels text {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    fill: var(--text-primary);
    background: transparent;
  }
}
</style>
