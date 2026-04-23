import { useEffect, useState } from "react";
import { attendanceApi } from "../services/api";

export default function AttendancePage() {
  const [records, setRecords] = useState([]);
  const [deletingId, setDeletingId] = useState(null);
  const [message, setMessage] = useState("");

  const load = async () => {
    const { data } = await attendanceApi.list();
    setRecords(data);
  };

  useEffect(() => {
    load();
  }, []);

  const exportCsv = async () => {
    const { data } = await attendanceApi.exportCsv();
    const url = window.URL.createObjectURL(new Blob([data]));
    const link = document.createElement("a");
    link.href = url;
    link.download = "attendance.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  const deleteRecord = async (id) => {
    const confirmed = window.confirm("Delete this attendance record?");
    if (!confirmed) return;

    setDeletingId(id);
    setMessage("");
    try {
      await attendanceApi.remove(id);
      setMessage("Attendance record deleted successfully.");
      await load();
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Failed to delete attendance record.");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-display text-lg">Attendance Logs</h3>
        <button onClick={exportCsv} className="rounded bg-accent text-white px-3 py-2">Export CSV</button>
      </div>
      {message ? <div className="mb-3 text-sm">{message}</div> : null}
      <div className="overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left border-b">
              <th className="p-2">Name</th>
              <th className="p-2">Department</th>
              <th className="p-2">Timestamp</th>
              <th className="p-2">Confidence</th>
              <th className="p-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {records.map((row) => (
              <tr key={row.id} className="border-b">
                <td className="p-2">{row.person_name}</td>
                <td className="p-2">{row.department}</td>
                <td className="p-2">{new Date(row.timestamp).toLocaleString()}</td>
                <td className="p-2">{row.confidence_score.toFixed(3)}</td>
                <td className="p-2">
                  <button
                    className="rounded bg-red-600 text-white px-2 py-1"
                    onClick={() => deleteRecord(row.id)}
                    disabled={deletingId === row.id}
                  >
                    {deletingId === row.id ? "Deleting..." : "Delete"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
