import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar, Line } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Tooltip, Legend);

export default function TrendChart({ type = "line", labels = [], values = [], label = "Attendance" }) {
  const data = {
    labels,
    datasets: [
      {
        label,
        data: values,
        borderColor: "#e85d04",
        backgroundColor: "rgba(111, 163, 239, 0.45)",
        tension: 0.25,
        fill: type === "line",
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: { display: true },
    },
  };

  return <div className="card">{type === "bar" ? <Bar data={data} options={options} /> : <Line data={data} options={options} />}</div>;
}
