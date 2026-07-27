import { getLaneTint, laneKinds, laneNodeSortWeight, palette } from './graphMeta'

export const DEFAULT_GRAPH_ZOOM = 0.84
export const MIN_GRAPH_ZOOM = 0.5
export const MAX_GRAPH_ZOOM = 1.35
export const NODE_DOT_RADIUS = 24
export const NODE_DOT_CENTER_OFFSET = 32

const LAYOUT = {
  maxVisibleNodes: 36,
  maxRows: 12,
  baseWidth: 206,
  columnGap: 14,
  laneGap: 18,
  nodeTop: 68,
  nodeStep: 82,
  bodyTop: 76,
  leftPadding: 18,
  minChartHeight: 640,
  minChartWidth: 980,
  laneHeaderTop: 22,
  laneBottomPadding: 28,
  laneBodyBottomPadding: 112,
}

export function laneDisplayMetrics(count) {
  const visibleCount = Math.min(count, LAYOUT.maxVisibleNodes)
  const itemCount = Math.max(1, visibleCount + (count > visibleCount ? 1 : 0))
  const columns = Math.max(1, Math.min(3, Math.ceil(itemCount / LAYOUT.maxRows)))
  const rows = Math.max(1, Math.ceil(itemCount / columns))
  return {
    visibleCount,
    hiddenCount: Math.max(0, count - visibleCount),
    itemCount,
    columns,
    rows,
    width: columns * LAYOUT.baseWidth + (columns - 1) * LAYOUT.columnGap,
  }
}

export function getGraphChartHeight(nodes, activeLaneDefinitions) {
  const maxLaneRows = Math.max(1, ...activeLaneDefinitions.map((lane) => {
    const kinds = new Set(laneKinds(lane))
    const count = nodes.filter(node => kinds.has(node.kind)).length
    return laneDisplayMetrics(count).rows
  }))
  return Math.max(
    LAYOUT.minChartHeight,
    LAYOUT.bodyTop + LAYOUT.nodeTop + maxLaneRows * LAYOUT.nodeStep + LAYOUT.laneBodyBottomPadding,
  )
}

export function getGraphChartWidth(nodes, activeLaneDefinitions) {
  const widths = activeLaneDefinitions.map((lane) => {
    const kinds = new Set(laneKinds(lane))
    const count = nodes.filter(node => kinds.has(node.kind)).length
    return laneDisplayMetrics(count).width
  })
  const laneCount = Math.max(widths.length, 1)
  const totalLaneWidth = widths.reduce((sum, width) => sum + width, 0)
  return Math.max(
    LAYOUT.minChartWidth,
    LAYOUT.leftPadding * 2 + totalLaneWidth + Math.max(0, laneCount - 1) * LAYOUT.laneGap,
  )
}

export function buildSwimlaneLayout(nodes, lanes, graphChartHeight) {
  const laneNodes = []
  let cursorX = LAYOUT.leftPadding

  const positionedLanes = lanes.map((lane, laneIndex) => {
    const color = palette[lane.kind] || '#64748b'
    const tint = getLaneTint(lane)
    const kinds = new Set(laneKinds(lane))
    const fullLaneItems = nodes
      .filter(node => kinds.has(node.kind))
      .sort((left, right) => {
        const weightDiff = laneNodeSortWeight(left) - laneNodeSortWeight(right)
        if (weightDiff !== 0) return weightDiff
        return String(left.label || '').localeCompare(String(right.label || ''), 'zh-Hans-CN')
      })

    const metrics = laneDisplayMetrics(fullLaneItems.length)
    const hiddenCount = metrics.hiddenCount
    const visibleItems = hiddenCount
      ? fullLaneItems.slice(0, metrics.visibleCount).concat([{
        id: `lane-summary:${lane.kind}`,
        label: `还有 ${hiddenCount} 个节点`,
        kind: 'summary',
        category: lane.label,
        metric: hiddenCount,
        isSummary: true,
      }])
      : fullLaneItems

    const laneItems = visibleItems.map((node, index) => {
      const columnIndex = Math.floor(index / metrics.rows)
      const rowIndex = index % metrics.rows
      const cardLeft = columnIndex * (LAYOUT.baseWidth + LAYOUT.columnGap) + LAYOUT.baseWidth / 2
      const centerX = cursorX + cardLeft
      const cardY = LAYOUT.nodeTop + rowIndex * LAYOUT.nodeStep
      const positioned = {
        ...node,
        x: centerX,
        centerX,
        centerY: LAYOUT.bodyTop + cardY + NODE_DOT_CENTER_OFFSET,
        cardY,
        cardLeft,
        color: palette[node.kind] || color,
      }
      laneNodes.push(positioned)
      return positioned
    })

    const positionedLane = {
      ...lane,
      x: cursorX,
      y: LAYOUT.bodyTop,
      titleY: LAYOUT.laneHeaderTop,
      width: metrics.width,
      height: graphChartHeight - LAYOUT.bodyTop - LAYOUT.laneBottomPadding,
      color,
      tint,
      index: laneIndex,
      nodes: laneItems,
      totalNodeCount: fullLaneItems.length,
      hiddenNodeCount: hiddenCount,
      columns: metrics.columns,
    }
    cursorX += metrics.width + LAYOUT.laneGap
    return positionedLane
  })

  return { lanes: positionedLanes, nodes: laneNodes }
}

export function laneStyle(lane, graphChartHeight) {
  return {
    left: `${lane.x}px`,
    top: '0px',
    width: `${lane.width}px`,
    height: `${graphChartHeight}px`,
    '--lane-color': lane.color,
  }
}

export function laneTitleStyle(lane) {
  return {
    top: `${lane.titleY}px`,
    borderColor: 'rgba(59, 130, 246, 0.28)',
    boxShadow: 'none',
  }
}

export function laneBodyStyle(lane) {
  const topColor = lane.index % 2 === 0 ? 'rgba(255, 255, 255, 0.90)' : 'rgba(248, 250, 252, 0.92)'
  return {
    top: `${lane.y}px`,
    height: `${lane.height}px`,
    background: `linear-gradient(180deg, ${topColor} 0%, ${lane.tint.fill} 100%)`,
    borderColor: lane.tint.border,
    boxShadow: 'none',
  }
}

export function nodeCardStyle(node) {
  return {
    top: `${node.cardY}px`,
    left: `${node.cardLeft}px`,
    '--node-color': node.color,
  }
}
