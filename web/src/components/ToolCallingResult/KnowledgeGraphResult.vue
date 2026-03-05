<template>
  <div class="knowledge-graph-result">
    <!-- 统计类结果展示 -->
    <div v-if="isStatisticsResult" class="statistics-result">
      <div class="stats-header">
        <BarChartOutlined class="stats-icon" />
        <span class="stats-title">知识图谱统计结果</span>
      </div>
      <div class="stats-summary">
        <div class="stats-scope" :title="statisticsData.scope || '整个图谱'">{{ statisticsData.scope || '整个图谱' }}</div>
        <div class="stats-total">
          <span class="total-number">{{ statisticsData.total_count }}</span>
          <span class="total-label">种类型</span>
        </div>
      </div>
      <div class="stats-breakdown" v-if="Object.keys(statisticsData.results_by_type || {}).length > 0">
        <div 
          v-for="(typeData, typeName) in statisticsData.results_by_type" 
          :key="typeName"
          class="stat-category"
        >
          <div class="category-header">
            <span class="category-name" :title="typeName">{{ typeName }}</span>
            <span class="category-count">{{ typeData.count }} 种</span>
          </div>
          <div class="category-entities">
            <a-tag 
              v-for="entity in (typeData.entities || []).slice(0, 10)" 
              :key="entity"
              class="entity-tag"
              :title="entity"
            >
              {{ entity }}
            </a-tag>
            <span v-if="(typeData.entities || []).length > 10" class="more-hint">
              等 {{ (typeData.entities || []).length }} 项
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 图谱搜索类结果展示 -->
    <div v-else class="search-result">
      <div class="kg-header" v-if="!hideHeader">
        <h4><DeploymentUnitOutlined /> 知识图谱推理结果</h4>
        <div class="result-summary">
          找到 <strong>{{ totalNodes }}</strong> 个实体、<strong>{{ totalRelations }}</strong> 个关系
          <span v-if="isTruncated" class="truncated-hint">
            （显示前 {{ totalRelations }} 条，共 {{ totalTriplesCount }} 条）
          </span>
        </div>
      </div>

      <!-- 推理链路（仅搜索类显示） -->
      <div class="graph-content" v-if="showContent">
        <div class="content-text">{{ contentPreview }}</div>
      </div>

      <div class="kg-reasoning" v-show="!isCollapsed && reasoningPaths.length > 0">
        <div class="reasoning-header">
          <span class="reasoning-title">
            <BranchesOutlined /> 推理链路
          </span>
          <span class="reasoning-hint">共 {{ reasoningPaths.length }} 条路径</span>
        </div>

        <div class="reasoning-paths">
          <div 
            class="reasoning-path" 
            v-for="(path, pIndex) in reasoningPaths" 
            :key="'path_'+pIndex"
          >
            <div class="path-number">{{ pIndex + 1 }}</div>
            <div class="path-content">
              <template v-for="(step, sIndex) in path" :key="'step_'+pIndex+'_'+sIndex">
                <span class="entity source">{{ step.source }}</span>
                <span class="relation-arrow">
                  <span class="arrow-line"></span>
                  <span class="relation-label">{{ step.type }}</span>
                  <span class="arrow-head">→</span>
                </span>
                <span class="entity target">{{ step.target }}</span>
                <span v-if="sIndex < path.length - 1" class="path-separator">→</span>
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { 
  DeploymentUnitOutlined, 
  BarChartOutlined,
  BranchesOutlined 
} from '@ant-design/icons-vue'

const props = defineProps({
  data: {
    type: [Array, Object],
    required: true
  },
  hideHeader: {
    type: Boolean,
    default: false
  }
})

const isCollapsed = ref(false)

// 英文关系类型到中文的映射
const RELATION_TYPE_MAP = {
  'OCCUR_AT': '发生于',
  'TYPICAL_CAUSE': '典型病因',
  'MAIN_CAUSE': '主要病因',
  'TREATMENT_MEASURE': '处置措施',
  'COMMON_DEFECT': '常见缺陷',
  'TYPICAL_DEFECT': '典型缺陷',
  'HAS_DEFECT': '存在缺陷',
  'HAS_CAUSE': '存在病因',
  'LOCATED_AT': '位于',
  'BELONGS_TO': '属于',
  'RELATED_TO': '相关',
}

