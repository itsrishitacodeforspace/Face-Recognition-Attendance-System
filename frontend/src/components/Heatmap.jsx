export default function AttendanceHeatmap({ title, data = {} }) {
  const entries = Object.entries(data);
  const max = Math.max(...entries.map(([, value]) => value), 1);

  return (
    <div className="card">
      <h3 className="font-display text-lg mb-3">{title}</h3>
      <div className="grid grid-cols-4 gap-2">
        {entries.map(([label, value]) => {
          const intensity = Math.max(0.15, value / max);
          return (
            <div
              key={label}
              className="rounded-xl p-2 text-sm"
              style={{ background: `rgba(232, 93, 4, ${intensity})`, color: intensity > 0.5 ? "white" : "#14222f" }}
            >
              <div className="font-semibold">{label}</div>
              <div>{value}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
