import { computed, nextTick, onBeforeUnmount, reactive, ref } from 'vue'

const GRAPH_DRAG_BLOCK_SELECTOR = 'button, a, input, textarea, .graph-legend-card, .graph-source-note'
const GRAPH_CLICK_BLOCK_SELECTOR = '.board-node, .graph-legend-card, .graph-source-note'

export function useGraphInteractions({
  graphPanelRef,
  graphPanelShellRef,
  graphLegendRef,
  graphChartWidth,
  graphChartHeight,
  defaultZoom,
  minZoom,
  maxZoom,
  clearSelection,
}) {
  const graphZoom = ref(defaultZoom)
  const graphDrag = reactive({ active: false, moved: false, x: 0, y: 0, scrollLeft: 0, scrollTop: 0 })
  const legendPosition = reactive({ x: null, y: null })
  const legendDrag = reactive({ active: false, offsetX: 0, offsetY: 0 })

  const graphLegendStyle = computed(() => {
    if (legendPosition.x === null || legendPosition.y === null) {
      return { top: '14px', right: '14px' }
    }
    return {
      left: `${legendPosition.x}px`,
      top: `${legendPosition.y}px`,
    }
  })

  const scaledGraphWidth = computed(() => Math.ceil(graphChartWidth.value * graphZoom.value))
  const scaledGraphHeight = computed(() => Math.ceil(graphChartHeight.value * graphZoom.value))

  function resetViewport() {
    graphZoom.value = defaultZoom
    graphPanelRef.value?.scrollTo({ left: 0, top: 0, behavior: 'smooth' })
  }

  function setGraphZoom(nextZoom, event) {
    const panel = graphPanelRef.value
    const currentZoom = graphZoom.value
    const zoom = Math.min(maxZoom, Math.max(minZoom, Number(nextZoom.toFixed(2))))
    if (zoom === currentZoom) return

    if (!event || !panel) {
      graphZoom.value = zoom
      return
    }

    const rect = panel.getBoundingClientRect()
    const cursorX = event.clientX - rect.left
    const cursorY = event.clientY - rect.top
    const logicalX = (panel.scrollLeft + cursorX) / currentZoom
    const logicalY = (panel.scrollTop + cursorY) / currentZoom
    graphZoom.value = zoom
    nextTick(() => {
      panel.scrollLeft = logicalX * zoom - cursorX
      panel.scrollTop = logicalY * zoom - cursorY
    })
  }

  function handleGraphWheel(event) {
    const delta = event.deltaY > 0 ? -0.08 : 0.08
    setGraphZoom(graphZoom.value + delta, event)
  }

  function startGraphDrag(event) {
    if (event.button !== 0) return
    if (event.target?.closest?.(GRAPH_DRAG_BLOCK_SELECTOR)) return
    const panel = graphPanelRef.value
    if (!panel) return
    graphDrag.active = true
    graphDrag.moved = false
    graphDrag.x = event.clientX
    graphDrag.y = event.clientY
    graphDrag.scrollLeft = panel.scrollLeft
    graphDrag.scrollTop = panel.scrollTop
    event.preventDefault()
  }

  function handleGraphDrag(event) {
    if (!graphDrag.active) return
    const panel = graphPanelRef.value
    if (!panel) return
    const deltaX = event.clientX - graphDrag.x
    const deltaY = event.clientY - graphDrag.y
    if (Math.abs(deltaX) > 3 || Math.abs(deltaY) > 3) {
      graphDrag.moved = true
    }
    panel.scrollLeft = graphDrag.scrollLeft - deltaX
    panel.scrollTop = graphDrag.scrollTop - deltaY
  }

  function stopGraphDrag() {
    graphDrag.active = false
  }

  function clampLegendPosition(x, y) {
    const shell = graphPanelShellRef.value
    const card = graphLegendRef.value
    if (!shell || !card) return { x, y }
    const padding = 8
    const maxX = Math.max(padding, shell.clientWidth - card.offsetWidth - padding)
    const maxY = Math.max(padding, shell.clientHeight - card.offsetHeight - padding)
    return {
      x: Math.min(Math.max(padding, x), maxX),
      y: Math.min(Math.max(padding, y), maxY),
    }
  }

  function startLegendDrag(event) {
    if (event.button !== 0) return
    const shell = graphPanelShellRef.value
    const card = graphLegendRef.value
    if (!shell || !card) return
    const shellRect = shell.getBoundingClientRect()
    const cardRect = card.getBoundingClientRect()
    const currentX = cardRect.left - shellRect.left
    const currentY = cardRect.top - shellRect.top
    const startPosition = clampLegendPosition(currentX, currentY)
    legendPosition.x = startPosition.x
    legendPosition.y = startPosition.y
    legendDrag.active = true
    legendDrag.offsetX = event.clientX - cardRect.left
    legendDrag.offsetY = event.clientY - cardRect.top
    window.addEventListener('mousemove', handleLegendDrag)
    window.addEventListener('mouseup', stopLegendDrag)
  }

  function handleLegendDrag(event) {
    if (!legendDrag.active) return
    const shell = graphPanelShellRef.value
    if (!shell) return
    const shellRect = shell.getBoundingClientRect()
    const next = clampLegendPosition(
      event.clientX - shellRect.left - legendDrag.offsetX,
      event.clientY - shellRect.top - legendDrag.offsetY,
    )
    legendPosition.x = next.x
    legendPosition.y = next.y
  }

  function stopLegendDrag() {
    legendDrag.active = false
    window.removeEventListener('mousemove', handleLegendDrag)
    window.removeEventListener('mouseup', stopLegendDrag)
  }

  function handleGraphPanelClick(event) {
    if (graphDrag.moved) {
      graphDrag.moved = false
      return
    }
    if (event.target?.closest?.(GRAPH_CLICK_BLOCK_SELECTOR)) return
    clearSelection?.()
  }

  onBeforeUnmount(() => {
    stopLegendDrag()
  })

  return {
    graphZoom,
    graphDrag,
    legendDrag,
    graphLegendStyle,
    scaledGraphWidth,
    scaledGraphHeight,
    resetViewport,
    handleGraphWheel,
    startGraphDrag,
    handleGraphDrag,
    stopGraphDrag,
    startLegendDrag,
    handleGraphPanelClick,
  }
}
