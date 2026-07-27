<template>
  <div class="knowledge-page workbench-page-shell">
    <section class="hero panel">
      <div class="hero-copy">
        <div class="hero-title-row">
          <span class="hero-icon"><el-icon><Share /></el-icon></span>
          <h2>知识图谱</h2>
          <p class="subtitle inline-subtitle">按知识环境聚合可观测性、事件中心与容器基础设施线索，形成服务视角的关系地图。</p>
        </div>
      </div>
    </section>

    <div class="stats-grid knowledge-stats">
      <div class="stat-card release-stat-card">
        <div class="stat-value">{{ filters.environment ? envLabel(filters.environment) : '--' }}</div>
        <div class="stat-label">当前环境</div>
        <div class="release-stat-desc">按环境聚合服务、基础设施与可观测线索</div>
      </div>
      <div class="stat-card release-stat-card">
        <div class="stat-value">{{ visibleSummary.node_count }}</div>
        <div class="stat-label">节点总数</div>
        <div class="release-stat-desc">当前图谱中可聚焦的实体节点数量</div>
      </div>
      <div class="stat-card release-stat-card">
        <div class="stat-value">{{ visibleSummary.edge_count }}</div>
        <div class="stat-label">关系数量</div>
        <div class="release-stat-desc">服务、依赖与运行时关系链路总量</div>
      </div>
      <div class="stat-card release-stat-card">
        <div class="stat-value">{{ visibleSummary.service_count }}</div>
        <div class="stat-label">服务对象</div>
        <div class="release-stat-desc">与当前环境关联的服务实体数量</div>
      </div>
    </div>

    <section class="workbench-inline-tip--panel knowledge-tip">
      <div class="tip-panel-head">
        <strong>图谱分析上下文</strong>
        <span>先锁定环境，再逐步缩小到系统与服务，可把事件中心、可观测性和基础设施线索汇聚到同一张关系图上。</span>
      </div>
      <div class="tip-panel-list">
        <div class="tip-panel-item">当前环境：{{ envLabel(filters.environment) || '未选择，请先锁定分析范围。' }}</div>
        <div class="tip-panel-item">已汇聚服务 {{ visibleSummary.service_count }} 个、基础设施 {{ visibleSummary.infrastructure_count }} 个、运行组件 {{ visibleSummary.runtime_component_count }} 个。</div>
        <div class="tip-panel-item">图谱视图用于排查关系脉络，图谱配置用于维护采集和聚合规则。</div>
        <div class="tip-panel-item">优先选中关键服务节点查看详情，再决定是否跳转到关联页面继续诊断。</div>
      </div>
    </section>

    <section class="tabs-card">
      <el-tabs v-model="activeTab" class="event-like-tabs" @tab-change="handleTabChange">
        <el-tab-pane name="graph">
          <template #label>
            <span class="tab-label"><el-icon><Share /></el-icon>图谱视图</span>
          </template>
        </el-tab-pane>
        <el-tab-pane name="config">
          <template #label>
            <span class="tab-label"><el-icon><Setting /></el-icon>图谱配置</span>
          </template>
        </el-tab-pane>
      </el-tabs>
    </section>

    <section class="panel tabs-panel">
      <template v-if="activeTab === 'graph'">
            <section class="topology-toolbar">
              <div class="toolbar-main">
                <span class="toolbar-label">
                  <span class="toolbar-label-dot"></span>
                  图谱范围
                </span>
                <el-select v-model="filters.environment" filterable placeholder="环境（必选）" style="width: 160px" @change="handleEnvironmentChange">
                  <el-option v-for="item in graph.filters?.environments || []" :key="item" :label="envLabel(item)" :value="item" />
                </el-select>
                <el-select v-model="filters.system" clearable filterable placeholder="系统" style="width: 180px" @change="loadGraph">
                  <el-option v-for="item in graph.filters?.systems || graph.filters?.business_lines || []" :key="item" :label="item" :value="item" />
                </el-select>
                <el-select v-model="filters.service" clearable filterable placeholder="服务" style="width: 220px" @change="loadGraph">
                  <el-option v-for="item in graph.filters?.services || []" :key="item" :label="item" :value="item" />
                </el-select>
              </div>
              <div class="toolbar-actions">
                <el-button @click="resetFilters">重置筛选</el-button>
                <el-button @click="resetCanvas">重置画布</el-button>
                <el-button type="primary" :loading="loading" @click="loadGraph">
                  <el-icon><RefreshRight /></el-icon>
                  刷新图谱
                </el-button>
              </div>
            </section>

            <div class="topology-summary-row">
              <div class="topology-kpis">
                <div class="topology-kpi">
                  <span class="kpi-label">节点数</span>
                  <span class="kpi-value">{{ visibleSummary.node_count }}</span>
                </div>
                <div class="topology-kpi">
                  <span class="kpi-label">关系数</span>
                  <span class="kpi-value">{{ visibleSummary.edge_count }}</span>
                </div>
                <div class="topology-kpi">
                  <span class="kpi-label">服务对象</span>
                  <span class="kpi-value">{{ visibleSummary.service_count }}</span>
                </div>
                <div class="topology-kpi">
                  <span class="kpi-label">基础设施</span>
                  <span class="kpi-value">{{ visibleSummary.infrastructure_count }}</span>
                </div>
                <div class="topology-kpi">
                  <span class="kpi-label">中间件 / DB</span>
                  <span class="kpi-value">{{ visibleSummary.runtime_component_count }}</span>
                </div>
                <el-button class="trace-topology-button" :disabled="!traceTopologyDatasourceId" @click="openTraceTopology">
                  <el-icon><Connection /></el-icon>
                  查看服务链路拓扑
                </el-button>
              </div>
              <div class="topology-summary-actions">
                <el-button class="summary-action-button" @click="adoptionDocVisible = true">
                  <el-icon><InfoFilled /></el-icon>
                  图谱自建说明
                </el-button>
              </div>
            </div>

            <section class="graph-layout">
              <div ref="graphPanelShellRef" class="graph-panel-shell">
                <div class="graph-source-note">
                  <el-icon><InfoFilled /></el-icon>
                  <span>当前图谱环境：{{ envLabel(filters.environment) || '未选择' }}</span>
                </div>
                <div
                  ref="graphLegendRef"
                  class="graph-legend-card"
                  :class="{ dragging: legendDrag.active }"
                  :style="graphLegendStyle"
                  @mousedown.stop.prevent="startLegendDrag"
                >
                  <div class="legend-title">节点类型</div>
                  <div v-for="item in nodeCategoryStats" :key="item.kind" class="legend-row">
                    <span class="legend-dot" :style="{ background: item.color }"></span>
                    <span>{{ item.label }}</span>
                    <em>{{ item.count }}</em>
                  </div>
                  <div class="legend-divider"></div>
                  <div class="legend-title">关系类型</div>
                  <div v-for="item in visibleRelationLegend" :key="item.key" class="legend-row">
                    <span class="legend-line" :class="`is-${item.key}`"></span>
                    <span>{{ item.label }}</span>
                  </div>
                </div>
                <div
                  ref="graphPanelRef"
                  class="graph-panel"
                  :class="{ dragging: graphDrag.active }"
                  v-loading="loading"
                  element-loading-text="正在加载知识图谱关系，可能会并行获取链路追踪、K8s / Docker 线索，请稍候..."
                  @wheel.prevent="handleGraphWheel"
                  @mousedown="startGraphDrag"
                  @mousemove="handleGraphDrag"
                  @mouseup="stopGraphDrag"
                  @mouseleave="stopGraphDrag"
                  @click="handleGraphPanelClick"
                >
                  <el-empty
                    v-if="!filters.environment"
                    class="graph-empty"
                    description="请先选择环境，知识图谱会按该环境关联的可观测性、事件中心与容器基础设施线索生成。"
                  />
                <div class="graph-board-viewport" :style="{ width: `${scaledGraphWidth}px`, height: `${scaledGraphHeight}px` }">
                  <div
                    class="graph-board"
                    :style="{
                      width: `${graphChartWidth}px`,
                      height: `${graphChartHeight}px`,
                      transform: `scale(${graphZoom})`,
                    }"
                  >
                    <svg class="graph-board-edges" :width="graphChartWidth" :height="graphChartHeight">
                      <path
                        v-for="edge in boardEdges"
                        :key="edge.id"
                        :d="edge.path"
                        class="board-edge"
                        :class="[`is-${edge.relation}`, { focused: edge.focused, dimmed: edge.dimmed }]"
                      />
                    </svg>
                    <section
                      v-for="lane in swimlaneLayout.lanes"
                      :key="lane.kind"
                      class="board-lane"
                      :style="laneStyle(lane)"
                    >
                      <div class="board-lane-title" :style="laneTitleStyle(lane)">
                        <span>{{ lane.label }}</span>
                      </div>
                      <div class="board-lane-body" :style="laneBodyStyle(lane)">
                        <div class="board-lane-count">{{ lane.totalNodeCount || lane.nodes.length }} 个节点</div>
                        <button
                          v-for="node in lane.nodes"
                          :key="node.id"
                          type="button"
                          class="board-node"
                          :class="{
                            active: selectedNodeId === node.id,
                            summary: node.isSummary,
                            related: isFocusedNeighbor(node.id),
                            dimmed: isDimmedNode(node.id),
                          }"
                          :style="nodeCardStyle(node)"
                          @click="node.isSummary ? null : selectNode(node)"
                        >
                          <span class="board-node-dot" :style="{ background: palette[node.kind] || '#64748b' }"></span>
                          <span v-if="nodeTypeBadge(node)" class="board-node-type">{{ nodeTypeBadge(node) }}</span>
                          <span class="board-node-label">{{ node.label }}</span>
                        </button>
                      </div>
                    </section>
                  </div>
                </div>
                </div>
              </div>

              <aside class="side-panel">
                <template v-if="selectedNode">
                  <div class="sidebar-header">
                    <div>
                      <div class="side-title">{{ selectedNode.label }}</div>
                      <div class="side-subtitle">{{ selectedNode.category || nodeKindLabel(selectedNode.kind) }}</div>
                    </div>
                    <el-tag>{{ nodeKindLabel(selectedNode.kind) }}</el-tag>
                  </div>
                  <div class="detail-grid">
                    <div class="detail-item">
                      <span>环境</span>
                      <strong>{{ envLabel(selectedNode.environment) }}</strong>
                    </div>
                    <div class="detail-item">
                      <span>系统</span>
                      <strong>{{ selectedNode.system_name || selectedNode.business_line || '-' }}</strong>
                    </div>
                    <div class="detail-item">
                      <span>服务</span>
                      <strong>{{ selectedNode.service || '-' }}</strong>
                    </div>
                    <div class="detail-item">
                      <span>权重</span>
                      <strong>{{ selectedNode.metric || 0 }}</strong>
                    </div>
                  </div>
                  <p v-if="selectedNode.description" class="node-desc">{{ selectedNode.description }}</p>
                  <div v-if="selectedNode.details?.length" class="node-details">
                    <div class="section-title">节点信息</div>
                    <div v-for="item in selectedNode.details" :key="`${item.label}-${item.value}`" class="capability-row">
                      <span>{{ item.label }}</span>
                      <strong>{{ item.value || '-' }}</strong>
                    </div>
                  </div>
                  <div v-if="selectedRelationStats.length || selectedNeighborKindStats.length || selectedNode.capabilities?.length" class="capability-list">
                    <div class="section-title">关联能力</div>
                    <div v-for="item in selectedRelationStats" :key="`relation-${item.key}`" class="capability-row">
                      <span>{{ item.label }}</span>
                      <strong>{{ item.count }}</strong>
                    </div>
                    <div v-for="item in selectedNeighborKindStats" :key="`kind-${item.kind}`" class="capability-row is-soft">
                      <span>{{ item.label }}</span>
                      <strong>{{ item.count }}</strong>
                    </div>
                    <div v-for="item in selectedNode.capabilities || []" :key="item.name" class="capability-row">
                      <span>{{ capabilityLabel(item.name) }}</span>
                      <strong>{{ item.count }}</strong>
                    </div>
                  </div>
                  <el-button v-if="selectedNode.route" type="primary" plain @click="openNode(selectedNode)">打开关联页面</el-button>
                </template>

                <template v-else>
                  <div class="sidebar-placeholder">
                    <div class="side-title">选择节点查看详情</div>
                    <div class="side-subtitle">点击画布节点查看环境、系统、服务、数据源和跳转入口；拖动画布或滚轮缩放可查看完整拓扑。</div>
                  </div>
                  <div class="section-title">高关联服务</div>
                  <button
                    v-for="node in topServices"
                    :key="node.id"
                    type="button"
                    class="service-row"
                    @click="selectNode(node)"
                  >
                    <span>{{ node.label }}</span>
                    <em>{{ node.metric }}</em>
                  </button>
                </template>
              </aside>
            </section>
      </template>
      <AIOpsKnowledgeConfig v-else embedded />
    </section>

    <el-dialog v-model="adoptionDocVisible" title="知识图谱服务识别流程" width="720px">
      <div class="adoption-doc">
        <section>
          <h3>服务识别优先级</h3>
          <ol>
            <li><strong>链路追踪优先：</strong>如果当前图谱环境配置的 Tracing 数据源能返回服务清单，图谱以 Tracing 服务作为主服务列表。</li>
            <li><strong>容器基础设施补充：</strong>K8s / Docker 不再抢占服务来源，主要用于补充服务运行在哪个集群、命名空间、主机或容器环境，并可通过工作负载标签补充系统归属。</li>
            <li><strong>Tracing 无数据时回退：</strong>当 Tracing 没有服务清单时，才从 K8s Deployment / StatefulSet / DaemonSet 和 Docker 容器中识别服务。</li>
            <li><strong>中间件 / DB 自动识别：</strong>图谱会从 Tracing Span 的组件与 Peer、K8s / Docker 运行对象中识别 Redis、MySQL、PostgreSQL、Kafka 等运行组件，并统一放入“中间件 / DB”泳道；“服务依赖”连线只使用 Tracing Span 和 K8s ConfigMap 中的显式线索。</li>
            <li><strong>事件与可观测性补证据：</strong>事件中心、告警和日志用于补充关联能力、业务系统归属和证据，不作为有 Tracing 时的主服务来源。</li>
          </ol>
        </section>
        <section>
          <h3>为什么这样做</h3>
          <p>Tracing 里的 service 通常代表真实发生调用的应用服务，最接近“服务视角”。K8s / Docker 看到的是运行时资源，容易包含基础组件、批处理任务、Job Pod 或工具镜像，因此更适合作为部署位置证据；但对 Redis、MySQL、PostgreSQL、Kafka 这类可判定运行组件，会单独沉淀为“中间件 / DB”节点。</p>
        </section>
        <section>
          <h3>服务所属系统</h3>
          <p>当前系统归属只从可观测性、事件中心和容器基础设施推断，不再依赖 CMDB。可用证据包括事件中心系统、告警系统、Tracing service 标签、平台发布记录和 K8s / Docker 工作负载标签；如果同名服务已有明确系统归属，就不会再挂到“未归属系统”。</p>
          <p>如果同一个服务确实属于多个系统，图谱会保留多个明确系统下的服务节点；只有完全没有系统证据时才归入“未归属系统”。后续建议优先补充 Tracing/告警标签、事件中心系统、发布记录系统或容器基础设施 label（如 <code>app.kubernetes.io/part-of</code>、<code>business_line</code>、<code>system</code>、<code>service.namespace</code>）。</p>
        </section>
      </div>
    </el-dialog>

    <el-dialog
      v-model="traceTopologyDialogVisible"
      width="76vw"
      class="trace-topology-dialog"
      append-to-body
      destroy-on-close
      :show-close="false"
      @opened="traceTopologyDialogReady = true"
      @closed="traceTopologyDialogReady = false"
    >
      <TraceObservability
        v-if="traceTopologyDialogReady"
        embedded
        topology
        :datasource-id="traceTopologyDatasourceId"
        :service="traceTopologyService"
      />
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Connection, InfoFilled, RefreshRight, Setting, Share } from '@element-plus/icons-vue'
import { getAIOpsKnowledgeGraph } from '@/api/modules/aiops'
import {
  capabilityLabel,
  edgeRelationLabel,
  envLabel,
  hiddenNodeKinds,
  laneDefinitions,
  laneKinds,
  nodeKindLabel,
  nodeTypeBadge,
  palette,
} from './knowledge-graph/graphMeta'
import {
  buildSwimlaneLayout,
  laneStyle as computeLaneStyle,
  DEFAULT_GRAPH_ZOOM,
  getGraphChartHeight,
  getGraphChartWidth,
  laneTitleStyle,
  laneBodyStyle,
  MAX_GRAPH_ZOOM,
  MIN_GRAPH_ZOOM,
  nodeCardStyle,
  NODE_DOT_RADIUS,
} from './knowledge-graph/graphLayout'
import {
  buildBoardEdges,
  isDimmedNode as checkDimmedNode,
  isFocusedNeighbor as checkFocusedNeighbor,
} from './knowledge-graph/graphFocus'
import {
  getGraphNodeById,
  getRelationLegendMap,
  getSelectedNode,
  getTraceTopologyDatasourceId,
  getTraceTopologyService,
  getVisibleGraphEdges,
  getVisibleGraphNodes,
} from './knowledge-graph/graphData'
import {
  buildSelectedFocus,
  getActiveLaneDefinitions,
  getNodeCategoryStats,
  getSelectedNeighborKindStats,
  getSelectedRelationStats,
  getTopServices,
  getVisibleRelationLegend,
  getVisibleSummary,
} from './knowledge-graph/graphSelectors'
import { useGraphInteractions } from './knowledge-graph/useGraphInteractions'
import { useKnowledgeGraphFlow } from './knowledge-graph/useKnowledgeGraphFlow'
import { useKnowledgeGraphSelection } from './knowledge-graph/useKnowledgeGraphSelection'
import AIOpsKnowledgeConfig from './AIOpsKnowledgeConfig.vue'
import TraceObservability from './TraceObservability.vue'

