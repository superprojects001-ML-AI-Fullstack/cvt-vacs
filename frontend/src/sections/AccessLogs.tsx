/**
 * Access Logs and Audit Trail Page
 */
import { useState, useEffect } from 'react';
import { ClipboardList, Search, Calendar, CheckCircle, XCircle, Clock, Download, Filter } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';

interface AccessLog {
  id: string;
  plate_number: string;
  token_id: string;
  access_decision: 'GRANTED' | 'DENIED';
  token_valid: boolean;
  plate_recognized: boolean;
  plate_match: boolean;
  confidence?: number;
  timestamp: string;
  anpr_processing_time_ms?: number;
  token_verification_time_ms?: number;
  total_response_time_ms?: number;
}

const API_BASE_URL = import.meta.env.VITE_API_URL;

export default function AccessLogs() {
  const [logs, setLogs] = useState<AccessLog[]>([]);
  const [filteredLogs, setFilteredLogs] = useState<AccessLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterDecision, setFilterDecision] = useState<string>('all');

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    filterLogs();
  }, [logs, searchQuery, filterDecision]);

  const fetchLogs = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/logs/access?limit=100`);
      if (response.ok) {
        const data = await response.json();
        setLogs(data.logs || []);
      }
    } catch (error) {
      console.error('Failed to fetch logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const filterLogs = () => {
    let filtered = [...logs];

    // Search filter
    if (searchQuery) {
      filtered = filtered.filter(log =>
        log.plate_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
        log.token_id.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    // Decision filter
    if (filterDecision !== 'all') {
      filtered = filtered.filter(log =>
        log.access_decision.toLowerCase() === filterDecision.toLowerCase()
      );
    }

    setFilteredLogs(filtered);
  };

  const exportLogs = () => {
    const csvContent = [
      ['Timestamp', 'Plate Number', 'Token ID', 'Decision', 'Token Valid', 'Plate Match', 'Confidence', 'Response Time (ms)'].join(','),
      ...filteredLogs.map(log => [
        new Date(log.timestamp).toISOString(),
        log.plate_number,
        log.token_id,
        log.access_decision,
        log.token_valid,
        log.plate_match,
        log.confidence || '',
        log.total_response_time_ms || ''
      ].join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `access-logs-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
    toast.success('Logs exported successfully');
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const getDecisionBadge = (decision: string) => {
    return decision === 'GRANTED' 
      ? <Badge className="bg-green-100 text-green-800 hover:bg-green-100">GRANTED</Badge>
      : <Badge variant="destructive">DENIED</Badge>;
  };

  const getStatusIcon = (status: boolean) => {
    return status 
      ? <CheckCircle className="w-4 h-4 text-green-500" />
      : <XCircle className="w-4 h-4 text-red-500" />;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Access Logs</h2>
          <p className="text-gray-500">Complete audit trail of all access attempts</p>
        </div>
        <Button onClick={exportLogs} variant="outline">
          <Download className="w-4 h-4 mr-2" />
          Export CSV
        </Button>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-gray-500">Total Logs</p>
            <p className="text-2xl font-bold">{logs.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-gray-500">Granted</p>
            <p className="text-2xl font-bold text-green-600">
              {logs.filter(l => l.access_decision === 'GRANTED').length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-gray-500">Denied</p>
            <p className="text-2xl font-bold text-red-600">
              {logs.filter(l => l.access_decision === 'DENIED').length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-gray-500">Success Rate</p>
            <p className="text-2xl font-bold text-blue-600">
              {logs.length > 0 
                ? Math.round((logs.filter(l => l.access_decision === 'GRANTED').length / logs.length) * 100)
                : 0}%
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Search by plate number or token ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={filterDecision} onValueChange={setFilterDecision}>
              <SelectTrigger className="w-[180px]">
                <Filter className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Filter by decision" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Decisions</SelectItem>
                <SelectItem value="granted">Granted</SelectItem>
                <SelectItem value="denied">Denied</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Logs Table */}
      <Card>
        <CardHeader>
          <CardTitle>Access History</CardTitle>
          <CardDescription>
            Showing {filteredLogs.length} of {logs.length} records
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
            </div>
          ) : filteredLogs.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <ClipboardList className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-medium">No logs found</p>
              <p className="text-sm">Access attempts will appear here</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Timestamp</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Plate Number</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Decision</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Token Valid</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Plate Match</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Confidence</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Response Time</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLogs.map((log) => (
                    <tr key={log.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4 text-sm text-gray-600">
                        {formatTime(log.timestamp)}
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-mono font-medium">{log.plate_number}</span>
                      </td>
                      <td className="py-3 px-4">
                        {getDecisionBadge(log.access_decision)}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(log.token_valid)}
                          <span className="text-sm">{log.token_valid ? 'Yes' : 'No'}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(log.plate_match)}
                          <span className="text-sm">{log.plate_match ? 'Yes' : 'No'}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        {log.confidence ? (
                          <span className="text-sm">{(log.confidence * 100).toFixed(1)}%</span>
                        ) : (
                          <span className="text-sm text-gray-400">-</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-600">
                        {log.total_response_time_ms ? (
                          <span>{log.total_response_time_ms.toFixed(0)}ms</span>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Legend */}
      <Card className="bg-gray-50 border-gray-200">
        <CardContent className="p-4">
          <p className="text-sm font-medium text-gray-700 mb-2">Log Entry Fields</p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-sm text-gray-600">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-green-500" />
              <span>Token Valid: JWT signature verified</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-green-500" />
              <span>Plate Match: ANPR matches registered plate</span>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-blue-500" />
              <span>Response Time: Total 2FA verification time</span>
            </div>
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-purple-500" />
              <span>Timestamp: UTC time of access attempt</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
