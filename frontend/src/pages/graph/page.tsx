import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Navbar from '@/components/feature/Navbar';
import Button from '@/components/base/Button';
import Badge from '@/components/base/Badge';
import { fetchKnowledgeGraph, type KnowledgeGraph, type GraphNode, type GraphEdge } from '@/services/knowledgeGraphApi';
import { createFittedGraphViewBox } from './viewBox';

interface NodeGroup { key: string; label: string; icon: string; color: string }

const NODE_GROUPS: NodeGroup[] = [
  { key: 'anchor', label: '预测与决策', icon: 'ri-links-line', color: '#ea580c' },
  { key: 'input', label: '目标与上下文', icon: 'ri-database-2-line', color: '#0d9488' },
  { key: 'features', label: '模型归因', icon: 'ri-bar-chart-2-line', color: '#16a34a' },
  { key: 'rules', label: '政策规则', icon: 'ri-checkbox-multiple-line', color: '#d97706' },
  { key: 'mechanisms', label: '机制相容性', icon: 'ri-git-branch-line', color: '#b45309' },
  { key: 'events', label: '历史类比', icon: 'ri-history-line', color: '#ca8a04' },
  { key: 'sources', label: '文献与本体', icon: 'ri-book-open-line', color: '#6366f1' },
];

const TIMELINE_STEPS = [
  { step: 0, label: '预测案例', desc: '确定起报、有效时间和空间范围' },
  { step: 1, label: '模型预测', desc: '生成并校准灾害概率' },
  { step: 2, label: '模型归因', desc: '读取模型实际使用的特征贡献' },
  { step: 3, label: '政策规则', desc: '执行版本化风险政策' },
  { step: 4, label: '知识解释', desc: '检查机制相容性并回溯文献/本体' },
  { step: 5, label: '风险评估', desc: '区分概率、敏感性与风险等级' },
  { step: 6, label: '历史类比', desc: '检索起报前的多维相似案例' },
];

const EMPTY_GRAPH: KnowledgeGraph = { predictionId: '', graphVersion: '', generatedAt: '', disclaimer: '', nodes: [], edges: [] };

const NODE_COLORS: Record<string, { fill: string; stroke: string; text: string }> = {
  case: { fill: '#fef3c7', stroke: '#d97706', text: '#92400e' },
  prediction: { fill: '#ffedd5', stroke: '#ea580c', text: '#9a3412' },
  model: { fill: '#fef7ed', stroke: '#c2410c', text: '#7c2d12' },
  hazard: { fill: '#fef2f2', stroke: '#dc2626', text: '#991b1b' },
  region: { fill: '#ecfdf5', stroke: '#059669', text: '#065f46' },
  feature: { fill: '#f0fdf4', stroke: '#16a34a', text: '#14532d' },
  rule: { fill: '#fff7ed', stroke: '#ea580c', text: '#7c2d12' },
  mechanism: { fill: '#fef9f0', stroke: '#b45309', text: '#78350f' },
  risk: { fill: '#fef2f2', stroke: '#dc2626', text: '#991b1b' },
  event: { fill: '#fef9c3', stroke: '#ca8a04', text: '#854d0e' },
  warning: { fill: '#fecaca', stroke: '#ef4444', text: '#7f1d1d' },
  source: { fill: '#eef2ff', stroke: '#6366f1', text: '#3730a3' },
  ontology: { fill: '#f5f3ff', stroke: '#7c3aed', text: '#5b21b6' },
};

const NODE_LABELS: Record<string, string> = {
  case: '案例',
  prediction: '预测',
  model: '模型',
  hazard: '灾种',
  region: '区域',
  feature: '特征',
  rule: '规则',
  mechanism: '机制',
  risk: '风险评估',
  event: '历史事件',
  warning: '预警',
  source: '文献来源',
  ontology: 'SWEET 对齐',
};