const route = useRoute()
const router = useRouter()
const graphPanelRef = ref(null)
const graphPanelShellRef = ref(null)
const graphLegendRef = ref(null)
const graph = ref({ nodes: [], edges: [], summary: {}, filters: {}, relation_legend: [] })
const adoptionDocVisible = ref(false)
const traceTopologyDialogVisible = ref(false)
const traceTopologyDialogReady = ref(false)
const filters = reactive({ environment: '', system: '', service: '' })
const {
  selectedNodeId,
  clearSelection,
  selectNode,
  openNode,
} = useKnowledgeGraphSelection({ router })

const graphNodes = computed(() => getVisibleGraphNodes(graph.value, hiddenNodeKinds))
const graphNodeById = computed(() => getGraphNodeById(graph.value))
const traceTopologyDatasourceId = computed(() => getTraceTopologyDatasourceId(graph.value))
const selectedNode = computed(() => getSelectedNode(graphNodes.value, selectedNodeId.value))
const traceTopologyService = computed(() => getTraceTopologyService(filters, selectedNode.value))
const graphEdges = computed(() => getVisibleGraphEdges(graph.value, graphNodeById.value))
const visibleSummary = computed(() => getVisibleSummary(graphNodes.value, graphEdges.value))
const relationLegendMap = computed(() => getRelationLegendMap(graph.value))
const selectedFocus = computed(() => buildSelectedFocus(selectedNodeId.value, graphEdges.value))
const selectedRelationStats = computed(() => getSelectedRelationStats(
  selectedNodeId.value,
  graphEdges.value,
  relationLegendMap.value,
  edgeRelationLabel,
))
const selectedNeighborKindStats = computed(() => getSelectedNeighborKindStats(
  selectedNodeId.value,
  graphEdges.value,
  graphNodeById.value,
  nodeKindLabel,
))
const topServices = computed(() => getTopServices(graphNodes.value))
const activeLaneDefinitions = computed(() => getActiveLaneDefinitions(graphNodes.value, laneDefinitions, laneKinds))
const graphChartHeight = computed(() => getGraphChartHeight(graphNodes.value, activeLaneDefinitions.value))
const graphChartWidth = computed(() => getGraphChartWidth(graphNodes.value, activeLaneDefinitions.value))
const swimlaneLayout = computed(() => buildSwimlaneLayout(graphNodes.value, activeLaneDefinitions.value, graphChartHeight.value))
const boardNodeMap = computed(() => new Map(swimlaneLayout.value.nodes.map(node => [node.id, node])))
const boardEdges = computed(() => buildBoardEdges(
  graphEdges.value,
  boardNodeMap.value,
  selectedNodeId.value,
  selectedFocus.value,
  NODE_DOT_RADIUS,
))
const nodeCategoryStats = computed(() => getNodeCategoryStats(graphNodes.value, laneDefinitions, laneKinds, palette))
const visibleRelationLegend = computed(() => getVisibleRelationLegend(graph.value.relation_legend, boardEdges.value))
const {
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
} = useGraphInteractions({
  graphPanelRef,
  graphPanelShellRef,
  graphLegendRef,
  graphChartWidth,
  graphChartHeight,
  defaultZoom: DEFAULT_GRAPH_ZOOM,
  minZoom: MIN_GRAPH_ZOOM,
  maxZoom: MAX_GRAPH_ZOOM,
  clearSelection,
})
const {
  loading,
  activeTab,
  loadGraph,
  resetFilters,
  handleEnvironmentChange,
  handleTabChange,
  openTraceTopology,
} = useKnowledgeGraphFlow({
  route,
  router,
  filters,
  graph,
  graphNodes,
  selectedNodeId,
  traceTopologyDatasourceId,
  traceTopologyDialogVisible,
  traceTopologyDialogReady,
  fetchGraph: (params) => getAIOpsKnowledgeGraph(params),
})

