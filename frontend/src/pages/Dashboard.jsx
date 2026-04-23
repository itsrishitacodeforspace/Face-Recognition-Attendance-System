import { useEffect, useState } from "react";
import { attendanceApi } from "../services/api";
import TrendChart from "../components/TrendChart";
import ConfidenceIndicator from "../components/ConfidenceIndicator";

export default function Dashboard() {
  const [today, setToday] = useState({ total_today: 0, unique_today: 0, avg_confidence: 0 });
  const [heatmap, setHeatmap] = useState({ weekly_trend: [] });

  useEffect(() => {
    const run = async () => {
      const [todayRes, heatmapRes] = await Promise.all([attendanceApi.today(), attendanceApi.heatmap()]);
      setToday(todayRes.data);
      setHeatmap(heatmapRes.data);
    };
    run();
  }, []);

  return (
    <div className="space-y-4">
      <div className="grid-auto">
        <div className="card"><h2 className="font-display text-lg">Today Total</h2><p className="text-3xl font-bold">{today.total_today}</p></div>
        <div className="card"><h2 className="font-display text-lg">Unique People</h2><p className="text-3xl font-bold">{today.unique_today}</p></div>
        <ConfidenceIndicator value={today.avg_confidence || 0} />
      </div>
      <TrendChart label="Weekly Attendance" labels={heatmap.weekly_trend.map((_, i) => `D${i + 1}`)} values={heatmap.weekly_trend || []} />
    </div>
  );
}
