import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './MainLayout';
import Dashboard from './Dashboard';
import LecturerManagement from './LecturerManagement';
import ScheduleManagement from './ScheduleManagement';
import Overview from './Overview';
import Settings from './Settings';
import FinancialOverview from './FinancialOverview';
import SubscriptionServices from './SubscriptionServices';
import MaintenanceScreen from './MaintenanceScreen';
import './App.css';

const App = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [maintenanceMode, setMaintenanceMode] = useState(null); // null = checking, true = maintenance, false = normal

  useEffect(() => {
    const token = localStorage.getItem('token');
    const userData = localStorage.getItem('user');

    if (token && userData) {
      try {
        setUser(JSON.parse(userData));
      } catch (e) {
        console.error('Error parsing user data:', e);
      }
    }

    setLoading(false);
  }, []);

  // Check maintenance mode status
  useEffect(() => {
    const checkMaintenanceMode = async () => {
      try {
        // Try public endpoint first (no auth required)
        const response = await fetch('http://localhost:8000/api/v1/system/maintenance-mode');
        
        if (response.ok) {
          const data = await response.json();
          // Convert to boolean: only true, 1, "true", "1" become true
          // false, 0, "false", "0", null, undefined all become false
          const rawValue = data.maintenanceMode;
          const isMaintenance = rawValue === true || 
                               rawValue === 1 || 
                               rawValue === "true" || 
                               rawValue === "1" ||
                               rawValue === "True";
          setMaintenanceMode(isMaintenance);
          console.log('Maintenance mode status:', isMaintenance, 'Raw value:', rawValue);
        } else {
          // If endpoint fails, default to false (no maintenance)
          setMaintenanceMode(false);
        }
      } catch (err) {
        console.error('Error checking maintenance mode:', err);
        // On error, default to false (no maintenance) to allow access
        setMaintenanceMode(false);
      }
    };

    checkMaintenanceMode();
    
    // Check maintenance mode every 30 seconds
    const interval = setInterval(checkMaintenanceMode, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');
    localStorage.removeItem('tenantName');
    setUser(null);
    window.location.href = '/login';
  };

  // Show loading while checking maintenance mode
  if (loading || maintenanceMode === null) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  // Show maintenance screen if maintenance mode is enabled
  if (maintenanceMode === true) {
    return <MaintenanceScreen />;
  }

  // Normal operation - show login or app
  return (
    <Router>
      <MainLayout user={user} onLogout={handleLogout}>
        <Routes>
          {/* Landing behaviour */}
          <Route
            path="/"
            element={user ? <Navigate to="/dashboard" replace /> : <Navigate to="/login" replace />}
          />

          {/* Core admin / overview routes */}
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/riggstech/admin/overview" element={<Overview />} />
          <Route path="/riggstech/admin/financial-overview" element={<FinancialOverview />} />
          <Route path="/riggstech/admin/subscription-services" element={<SubscriptionServices />} />
          <Route path="/riggstech/admin/lecturer-management" element={<LecturerManagement />} />
          <Route path="/schedules" element={<ScheduleManagement />} />
          <Route path="/settings" element={<Settings />} />

          {/* Simple placeholder login page for now */}
          <Route
            path="/login"
            element={
              <div className="app-content">
                <h1>EduSphere</h1>
                <h2>Transform Your School Management Experience</h2>
                <p>Please implement your login form here.</p>
              </div>
            }
          />

          {/* Fallback */}
          <Route path="*" element={<div>404 Not Found</div>} />
        </Routes>
      </MainLayout>
    </Router>
  );
};

export default App;
