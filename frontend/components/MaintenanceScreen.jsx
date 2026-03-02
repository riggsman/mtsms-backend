import React from 'react';
import './App.css';

const MaintenanceScreen = () => {
  return (
    <div className="app-content" style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      textAlign: 'center',
      padding: '2rem',
      backgroundColor: '#f5f5f5',
    }}>
      <div style={{
        maxWidth: '600px',
        padding: '3rem',
        backgroundColor: '#fff',
        borderRadius: '8px',
        boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
      }}>
        <div style={{
          fontSize: '4rem',
          marginBottom: '1rem',
        }}>
          🔧
        </div>
        <h1 style={{
          color: '#2e7d32',
          fontSize: '2.5rem',
          marginBottom: '1rem',
          fontWeight: 700,
        }}>
          System Under Maintenance
        </h1>
        <p style={{
          color: '#666',
          fontSize: '1.1rem',
          marginBottom: '2rem',
          lineHeight: '1.6',
        }}>
          We're currently performing scheduled maintenance to improve your experience.
          Please check back shortly.
        </p>
        <p style={{
          color: '#999',
          fontSize: '0.9rem',
        }}>
          Thank you for your patience.
        </p>
      </div>
    </div>
  );
};

export default MaintenanceScreen;