function isFocusedNeighbor(nodeId) {
  return checkFocusedNeighbor(selectedNodeId.value, selectedFocus.value, nodeId)
}

function isDimmedNode(nodeId) {
  return checkDimmedNode(selectedNodeId.value, selectedFocus.value, nodeId)
}

function laneStyle(lane) {
  return computeLaneStyle(lane, graphChartHeight.value)
}

function resetCanvas() {
  clearSelection()
  resetViewport()
}
</script>

<style scoped>
.knowledge-page {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: #0f172a;
}

.panel {
  background: #ffffff;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 14px;
  box-shadow: none;
  padding: 12px 14px;
}

.tabs-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tabs-card {
  display: flex;
  align-items: flex-start;
  width: 100%;
  padding: 4px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: none;
}

.tabs-panel :deep(.el-tabs__header) {
  margin-bottom: 10px;
}

.event-like-tabs :deep(.el-tabs__header) {
  margin: 0;
}

.event-like-tabs {
  width: 100%;
}

.event-like-tabs :deep(.el-tabs__nav-wrap) {
  display: block;
  max-width: 100%;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.event-like-tabs :deep(.el-tabs__nav-wrap::after),
.event-like-tabs :deep(.el-tabs__active-bar) {
  display: none;
}

.event-like-tabs :deep(.el-tabs__content) {
  display: none;
}

.event-like-tabs :deep(.el-tabs__nav-scroll) {
  overflow: visible;
}

.event-like-tabs :deep(.el-tabs__nav) {
  display: flex;
  gap: 8px;
  border: 0;
}

.event-like-tabs :deep(.el-tabs__item) {
  min-height: 38px;
  height: 38px;
  padding: 0 20px !important;
  border-radius: 8px;
  color: #4e5969;
  font-size: 13px;
  font-weight: 700;
  line-height: 38px;
}

.event-like-tabs :deep(.el-tabs__item:hover) {
  background: rgba(51, 112, 255, 0.06);
  color: #245bdb;
}

.event-like-tabs :deep(.el-tabs__item.is-active) {
  background: #e8f0ff;
  color: #245bdb;
  box-shadow: inset 0 0 0 1px rgba(51, 112, 255, 0.08);
}

.tab-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.tab-label :deep(.el-icon) {
  font-size: 15px;
}

.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.hero-title-row,
.toolbar-main {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.toolbar-main {
  flex: 1 1 auto;
  min-width: 0;
}

.hero-title-row h2 {
  margin: 0;
  font-size: 23px;
  color: #0f172a;
}

.subtitle {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.45;
}

.inline-subtitle {
  padding-left: 2px;
}

.hero-icon {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #245bdb;
  background: rgba(36, 91, 219, 0.1);
}

.knowledge-stats {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.knowledge-tip {
  margin-top: -2px;
}

.topology-toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  margin-bottom: 4px;
}

.toolbar-actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.toolbar-actions :deep(.el-button) {
  margin-left: 0;
}

.summary-action-button,
.trace-topology-button {
  height: 32px;
  min-width: 0;
  padding: 0 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
  box-shadow: none;
}

.summary-action-button {
  border-color: rgba(148, 163, 184, 0.28);
  color: #475569;
  background: rgba(255, 255, 255, 0.72);
}

.summary-action-button:not(.is-disabled):hover {
  border-color: rgba(100, 116, 139, 0.36);
  color: #334155;
  background: rgba(248, 250, 252, 0.92);
}

.trace-topology-button {
  margin-left: 8px;
  border-color: rgba(51, 112, 255, 0.16);
  color: #3370ff;
  background: rgba(232, 240, 255, 0.42);
  box-shadow: 0 6px 14px rgba(36, 91, 219, 0.05);
}

.trace-topology-button:not(.is-disabled):hover {
  border-color: rgba(51, 112, 255, 0.26);
  color: #245bdb;
  background: rgba(219, 234, 254, 0.64);
  box-shadow: 0 8px 18px rgba(36, 91, 219, 0.08);
}

.trace-topology-button.is-disabled,
.trace-topology-button.is-disabled:hover {
  border-color: rgba(148, 163, 184, 0.18);
  color: #cbd5e1;
  background: rgba(248, 250, 252, 0.62);
  box-shadow: none;
}

:global(.trace-topology-dialog.el-dialog) {
  max-width: 1120px;
  border-radius: 18px;
  overflow: hidden;
}

:global(.trace-topology-dialog .el-dialog__header) {
  display: none;
}

:global(.trace-topology-dialog .el-dialog__body) {
  margin: 0;
  max-height: calc(100vh - 48px);
  overflow: hidden;
  padding: 0;
  background: #ffffff;
}

.toolbar-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(241, 245, 249, 0.96) 100%);
  color: #334155;
  font-size: 13px;
  font-weight: 600;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06);
}

