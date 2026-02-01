import { useState, useRef, useEffect, useCallback } from 'react';
import { Play, ChevronDown, ChevronUp, AlertTriangle } from 'lucide-react';

interface CodeSandboxProps {
  artifact: { id: string; content?: any };
}

export default function CodeSandbox({ artifact }: CodeSandboxProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [executed, setExecuted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSource, setShowSource] = useState(false);

  const content = artifact.content || {};
  const source = content.source || '';

  const execute = useCallback(() => {
    if (!iframeRef.current || !source) return;

    setError(null);
    setExecuted(true);

    const html = `<!DOCTYPE html>
<html>
<head>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #06060c; overflow: hidden; }
  canvas { display: block; }
</style>
</head>
<body>
<canvas id="c" width="400" height="300"></canvas>
<script>
  // Disable network access
  window.fetch = undefined;
  window.XMLHttpRequest = undefined;
  window.WebSocket = undefined;
  window.EventSource = undefined;

  const canvas = document.getElementById('c');
  const ctx = canvas.getContext('2d');

  // Timeout protection
  const __timeout = setTimeout(() => {
    window.parent.postMessage({ type: 'sandbox-error', error: 'Execution timeout (5s)' }, '*');
  }, 5000);

  try {
    ${source}
    clearTimeout(__timeout);
    window.parent.postMessage({ type: 'sandbox-done' }, '*');
  } catch(e) {
    clearTimeout(__timeout);
    window.parent.postMessage({ type: 'sandbox-error', error: e.message }, '*');
  }
</script>
</body>
</html>`;

    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    iframeRef.current.src = url;

    // Cleanup blob URL after load
    iframeRef.current.onload = () => {
      URL.revokeObjectURL(url);
    };
  }, [source]);

  // Listen for messages from sandbox
  useEffect(() => {
    const handler = (e: MessageEvent) => {
      if (e.data?.type === 'sandbox-error') {
        setError(e.data.error || 'Unknown error');
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, []);

  return (
    <div className="rounded-xl bg-black/30 border border-white/[0.06] overflow-hidden">
      {/* Canvas area */}
      <div className="relative bg-[#06060c]" style={{ height: 300 }}>
        <iframe
          ref={iframeRef}
          sandbox="allow-scripts"
          className="w-full h-full border-0"
          title={`sandbox-${artifact.id}`}
          style={{ display: executed ? 'block' : 'none' }}
        />
        {!executed && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
            <button
              onClick={execute}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-accent/20 text-accent hover:bg-accent/30 transition-colors text-[12px] font-medium"
            >
              <Play size={14} />
              Run Code
            </button>
            <span className="text-[10px] text-text-3">Sandboxed execution</span>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-start gap-2 px-3 py-2 bg-red-500/10 border-t border-red-500/20">
          <AlertTriangle size={12} className="text-red-400 flex-shrink-0 mt-0.5" />
          <span className="text-[11px] text-red-400 mono">{error}</span>
        </div>
      )}

      {/* Source toggle */}
      {source && (
        <div className="border-t border-white/[0.06]">
          <button
            onClick={() => setShowSource(!showSource)}
            className="w-full flex items-center justify-between px-3 py-2 text-[10px] text-text-3 hover:bg-white/[0.02] transition-colors"
          >
            <span className="font-medium uppercase tracking-wider">Source ({content.language || 'javascript'})</span>
            {showSource ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
          {showSource && (
            <div className="px-3 pb-3">
              <pre className="p-3 rounded-lg bg-black/40 border border-white/[0.04] text-[11px] text-text-2 mono leading-relaxed overflow-x-auto max-h-48 whitespace-pre-wrap">
                {source}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
