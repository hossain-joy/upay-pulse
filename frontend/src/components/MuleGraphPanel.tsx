import React, { useState } from 'react';
import { Share2, Filter, RefreshCw, Lock, Unlock, AlertTriangle, Users, ZoomIn, ZoomOut } from 'lucide-react';
import { GraphTopology, GraphNode, GraphEdge } from '../types';

interface Props {
  topology: GraphTopology | null;
  loadingGraph: boolean;
  selectedNode: GraphNode | null;
  selectedCluster: string;
  isFreezingNode: boolean;
  onSelectNode: (n: GraphNode) => void;
  onClusterChange: (c: string) => void;
  onRefresh: () => void;
  onFreeze: () => void;
  onUnfreeze: () => void;
}

const NODE_META: Record<string, { label: string; fill: string; stroke: string; glow: string; icon: string }> = {
  VICTIM:        { label: 'Victim',        fill: '#0c4a6e', stroke: '#38bdf8', glow: '#38bdf840', icon: '👤' },
  PRIMARY_MULE:  { label: 'Primary Mule',  fill: '#7f1d1d', stroke: '#f43f5e', glow: '#f43f5e50', icon: '🎯' },
  SECONDARY_MULE:{ label: 'Relay Mule',    fill: '#7c2d12', stroke: '#fb923c', glow: '#fb923c40', icon: '🔄' },
  CASH_OUT_AGENT:{ label: 'Cash-Out Agent',fill: '#14532d', stroke: '#4ade80', glow: '#4ade8040', icon: '🏧' },
  AGENT:         { label: 'Agent',          fill: '#14532d', stroke: '#4ade80', glow: '#4ade8040', icon: '🏧' },
  NORMAL_USER:   { label: 'Normal User',   fill: '#1e293b', stroke: '#64748b', glow: '#64748b20', icon: '👥' },
};

function getMeta(node: GraphNode) {
  return NODE_META[node.node_type] ?? NODE_META['NORMAL_USER'];
}

function riskColor(score: number) {
  if (score >= 0.8) return '#f43f5e';
  if (score >= 0.5) return '#fb923c';
  if (score >= 0.3) return '#facc15';
  return '#4ade80';
}

function buildPositions(nodes: GraphNode[]): Record<string, { x: number; y: number }> {
  const pos: Record<string, { x: number; y: number }> = {};
  const layers: Record<string, GraphNode[]> = {
    VICTIM: [], PRIMARY_MULE: [], SECONDARY_MULE: [], AGENT: [], NORMAL_USER: [],
  };
  nodes.forEach(n => {
    if (n.node_type === 'VICTIM') layers.VICTIM.push(n);
    else if (n.node_type === 'PRIMARY_MULE') layers.PRIMARY_MULE.push(n);
    else if (n.node_type === 'SECONDARY_MULE') layers.SECONDARY_MULE.push(n);
    else if (n.is_agent || n.node_type === 'CASH_OUT_AGENT' || n.node_type === 'AGENT') layers.AGENT.push(n);
    else layers.NORMAL_USER.push(n);
  });
  const xMap: Record<string, number> = { VICTIM: 100, PRIMARY_MULE: 260, SECONDARY_MULE: 420, AGENT: 580, NORMAL_USER: 340 };
  const H = 400;
  Object.entries(layers).forEach(([type, group]) => {
    group.forEach((node, i) => {
      const step = H / (group.length + 1);
      pos[node.id] = { x: xMap[type], y: Math.round(step * (i + 1)) };
    });
  });
  return pos;
}

function curvedPath(x1: number, y1: number, x2: number, y2: number): string {
  const cx = (x1 + x2) / 2;
  return `M ${x1} ${y1} C ${cx} ${y1}, ${cx} ${y2}, ${x2} ${y2}`;
}

