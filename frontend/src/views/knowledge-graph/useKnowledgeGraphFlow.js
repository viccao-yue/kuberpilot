import { nextTick, onMounted, ref, watch } from 'vue'

export function useKnowledgeGraphFlow({
  route,
  router,
  filters,
  graph,
  graphNodes,
  selectedNodeId,
  traceTopologyDatasourceId,
  traceTopologyDialogVisible,
  traceTopologyDialogReady,
  fetchGraph,
}) {
  const loading = ref(false)
  const activeTab = ref(route.query.tab === 'config' ? 'config' : 'graph')

  function buildQueryParams() {
    const params = {}
    if (filters.environment) params.environment = filters.environment
    if (filters.system) params.system = filters.system
    if (filters.service) params.service = filters.service
    return params
  }

  async function loadGraph() {
    if (activeTab.value !== 'graph') return
    loading.value = true
    try {
      graph.value = await fetchGraph(buildQueryParams())
      if (!filters.environment && graph.value.filters?.environments?.length) {
        const defaultEnvironment = graph.value.filters.default_environment
        filters.environment = graph.value.filters.environments.includes(defaultEnvironment)
          ? defaultEnvironment
          : graph.value.filters.environments[0]
        await loadGraph()
        return
      }
      if (selectedNodeId.value && !graphNodes.value.some(item => item.id === selectedNodeId.value)) {
        selectedNodeId.value = ''
      }
      await nextTick()
    } finally {
      loading.value = false
    }
  }

  function resetFilters() {
    filters.system = ''
    filters.service = ''
    selectedNodeId.value = ''
    loadGraph()
  }

  function handleEnvironmentChange() {
    filters.system = ''
    filters.service = ''
    selectedNodeId.value = ''
    loadGraph()
  }

  function ensureGraphLoaded() {
    nextTick(() => {
      if (!(graph.value.nodes || []).length && !filters.environment) {
        loadGraph()
      }
    })
  }

  function handleTabChange(tabName) {
    const nextQuery = { ...route.query }
    if (tabName === 'config') {
      nextQuery.tab = 'config'
    } else {
      delete nextQuery.tab
    }
    router.replace({ path: '/aiops/knowledge', query: nextQuery })
    if (tabName === 'graph') ensureGraphLoaded()
  }

  function openTraceTopology() {
    if (!traceTopologyDatasourceId.value) return
    traceTopologyDialogReady.value = false
    traceTopologyDialogVisible.value = true
  }

  watch(
    () => route.query.tab,
    (value) => {
      const nextTab = value === 'config' ? 'config' : 'graph'
      if (activeTab.value !== nextTab) {
        activeTab.value = nextTab
        if (nextTab === 'graph') ensureGraphLoaded()
      }
    },
  )

  onMounted(() => {
    if (activeTab.value === 'graph') loadGraph()
  })

  return {
    loading,
    activeTab,
    loadGraph,
    resetFilters,
    handleEnvironmentChange,
    handleTabChange,
    openTraceTopology,
  }
}