.toolbar-label-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: linear-gradient(180deg, #0ea5e9 0%, #14b8a6 100%);
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.12);
}

.topology-summary-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}

.topology-kpis {
  display: flex;
  gap: 8px;
  flex: 1 1 auto;
  flex-wrap: wrap;
  min-width: 0;
}

.topology-summary-actions {
  display: flex;
  flex: 0 0 auto;
  align-items: flex-start;
  gap: 8px;
  white-space: nowrap;
}

.topology-kpi {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 5px 11px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 12px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.kpi-label {
  color: #64748b;
  font-size: 12px;
  line-height: 1;
  white-space: nowrap;
}

.kpi-value {
  color: #0f172a;
  font-size: 17px;
  font-weight: 700;
  line-height: 1;
}

.graph-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 248px;
  gap: 10px;
  min-height: 640px;
}

.graph-panel-shell {
  position: relative;
  min-width: 0;
}

.graph-panel,
.side-panel {
  position: relative;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 22px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  overflow: hidden;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.10);
}

.graph-panel {
  height: min(72vh, 680px);
  min-height: 640px;
  overflow: auto;
  cursor: grab;
  background:
    linear-gradient(rgba(148, 163, 184, 0.07) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.07) 1px, transparent 1px),
    linear-gradient(rgba(59, 130, 246, 0.10) 1px, transparent 1px),
    linear-gradient(90deg, rgba(59, 130, 246, 0.10) 1px, transparent 1px),
    radial-gradient(circle at top left, rgba(59, 130, 246, 0.08), transparent 28%),
    radial-gradient(circle at bottom right, rgba(16, 185, 129, 0.08), transparent 30%),
    linear-gradient(180deg, #f8fbff 0%, #f1f7fd 100%);
  background-size: 22px 22px, 22px 22px, 88px 88px, 88px 88px, auto, auto, auto;
  scrollbar-width: thin;
}