export const MuleGraphPanel: React.FC<Props> = ({
  topology, loadingGraph, selectedNode, selectedCluster,
  isFreezingNode, onSelectNode, onClusterChange, onRefresh, onFreeze, onUnfreeze,
}) => {
  const [zoom, setZoom] = useState(1);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  const positions = topology ? buildPositions(topology.nodes) : {};

  const nodeRadius = (node: GraphNode) => {
    if (node.node_type === 'PRIMARY_MULE') return 26;
    if (node.node_type === 'SECONDARY_MULE') return 22;
    if (node.is_agent || node.node_type === 'CASH_OUT_AGENT' || node.node_type === 'AGENT') return 22;
    return 18;
  };

  return (
    <div className="space-y-4">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-2xl bg-slate-900/90 border border-indigo-500/20">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Share2 className="w-4 h-4 text-indigo-400" />
            Money-Mule Syndicate Graph
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Directed flow: Victim → Primary Mule → Relay → Cash-Out Agent. Click any node to inspect.
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <select
            value={selectedCluster}
            onChange={e => onClusterChange(e.target.value)}
            className="bg-slate-950 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
          >
            <option value="all">All Syndicates</option>
            {topology?.clusters?.map(c => (
              <option key={c.cluster_id} value={c.cluster_id}>
                {c.cluster_id} · {c.size} nodes · ৳{(c.total_volume / 1000).toFixed(0)}k
              </option>
            ))}
          </select>
          <button onClick={() => setZoom(z => Math.min(2, z + 0.2))} className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300">
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button onClick={() => setZoom(z => Math.max(0.5, z - 0.2))} className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300">
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <button onClick={onRefresh} disabled={loadingGraph} className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300">
            <RefreshCw className={`w-3.5 h-3.5 ${loadingGraph ? 'animate-spin text-indigo-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Cluster summary pills */}
      {topology && topology.clusters.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {topology.clusters.map(c => (
            <button
              key={c.cluster_id}
              onClick={() => onClusterChange(c.cluster_id === selectedCluster ? 'all' : c.cluster_id)}
              className={`px-3 py-1 rounded-full text-[11px] font-mono border transition ${
                selectedCluster === c.cluster_id
                  ? 'bg-indigo-600/30 border-indigo-400/60 text-indigo-200'
                  : 'bg-slate-900 border-slate-700 text-slate-400 hover:border-indigo-500/50 hover:text-white'
              }`}
            >
              {c.cluster_id} · {c.size} nodes · ৳{(c.total_volume / 1000).toFixed(0)}k
            </button>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* SVG Canvas */}
        <div className="lg:col-span-2 rounded-2xl bg-slate-950 border border-slate-800 overflow-hidden relative">
          {/* Flow lane labels */}
          <div className="absolute top-3 left-0 right-0 flex justify-around px-6 pointer-events-none z-10">
            {[
              { label: 'VICTIMS', color: 'text-sky-400' },
              { label: 'PRIMARY MULES', color: 'text-rose-400' },
              { label: 'RELAY LAYER', color: 'text-orange-400' },
              { label: 'CASH-OUT', color: 'text-emerald-400' },
            ].map(({ label, color }) => (
              <span key={label} className={`text-[9px] font-mono font-bold tracking-widest ${color} opacity-60`}>{label}</span>
            ))}
          </div>

          {/* Lane dividers */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 680 440" preserveAspectRatio="none">
            {[180, 340, 500].map(x => (
              <line key={x} x1={x} y1={0} x2={x} y2={440} stroke="#1e293b" strokeWidth="1" strokeDasharray="4 4" />
            ))}
          </svg>

          {loadingGraph ? (
            <div className="flex items-center justify-center h-96 text-xs text-slate-400">
              <div className="text-center">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-400" />
                Computing NetworkX graph layout...
              </div>
            </div>
          ) : !topology || topology.nodes.length === 0 ? (
            <div className="flex items-center justify-center h-96 text-xs text-slate-500">
              No nodes in selected cluster.
            </div>
          ) : (
            <div className="overflow-auto" style={{ maxHeight: '480px' }}>
              <svg
                viewBox="0 0 680 440"
                className="w-full select-none"
                style={{ transform: `scale(${zoom})`, transformOrigin: 'top left', minHeight: '440px' }}
              >
                <defs>
                  {/* Arrow markers */}
                  <marker id="arr-normal" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#475569" />
                  </marker>
                  <marker id="arr-high" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#f43f5e" />
                  </marker>
                  <marker id="arr-cashout" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#f59e0b" />
                  </marker>
                  {/* Glow filters */}
                  <filter id="glow-red" x="-50%" y="-50%" width="200%" height="200%">
                    <feGaussianBlur stdDeviation="4" result="blur" />
                    <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
                  </filter>
                  <filter id="glow-blue" x="-50%" y="-50%" width="200%" height="200%">
                    <feGaussianBlur stdDeviation="3" result="blur" />
                    <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
                  </filter>
                </defs>

                {/* Edges */}
                {topology.edges.map(edge => {
                  const p1 = positions[edge.source];
                  const p2 = positions[edge.target];
                  if (!p1 || !p2) return null;
                  const isCashOut = edge.is_cash_out;
                  const isHigh = edge.amount >= 50000;
                  const stroke = isCashOut ? '#f59e0b' : isHigh ? '#f43f5e' : '#334155';
                  const marker = isCashOut ? 'url(#arr-cashout)' : isHigh ? 'url(#arr-high)' : 'url(#arr-normal)';
                  const midX = (p1.x + p2.x) / 2;
                  const midY = (p1.y + p2.y) / 2 - 10;
                  return (
                    <g key={edge.id}>
                      <path
                        d={curvedPath(p1.x, p1.y, p2.x, p2.y)}
                        fill="none"
                        stroke={stroke}
                        strokeWidth={isCashOut || isHigh ? 2.5 : 1.5}
                        strokeOpacity={0.7}
                        markerEnd={marker}
                      />
                      <text x={midX} y={midY} fill={stroke} fontSize="9" fontFamily="monospace" fontWeight="bold" textAnchor="middle" opacity="0.9">
                        ৳{(edge.amount / 1000).toFixed(0)}k{edge.tx_count > 1 ? ` ×${edge.tx_count}` : ''}
                      </text>
                    </g>
                  );
                })}

                {/* Nodes */}
                {topology.nodes.map(node => {
                  const pos = positions[node.id];
                  if (!pos) return null;
                  const meta = getMeta(node);
                  const r = nodeRadius(node);
                  const isSelected = selectedNode?.id === node.id;
                  const isHovered = hoveredNode === node.id;
                  const isPrimary = node.node_type === 'PRIMARY_MULE';
                  return (
                    <g
                      key={node.id}
                      className="cursor-pointer"
                      onClick={() => onSelectNode(node)}
                      onMouseEnter={() => setHoveredNode(node.id)}
                      onMouseLeave={() => setHoveredNode(null)}
                    >
                      {/* Outer glow ring for selected */}
                      {isSelected && (
                        <circle cx={pos.x} cy={pos.y} r={r + 10} fill="none" stroke="#06b6d4" strokeWidth="2" strokeDasharray="5 3" opacity="0.8" />
                      )}
                      {/* Pulse ring for active mules */}
                      {isPrimary && !node.is_frozen && (
                        <circle cx={pos.x} cy={pos.y} r={r + 6} fill={meta.glow} stroke={meta.stroke} strokeWidth="1" opacity="0.4" className="animate-ping" />
                      )}
                      {/* Main node circle */}
                      <circle
                        cx={pos.x} cy={pos.y} r={r}
                        fill={meta.fill}
                        stroke={node.is_frozen ? '#ef4444' : isSelected || isHovered ? '#06b6d4' : meta.stroke}
                        strokeWidth={node.is_frozen ? 3 : isSelected ? 2.5 : 2}
                        strokeDasharray={node.is_frozen ? '4 2' : undefined}
                        filter={isPrimary && !node.is_frozen ? 'url(#glow-red)' : undefined}
                      />
                      {/* Risk score arc */}
                      <circle
                        cx={pos.x} cy={pos.y} r={r - 4}
                        fill="none"
                        stroke={riskColor(node.risk_score)}
                        strokeWidth="2.5"
                        strokeDasharray={`${node.risk_score * 2 * Math.PI * (r - 4)} ${2 * Math.PI * (r - 4)}`}
                        strokeLinecap="round"
                        transform={`rotate(-90 ${pos.x} ${pos.y})`}
                        opacity="0.6"
                      />
                      {/* Icon */}
                      <text x={pos.x} y={pos.y - 3} textAnchor="middle" fontSize={r > 22 ? '13' : '11'} dominantBaseline="middle">
                        {node.is_frozen ? '🔒' : meta.icon}
                      </text>
                      {/* Risk % below icon */}
                      <text x={pos.x} y={pos.y + 10} textAnchor="middle" fontSize="8" fill={riskColor(node.risk_score)} fontFamily="monospace" fontWeight="bold">
                        {(node.risk_score * 100).toFixed(0)}%
                      </text>
                      {/* Label below node */}
                      <text x={pos.x} y={pos.y + r + 13} textAnchor="middle" fontSize="9" fill={node.is_frozen ? '#f87171' : '#94a3b8'} fontFamily="sans-serif">
                        {node.label.length > 16 ? node.label.slice(0, 15) + '…' : node.label}
                      </text>
                      {/* Hover tooltip */}
                      {isHovered && (
                        <g>
                          <rect x={pos.x - 60} y={pos.y - r - 42} width="120" height="34" rx="6" fill="#0f172a" stroke="#334155" strokeWidth="1" />
                          <text x={pos.x} y={pos.y - r - 28} textAnchor="middle" fontSize="9" fill="#e2e8f0" fontFamily="monospace">
                            In: {node.in_degree} · Out: {node.out_degree}
                          </text>
                          <text x={pos.x} y={pos.y - r - 16} textAnchor="middle" fontSize="9" fill="#94a3b8" fontFamily="monospace">
                            ৳{(node.total_received / 1000).toFixed(0)}k recv · PR {node.pagerank?.toFixed(3)}
                          </text>
                        </g>
                      )}
                    </g>
                  );
                })}
              </svg>
            </div>
          )}

          {/* Legend */}
          <div className="px-4 py-3 border-t border-slate-800 flex flex-wrap gap-3 text-[10px] text-slate-400">
            {Object.entries(NODE_META).filter(([k]) => k !== 'NORMAL_USER').map(([, v]) => (
              <span key={v.label} className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full border" style={{ background: v.fill, borderColor: v.stroke }} />
                {v.label}
              </span>
            ))}
            <span className="flex items-center gap-1.5 ml-2"><span className="w-5 h-0.5 bg-amber-400 rounded" /> Cash-Out flow</span>
            <span className="flex items-center gap-1.5"><span className="w-5 h-0.5 bg-rose-500 rounded" /> High-volume</span>
            <span className="flex items-center gap-1.5"><span className="w-5 h-0.5 bg-slate-600 rounded" /> Normal flow</span>
          </div>
        </div>

        {/* Node Inspector */}
        <div className="rounded-2xl bg-slate-900/90 border border-slate-800 p-4 flex flex-col gap-4">
          {selectedNode ? (
            <>
              {/* Header */}
              <div className="flex items-start justify-between gap-2 pb-3 border-b border-slate-800">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-lg">{getMeta(selectedNode).icon}</span>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
                      selectedNode.is_frozen
                        ? 'bg-rose-950 text-rose-300 border-rose-500/40'
                        : 'bg-emerald-950 text-emerald-300 border-emerald-500/40'
                    }`}>
                      {selectedNode.is_frozen ? '🔒 FROZEN' : '● ACTIVE'}
                    </span>
                  </div>
                  <div className="text-sm font-bold text-white leading-tight">{selectedNode.label}</div>
                  <div className="text-[10px] font-mono text-slate-500 mt-0.5">{selectedNode.id}</div>
                  {selectedNode.cluster_id && (
                    <span className="inline-block mt-1 text-[10px] font-mono px-2 py-0.5 bg-indigo-950 text-indigo-300 border border-indigo-500/30 rounded-full">
                      {selectedNode.cluster_id}
                    </span>
                  )}
                </div>
              </div>

              {/* Risk gauge */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-400">Risk Score</span>
                  <span className="font-mono font-bold" style={{ color: riskColor(selectedNode.risk_score) }}>
                    {(selectedNode.risk_score * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{ width: `${selectedNode.risk_score * 100}%`, background: riskColor(selectedNode.risk_score) }}
                  />
                </div>
              </div>

              {/* Stats grid */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                {[
                  { label: 'In-Degree', value: `${selectedNode.in_degree} sources` },
                  { label: 'Out-Degree', value: `${selectedNode.out_degree} targets` },
                  { label: 'Total Received', value: `৳${(selectedNode.total_received / 1000).toFixed(1)}k` },
                  { label: 'Total Sent', value: `৳${(selectedNode.total_sent / 1000).toFixed(1)}k` },
                  { label: 'PageRank', value: selectedNode.pagerank?.toFixed(4) ?? '—' },
                  { label: 'Node Type', value: selectedNode.node_type.replace(/_/g, ' ') },
                ].map(({ label, value }) => (
                  <div key={label} className="p-2 rounded-xl bg-slate-950 border border-slate-800">
                    <div className="text-[9px] text-slate-500 uppercase tracking-wider">{label}</div>
                    <div className="font-mono text-xs text-white font-semibold mt-0.5 truncate">{value}</div>
                  </div>
                ))}
              </div>

              {/* Anomaly flags */}
              {selectedNode.reasons && selectedNode.reasons.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-[10px] font-mono uppercase text-slate-400 tracking-wider">Anomaly Flags</div>
                  {selectedNode.reasons.map((r, i) => (
                    <div key={i} className="flex items-start gap-2 p-2 rounded-xl bg-rose-950/30 border border-rose-500/20 text-xs text-slate-300">
                      <AlertTriangle className="w-3 h-3 text-rose-400 shrink-0 mt-0.5" />
                      <span>{r}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Action button */}
              {selectedNode.is_frozen ? (
                <button
                  onClick={onUnfreeze}
                  disabled={isFreezingNode}
                  className="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center justify-center gap-2 transition disabled:opacity-50"
                >
                  {isFreezingNode ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Unlock className="w-3.5 h-3.5" />}
                  Unfreeze Account
                </button>
              ) : (
                <button
                  onClick={onFreeze}
                  disabled={isFreezingNode}
                  className="w-full py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold flex items-center justify-center gap-2 transition disabled:opacity-50"
                >
                  {isFreezingNode ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Lock className="w-3.5 h-3.5" />}
                  Master Freeze (&lt;300ms SLA)
                </button>
              )}
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-full py-16 text-center gap-3">
              <Users className="w-8 h-8 text-slate-700" />
              <p className="text-xs text-slate-500">Click any node in the graph<br />to inspect its profile and act.</p>
            </div>
          )}
        </div>
      </div>

      {/* Summary stats bar */}
      {topology && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Total Nodes', value: topology.summary.total_nodes, color: 'text-cyan-400' },
            { label: 'Total Edges', value: topology.summary.total_edges, color: 'text-indigo-400' },
            { label: 'Mule Nodes', value: topology.summary.mule_nodes_detected, color: 'text-rose-400' },
            { label: 'Syndicate Rings', value: topology.summary.clusters_detected, color: 'text-amber-400' },
          ].map(({ label, value, color }) => (
            <div key={label} className="rounded-xl bg-slate-900/80 border border-slate-800 p-3 text-center">
              <div className={`text-xl font-black font-mono ${color}`}>{value}</div>
              <div className="text-[10px] text-slate-500 mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
