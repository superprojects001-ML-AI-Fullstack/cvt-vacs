/**
 * Vehicle Registration Page
 */
import { useState, useEffect } from 'react';
import { Car, Plus, Search, CheckCircle, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { toast } from 'sonner';

// Constants
const API_BASE_URL = import.meta.env.VITE_API_URL;
const DEFAULT_VEHICLE_TYPE = 'sedan';
const DEFAULT_LIMIT = 100;

const vehicleTypes = [
  { value: 'sedan', label: 'Sedan' },
  { value: 'suv', label: 'SUV' },
  { value: 'truck', label: 'Truck' },
  { value: 'van', label: 'Van' },
  { value: 'motorcycle', label: 'Motorcycle' },
  { value: 'other', label: 'Other' }
];

interface Vehicle {
  id: string;
  plate_number: string;
  vehicle_type: string;
  make?: string;
  model?: string;
  color?: string;
  user_id: string;
  status: string;
  registered_at: string;
}

export default function VehicleRegistration() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    plate_number: '',
    vehicle_type: DEFAULT_VEHICLE_TYPE,
    make: '',
    model: '',
    color: '',
    user_id: ''
  });

  useEffect(() => {
    fetchVehicles();
  }, []);

  const fetchVehicles = async () => {
    // Debug: Check if API URL is configured
    if (!API_BASE_URL) {
      console.error('❌ VITE_API_URL is not set!');
      toast.error('API URL is not configured. Check environment variables.');
      setLoading(false);
      return;
    }

    const url = `${API_BASE_URL}/vehicles/all?limit=${DEFAULT_LIMIT}`;
    console.log('🔍 Fetching from:', url);

    try {
      const response = await fetch(url);
      console.log('📡 Response status:', response.status);

      if (response.ok) {
        const data = await response.json();
        console.log('✅ Data received:', data);
        setVehicles(data.vehicles || []);
      } else {
        const errorText = await response.text();
        console.error('❌ Error response:', errorText);
        toast.error(`Failed to fetch vehicles: ${response.status}`);
      }
    } catch (error) {
      console.error('❌ Network error:', error);
      toast.error('Network error - check console for details');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validation
    if (!formData.plate_number.trim()) {
      toast.error('License plate number is required');
      return;
    }
    if (!formData.user_id.trim()) {
      toast.error('Owner User ID is required');
      return;
    }

    if (!API_BASE_URL) {
      toast.error('API URL is not configured');
      return;
    }

    setIsSubmitting(true);

    const url = `${API_BASE_URL}/vehicles/register`;
    console.log('📝 POST to:', url);
    console.log('📦 Payload:', formData);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      console.log('📡 Response status:', response.status);

      if (response.ok) {
        const data = await response.json();
        console.log('✅ Registration success:', data);
        toast.success('Vehicle registered successfully!');
        setIsDialogOpen(false);
        resetForm();
        fetchVehicles();
      } else {
        const errorData = await response.json().catch(() => ({}));
        console.error('❌ Registration failed:', errorData);
        toast.error(errorData.detail || `Failed: ${response.status}`);
      }
    } catch (error) {
      console.error('❌ Network error:', error);
      toast.error('Network error - check console');
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetForm = () => {
    setFormData({
      plate_number: '',
      vehicle_type: DEFAULT_VEHICLE_TYPE,
      make: '',
      model: '',
      color: '',
      user_id: ''
    });
  };

  const filteredVehicles = vehicles.filter((v) =>
    v.plate_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
    v.make?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    v.model?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getStatusBadge = (status: string) => {
    const statusMap: Record<string, { className: string; label: string }> = {
      active: { className: 'bg-green-100 text-green-800', label: 'Active' },
      inactive: { className: 'bg-gray-100 text-gray-800', label: 'Inactive' },
      banned: { className: 'bg-red-100 text-red-800', label: 'Banned' },
      suspended: { className: 'bg-yellow-100 text-yellow-800', label: 'Suspended' }
    };

    const config = statusMap[status.toLowerCase()] || {
      className: 'bg-gray-100 text-gray-800',
      label: status.charAt(0).toUpperCase() + status.slice(1)
    };

    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full ${config.className}`}>
        {config.label}
      </span>
    );
  };

  const openRegisterDialog = () => {
    resetForm();
    setIsDialogOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Vehicle Registration</h2>
          <p className="text-gray-500">Manage registered vehicles in the system</p>
        </div>
        <Button onClick={openRegisterDialog} className="gap-2">
          <Plus className="w-4 h-4" />
          Register Vehicle
        </Button>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              placeholder="Search by plate number, make, or model..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Vehicles List */}
      <Card>
        <CardHeader>
          <CardTitle>Registered Vehicles</CardTitle>
          <CardDescription>
            {filteredVehicles.length} vehicle{filteredVehicles.length !== 1 ? 's' : ''} found
          </CardDescription>
        </CardHeader>

        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
            </div>
          ) : filteredVehicles.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <Car className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-medium">No vehicles found</p>
              <p className="text-sm">Register a vehicle to get started</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Plate Number</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Type</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Make/Model</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Color</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Status</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Registered</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredVehicles.map((vehicle) => (
                    <tr key={vehicle.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <Car className="w-4 h-4 text-gray-400" />
                          <span className="font-medium">{vehicle.plate_number}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 capitalize">{vehicle.vehicle_type}</td>
                      <td className="py-3 px-4">
                        {vehicle.make && vehicle.model
                          ? `${vehicle.make} ${vehicle.model}`
                          : (vehicle.make || vehicle.model || '-')}
                      </td>
                      <td className="py-3 px-4 capitalize">{vehicle.color || '-'}</td>
                      <td className="py-3 px-4">{getStatusBadge(vehicle.status)}</td>
                      <td className="py-3 px-4 text-sm text-gray-500">
                        {new Date(vehicle.registered_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Registration Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Register New Vehicle</DialogTitle>
            <DialogDescription>
              Enter vehicle details to register in the access control system
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label htmlFor="plate_number">License Plate Number *</Label>
              <Input
                id="plate_number"
                placeholder="e.g., ABC-123-XY"
                value={formData.plate_number}
                onChange={(e) => setFormData({ ...formData, plate_number: e.target.value })}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="vehicle_type">Vehicle Type</Label>
              <Select
                value={formData.vehicle_type}
                onValueChange={(value) => setFormData({ ...formData, vehicle_type: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {vehicleTypes.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="make">Make</Label>
                <Input
                  id="make"
                  placeholder="e.g., Toyota"
                  value={formData.make}
                  onChange={(e) => setFormData({ ...formData, make: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="model">Model</Label>
                <Input
                  id="model"
                  placeholder="e.g., Camry"
                  value={formData.model}
                  onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="color">Color</Label>
              <Input
                id="color"
                placeholder="e.g., Black"
                value={formData.color}
                onChange={(e) => setFormData({ ...formData, color: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="user_id">Owner User ID *</Label>
              <Input
                id="user_id"
                placeholder="Enter user ID"
                value={formData.user_id}
                onChange={(e) => setFormData({ ...formData, user_id: e.target.value })}
                required
              />
            </div>

            <div className="flex gap-3 pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsDialogOpen(false)}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                className="flex-1"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Registering...
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Register Vehicle
                  </>
                )}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}