.graph-panel.dragging {
  cursor: grabbing;
  user-select: none;
}

.graph-panel::before {
  display: none;
}

.graph-panel :deep(.el-loading-mask) {
  border-radius: 20px;
  background: rgba(248, 250, 252, 0.72);
}

.graph-board-viewport {
  position: relative;
  min-width: 100%;
  overflow: hidden;
}

.graph-board {
  position: absolute;
  top: 0;
  left: 0;
  transform-origin: 0 0;
}

.graph-board-edges {
  position: absolute;
  inset: 0;
  z-index: 3;
  pointer-events: none;
}

.board-edge {
  fill: none;
  stroke: rgba(139, 92, 246, 0.34);
  stroke-width: 1.5;
  stroke-linecap: round;
  transition: opacity 0.16s ease, stroke-width 0.16s ease, stroke 0.16s ease;
}

.board-edge.focused {
  opacity: 0.96;
  stroke-width: 2.8;
}

.board-edge.dimmed {
  opacity: 0.08;
  stroke-width: 1;
}

.board-edge.is-system_service {
  stroke: rgba(139, 92, 246, 0.36);
}

.board-edge.is-environment_system {
  stroke: rgba(37, 99, 235, 0.42);
}

.board-edge.is-observability_link {
  stroke: rgba(14, 165, 233, 0.86);
  stroke-dasharray: none;
  stroke-width: 2.8;
}