// 将关系类型转换为中文
const normalizeRelationType = (type) => {
  if (!type) return '相关'
  const upperType = type.toUpperCase()
  return RELATION_TYPE_MAP[upperType] || RELATION_TYPE_MAP[type] || type
}

// 判断是否为统计类结果
const isStatisticsResult = computed(() => {
  if (!props.data || typeof props.data !== 'object') return false
  return props.data.query_type === 'statistics'
})

// 统计数据
const statisticsData = computed(() => {
  if (!isStatisticsResult.value) return {}
  return {
    keyword: props.data.keyword || '',
    query_labels: props.data.query_labels || [],
    scope: props.data.scope || '整个图谱',
    total_count: props.data.total_count || 0,
    results_by_type: props.data.results_by_type || {},
    text_summary: props.data.text_summary || ''
  }
})

// 计算属性：解析图谱数据
const graphData = computed(() => {
  const nodes = new Map()
  const edges = []
  let edgeId = 0

  // 跳过统计类结果
  if (isStatisticsResult.value) {
    return { nodes: [], edges: [] }
  }

  // 处理新格式数据：只关注 triples 字段
  if (props.data && typeof props.data === 'object' && 'triples' in props.data) {
    const { triples = [] } = props.data

    // 处理 triples 数据
    triples.forEach(triple => {
      if (Array.isArray(triple) && triple.length >= 3) {
        const [source, relation, target] = triple

        // 添加源节点
        if (source && typeof source === 'string') {
          if (!nodes.has(source)) {
            nodes.set(source, {
              id: source,
              name: source
            })
          }
        }

        // 添加目标节点
        if (target && typeof target === 'string') {
          if (!nodes.has(target)) {
            nodes.set(target, {
              id: target,
              name: target
            })
          }
        }

        // 添加边（避免重复）
        if (source && target && relation &&
            typeof source === 'string' &&
            typeof target === 'string' &&
            typeof relation === 'string') {
          const edgeKey = `${source}-${relation}-${target}`
          const existingEdge = edges.find(e => 
            e.source_id === source && e.target_id === target && e.type === relation
          )
          if (!existingEdge) {
            edges.push({
              source_id: source,
              target_id: target,
              type: relation,
              id: `edge_${edgeId++}`
            })
          }
        }
      }
    })
  }

  return {
    nodes: Array.from(nodes.values()),
    edges: edges
  }
})

// 统计信息 - 使用 Set 确保准确去重
const totalNodes = computed(() => graphData.value.nodes.length)
const totalRelations = computed(() => graphData.value.edges.length)

const graphContent = computed(() => {
  if (!props.data || typeof props.data !== 'object') return ''
  const content = props.data.content
  return typeof content === 'string' ? content.trim() : ''
})

const showContent = computed(() => !isStatisticsResult.value && graphContent.value)

const contentPreview = computed(() => {
  const content = graphContent.value
  if (!content) return ''
  return content.length > 800 ? `${content.slice(0, 800)}...` : content
})

// 截断信息
const isTruncated = computed(() => props.data?.is_truncated || false)
const totalTriplesCount = computed(() => props.data?.total_triples || totalRelations.value)

