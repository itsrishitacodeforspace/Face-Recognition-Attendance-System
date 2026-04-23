import { useEffect, useState } from "react";
import { attendanceApi } from "../services/api";
import TrendChart from "../components/TrendChart";

export default function TrendsPage() {
  const [data, setData] = useState({ attendance_by_department: [], confidence_distribution: [] });

  useEffect(() => {
    attendanceApi.trends().then((res) => setData(res.data));
  }, []);

  return (
    <div className="space-y-4">
      <TrendChart
        type="bar"
        label="Attendance by Department"
        labels={data.attendance_by_department.map((x) => x.department)}
        values={data.attendance_by_department.map((x) => x.count)}
      />
      <TrendChart
        type="line"
        label="Confidence Distribution"
        labels={data.confidence_distribution.map((x) => `${x.bucket}`)}
        values={data.confidence_distribution.map((x) => x.count)}
      />
    </div>
  );
}