.board-edge.is-environment_infrastructure {
  stroke: rgba(249, 115, 22, 0.72);
  stroke-width: 2.4;
}

.board-edge.is-service_runtime,
.board-edge.is-system_runtime {
  stroke: rgba(8, 145, 178, 0.42);
  stroke-width: 1.45;
}

.board-edge.is-service_deployment {
  stroke: rgba(34, 197, 94, 0.34);
  stroke-width: 1.35;
}

.board-edge.is-infrastructure_member {
  stroke: rgba(245, 158, 11, 0.58);
  stroke-width: 1.8;
  stroke-dasharray: 8 6;
}

.board-edge.is-event_context {
  stroke: rgba(249, 115, 22, 0.68);
  stroke-dasharray: 11 8;
}

.board-lane {
  position: absolute;
  z-index: 2;
}

.board-lane-title {
  position: absolute;
  left: 0;
  right: 0;
  z-index: 7;
  height: 34px;
  border: 1px solid rgba(59, 130, 246, 0.28);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.98);
  color: #0f172a;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 600;
}

.board-lane-title::before {
  display: none;
}

.board-lane-body {
  position: absolute;
  left: 0;
  right: 0;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 18px;
  overflow: hidden;
}

.board-lane-body::after {
  content: "";
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.28) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.28) 1px, transparent 1px);
  background-size: 28px 28px;
  pointer-events: none;
}

