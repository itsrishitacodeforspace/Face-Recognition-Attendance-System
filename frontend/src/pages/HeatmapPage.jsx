import { useEffect, useState } from "react";
import { attendanceApi } from "../services/api";
import AttendanceHeatmap from "../components/Heatmap";

export default function HeatmapPage() {
  const [data, setData] = useState({ hourly: {}, daily: {} });

  useEffect(() => {
    attendanceApi.heatmap().then((res) => setData(res.data));
  }, []);

  return (
    <div className="space-y-4">
      <AttendanceHeatmap title="Hourly Pattern" data={data.hourly} />
      <AttendanceHeatmap title="Daily Pattern" data={data.daily} />
    </div>
  );
}
