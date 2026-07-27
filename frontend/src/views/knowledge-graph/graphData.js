export function getVisibleGraphNodes(graph, hiddenNodeKinds) {
  return (graph.nodes || []).filter((node) => {
    if (hiddenNodeKinds.has(node.kind)) return false
    if (node.infra_type === 'task_resource_environment') return false
    if (String(node.id || '').startsWith('infrastructure:task_resource_env:')) return false
    return !String(node.id || '').startsWith('capability:')
  })
}

export function getGraphNodeById(graph) {
  return new Map((graph.nodes || []).map(node => [node.id, node]))
}

export function getTraceTopologyDatasourceId(graph) {
  const traceNode = (graph.nodes || []).find(node => String(node.id || '').startsWith('trace_ds:'))
  return traceNode ? String(traceNode.id).replace('trace_ds:', '') : ''
}

export function getTraceTopologyService(filters, selectedNode) {
  if (filters.service) return filters.service
  if (selectedNode?.service) return selectedNode.service
  if (selectedNode?.kind === 'service') return selectedNode.label || selectedNode.name || ''
  return ''
}

export function getVisibleGraphEdges(graph, graphNodeById) {
  return (graph.edges || []).filter((edge) => {
    const source = graphNodeById.get(edge.source)
    const target = graphNodeById.get(edge.target)
    if (!source || !target) return false
    const kinds = new Set([source.kind, target.kind])
    return (
      (edge.relation === 'system_service' && kinds.has('system') && kinds.has('service'))
      || edge.relation === 'service_deployment'
      || edge.relation === 'infrastructure_member'
      || edge.relation === 'service_runtime'
      || edge.relation === 'system_runtime'
    )
  })
}

export function getSelectedNode(nodes, selectedNodeId) {
  return nodes.find(item => item.id === selectedNodeId) || null
}

export function getRelationLegendMap(graph) {
  return new Map((graph.relation_legend || []).map(item => [item.key, item.label]))
}
