export default function ConfidenceIndicator({ value = 0 }) {
  const pct = Math.round(value * 100);
  const color = value > 0.8 ? "#63a088" : value > 0.6 ? "#eab308" : "#ef4444";

  return (
    <div className="card">
      <h4 className="font-display">Confidence</h4>
      <div className="mt-2 h-3 rounded-full bg-slate-200 overflow-hidden">
        <div style={{ width: `${pct}%`, background: color }} className="h-full transition-all" />
      </div>
      <div className="mt-2 text-sm font-semibold">{pct}%</div>
    </div>
  );
}
