import { useRef, useEffect, useCallback, useState } from 'react';
import { useDetailStore } from '../../stores/detailStore';

interface GraphNode {
  id: string;
  name: string;
  category: string;
  adoption_count: number;
  definition: string;
  // Physics
  x: number;
  y: number;
  vx: number;
  vy: number;
}

interface GraphEdge {
  source: string;
  target: string;
  weight: number;
}

interface ConceptGraphProps {
  nodes: { id: string; name: string; category: string; adoption_count: number; definition: string }[];
  edges: { source: string; target: string; weight: number }[];
  width: number;
  height: number;
}

const CATEGORY_COLORS: Record<string, string> = {
  philosophy: '#7c5bf5',
  religion: '#f472b6',
  government: '#3b82f6',
  economy: '#fbbf24',
  art: '#f87171',
  technology: '#34d399',
  social_norm: '#818cf8',
  organization: '#fb923c',
};

const DEFAULT_COLOR = '#6b7280';

export default function ConceptGraph({ nodes: rawNodes, edges: rawEdges, width, height }: ConceptGraphProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const nodesRef = useRef<GraphNode[]>([]);
  const edgesRef = useRef<GraphEdge[]>([]);
  const animRef = useRef<number>(0);
  const dragRef = useRef<{ nodeIdx: number; offsetX: number; offsetY: number } | null>(null);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const openDetail = useDetailStore((s) => s.openDetail);

  // Initialize nodes with positions
  useEffect(() => {
    const cx = width / 2;
    const cy = height / 2;
    nodesRef.current = rawNodes.map((n, i) => ({
      ...n,
      x: cx + Math.cos(i * 2.4) * (80 + Math.random() * 60),
      y: cy + Math.sin(i * 2.4) * (80 + Math.random() * 60),
      vx: 0,
      vy: 0,
    }));
    edgesRef.current = rawEdges;
  }, [rawNodes, rawEdges, width, height]);

  // Physics simulation + rendering
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = width;
    canvas.height = height;

    const cx = width / 2;
    const cy = height / 2;
    let ticks = 0;

    function simulate() {
      const nodes = nodesRef.current;
      const edges = edgesRef.current;
      if (nodes.length === 0) return;

      const damping = 0.85;
      const repulsion = 2000;
      const springLength = 80;
      const springK = 0.02;
      const centerGravity = 0.005;

      // Apply forces
      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i];
        // Repulsion from other nodes
        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j];
          let dx = a.x - b.x;
          let dy = a.y - b.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = repulsion / (dist * dist);
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          a.vx += fx;
          a.vy += fy;
          b.vx -= fx;
          b.vy -= fy;
        }

        // Center gravity
        a.vx += (cx - a.x) * centerGravity;
        a.vy += (cy - a.y) * centerGravity;
      }

      // Spring forces (edges)
      const nodeMap = new Map(nodes.map((n, i) => [n.id, i]));
      for (const edge of edges) {
        const ai = nodeMap.get(edge.source);
        const bi = nodeMap.get(edge.target);
        if (ai === undefined || bi === undefined) continue;
        const a = nodes[ai];
        const b = nodes[bi];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const displacement = dist - springLength;
        const force = springK * displacement * (edge.weight || 1);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        a.vx += fx;
        a.vy += fy;
        b.vx -= fx;
        b.vy -= fy;
      }

      // Update positions
      for (const node of nodes) {
        if (dragRef.current && nodes[dragRef.current.nodeIdx] === node) continue;
        node.vx *= damping;
        node.vy *= damping;
        node.x += node.vx;
        node.y += node.vy;
        // Bounds
        node.x = Math.max(20, Math.min(width - 20, node.x));
        node.y = Math.max(20, Math.min(height - 20, node.y));
      }

      ticks++;
    }

    function render() {
      if (!ctx) return;
      const nodes = nodesRef.current;
      const edges = edgesRef.current;

      ctx.clearRect(0, 0, width, height);

      const nodeMap = new Map(nodes.map((n, i) => [n.id, i]));

      // Draw edges
      for (const edge of edges) {
        const ai = nodeMap.get(edge.source);
        const bi = nodeMap.get(edge.target);
        if (ai === undefined || bi === undefined) continue;
        const a = nodes[ai];
        const b = nodes[bi];
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.strokeStyle = `rgba(124, 91, 245, ${Math.min(0.4, 0.1 * edge.weight)})`;
        ctx.lineWidth = Math.min(3, 0.5 + edge.weight * 0.5);
        ctx.stroke();
      }

      // Draw nodes
      for (const node of nodes) {
        const radius = Math.max(5, Math.min(20, 4 + node.adoption_count * 2));
        const color = CATEGORY_COLORS[node.category] || DEFAULT_COLOR;

        // Glow
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius + 4, 0, Math.PI * 2);
        ctx.fillStyle = color + '20';
        ctx.fill();

        // Body
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.strokeStyle = color + '80';
        ctx.lineWidth = 1;
        ctx.stroke();

        // Label
        ctx.font = '10px system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillStyle = '#e0e0e0';
        ctx.fillText(
          node.name.length > 14 ? node.name.slice(0, 12) + '..' : node.name,
          node.x,
          node.y + radius + 14
        );
      }

      // Hovered tooltip
      if (hoveredNode) {
        const x = hoveredNode.x + 15;
        const y = hoveredNode.y - 10;
        ctx.font = '11px system-ui, sans-serif';
        const text = `${hoveredNode.name} (${hoveredNode.category})`;
        const tw = ctx.measureText(text).width;
        ctx.fillStyle = 'rgba(6, 6, 12, 0.9)';
        ctx.fillRect(x - 4, y - 14, tw + 8, 20);
        ctx.strokeStyle = 'rgba(124, 91, 245, 0.3)';
        ctx.lineWidth = 1;
        ctx.strokeRect(x - 4, y - 14, tw + 8, 20);
        ctx.fillStyle = '#e0e0e0';
        ctx.fillText(text, x - 4 + (tw + 8) / 2, y);
        ctx.textAlign = 'start';
      }
    }

    function tick() {
      // Slow down simulation after stabilization
      if (ticks < 200) simulate();
      render();
      animRef.current = requestAnimationFrame(tick);
    }

    animRef.current = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(animRef.current);
    };
  }, [width, height, hoveredNode]);

  // Mouse interactions
  const findNode = useCallback((mx: number, my: number): number => {
    const nodes = nodesRef.current;
    for (let i = nodes.length - 1; i >= 0; i--) {
      const n = nodes[i];
      const r = Math.max(5, Math.min(20, 4 + n.adoption_count * 2));
      const dx = mx - n.x;
      const dy = my - n.y;
      if (dx * dx + dy * dy <= (r + 4) * (r + 4)) return i;
    }
    return -1;
  }, []);

  const getMousePos = useCallback((e: React.MouseEvent) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return { x: 0, y: 0 };
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    const pos = getMousePos(e);
    const idx = findNode(pos.x, pos.y);
    if (idx >= 0) {
      const n = nodesRef.current[idx];
      dragRef.current = { nodeIdx: idx, offsetX: pos.x - n.x, offsetY: pos.y - n.y };
    }
  }, [findNode, getMousePos]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    const pos = getMousePos(e);
    if (dragRef.current) {
      const n = nodesRef.current[dragRef.current.nodeIdx];
      n.x = pos.x - dragRef.current.offsetX;
      n.y = pos.y - dragRef.current.offsetY;
      n.vx = 0;
      n.vy = 0;
    } else {
      const idx = findNode(pos.x, pos.y);
      setHoveredNode(idx >= 0 ? nodesRef.current[idx] : null);
    }
  }, [findNode, getMousePos]);

  const handleMouseUp = useCallback(() => {
    dragRef.current = null;
  }, []);

  const handleClick = useCallback((e: React.MouseEvent) => {
    const pos = getMousePos(e);
    const idx = findNode(pos.x, pos.y);
    if (idx >= 0) {
      const n = nodesRef.current[idx];
      openDetail('concept', {
        id: n.id,
        name: n.name,
        category: n.category,
        adoption_count: n.adoption_count,
        definition: n.definition,
      });
    }
  }, [findNode, getMousePos, openDetail]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      className="cursor-grab active:cursor-grabbing rounded-lg"
      style={{ width, height }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onClick={handleClick}
    />
  );
}
