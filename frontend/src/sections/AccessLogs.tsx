import { useState, useEffect, useMemo } from "react";
import { CheckCircle, XCircle, Download } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";

/* ================= CONFIG ================= */
const CONFIG = {
  API_BASE_URL: import.meta.env.VITE_API_URL,
  ACCESS_LOGS_ENDPOINT: "/logs/access",
  LIMIT: 100,
  REFRESH_INTERVAL: 10000,
};

/* ================= TYPES ================= */
interface AccessLog {
  id: string;
  plate_number: string;
  token_id: string;
  access_decision: "GRANTED" | "DENIED";
  token_valid: boolean;
  plate_match: boolean;
  confidence?: number;
  timestamp: string;
  total_response_time_ms?: number;
}

/* ================= COMPONENT ================= */
export default function AccessLogs() {
  const [logs, setLogs] = useState<AccessLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [decision, setDecision] = useState("all");

  // Fetch logs
  const fetchLogs = async () => {
    try {
      const res = await fetch(
        `${CONFIG.API_BASE_URL}${CONFIG.ACCESS_LOGS_ENDPOINT}?limit=${CONFIG.LIMIT}`
      );

      if (!res.ok) throw new Error();

      const data = await res.json();
      setLogs(data.logs || []);
    } catch {
      toast.error("Failed to fetch logs");
    } finally {
      setLoading(false);
    }
  };

  // Auto refresh
  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, CONFIG.REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, []);

  // Filter logs
  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      const matchSearch =
        log.plate_number.toLowerCase().includes(search.toLowerCase()) ||
        log.token_id.toLowerCase().includes(search.toLowerCase());

      const matchDecision =
        decision === "all" || log.access_decision === decision;

      return matchSearch && matchDecision;
    });
  }, [logs, search, decision]);

  // Stats
  const stats = useMemo(() => {
    const granted = logs.filter((l) => l.access_decision === "GRANTED").length;

    return {
      total: logs.length,
      granted,
      denied: logs.length - granted,
      rate: logs.length
        ? Math.round((granted / logs.length) * 100)
        : 0,
    };
  }, [logs]);

  // Export CSV
  const exportCSV = () => {
    if (!filteredLogs.length) {
      toast.warning("No logs to export");
      return;
    }

    const headers = Object.keys(filteredLogs[0]);

    const rows = filteredLogs.map((log) =>
      headers.map((h) => (log as any)[h] ?? "").join(",")
    );

    const csv = [headers.join(","), ...rows].join("\n");

    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `logs-${new Date().toISOString().split("T")[0]}.csv`;
    a.click();

    URL.revokeObjectURL(url);
    toast.success("Export successful");
  };

  const icon = (status: boolean) =>
    status ? (
      <CheckCircle className="w-4 h-4 text-green-500" />
    ) : (
      <XCircle className="w-4 h-4 text-red-500" />
    );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between">
        <h2 className="text-xl font-bold">Access Logs</h2>
        <Button onClick={exportCSV}>
          <Download className="w-4 h-4 mr-2" />
          Export
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <Stat title="Total" value={stats.total} />
        <Stat title="Granted" value={stats.granted} />
        <Stat title="Denied" value={stats.denied} />
        <Stat title="Success %" value={`${stats.rate}%`} />
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <Input
          placeholder="Search plate or token..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <Select value={decision} onValueChange={setDecision}>
          <SelectTrigger>
            <SelectValue placeholder="Decision" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="GRANTED">Granted</SelectItem>
            <SelectItem value="DENIED">Denied</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <Card>
        <CardHeader>
          <CardTitle>
            {filteredLogs.length} / {logs.length} Records
          </CardTitle>
        </CardHeader>

        <CardContent>
          {loading ? (
            <p>Loading...</p>
          ) : !filteredLogs.length ? (
            <p className="text-center text-gray-500">No logs found</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Plate</th>
                  <th>Decision</th>
                  <th>Token</th>
                  <th>Match</th>
                </tr>
              </thead>
              <tbody>
                {filteredLogs.map((log) => (
                  <tr key={log.id}>
                    <td>{new Date(log.timestamp).toLocaleString()}</td>
                    <td>{log.plate_number}</td>
                    <td>{log.access_decision}</td>
                    <td>{icon(log.token_valid)}</td>
                    <td>{icon(log.plate_match)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

/* ================= REUSABLE STAT ================= */
function Stat({ title, value }: any) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-sm text-gray-500">{title}</p>
        <p className="text-xl font-bold">{value}</p>
      </CardContent>
    </Card>
  );
}