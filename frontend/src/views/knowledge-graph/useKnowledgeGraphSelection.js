import { ref } from 'vue'

export function useKnowledgeGraphSelection({ router }) {
  const selectedNodeId = ref('')

  function clearSelection() {
    selectedNodeId.value = ''
  }

  function selectNode(node) {
    selectedNodeId.value = node?.id || ''
  }

  function openNode(node) {
    if (!node?.route) return
    router.push(node.route)
  }

  return {
    selectedNodeId,
    clearSelection,
    selectNode,
    openNode,
  }
}
