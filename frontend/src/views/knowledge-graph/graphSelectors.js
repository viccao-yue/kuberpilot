export function getVisibleSummary(nodes, edges) {
  const kindCounts = nodes.reduce((acc, node) => {
    acc[node.kind] = (acc[node.kind] || 0) + 1
    return acc
  }, {})

  return {
    node_count: nodes.length,
    edge_count: edges.length,
    service_count: kindCounts.service || 0,
    datasource_count: kindCounts.datasource || 0,
    infrastructure_count: kindCounts.infrastructure || 0,
    runtime_component_count: kindCounts.runtime_component || 0,
  }
}

export function buildSelectedFocus(selectedId, edges) {
  const nodeIds = new Set()
  const edgeIds = new Set()
  if (!selectedId) return { nodeIds, edgeIds }

  nodeIds.add(selectedId)
  edges.forEach((edge) => {
    if (edge.source !== selectedId && edge.target !== selectedId) return
    edgeIds.add(edge.id)
    nodeIds.add(edge.source)
    nodeIds.add(edge.target)
  })
  return { nodeIds, edgeIds }
}

export function getSelectedRelationStats(selectedId, edges, relationLegendMap, edgeRelationLabel) {
  if (!selectedId) return []

  const counter = new Map()
  edges.forEach((edge) => {
    if (edge.source !== selectedId && edge.target !== selectedId) return
    const key = edge.relation || 'related'
    counter.set(key, (counter.get(key) || 0) + 1)
  })

  return [...counter.entries()]
    .map(([key, count]) => ({
      key,
      label: relationLegendMap.get(key) || edgeRelationLabel(key),
      count,
    }))
    .sort((left, right) => right.count - left.count || left.label.localeCompare(right.label, 'zh-Hans-CN'))
}

export function getSelectedNeighborKindStats(selectedId, edges, nodeById, nodeKindLabel) {
  if (!selectedId) return []

  const neighborIds = new Set()
  edges.forEach((edge) => {
    if (edge.source === selectedId) neighborIds.add(edge.target)
    if (edge.target === selectedId) neighborIds.add(edge.source)
  })

  const counter = new Map()
  neighborIds.forEach((nodeId) => {
    const node = nodeById.get(nodeId)
    if (!node) return
    counter.set(node.kind, (counter.get(node.kind) || 0) + 1)
  })

  return [...counter.entries()]
    .map(([kind, count]) => ({
      kind,
      label: `${nodeKindLabel(kind)}节点`,
      count,
    }))
    .sort((left, right) => right.count - left.count || left.label.localeCompare(right.label, 'zh-Hans-CN'))
}

export function getTopServices(nodes, limit = 8) {
  return nodes
    .filter(item => item.kind === 'service')
    .slice()
    .sort((left, right) => Number(right.metric || 0) - Number(left.metric || 0))
    .slice(0, limit)
}

export function getActiveLaneDefinitions(nodes, laneDefinitions, laneKinds) {
  const presentKinds = new Set(nodes.map(node => node.kind))
  return laneDefinitions.filter(lane => laneKinds(lane).some(kind => presentKinds.has(kind)))
}

export function getNodeCategoryStats(nodes, laneDefinitions, laneKinds, palette) {
  const counts = nodes.reduce((acc, node) => {
    acc[node.kind] = (acc[node.kind] || 0) + 1
    return acc
  }, {})

  return laneDefinitions
    .map((lane) => ({
      kind: lane.kind,
      label: lane.label,
      color: palette[lane.kind] || '#64748b',
      count: laneKinds(lane).reduce((sum, kind) => sum + (counts[kind] || 0), 0),
    }))
    .filter(item => item.count > 0)
}

export function getVisibleRelationLegend(relationLegend, boardEdges) {
  const visibleRelationKeys = new Set(boardEdges.map(edge => edge.relation))
  return (relationLegend || []).filter(item => visibleRelationKeys.has(item.key))
}
