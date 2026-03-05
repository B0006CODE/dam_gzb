import { apiGet, apiPost } from './base'

export const lightragApi = {
  
  getSubgraph: async (params) => {
    const { db_id, node_label = "*", max_depth = 2, max_nodes = 100 } = params

    if (!db_id) {
      throw new Error('db_id is required')
    }

    const queryParams = new URLSearchParams({
      db_id: db_id,
      node_label: node_label,
      max_depth: max_depth.toString(),
      max_nodes: max_nodes.toString()
    })

    return await apiGet(`/api/graph/lightrag/subgraph?${queryParams.toString()}`, {}, true)
  },

  
  getDatabases: async () => {
    return await apiGet('/api/graph/lightrag/databases', {}, true)
  },

  
  getLabels: async (db_id) => {
    if (!db_id) {
      throw new Error('db_id is required')
    }

    const queryParams = new URLSearchParams({
      db_id: db_id
    })

    return await apiGet(`/api/graph/lightrag/labels?${queryParams.toString()}`, {}, true)
  },

  
  getStats: async (db_id) => {
    if (!db_id) {
      throw new Error('db_id is required')
    }

    const queryParams = new URLSearchParams({
      db_id: db_id
    })

    return await apiGet(`/api/graph/lightrag/stats?${queryParams.toString()}`, {}, true)
  }
}

export async function getPagedSubgraph(params) {
  const {
    db_id,
    center = '*',
    depth = 2,
    limit = 200,
    page = 1,
    fields = 'compact',
  } = params || {}

  if (!db_id) throw new Error('db_id is required')

  const qp = new URLSearchParams({
    db_id: String(db_id),
    center: String(center),
    depth: String(depth),
    limit: String(limit),
    page: String(page),
    fields: String(fields),
  })

  return await apiGet(`/api/graph/subgraph?${qp.toString()}`, {}, true)
}

export const neo4jApi = {
  
  getSampleNodes: async (kgdb_name = 'neo4j', num = 100) => {
    const queryParams = new URLSearchParams({
      kgdb_name: kgdb_name,
      num: num.toString()
    })

    return await apiGet(`/api/graph/neo4j/nodes?${queryParams.toString()}`, {}, true)
  },

  
  queryNode: async (entity_name) => {
    if (!entity_name) {
      throw new Error('entity_name is required')
    }

    const queryParams = new URLSearchParams({
      entity_name: entity_name
    })

    return await apiGet(`/api/graph/neo4j/node?${queryParams.toString()}`, {}, true)
  },

  
  expandNode: async (node_id, options = {}) => {
    if (!node_id) {
      throw new Error('node_id is required')
    }

    const { limit = 80 } = options || {}
    const queryParams = new URLSearchParams({
      node_id: String(node_id),
      limit: String(limit),
    })

    return await apiGet(`/api/graph/neo4j/expand?${queryParams.toString()}`, {}, true)
  },

  
  addEntities: async (file_path, kgdb_name = 'neo4j') => {
    return await apiPost('/api/graph/neo4j/add-entities', {
      file_path: file_path,
      kgdb_name: kgdb_name
    }, {}, true)
  },

  
  indexEntities: async (kgdb_name = 'neo4j') => {
    return await apiPost('/api/graph/neo4j/index-entities', {
      kgdb_name: kgdb_name
    }, {}, true)
  },

  
  getInfo: async () => {
    return await apiGet('/api/graph/neo4j/info', {}, true)
  }
}

export const getEntityTypeColor = (entityType) => {
  const colorMap = {
    'person': '#FF6B6B',
    'organization': '#4ECDC4',
    'location': '#45B7D1',
    'geo': '#45B7D1',
    'event': '#96CEB4',
    'category': '#FFEAA7',
    'equipment': '#DDA0DD',
    'athlete': '#FF7675',
    'record': '#FD79A8',
    'year': '#FDCB6E',
    'UNKNOWN': '#B2BEC3',
    'unknown': '#B2BEC3'
  }

  return colorMap[entityType] || colorMap['unknown']
}

export const calculateEdgeWidth = (weight, minWeight = 1, maxWeight = 10) => {
  const minWidth = 1
  const maxWidth = 5
  const normalizedWeight = (weight - minWeight) / (maxWeight - minWeight)
  return minWidth + normalizedWeight * (maxWidth - minWidth)
}
export const getGraphNodes = async (params = {}) => {
  console.warn('getGraphNodes is deprecated, use neo4jApi.getSampleNodes instead')
  return neo4jApi.getSampleNodes(params.kgdb_name || 'neo4j', params.num || 100)
}

export const getGraphNode = async (params = {}) => {
  console.warn('getGraphNode is deprecated, use neo4jApi.queryNode instead')
  return neo4jApi.queryNode(params.entity_name)
}

export const addByJsonl = async (file_path, kgdb_name = 'neo4j') => {
  console.warn('addByJsonl is deprecated, use neo4jApi.addEntities instead')
  return neo4jApi.addEntities(file_path, kgdb_name)
}

export const indexNodes = async (kgdb_name = 'neo4j') => {
  console.warn('indexNodes is deprecated, use neo4jApi.indexEntities instead')
  return neo4jApi.indexEntities(kgdb_name)
}

export const getGraphStats = async () => {
  console.warn('getGraphStats is deprecated, use neo4jApi.getInfo instead')
  return neo4jApi.getInfo()
}
export const graphApi = {
  getSubgraph: getPagedSubgraph,
  getDatabases: lightragApi.getDatabases,
  getLabels: lightragApi.getLabels,
  getStats: lightragApi.getStats,
  ...neo4jApi
}
