import React, { useState, useEffect } from 'react';
import MainLayout from './MainLayout';
import './App.css';

const App = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is logged in
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

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('tenantName');
    setUser(null);
    window.location.href = '/login';
  };

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <MainLayout user={user} onLogout={handleLogout}>
      {/* Your page content goes here */}
      <div className="app-content">
        <h1>Welcome to MTSMS</h1>
        <p>Multi-Tenant School Management System</p>
      </div>
    </MainLayout>
  );
};

export default App;
