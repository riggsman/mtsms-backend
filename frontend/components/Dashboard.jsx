import React, { useEffect, useState } from 'react';
import './Dashboard.css';

const Dashboard = () => {
  const [recentActivities, setRecentActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadRecentActivities();
  }, []);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    const tenantName = localStorage.getItem('tenantName') || 'riggstech';
    return {
      'Authorization': `Bearer ${token}`,
      'X-Tenant-Name': tenantName,
      'Content-Type': 'application/json'
    };
  };

  const loadRecentActivities = async () => {
    setLoading(true);
    setError('');
    try {
      // Fetch only 3 most recent activities
      const response = await fetch(
        'http://localhost:8000/api/v1/activities?page=1&page_size=3',
        {
          headers: getAuthHeaders()
        }
      );

      if (!response.ok) {
        throw new Error('Failed to load recent activities');
      }

      const data = await response.json();
      const items = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : [];
      // Ensure we only show 3 items
      setRecentActivities(items.slice(0, 3));
    } catch (err) {
      console.error('Error loading recent activities:', err);
      setError(err.message || 'Failed to load recent activities');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return 'N/A';
    }
  };

  return (
    <div className="dashboard-main">
      <div className="dashboard-header">
        <h1>Dashboard Overview</h1>
      </div>

      {error && (
        <div className="error-message" style={{ marginBottom: '1rem' }}>
          {error}
        </div>
      )}

      <div className="dashboard-content">
        {/* Recent Activities Section */}
        <div className="dashboard-section">
          <div className="section-header">
            <h2>Recent Activities</h2>
            <a href="/activities" className="view-all-link">View All</a>
          </div>

          {loading ? (
            <div className="loading-state">
              <p>Loading recent activities...</p>
            </div>
          ) : recentActivities.length === 0 ? (
            <div className="empty-state">
              <p>No recent activities available.</p>
            </div>
          ) : (
            <div className="activities-list">
              {recentActivities.map((activity, index) => (
                <div
                  key={activity.id}
                  className="activity-item"
                  style={{
                    borderBottom: index < recentActivities.length - 1 ? '1px solid #dee2e6' : 'none'
                  }}
                >
                  <div className="activity-content">
                    <div className="activity-header">
                      <span className="activity-action">{activity.action}</span>
                      <span className="activity-type">{activity.entity_type}</span>
                    </div>
                    {activity.content && (
                      <p className="activity-details">{activity.content}</p>
                    )}
                    <div className="activity-footer">
                      <span className="activity-performer">
                        By: {activity.performed_by} ({activity.performer_role})
                      </span>
                      <span className="activity-date">
                        {formatDate(activity.created_at)}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Add more dashboard sections here */}
      </div>
    </div>
  );
};

export default Dashboard;