// 将三元组按连通关系合并为有序路径
const reasoningPaths = computed(() => {
  // 统计类不显示推理链路
  if (isStatisticsResult.value) return []
  
  const nodes = graphData.value.nodes
  const edges = graphData.value.edges
  if (!Array.isArray(nodes) || !Array.isArray(edges) || edges.length === 0) return []

  const nameOf = (id) => {
    const node = nodes.find(n => n.id === id)
    return node?.name || id
  }

  // 构建出边映射
  const outMap = new Map()
  const inDegree = new Map()

  edges.forEach(e => {
    if (!outMap.has(e.source_id)) outMap.set(e.source_id, [])
    outMap.get(e.source_id).push(e)
    
    // 统计入度
    inDegree.set(e.target_id, (inDegree.get(e.target_id) || 0) + 1)
  })

  // 找到所有入度为0的节点作为路径起点
  const allNodeIds = new Set([...outMap.keys(), ...inDegree.keys()])
  let startNodes = Array.from(allNodeIds).filter(id => !inDegree.has(id) || inDegree.get(id) === 0)
  
  // 如果没有入度为0的节点（环形图），选择有出边的节点
  if (startNodes.length === 0) {
    startNodes = Array.from(outMap.keys())
  }

  const paths = []
  const visitedEdges = new Set()
  const MAX_PATHS = 3  // 限制最大路径数，提高性能和可读性
  const MAX_STEPS = 5  // 限制单条路径最大步数

  for (const start of startNodes) {
    if (paths.length >= MAX_PATHS) break
    
    const stack = [{ nodeId: start, path: [], visited: new Set([start]) }]
    
    while (stack.length > 0 && paths.length < MAX_PATHS) {
      const { nodeId, path, visited } = stack.pop()
      
      const outEdges = outMap.get(nodeId) || []
      let extended = false
      
      for (const edge of outEdges) {
        const edgeKey = `${edge.source_id}-${edge.type}-${edge.target_id}`
        
        if (!visitedEdges.has(edgeKey) && !visited.has(edge.target_id) && path.length < MAX_STEPS) {
          const newPath = [...path, {
            source: nameOf(edge.source_id),
            type: normalizeRelationType(edge.type),
            target: nameOf(edge.target_id)
          }]
          
          const newVisited = new Set(visited)
          newVisited.add(edge.target_id)
          
          stack.push({
            nodeId: edge.target_id,
            path: newPath,
            visited: newVisited
          })
          
          visitedEdges.add(edgeKey)
          extended = true
        }
      }
      
      // 如果无法继续扩展且路径非空，保存路径
      if (!extended && path.length > 0) {
        paths.push(path)
      }
    }
  }

  // 如果没有找到路径，将每个三元组作为单独的路径
  if (paths.length === 0 && edges.length > 0) {
    return edges.slice(0, MAX_PATHS).map(e => [{
      source: nameOf(e.source_id),
      type: normalizeRelationType(e.type),
      target: nameOf(e.target_id)
    }])
  }

  // 去重：移除内容相同的路径（英文/中文关系类型已统一）
  const pathKeys = new Set()
  const uniquePaths = paths.filter(path => {
    const key = path.map(step => `${step.source}|${step.type}|${step.target}`).join('→')
    if (pathKeys.has(key)) return false
    pathKeys.add(key)
    return true
  })

  // 按路径长度排序，优先显示较长的路径
  return uniquePaths.sort((a, b) => b.length - a.length).slice(0, MAX_PATHS)
})
</script>