const EDGE_COLORS: Record<string, string> = {
  PRODUCED: '#d97706',
  GENERATED: '#c2410c',
  FOR_REGION: '#0d9488',
  PREDICTS: '#e11d48',
  HAS_ATTRIBUTION: '#16a34a',
  USES: '#ea580c',
  TRIGGERS: '#ea580c',
  CONSISTENT_WITH: '#b45309',
  FAVOURS: '#e11d48',
  GROUNDED_IN: '#6366f1',
  ALIGNED_WITH: '#7c3aed',
  INFORMS: '#d97706',
  ASSESSED_AS: '#dc2626',
  SIMILAR_TO: '#ca8a04',
  RESULTS_IN: '#ef4444',
  INSTANCE_OF: '#d97706',
};

type NodePos = { x: number; y: number; vx: number; vy: number };

export default function KnowledgeGraphPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [graphData, setGraphData] = useState<KnowledgeGraph>(EMPTY_GRAPH);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [positions, setPositions] = useState<Record<string, NodePos>>({});
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [dragNode, setDragNode] = useState<string | null>(null);
  const [viewBox, setViewBox] = useState({ x: 0, y: 0, w: 900, h: 600 });
  const animFrameRef = useRef<number>(0);
  const positionsRef = useRef<Record<string, NodePos>>({});
  const [dimensions, setDimensions] = useState({ width: 900, height: 600 });
  const [hasMeasuredContainer, setHasMeasuredContainer] = useState(false);
  const fittedPredictionRef = useRef<string | null>(null);

  useEffect(() => {
    if (!id) {
      setLoadError('缺少预测 ID');
      setIsLoading(false);
      return;
    }
    let cancelled = false;
    setIsLoading(true);
    fetchKnowledgeGraph(id)
      .then((data) => { if (!cancelled) { setGraphData(data); setLoadError(null); } })
      .catch((error: unknown) => { if (!cancelled) setLoadError(error instanceof Error ? error.message : '未知加载错误'); })
      .finally(() => { if (!cancelled) setIsLoading(false); });
    return () => { cancelled = true; };
  }, [id]);

  // Collapsed groups & timeline
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
  const [currentStep, setCurrentStep] = useState(6);
  const [isPlaying, setIsPlaying] = useState(false);
  const playIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Visible nodes & edges
  const visibleNodes = useMemo(() => {
    return graphData.nodes.filter((n) => {
      if (collapsedGroups.has(n.group)) return false;
      if (n.step > currentStep) return false;
      return true;
    });
  }, [graphData.nodes, collapsedGroups, currentStep]);

  const visibleEdges = useMemo(() => {
    const visibleNodeIds = new Set(visibleNodes.map((n) => n.id));
    return graphData.edges.filter((e) => {
      if (e.step > currentStep) return false;
      if (!visibleNodeIds.has(e.source) || !visibleNodeIds.has(e.target)) return false;
      return true;
    });
  }, [graphData.edges, visibleNodes, currentStep]);

  // Initialize positions for ALL nodes (so they don't jump when becoming visible)
  useEffect(() => {
    const w = dimensions.width;
    const h = dimensions.height;
    const cx = w / 2;
    const cy = h / 2;

    const nodePositions: Record<string, NodePos> = {};
    const layoutNodes = [...graphData.nodes];

    const anchors = graphData.nodes.filter((node) => node.group === 'anchor').map((node) => node.id);
    anchors.forEach((id, i) => {
      const angle = (i / anchors.length) * Math.PI * 2 - Math.PI / 2;
      const r = Math.min(w, h) * 0.28;
      nodePositions[id] = { x: cx + Math.cos(angle) * r, y: cy + Math.sin(angle) * r, vx: 0, vy: 0 };
    });

    const others = layoutNodes.filter((n) => !anchors.includes(n.id));
    others.forEach((node, i) => {
      const angle = (i / others.length) * Math.PI * 2;
      const r = Math.min(w, h) * 0.18;
      nodePositions[node.id] = { x: cx + Math.cos(angle) * r, y: cy + Math.sin(angle) * r, vx: 0, vy: 0 };
    });

    setPositions(nodePositions);
    positionsRef.current = nodePositions;
  }, [dimensions, graphData]);

  const fitGraphToView = useCallback(() => {
    setViewBox(createFittedGraphViewBox(dimensions));
  }, [dimensions]);

  // The force layout uses measured container dimensions. Match the SVG viewport
  // after the first real measurement so nodes are visible without a manual reset.
  useEffect(() => {
    if (!hasMeasuredContainer || !graphData.predictionId || graphData.nodes.length === 0) return;
    if (fittedPredictionRef.current === graphData.predictionId) return;
    fitGraphToView();
    fittedPredictionRef.current = graphData.predictionId;
  }, [fitGraphToView, graphData.nodes.length, graphData.predictionId, hasMeasuredContainer]);

  // Resize observer
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        setDimensions({ width: Math.max(width, 800), height: Math.max(height, 500) });
        setHasMeasuredContainer(true);
      }
    });

    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  // Force simulation - runs on visible nodes only
  useEffect(() => {
    if (visibleNodes.length === 0) return;

    let running = true;
    const nodePositions = positionsRef.current;
    const visibleNodeIds = new Set(visibleNodes.map((n) => n.id));
    const visibleEdgeIds = new Set(visibleEdges.map((e) => e.id));

    const simulate = () => {
      if (!running) return;
      const cx = dimensions.width / 2;
      const cy = dimensions.height / 2;
      const anchors = new Set(graphData.nodes.filter((node) => node.group === 'anchor').map((node) => node.id));

      // Apply forces only to visible, non-dragged nodes
      for (const node of graphData.nodes) {
        if (!visibleNodeIds.has(node.id)) continue;
        const pos = nodePositions[node.id];
        if (!pos || node.id === dragNode) continue;

        if (!anchors.has(node.id)) {
          pos.vx += (cx - pos.x) * 0.0003;
          pos.vy += (cy - pos.y) * 0.0003;
        }
        pos.vx *= 0.65;
        pos.vy *= 0.65;
      }

      // Repulsion
      const visibleArr = graphData.nodes.filter((n) => visibleNodeIds.has(n.id));
      for (let i = 0; i < visibleArr.length; i++) {
        for (let j = i + 1; j < visibleArr.length; j++) {
          const a = nodePositions[visibleArr[i].id];
          const b = nodePositions[visibleArr[j].id];
          if (!a || !b) continue;
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
          const force = 8000 / (dist * dist);
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;

          if (visibleArr[i].id !== dragNode) { a.vx -= fx; a.vy -= fy; }
          if (visibleArr[j].id !== dragNode) { b.vx += fx; b.vy += fy; }
        }
      }

      // Edge springs
      for (const edge of graphData.edges) {
        if (!visibleEdgeIds.has(edge.id)) continue;
        const a = nodePositions[edge.source];
        const b = nodePositions[edge.target];
        if (!a || !b) continue;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
        const targetLen = 120;
        const force = (dist - targetLen) * 0.02;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;

        if (edge.source !== dragNode) { a.vx += fx; a.vy += fy; }
        if (edge.target !== dragNode) { b.vx -= fx; b.vy -= fy; }
      }

      // Apply velocities
      let totalMotion = 0;
      for (const node of graphData.nodes) {
        if (!visibleNodeIds.has(node.id)) continue;
        const pos = nodePositions[node.id];
        if (!pos || node.id === dragNode) continue;
        pos.x = Math.max(20, Math.min(dimensions.width - 20, pos.x + pos.vx));
        pos.y = Math.max(20, Math.min(dimensions.height - 20, pos.y + pos.vy));
        totalMotion += Math.abs(pos.vx) + Math.abs(pos.vy);
      }

      setPositions({ ...nodePositions });

      if (totalMotion > 0.5) {
        animFrameRef.current = requestAnimationFrame(simulate);
      }
    };

    animFrameRef.current = requestAnimationFrame(simulate);
    return () => { running = false; cancelAnimationFrame(animFrameRef.current); };
  }, [graphData.edges, graphData.nodes, visibleNodes, visibleEdges, dragNode, dimensions]);

  // Timeline playback
  useEffect(() => {
    if (!isPlaying) {
      if (playIntervalRef.current) clearInterval(playIntervalRef.current);
      return;
    }

    playIntervalRef.current = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev >= 6) {
          setIsPlaying(false);
          return 6;
        }
        return prev + 1;
      });
    }, 800);

    return () => {
      if (playIntervalRef.current) clearInterval(playIntervalRef.current);
    };
  }, [isPlaying]);

  // Get node position
  const getNodePos = useCallback((id: string): NodePos => {
    return positions[id] || { x: 0, y: 0, vx: 0, vy: 0 };
  }, [positions]);

  // SVG event handlers
  const handleMouseDown = (e: React.MouseEvent, nodeId: string) => {
    e.stopPropagation();
    setDragNode(nodeId);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!dragNode || !svgRef.current) return;
    const svg = svgRef.current;
    const pt = svg.createSVGPoint();
    pt.x = e.clientX;
    pt.y = e.clientY;
    const svgPt = pt.matrixTransform(svg.getScreenCTM()?.inverse());
    setPositions((prev) => {
      const updated = { ...prev };
      if (updated[dragNode]) {
        updated[dragNode] = { ...updated[dragNode], x: svgPt.x, y: svgPt.y, vx: 0, vy: 0 };
      }
      positionsRef.current = updated;
      return updated;
    });
  };

  const handleMouseUp = () => {
    setDragNode(null);
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const scale = e.deltaY > 0 ? 1.1 : 0.9;
    setViewBox((prev) => {
      const newW = prev.w * scale;
      const newH = prev.h * scale;
      const cx = prev.x + prev.w / 2;
      const cy = prev.y + prev.h / 2;
      return { x: cx - newW / 2, y: cy - newH / 2, w: newW, h: newH };
    });
  };

  const getRelatedEdges = (nodeId: string) => {
    return visibleEdges.filter((e) => e.source === nodeId || e.target === nodeId);
  };

  const isEdgeHighlighted = (edge: GraphEdge) => {
    if (!hoveredNode && !selectedNode) return true;
    if (hoveredNode) return edge.source === hoveredNode || edge.target === hoveredNode;
    if (selectedNode) return edge.source === selectedNode || edge.target === selectedNode;
    return true;
  };

  const isNodeDimmed = (nodeId: string) => {
    if (!hoveredNode && !selectedNode) return false;
    const active = hoveredNode || selectedNode;
    if (nodeId === active) return false;
    const relatedEdges = visibleEdges.filter(
      (e) => (e.source === active && e.target === nodeId) || (e.target === active && e.source === nodeId)
    );
    return relatedEdges.length === 0;
  };

  // Toggle group collapse
  const toggleGroup = (groupKey: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupKey)) next.delete(groupKey);
      else next.add(groupKey);
      return next;
    });
  };

  // Navigate to explanation detail
  const navigateToDetail = (node: GraphNode) => {
    const tab = node.navigateTab || 'overview';
    navigate(`/prediction/${graphData.predictionId}`, { state: { activeTab: tab } });
  };

  // Reset timeline
  const showAllSteps = () => {
    setCurrentStep(6);
    setIsPlaying(false);
  };

  // Selected node data
  const selectedNodeData = useMemo(() => {
    if (!selectedNode) return null;
    return graphData.nodes.find((n) => n.id === selectedNode) || null;
  }, [graphData.nodes, selectedNode]);

  return (
    <div className="min-h-screen bg-background-50 flex flex-col">
      <Navbar />

      <div className="flex-1 flex flex-col">
        {/* Toolbar */}
        <div className="border-b border-background-200/70 px-6 py-3 flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" icon="ri-arrow-left-line" onClick={() => navigate(-1)}>
              返回
            </Button>
            <h1 className="font-heading text-lg text-foreground-900">解释证据图谱</h1>
            <Badge variant="secondary">{graphData.predictionId}</Badge>
            {graphData.graphVersion && <Badge variant="secondary">KB {graphData.graphVersion}</Badge>}
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <div className="text-xs text-foreground-500 px-3 py-1.5 bg-background-100 rounded-full">
              {visibleNodes.length}/{graphData.nodes.length} 节点 · {visibleEdges.length}/{graphData.edges.length} 边
            </div>
            <Button
              variant="outline"
              size="sm"
              icon="ri-fullscreen-line"
              onClick={fitGraphToView}
            >
              重置视图
            </Button>
            <Button
              variant="outline"
              size="sm"
              icon="ri-play-list-2-line"
              onClick={showAllSteps}
            >
              显示全部
            </Button>
          </div>
        </div>

        {/* Main content: sidebar + graph */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left sidebar - group panel */}
          <div className="w-48 flex-shrink-0 border-r border-background-200/70 bg-background-50 p-3 flex flex-col gap-1 overflow-y-auto">
            <p className="text-[11px] font-medium text-foreground-500 px-1 mb-1 uppercase tracking-wide">节点分组</p>
            {NODE_GROUPS.map((group) => {
              const isCollapsed = collapsedGroups.has(group.key);
              const groupNodes = graphData.nodes.filter((node) => node.group === group.key).map((node) => node.id);
              const visibleCount = groupNodes.filter((nid) => {
                const node = graphData.nodes.find((n) => n.id === nid);
                return node && node.step <= currentStep;
              }).length;

              return (
                <button
                  key={group.key}
                  onClick={() => toggleGroup(group.key)}
                  className={`flex items-center gap-2 px-2.5 py-2 rounded-lg text-left cursor-pointer transition-all duration-200 border ${
                    isCollapsed
                      ? 'bg-background-100 border-background-200/50 opacity-60'
                      : 'bg-background-50 border-background-200/70 hover:border-background-300'
                  }`}
                >
                  <span className="w-3 h-3 rounded-sm flex-shrink-0" style={{ backgroundColor: group.color }}></span>
                  <span className="flex-1 text-xs text-foreground-800 font-medium truncate">{group.label}</span>
                  <span className={`text-xs flex-shrink-0 ${isCollapsed ? 'text-foreground-300' : 'text-foreground-500'}`}>
                    {visibleCount}
                  </span>
                  <i className={`text-xs flex-shrink-0 transition-transform duration-200 ${isCollapsed ? 'text-foreground-300 ri-eye-off-line' : 'text-foreground-400 ri-eye-line'}`}></i>
                </button>
              );
            })}

            <div className="mt-3 pt-3 border-t border-background-200/50">
              <button
                onClick={() => setCollapsedGroups(new Set())}
                className="w-full text-[11px] text-foreground-500 hover:text-foreground-700 cursor-pointer px-1 py-1"
              >
                <i className="ri-eye-line mr-1"></i>展开全部
              </button>
              <button
                onClick={() => setCollapsedGroups(new Set(NODE_GROUPS.map((g) => g.key)))}
                className="w-full text-[11px] text-foreground-500 hover:text-foreground-700 cursor-pointer px-1 py-1"
              >
                <i className="ri-eye-off-line mr-1"></i>折叠全部
              </button>
            </div>
          </div>

          {/* Right - graph area */}
          <div ref={containerRef} className="flex-1 relative bg-background-50 overflow-hidden" style={{ minHeight: '600px' }}>
            {isLoading && (
              <div className="absolute inset-0 z-20 flex items-center justify-center bg-background-50/80 text-sm text-foreground-500">
                <i className="ri-loader-4-line animate-spin mr-2"></i>正在查询知识库并生成解释视图…
              </div>
            )}
            {loadError && (
              <div className="absolute inset-0 z-20 flex items-center justify-center bg-background-50/90">
                <div className="max-w-md text-center"><i className="ri-error-warning-line text-3xl text-red-500"></i><p className="mt-2 text-sm text-foreground-700">{loadError}</p></div>
              </div>
            )}
            <svg
              ref={svgRef}
              viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.w} ${viewBox.h}`}
              className="w-full h-full"
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              onWheel={handleWheel}
            >
              <defs>
                {visibleEdges.map((edge) => (
                  <marker
                    key={edge.id}
                    id={`arrow-${edge.id}`}
                    viewBox="0 0 10 10"
                    refX="8"
                    refY="5"
                    markerWidth="6"
                    markerHeight="6"
                    orient="auto-start-reverse"
                  >
                    <path d="M 0 0 L 10 5 L 0 10 z" fill={EDGE_COLORS[edge.type] || '#999'} opacity="0.7" />
                  </marker>
                ))}
              </defs>

              {/* Edges */}
              {visibleEdges.map((edge) => {
                const source = getNodePos(edge.source);
                const target = getNodePos(edge.target);
                if (!source || !target) return null;
                const highlighted = isEdgeHighlighted(edge);
                const opacity = highlighted ? 0.8 : 0.1;

                const dx = target.x - source.x;
                const dy = target.y - source.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist === 0) return null;
                const nx = dx / dist;
                const ny = dy / dist;

                const sx = source.x + nx * 45;
                const sy = source.y + ny * 45;
                const tx = target.x - nx * 45;
                const ty = target.y - ny * 45;

                return (
                  <g key={edge.id}>
                    <line
                      x1={sx} y1={sy} x2={tx} y2={ty}
                      stroke={EDGE_COLORS[edge.type] || '#999'}
                      strokeWidth={highlighted ? 2 : 1}
                      opacity={opacity}
                      markerEnd={`url(#arrow-${edge.id})`}
                      className="transition-all duration-300"
                    />
                    {highlighted && (
                      <text
                        x={(sx + tx) / 2}
                        y={(sy + ty) / 2 - 6}
                        textAnchor="middle"
                        fontSize="9"
                        fill={EDGE_COLORS[edge.type] || '#999'}
                        className="pointer-events-none"
                      >
                        {edge.label}
                      </text>
                    )}
                  </g>
                );
              })}

              {/* Nodes */}
              {visibleNodes.map((node) => {
                const pos = getNodePos(node.id);
                const colors = NODE_COLORS[node.type] || { fill: '#f3f4f6', stroke: '#9ca3af', text: '#374151' };
                const isSelected = selectedNode === node.id;
                const isHovered = hoveredNode === node.id;
                const dimmed = isNodeDimmed(node.id);

                const lines = node.label.split('\n');
                const boxWidth = Math.max(...lines.map((l) => l.length * 8)) + 20;
                const boxHeight = lines.length * 16 + 16;

                return (
                  <g
                    key={node.id}
                    transform={`translate(${pos.x - boxWidth / 2}, ${pos.y - boxHeight / 2})`}
                    onMouseDown={(e) => handleMouseDown(e, node.id)}
                    onMouseEnter={() => setHoveredNode(node.id)}
                    onMouseLeave={() => setHoveredNode(null)}
                    onClick={() => setSelectedNode(isSelected ? null : node.id)}
                    className={`cursor-grab ${dimmed ? 'opacity-20' : 'opacity-100'} transition-opacity duration-300`}
                    style={{ cursor: dragNode === node.id ? 'grabbing' : 'pointer' }}
                  >
                    <rect
                      width={boxWidth}
                      height={boxHeight}
                      rx="6"
                      fill={colors.fill}
                      stroke={isSelected ? colors.stroke : isHovered ? colors.stroke : colors.stroke}
                      strokeWidth={isSelected || isHovered ? 2.5 : 1}
                      className="transition-all duration-200"
                    />
                    {lines.map((line, i) => (
                      <text
                        key={i}
                        x={boxWidth / 2}
                        y={14 + i * 16}
                        textAnchor="middle"
                        fontSize="11"
                        fill={colors.text}
                        fontWeight={i === 0 ? '600' : '400'}
                        className="pointer-events-none"
                      >
                        {line}
                      </text>
                    ))}
                  </g>
                );
              })}
            </svg>

            {/* Node detail panel */}
            {selectedNode && selectedNodeData && (
              <div className="absolute top-4 right-4 w-72 bg-background-50 border border-background-200/70 rounded-lg p-4 shadow-sm">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-medium text-sm text-foreground-900">节点详情</h4>
                  <button
                    onClick={() => setSelectedNode(null)}
                    className="p-1 rounded hover:bg-background-100 cursor-pointer text-foreground-400"
                  >
                    <i className="ri-close-line text-sm"></i>
                  </button>
                </div>

                <div className="space-y-2.5">
                  <div className="flex items-center gap-2">
                    <span
                      className="w-3 h-3 rounded-sm"
                      style={{
                        backgroundColor: NODE_COLORS[selectedNodeData.type]?.fill || '#eee',
                        border: `1px solid ${NODE_COLORS[selectedNodeData.type]?.stroke || '#ccc'}`,
                      }}
                    ></span>
                    <Badge variant="secondary" size="sm">{NODE_LABELS[selectedNodeData.type] || selectedNodeData.type}</Badge>
                  </div>

                  <div>
                    <span className="text-xs text-foreground-500">ID</span>
                    <p className="text-xs text-foreground-700 mt-0.5 font-mono break-all">{selectedNodeData.id}</p>
                  </div>

                  <div>
                    <span className="text-xs text-foreground-500">分组</span>
                    <p className="text-xs text-foreground-700 mt-0.5">
                      {NODE_GROUPS.find((g) => g.key === selectedNodeData.group)?.label || selectedNodeData.group}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div><span className="text-xs text-foreground-500">证据类型</span><p className="text-xs text-foreground-700 mt-0.5">{selectedNodeData.evidenceKind}</p></div>
                    <div><span className="text-xs text-foreground-500">状态</span><p className="text-xs text-foreground-700 mt-0.5">{selectedNodeData.status}</p></div>
                  </div>

                  {Object.keys(selectedNodeData.details).length > 0 && (
                    <div className="pt-2 border-t border-background-200/50">
                      <span className="text-xs text-foreground-500">可追溯属性</span>
                      <div className="mt-1 space-y-1 max-h-40 overflow-y-auto">
                        {Object.entries(selectedNodeData.details).map(([key, value]) => (
                          <div key={key} className="text-[11px] break-words"><span className="text-foreground-400">{key}: </span><span className="text-foreground-700">{String(value)}</span></div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div>
                    <span className="text-xs text-foreground-500">时间步</span>
                    <p className="text-xs text-foreground-700 mt-0.5">
                      第 {selectedNodeData.step} 步 · {TIMELINE_STEPS[selectedNodeData.step]?.label || '-'}
                    </p>
                  </div>

                  {(() => {
                    const relatedEdges = getRelatedEdges(selectedNodeData.id);
                    return (
                      <div className="pt-2 border-t border-background-200/50">
                        <span className="text-xs text-foreground-500">关联边 ({relatedEdges.length})</span>
                        <div className="mt-1 space-y-1 max-h-32 overflow-y-auto">
                          {relatedEdges.slice(0, 8).map((e) => (
                            <div key={e.id} title={e.rationale} className="flex items-center gap-1.5 text-[11px]">
                              <span
                                className="w-2 h-2 rounded-full flex-shrink-0"
                                style={{ backgroundColor: EDGE_COLORS[e.type] || '#999' }}
                              ></span>
                              <span className="text-foreground-600">{e.label}</span>
                              <span className="text-foreground-400">
                                → {e.source === selectedNodeData.id
                                  ? (graphData.nodes.find((n) => n.id === e.target)?.label.split('\n')[0] || e.target)
                                  : (graphData.nodes.find((n) => n.id === e.source)?.label.split('\n')[0] || e.source)}
                              </span>
                              {e.confidence != null && <span className="text-foreground-500">{(e.confidence * 100).toFixed(0)}%</span>}
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })()}

                  {/* Navigate button */}
                  {selectedNodeData.navigateTab && (
                    <div className="pt-2 border-t border-background-200/50">
                      <Button
                        variant="primary"
                        size="sm"
                        icon="ri-external-link-line"
                        className="w-full"
                        onClick={() => navigateToDetail(selectedNodeData)}
                      >
                        查看解释详情
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Timeline bar */}
        <div className="border-t border-background-200/70 bg-background-50 px-6 py-3">
          <div className="flex items-center gap-3">
            {/* Play/Pause */}
            <button
              onClick={() => {
                if (isPlaying) {
                  setIsPlaying(false);
                } else {
                  if (currentStep >= 6) setCurrentStep(0);
                  setIsPlaying(true);
                }
              }}
              className="w-8 h-8 rounded-full flex items-center justify-center cursor-pointer bg-primary-500 text-white hover:bg-primary-600 transition-colors"
            >
              <i className={`text-sm ${isPlaying ? 'ri-pause-fill' : 'ri-play-fill'}`}></i>
            </button>

            {/* Reset */}
            <button
              onClick={() => { setCurrentStep(0); setIsPlaying(false); }}
              className="w-7 h-7 rounded-full flex items-center justify-center cursor-pointer text-foreground-400 hover:text-foreground-600 hover:bg-background-100 transition-colors"
              title="回到起点"
            >
              <i className="ri-skip-back-fill text-sm"></i>
            </button>

            {/* Step indicator */}
            <span className="text-xs font-medium text-foreground-600 min-w-[100px] whitespace-nowrap">
              第 {currentStep} 步: {TIMELINE_STEPS[currentStep]?.desc || '-'}
            </span>

            {/* Slider */}
            <div className="flex-1 relative">
              <input
                type="range"
                min="0"
                max="6"
                value={currentStep}
                onChange={(e) => { setCurrentStep(Number(e.target.value)); setIsPlaying(false); }}
                className="w-full h-2 rounded-full bg-background-200 appearance-none cursor-pointer accent-primary-500"
                style={{
                  background: `linear-gradient(to right, oklch(var(--primary-500)) 0%, oklch(var(--primary-500)) ${(currentStep / 6) * 100}%, oklch(var(--background-300) / 0.6) ${(currentStep / 6) * 100}%, oklch(var(--background-300) / 0.6) 100%)`,
                }}
              />

              {/* Step dots */}
              <div className="absolute top-1/2 -translate-y-1/2 left-0 right-0 flex justify-between pointer-events-none">
                {TIMELINE_STEPS.map((ts) => (
                  <div
                    key={ts.step}
                    className={`w-2.5 h-2.5 rounded-full transition-colors duration-300 ${
                      ts.step <= currentStep ? 'bg-primary-500' : 'bg-background-300'
                    }`}
                    title={ts.label}
                  ></div>
                ))}
              </div>
            </div>

            {/* Step labels */}
            <div className="hidden lg:flex items-center gap-1.5 flex-shrink-0">
              {TIMELINE_STEPS.map((ts) => (
                <button
                  key={ts.step}
                  onClick={() => { setCurrentStep(ts.step); setIsPlaying(false); }}
                  className={`text-[10px] px-2 py-0.5 rounded-full cursor-pointer whitespace-nowrap transition-colors ${
                    ts.step <= currentStep
                      ? 'bg-primary-100 text-primary-700'
                      : 'bg-background-100 text-foreground-400 hover:text-foreground-500'
                  }`}
                >
                  {ts.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <footer className="border-t border-background-200/70 bg-background-100 px-6 py-2.5">
        <div className="flex items-center justify-between text-xs text-foreground-400">
          <span>拖拽节点调整布局 · 滚轮缩放 · 点击节点查看详情 · 双击分组折叠 · 底部时间轴回放</span>
          <span>{graphData.disclaimer || '知识图谱仅记录可追溯证据链，不替代模型预测'}</span>
        </div>
      </footer>

    </div>
  );
}
