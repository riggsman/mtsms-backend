import React from 'react';
import Navbar from './Navbar';
import './MainLayout.css';

const MainLayout = ({ children, user, onLogout }) => {
  return (
    <div className="main-layout">
      <Navbar user={user} onLogout={onLogout} />
      <main className="main-content">
        <div className="content-wrapper">
          {children}
        </div>
      </main>
      <footer className="main-footer">
        <div className="footer-content">
          <p>&copy; {new Date().getFullYear()} MTSMS - Multi-Tenant School Management System</p>
          <p className="footer-links">
            <a href="/about">About</a>
            <span> | </span>
            <a href="/contact">Contact</a>
            <span> | </span>
            <a href="/privacy">Privacy Policy</a>
          </p>
        </div>
      </footer>
    </div>
  );
};

export default MainLayout;