<style lang="less" scoped>
.knowledge-graph-result {
  background: transparent;
  border-radius: 12px;

  // ============ 统计类结果样式 ============
  .statistics-result {
    padding: 16px;
    background: rgba(6, 182, 212, 0.05); /* 极淡的青色背景 */
    border-radius: 12px;
    border: 1px solid rgba(6, 182, 212, 0.2);

    .stats-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 16px;

      .stats-icon {
        font-size: 20px;
        color: var(--main-color);
      }

      .stats-title {
        font-size: 15px;
        font-weight: 600;
        color: var(--text-primary);
      }
    }

    .stats-summary {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px;
      background: var(--bg-elevated);
      border-radius: 8px;
      margin-bottom: 16px;
      border: var(--glass-border);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);

      .stats-scope {
        font-size: 14px;
        color: var(--text-secondary);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 60%;
      }

      .stats-total {
        display: flex;
        align-items: baseline;
        gap: 4px;

        .total-number {
          font-size: 28px;
          font-weight: 700;
          color: var(--main-color);
          line-height: 1;
          text-shadow: 0 0 10px rgba(6, 182, 212, 0.3);
        }

        .total-label {
          font-size: 13px;
          color: var(--text-secondary);
        }
      }
    }

    .stats-breakdown {
      display: flex;
      flex-direction: column;
      gap: 12px;

      .stat-category {
        background: var(--bg-elevated);
        border-radius: 8px;
        padding: 12px;
        border: var(--glass-border);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);

        .category-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;

          .category-name {
            font-weight: 600;
            color: var(--text-primary);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            max-width: 70%;
          }

          .category-count {
            font-size: 13px;
            color: var(--main-color);
            background: rgba(6, 182, 212, 0.1);
            padding: 2px 8px;
            border-radius: 12px;
            border: 1px solid rgba(6, 182, 212, 0.2);
          }
        }

        .category-entities {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;

          .entity-tag {
            margin: 0;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: var(--text-secondary);
            font-size: 12px;
            max-width: 180px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            display: inline-block;
            vertical-align: middle;
            
            &:hover {
              color: var(--text-primary);
              border-color: var(--main-color);
              background: rgba(6, 182, 212, 0.1);
            }
          }

          .more-hint {
            font-size: 12px;
            color: var(--text-tertiary);
            align-self: center;
          }
        }
      }
    }
  }

  // ============ 搜索类结果样式 ============
  .search-result {
    .kg-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 12px 16px;
      background: rgba(255, 255, 255, 0.03);
      border-radius: 12px 12px 0 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);

      h4 {
        margin: 0;
        color: var(--main-color);
        font-size: 14px;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 6px;
      }

      .result-summary {
        font-size: 13px;
        color: var(--text-secondary);

        strong {
          color: var(--main-color);
          font-weight: 600;
        }
        
        .truncated-hint {
          font-size: 12px;
          color: #f59e0b;
          margin-left: 4px;
        }
      }
    }

    // ============ 推理链路样式 ============
    .graph-content {
      margin: 8px 0 12px;
      padding: 10px 12px;
      background: rgba(15, 23, 42, 0.35);
      border: 1px solid rgba(148, 163, 184, 0.2);
      border-radius: 8px;
      color: var(--text-secondary);
      font-size: 13px;
      line-height: 1.6;
      white-space: pre-wrap;
    }

    .kg-reasoning {
      margin: 12px 8px 10px;
      padding: 16px;
      border-radius: 12px;
      border: 1px solid rgba(124, 58, 237, 0.2);
      background: rgba(124, 58, 237, 0.05);

      .reasoning-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;

        .reasoning-title {
          display: flex;
          align-items: center;
          gap: 6px;
          font-weight: 600;
          font-size: 14px;
          color: #a78bfa;
        }

        .reasoning-hint {
          font-size: 12px;
          color: #c4b5fd;
          background: rgba(0, 0, 0, 0.2);
          padding: 2px 8px;
          border-radius: 10px;
        }
      }

      .reasoning-paths {
        display: flex;
        flex-direction: column;
        gap: 10px;
      }

      .reasoning-path {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        background: var(--bg-elevated);
        padding: 12px 14px;
        border-radius: 8px;
        border: var(--glass-border);
        transition: all 0.2s ease;

        &:hover {
          border-color: #8b5cf6;
          box-shadow: 0 0 10px rgba(139, 92, 246, 0.2);
        }

        .path-number {
          flex-shrink: 0;
          width: 24px;
          height: 24px;
          background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
          color: white;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          font-weight: 600;
        }

        .path-content {
          flex: 1;
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 6px;
          font-size: 13px;
          line-height: 1.6;
          color: var(--text-secondary);
        }

        .entity {
          padding: 3px 10px;
          border-radius: 14px;
          font-weight: 500;

          &.source {
            background: rgba(59, 130, 246, 0.15);
            color: #60a5fa;
            border: 1px solid rgba(59, 130, 246, 0.3);
          }

          &.target {
            background: rgba(34, 197, 94, 0.15);
            color: #4ade80;
            border: 1px solid rgba(34, 197, 94, 0.3);
          }
        }

        .relation-arrow {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          color: #a78bfa;

          .arrow-line {
            width: 16px;
            height: 2px;
            background: linear-gradient(90deg, #a78bfa 0%, #8b5cf6 100%);
            border-radius: 1px;
          }

          .relation-label {
            padding: 2px 8px;
            background: rgba(139, 92, 246, 0.1);
            border: 1px solid rgba(139, 92, 246, 0.3);
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            color: #c4b5fd;
          }

          .arrow-head {
            color: #a78bfa;
            font-weight: bold;
          }
        }

        .path-separator {
          color: #8b5cf6;
          margin: 0 2px;
        }
      }
    }
  }
}
</style>
