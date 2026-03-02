import React, { useEffect, useState } from 'react';
import './Dashboard.css'; // reuse basic layout styles

const Settings = () => {
  const [emails, setEmails] = useState([
    { email: '', enabled: true },
    { email: '', enabled: false },
    { email: '', enabled: false },
  ]);
  const [maintenanceMode, setMaintenanceMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  };

  const loadNotificationEmails = async () => {
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      const response = await fetch(
        'http://localhost:8000/api/v1/system-config/notification-admin-emails',
        {
          headers: getAuthHeaders(),
        }
      );

      if (!response.ok) {
        // 404 just means not configured yet; fall back to defaults
        if (response.status !== 404) {
          throw new Error('Failed to load notification admin emails');
        }
        return;
      }

      const data = await response.json();
      if (Array.isArray(data.emails)) {
        const filled = data.emails.concat(
          Array(3 - data.emails.length).fill({ email: '', enabled: false })
        ).slice(0, 3);
        setEmails(filled);
      }
    } catch (err) {
      console.error('Error loading notification emails:', err);
      setError(err.message || 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const loadSystemSettings = async () => {
    try {
      // Try to get full settings first (requires system admin auth)
      let response = await fetch(
        'http://localhost:8000/api/v1/system/settings',
        {
          headers: getAuthHeaders(),
        }
      );

      if (response.ok) {
        const data = await response.json();
        console.log('Full settings response:', data);
        if (data.maintenanceMode !== undefined) {
          setMaintenanceMode(!!data.maintenanceMode); // Ensure boolean
          console.log('Loaded maintenance mode from full settings:', data.maintenanceMode);
          return;
        }
      }

      // If full settings endpoint fails, try the public state endpoint
      console.log('Full settings endpoint failed, trying public state endpoint...');
      response = await fetch(
        'http://localhost:8000/api/v1/system/settings/state',
        {
          headers: getAuthHeaders(),
        }
      );

      if (response.ok) {
        const data = await response.json();
        console.log('State endpoint response:', data);
        if (data.maintenanceMode !== undefined) {
          setMaintenanceMode(!!data.maintenanceMode); // Ensure boolean
          console.log('Loaded maintenance mode from state endpoint:', data.maintenanceMode);
          return;
        }
      }

      // Try the maintenance-mode endpoint as last resort
      console.log('State endpoint failed, trying maintenance-mode endpoint...');
      response = await fetch(
        'http://localhost:8000/api/v1/system/maintenance-mode',
        {
          headers: getAuthHeaders(),
        }
      );

      if (response.ok) {
        const data = await response.json();
        console.log('Maintenance-mode endpoint response:', data);
        if (data.maintenanceMode !== undefined) {
          setMaintenanceMode(!!data.maintenanceMode); // Ensure boolean
          console.log('Loaded maintenance mode from maintenance-mode endpoint:', data.maintenanceMode);
        }
      } else {
        console.error('All endpoints failed. Status:', response.status);
        const errorText = await response.text();
        console.error('Error response:', errorText);
      }
    } catch (err) {
      console.error('Error loading system settings:', err);
      // Don't show error for this, just use defaults
    }
  };

  useEffect(() => {
    loadNotificationEmails();
    loadSystemSettings();
  }, []);

  const handleEmailChange = (index, field, value) => {
    setEmails((prev) => {
      const next = [...prev];
      next[index] = {
        ...next[index],
        [field]: field === 'email' ? value : value,
      };
      return next;
    });
  };

  const handleMaintenanceModeToggle = async (checked) => {
    setMaintenanceMode(checked);
    try {
      const response = await fetch(
        'http://localhost:8000/api/v1/system/settings',
        {
          method: 'PUT',
          headers: getAuthHeaders(),
          body: JSON.stringify({
            maintenanceMode: checked,
          }),
        }
      );

      if (!response.ok) {
        // Revert on error
        setMaintenanceMode(!checked);
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || 'Failed to update maintenance mode');
      }
    } catch (err) {
      console.error('Error updating maintenance mode:', err);
      setError(err.message || 'Failed to update maintenance mode');
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');

    try {
      const payload = {
        emails: emails
          .filter((e) => e.email && e.email.trim().length > 0)
          .map((e) => ({
            email: e.email.trim(),
            enabled: !!e.enabled,
          })),
      };

      const response = await fetch(
        'http://localhost:8000/api/v1/system-config/notification-admin-emails',
        {
          method: 'PUT',
          headers: getAuthHeaders(),
          body: JSON.stringify(payload),
        }
      );

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || 'Failed to save settings');
      }

      setSuccess('Notification admin emails updated successfully.');
    } catch (err) {
      console.error('Error saving notification emails:', err);
      setError(err.message || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="dashboard-main">
      <div className="dashboard-header">
        <h1>Settings</h1>
        <p style={{ marginTop: '0.5rem', color: '#555' }}>
          Configure system admin notification emails (max 3).
        </p>
      </div>

      <div className="dashboard-content">
        {/* System Settings Section */}
        <div className="dashboard-section">
          <div className="section-header">
            <h2>System Settings</h2>
          </div>
          {error && (
            <div className="error-message" style={{ marginBottom: '1rem' }}>
              {error}
            </div>
          )}
          {success && (
            <div
              className="success-message"
              style={{
                marginBottom: '1rem',
                padding: '0.75rem 1rem',
                borderRadius: '4px',
                backgroundColor: '#e8f5e9',
                color: '#2e7d32',
              }}
            >
              {success}
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '1rem',
                backgroundColor: '#f8f9fa',
                borderRadius: '4px',
              }}
            >
              <div>
                <label style={{ fontWeight: 600, display: 'block', marginBottom: '0.25rem' }}>
                  Maintenance Mode
                </label>
                <p style={{ margin: 0, fontSize: '0.9rem', color: '#6c757d' }}>
                  When enabled, the system will be in maintenance mode and users will see a maintenance message.
                </p>
              </div>
              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  cursor: 'pointer',
                }}
              >
                <input
                  type="checkbox"
                  checked={maintenanceMode}
                  onChange={(e) => handleMaintenanceModeToggle(e.target.checked)}
                  style={{
                    width: '20px',
                    height: '20px',
                    cursor: 'pointer',
                  }}
                />
                <span style={{ fontWeight: 500 }}>
                  {maintenanceMode ? 'Enabled' : 'Disabled'}
                </span>
              </label>
            </div>
          </div>
        </div>

        {/* Notification Emails Section */}
        <div className="dashboard-section">
          <div className="section-header">
            <h2>Notification Admin Emails</h2>
          </div>
          <p style={{ marginBottom: '1rem', color: '#555' }}>
            Configure system admin notification emails (max 3).
          </p>

          <form onSubmit={handleSave}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {emails.map((item, index) => (
                <div
                  key={index}
                  style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '0.75rem',
                    alignItems: 'center',
                  }}
                >
                  <label style={{ minWidth: '80px' }}>Email {index + 1}</label>
                  <input
                    type="email"
                    value={item.email}
                    onChange={(e) => handleEmailChange(index, 'email', e.target.value)}
                    placeholder="admin@example.com"
                    style={{
                      flex: '1 1 250px',
                      padding: '0.5rem 0.75rem',
                      borderRadius: '4px',
                      border: '1px solid #ccc',
                    }}
                  />
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    <input
                      type="checkbox"
                      checked={!!item.enabled}
                      onChange={(e) =>
                        handleEmailChange(index, 'enabled', e.target.checked)
                      }
                    />
                    <span>Receive notifications</span>
                  </label>
                </div>
              ))}
            </div>

            <div style={{ marginTop: '1.5rem' }}>
              <button
                type="submit"
                disabled={saving}
                style={{
                  padding: '0.5rem 1.5rem',
                  backgroundColor: '#4CAF50',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: saving ? 'default' : 'pointer',
                  opacity: saving ? 0.7 : 1,
                }}
              >
                {saving ? 'Saving...' : 'Save Settings'}
              </button>
            </div>
          </form>

          {loading && (
            <p style={{ marginTop: '1rem', color: '#555' }}>
              Loading current settings...
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default Settings;