.board-lane-body::before {
  display: none;
}

.board-lane-count {
  position: absolute;
  top: 14px;
  left: 16px;
  z-index: 5;
  padding: 3px 9px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.90);
  color: #475569;
  font-size: 12px;
  font-weight: 600;
}

.board-node {
  position: absolute;
  left: 50%;
  z-index: 6;
  width: 156px;
  min-height: 78px;
  padding: 8px 10px 9px;
  border: 0;
  background: transparent;
  color: #0f172a;
  transform: translateX(-50%);
  cursor: pointer;
  font: inherit;
  transition: filter 0.16s ease, opacity 0.16s ease, transform 0.16s ease;
}

.board-node-dot {
  width: 48px;
  height: 48px;
  margin: 0 auto 10px;
  border: 2px solid rgba(255, 255, 255, 0.98);
  border-radius: 50%;
  display: block;
  position: relative;
  box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.12);
}

.board-node-dot::before {
  content: "";
  position: absolute;
  inset: -22px;
  z-index: -1;
  border-radius: 50%;
  background: radial-gradient(
    circle,
    color-mix(in srgb, var(--node-color) 18%, transparent) 0%,
    color-mix(in srgb, var(--node-color) 10%, transparent) 36%,
    transparent 70%
  );
  pointer-events: none;
}

.board-node-type {
  position: absolute;
  top: 46px;
  left: 50%;
  z-index: 2;
  padding: 1px 6px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.96);
  color: #475569;
  font-size: 10px;
  font-weight: 600;
  line-height: 1.35;
  transform: translateX(-50%);
  pointer-events: none;
}

.board-node-label {
  max-width: 148px;
  margin: 0 auto;
  padding: 5px 10px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.98);
  display: block;
  overflow: hidden;
  color: #0f172a;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
  box-shadow: none;
}

.board-node:hover,
.board-node.active {
  z-index: 12;
  filter: saturate(1.08);
}

.board-node.related {
  z-index: 9;
}

.board-node.dimmed {
  opacity: 0.22;
  filter: grayscale(0.75) saturate(0.68);
}

.board-node.summary {
  cursor: default;
  pointer-events: none;
}

.board-node.summary .board-node-dot {
  width: 38px;
  height: 38px;
  opacity: 0.7;
}

.board-node.summary .board-node-label {
  border-style: dashed;
  color: #64748b;
  font-weight: 700;
}

.board-node:hover .board-node-dot,
.board-node.active .board-node-dot {
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.98), 0 0 0 5px color-mix(in srgb, var(--node-color) 18%, transparent);
}

.board-node:hover .board-node-dot::before,
.board-node.active .board-node-dot::before {
  background: radial-gradient(
    circle,
    color-mix(in srgb, var(--node-color) 24%, transparent) 0%,
    color-mix(in srgb, var(--node-color) 13%, transparent) 38%,
    transparent 72%
  );
}

