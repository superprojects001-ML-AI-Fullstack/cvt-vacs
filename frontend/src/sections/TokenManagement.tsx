import { useState } from 'react';
import { Key, Plus, Copy, CheckCircle, Clock, XCircle, QrCode, Loader2, Shield } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { toast } from 'sonner';

const API_BASE_URL = import.meta.env.VITE_API_URL;

const tokenTypes = [
  { value: 'jwt', label: 'JWT Token' },
  { value: 'qr', label: 'QR Code' },
  { value: 'otp', label: 'One-Time Password (OTP)' }
];

export default function TokenManagement() {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isVerifyDialogOpen, setIsVerifyDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [generatedToken, setGeneratedToken] = useState<any>(null);
  const [copied, setCopied] = useState(false);

  const [issueForm, setIssueForm] = useState({
    user_id: '',
    plate_number: '',
    token_type: 'jwt',
    expiry_hours: '24'
  });

  const [verifyForm, setVerifyForm] = useState({
    token: '',
    plate_number: ''
  });

  const [verifyResult, setVerifyResult] = useState<any>(null);

  const handleIssueToken = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const response = await fetch(
        `${API_BASE_URL}/tokens/issue?user_id=${issueForm.user_id}&plate_number=${issueForm.plate_number}&token_type=${issueForm.token_type}&expiry_hours=${issueForm.expiry_hours}`,
        { method: 'POST' }
      );

      if (response.ok) {
        const data = await response.json();
        setGeneratedToken(data.token);
        toast.success('Token issued successfully!');
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to issue token');
      }
    } catch {
      toast.error('Network error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVerifyToken = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const response = await fetch(
        `${API_BASE_URL}/tokens/verify-with-plate?token=${encodeURIComponent(verifyForm.token)}&detected_plate=${verifyForm.plate_number}`,
        { method: 'POST' }
      );

      if (response.ok) {
        const data = await response.json();
        setVerifyResult(data);
        toast.success(data.access_granted ? 'Access granted!' : 'Access denied');
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Verification failed');
      }
    } catch {
      toast.error('Network error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">Token Management</h2>
          <p className="text-gray-500">Issue and verify tokens</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setIsVerifyDialogOpen(true)}>
            <Shield className="w-4 h-4 mr-2" /> Verify
          </Button>
          <Button onClick={() => setIsDialogOpen(true)}>
            <Plus className="w-4 h-4 mr-2" /> Issue
          </Button>
        </div>
      </div>

      {/* Issue Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Issue Token</DialogTitle>
          </DialogHeader>

          {!generatedToken ? (
            <form onSubmit={handleIssueToken} className="space-y-4">
              <Input placeholder="Plate Number" value={issueForm.plate_number} onChange={(e) => setIssueForm({ ...issueForm, plate_number: e.target.value })} />
              <Input placeholder="User ID" value={issueForm.user_id} onChange={(e) => setIssueForm({ ...issueForm, user_id: e.target.value })} />

              <Select value={issueForm.token_type} onValueChange={(v) => setIssueForm({ ...issueForm, token_type: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {tokenTypes.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                </SelectContent>
              </Select>

              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? <Loader2 className="animate-spin" /> : 'Issue Token'}
              </Button>
            </form>
          ) : (
            <div>
              <p className="text-green-600">Token Generated</p>
              <Input value={generatedToken.token_string} readOnly />
              <Button onClick={() => copyToClipboard(generatedToken.token_string)}>
                {copied ? 'Copied' : 'Copy'}
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Verify Dialog */}
      <Dialog open={isVerifyDialogOpen} onOpenChange={setIsVerifyDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Verify Token</DialogTitle>
          </DialogHeader>

          <form onSubmit={handleVerifyToken} className="space-y-4">
            <Input placeholder="Token" value={verifyForm.token} onChange={(e) => setVerifyForm({ ...verifyForm, token: e.target.value })} />
            <Input placeholder="Plate Number" value={verifyForm.plate_number} onChange={(e) => setVerifyForm({ ...verifyForm, plate_number: e.target.value })} />

            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? <Loader2 className="animate-spin" /> : 'Verify'}
            </Button>

            {verifyResult && (
              <div>
                {verifyResult.access_granted ? 'Access Granted' : 'Access Denied'}
              </div>
            )}
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
