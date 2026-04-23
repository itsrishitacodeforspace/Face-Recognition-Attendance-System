export default function LiveFeed({ events = [], onClear }) {
  const formatIst = (value) => {
    if (!value) return "-";
    const date = new Date(value);
    return new Intl.DateTimeFormat("en-IN", {
      timeZone: "Asia/Kolkata",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    }).format(date);
  };

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-display text-lg">Live Recognition Events</h3>
        <button onClick={onClear} className="rounded bg-slate-800 text-white px-3 py-1 text-sm">Clear</button>
      </div>
      <div className="max-h-[420px] overflow-auto space-y-2">
        {events.map((event, idx) => (
          <div key={`${event.timestamp}-${idx}`} className="rounded-xl border border-slate-200 p-3 text-sm bg-white">
            <div className="font-semibold">{event.name || "Unknown"}</div>
            <div>ID: {event.person_id ?? event.person_details?.person_id ?? "-"}</div>
            <div>Department: {event.person_details?.department || "-"}</div>
            <div>Email: {event.person_details?.email || "-"}</div>
            <div>Confidence: {(event.confidence || 0).toFixed(3)}</div>
            {typeof event.target_confidence === "number" ? (
              <div>
                Target: {event.target_confidence.toFixed(2)} | {event.meets_target ? "Meets target" : "Below target"}
              </div>
            ) : null}
            <div>Status: {event.message}</div>
            <div>Time (IST): {formatIst(event.timestamp)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