.board-node.active .board-node-label {
  border-color: color-mix(in srgb, var(--node-color) 38%, rgba(148, 163, 184, 0.24));
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.15);
}

.board-node.related .board-node-label {
  border-color: color-mix(in srgb, var(--node-color) 26%, rgba(148, 163, 184, 0.24));
}

.graph-empty {
  position: absolute;
  inset: 0;
  z-index: 8;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(248, 250, 252, 0.76);
}

.graph-source-note {
  position: absolute;
  bottom: 14px;
  left: 14px;
  z-index: 9;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 10px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.96);
  color: #0f172a;
  font-size: 11px;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.10);
}

.graph-legend-card {
  position: absolute;
  top: 14px;
  right: 14px;
  z-index: 9;
  min-width: 118px;
  max-width: 138px;
  padding: 9px 10px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.97);
  color: #334155;
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.12);
  backdrop-filter: blur(8px);
  cursor: grab;
  user-select: none;
  touch-action: none;
}

.graph-legend-card.dragging {
  cursor: grabbing;
  box-shadow: 0 20px 42px rgba(15, 23, 42, 0.18);
}

.side-panel {
  min-width: 0;
  padding: 15px;
  color: #0f172a;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.sidebar-placeholder {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.side-title {
  color: #0f172a;
  font-size: 16px;
  font-weight: 700;
}

.side-subtitle,
.node-desc {
  color: #64748b;
  font-size: 12px;
  line-height: 1.55;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;
}

.detail-item,
.capability-row,
.service-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 11px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.95);
}

.detail-item {
  flex-direction: column;
  align-items: flex-start;
}

.detail-item span,
.section-title {
  color: #64748b;
  font-size: 11px;
}

.detail-item strong,
.capability-row strong {
  color: #0f172a;
  font-size: 12px;
}

.capability-row.is-soft {
  background: rgba(248, 250, 252, 0.92);
}

.section-title {
  margin: 12px 0 7px;
  font-weight: 700;
}

.legend-title {
  margin-bottom: 6px;
  color: #0f172a;
  font-size: 11px;
  font-weight: 700;
}

.legend-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 6px;
  margin-bottom: 5px;
  color: #475569;
  font-size: 11px;
}

.adoption-doc {
  display: flex;
  flex-direction: column;
  gap: 14px;
  color: #334155;
  font-size: 13px;
  line-height: 1.7;
}

.adoption-doc h3 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 15px;
}

.adoption-doc p,
.adoption-doc ol {
  margin: 0;
}

.adoption-doc ol {
  padding-left: 20px;
}

.adoption-doc li + li {
  margin-top: 6px;
}

.adoption-doc code {
  padding: 1px 5px;
  border-radius: 6px;
  background: #f1f5f9;
  color: #0f766e;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.legend-line {
  display: inline-block;
  width: 22px;
  border-top: 2px solid #94a3b8;
}

.legend-line.is-system_service {
  border-color: #8b5cf6;
}

.legend-line.is-environment_system {
  border-color: #2563eb;
}

.legend-line.is-observability_link {
  border-color: #0ea5e9;
}

.legend-line.is-environment_infrastructure {
  border-color: #f97316;
}

.legend-line.is-service_runtime,
.legend-line.is-system_runtime {
  border-color: rgba(8, 145, 178, 0.58);
}

.legend-line.is-service_deployment {
  border-color: rgba(34, 197, 94, 0.46);
}

.legend-line.is-infrastructure_member {
  border-color: #f59e0b;
  border-top-style: dashed;
}

.legend-line.is-event_context {
  border-color: #f97316;
  border-top-style: dashed;
}

.legend-divider {
  height: 1px;
  margin: 8px 0;
  background: rgba(148, 163, 184, 0.2);
}

.legend-row em {
  color: #64748b;
  font-size: 10px;
  font-style: normal;
}

.service-row {
  width: 100%;
  margin-bottom: 8px;
  color: #0f172a;
  cursor: pointer;
  text-align: left;
  font: inherit;
  transition: border-color 0.16s ease, transform 0.16s ease, box-shadow 0.16s ease;
}

.service-row:hover {
  transform: translateY(-1px);
  border-color: rgba(14, 165, 233, 0.28);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

.service-row span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.service-row em {
  color: #64748b;
  font-size: 11px;
  font-style: normal;
}

@media (max-width: 1100px) {
  .knowledge-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .topology-toolbar {
    grid-template-columns: 1fr;
  }

  .toolbar-actions {
    flex-wrap: wrap;
  }

  .topology-summary-row {
    flex-direction: column;
  }

  .topology-summary-actions {
    flex-wrap: wrap;
  }

  .graph-layout {
    grid-template-columns: 1fr;
  }

  .graph-panel {
    min-height: 520px;
  }
}

@media (max-width: 720px) {
  .knowledge-stats {
    grid-template-columns: 1fr;
  }

  .graph-legend-card,
  .graph-source-note {
    position: static;
    margin: 10px 10px 0;
    transform: none;
  }

}
</style>
