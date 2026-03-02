import React, { useState, useEffect } from 'react';
import './Navbar.css';

const Navbar = ({ user, onLogout }) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
      if (window.innerWidth >= 768) {
        setIsMenuOpen(false);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const toggleMenu = () => {
    setIsMenuOpen(!isMenuOpen);
  };

  const closeMenu = () => {
    setIsMenuOpen(false);
  };

  const menuItems = [
    { label: 'Dashboard', path: '/dashboard', roles: ['admin', 'staff', 'teacher', 'student', 'parent'] },
    { label: 'Financial Overview', path: '/riggstech/admin/financial-overview', roles: ['admin', 'staff', 'super_admin'] },
    { label: 'Subscription Services', path: '/riggstech/admin/subscription-services', roles: ['admin', 'super_admin'] },
    { label: 'Students', path: '/students', roles: ['admin', 'staff', 'teacher'] },
    { label: 'Teachers', path: '/teachers', roles: ['admin', 'staff'] },
    { label: 'Courses', path: '/courses', roles: ['admin', 'staff', 'teacher'] },
    { label: 'Schedules', path: '/schedules', roles: ['admin', 'staff', 'teacher', 'student'] },
    { label: 'Assignments', path: '/assignments', roles: ['admin', 'staff', 'teacher', 'student'] },
    { label: 'Announcements', path: '/announcements', roles: ['admin', 'staff', 'teacher', 'student', 'parent'] },
    { label: 'Activities', path: '/activities', roles: ['admin', 'staff'] },
    { label: 'Users', path: '/users', roles: ['admin', 'super_admin'] },
    { label: 'Classes', path: '/classes', roles: ['admin', 'staff'] },
    { label: 'Enrollments', path: '/enrollments', roles: ['admin', 'staff'] },
    { label: 'Complaints', path: '/complaints', roles: ['admin', 'staff', 'student', 'parent'] },
    { label: 'System Admin', path: '/system-admin', roles: ['super_admin', 'system_admin', 'system_super_admin'] },
    { label: 'Settings', path: '/settings', roles: ['admin', 'staff'] },
  ];

  const filteredMenuItems = menuItems.filter(item => 
    user && item.roles.some(role => 
      user.role === role || 
      (role === 'admin' && user.role?.startsWith('system_')) ||
      (role === 'super_admin' && (user.role === 'super_admin' || user.role?.startsWith('system_')))
    )
  );

  return (
    <nav className="navbar">
      <div className="navbar-container">
        {/* Logo/Brand */}
        <div className="navbar-brand">
          <a href="/" className="brand-link">
            <span className="brand-text">MTSMS</span>
          </a>
        </div>

        {/* Desktop Menu */}
        <ul className={`navbar-menu ${isMenuOpen ? 'active' : ''}`}>
          {filteredMenuItems.map((item, index) => (
            <li key={index} className="navbar-item">
              <a href={item.path} className="navbar-link" onClick={closeMenu}>
                {item.label}
              </a>
            </li>
          ))}
        </ul>

        {/* User Menu */}
        <div className="navbar-user">
          {user && (
            <div className="user-info">
              <span className="user-name">{user.username || user.email}</span>
              <span className="user-role">{user.role}</span>
            </div>
          )}
          {onLogout && (
            <button className="logout-btn" onClick={onLogout}>
              Logout
            </button>
          )}
        </div>

        {/* Mobile Menu Toggle */}
        <button 
          className={`navbar-toggle ${isMenuOpen ? 'active' : ''}`}
          onClick={toggleMenu}
          aria-label="Toggle menu"
        >
          <span className="hamburger-line"></span>
          <span className="hamburger-line"></span>
          <span className="hamburger-line"></span>
        </button>
      </div>
    </nav>
  );
};

export default Navbar;
