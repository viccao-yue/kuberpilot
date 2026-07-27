export function isFocusedNeighbor(selectedNodeId, selectedFocus, nodeId) {
  return Boolean(selectedNodeId && nodeId !== selectedNodeId && selectedFocus.nodeIds.has(nodeId))
}

export function isDimmedNode(selectedNodeId, selectedFocus, nodeId) {
  return Boolean(selectedNodeId && !selectedFocus.nodeIds.has(nodeId))
}

export function isFocusedEdge(selectedNodeId, selectedFocus, edgeId) {
  return Boolean(selectedNodeId && selectedFocus.edgeIds.has(edgeId))
}

export function isDimmedEdge(selectedNodeId, selectedFocus, edgeId) {
  return Boolean(selectedNodeId && !selectedFocus.edgeIds.has(edgeId))
}

export function buildBoardEdges(graphEdges, boardNodeMap, selectedNodeId, selectedFocus, nodeDotRadius) {
  return graphEdges
    .map((edge, index) => {
      const source = boardNodeMap.get(edge.source)
      const target = boardNodeMap.get(edge.target)
      if (!source || !target) return null

      const leftNode = source.x <= target.x ? source : target
      const rightNode = source.x <= target.x ? target : source
      const sourceX = leftNode.centerX + nodeDotRadius
      const targetX = rightNode.centerX - nodeDotRadius
      const sourceY = leftNode.centerY
      const targetY = rightNode.centerY
      const midX = (sourceX + targetX) / 2
      const edgeId = `${edge.source}-${edge.target}-${edge.relation || index}`

      return {
        id: edgeId,
        relation: edge.relation || 'default',
        path: `M ${sourceX} ${sourceY} C ${midX} ${sourceY}, ${midX} ${targetY}, ${targetX} ${targetY}`,
        focused: isFocusedEdge(selectedNodeId, selectedFocus, edge.id),
        dimmed: isDimmedEdge(selectedNodeId, selectedFocus, edge.id),
      }
    })
    .filter(Boolean)
}
