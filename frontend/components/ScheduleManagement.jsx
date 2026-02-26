import React, { useEffect, useState } from 'react';
import './ScheduleManagement.css';

const ScheduleManagement = () => {
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [editing, setEditing] = useState(null); // null = creating
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    course_name: '',
    instructor: '',
    day: 'Monday',
    start_time: '08:00',
    end_time: '09:00',
    room: '',
    capacity: '',
    description: '',
  });
  const [saving, setSaving] = useState(false);

  // Time slots for schedule creation
  const timeSlots = [
    '08:00', '08:30', '09:00', '09:30', '10:00', '10:30',
    '11:00', '11:30', '12:00', '12:30', '13:00', '13:30',
    '14:00', '14:30', '15:00', '15:30', '16:00', '16:30',
    '17:00', '17:30', '18:00'
  ];

  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

  // Get user from localStorage or context
  const getUser = () => {
    try {
      const userData = localStorage.getItem('user');
      return userData ? JSON.parse(userData) : null;
    } catch {
      return null;
    }
  };

  const user = getUser();
  const canManage =
    user &&
    user.role &&
    (user.role.toLowerCase().includes('admin') ||
      user.role.toLowerCase().includes('staff') ||
      user.role.toLowerCase().includes('secretary'));

  useEffect(() => {
    loadSchedules();
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

  const loadSchedules = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(
        'http://localhost:8000/api/v1/schedules?page=1&page_size=50',
        {
          headers: getAuthHeaders()
        }
      );

      if (!response.ok) {
        throw new Error('Failed to load schedules');
      }

      const data = await response.json();
      const items = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : [];
      setSchedules(items);
    } catch (err) {
      console.error('Error loading schedules:', err);
      setError(err.message || 'Failed to load schedules');
    } finally {
      setLoading(false);
    }
  };

  const startCreate = () => {
    setEditing(null);
    setFormData({
      course_name: '',
      instructor: '',
      day: 'Monday',
      start_time: '08:00',
      end_time: '09:00',
      room: '',
      capacity: '',
      description: '',
    });
    setShowModal(true);
  };

  const startEdit = (schedule) => {
    setEditing(schedule);
    setFormData({
      course_name: schedule.course_name || '',
      instructor: schedule.instructor || '',
      day: schedule.day || 'Monday',
      start_time: schedule.start_time || '08:00',
      end_time: schedule.end_time || '09:00',
      room: schedule.room || '',
      capacity: schedule.capacity || '',
      description: schedule.description || '',
    });
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditing(null);
    setFormData({
      course_name: '',
      instructor: '',
      day: 'Monday',
      start_time: '08:00',
      end_time: '09:00',
      room: '',
      capacity: '',
      description: '',
    });
    setError('');
  };

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.course_name.trim() || !formData.instructor.trim()) {
      setError('Course name and instructor are required');
      return;
    }

    setSaving(true);
    setError('');
    try {
      const url = editing
        ? `http://localhost:8000/api/v1/schedules/${editing.id}`
        : 'http://localhost:8000/api/v1/schedules';
      
      const method = editing ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: getAuthHeaders(),
        body: JSON.stringify(formData)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || errorData.message || 'Failed to save schedule');
      }

      setFormData({
        course_name: '',
        instructor: '',
        day: 'Monday',
        start_time: '08:00',
        end_time: '09:00',
        room: '',
        capacity: '',
        description: '',
      });
      setEditing(null);
      setShowModal(false);
      await loadSchedules();
    } catch (err) {
      console.error('Error saving schedule:', err);
      setError(err.message || 'Failed to save schedule');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (schedule) => {
    if (!window.confirm('Are you sure you want to delete this schedule?')) return;

    try {
      const response = await fetch(
        `http://localhost:8000/api/v1/schedules/${schedule.id}`,
        {
          method: 'DELETE',
          headers: getAuthHeaders()
        }
      );

      if (!response.ok) {
        throw new Error('Failed to delete schedule');
      }

      await loadSchedules();
    } catch (err) {
      console.error('Error deleting schedule:', err);
      setError(err.message || 'Failed to delete schedule');
    }
  };

  return (
    <div className="announcement-main">
      <div className="announcement-header">
        <h1>Schedule Management</h1>
        {canManage && (
          <button
            type="button"
            className="primary-btn"
            onClick={startCreate}
            style={{ marginLeft: 'auto' }}
          >
            Add Schedule
          </button>
        )}
      </div>

      {error && !showModal && (
        <div className="error-message" style={{ marginBottom: '1rem' }}>
          {error}
        </div>
      )}

      {/* Modal for Create/Edit Schedule */}
      {showModal && canManage && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '1rem'
          }}
          onClick={closeModal}
        >
          <div
            style={{
              backgroundColor: 'white',
              borderRadius: '8px',
              padding: '2rem',
              maxWidth: '700px',
              width: '100%',
              maxHeight: '90vh',
              overflowY: 'auto',
              boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
              position: 'relative'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close Button */}
            <button
              type="button"
              onClick={closeModal}
              style={{
                position: 'absolute',
                top: '1rem',
                right: '1rem',
                background: 'none',
                border: 'none',
                fontSize: '1.5rem',
                cursor: 'pointer',
                color: '#6c757d',
                width: '32px',
                height: '32px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: '4px',
                transition: 'background-color 0.2s'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#f8f9fa';
                e.currentTarget.style.color = '#212529';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.color = '#6c757d';
              }}
            >
              ×
            </button>

            <h2 style={{ marginBottom: '1.5rem', color: '#212529', fontSize: '1.5rem' }}>
              {editing ? 'Edit Schedule' : 'Create Schedule'}
            </h2>

            {error && (
              <div className="error-message" style={{ marginBottom: '1rem' }}>
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="form-group" style={{ marginBottom: '1.25rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: '#495057' }}>
                  Course Name <span style={{ color: '#dc3545' }}>*</span>
                </label>
                <input
                  type="text"
                  value={formData.course_name}
                  onChange={(e) => handleChange('course_name', e.target.value)}
                  placeholder="Enter course name"
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    fontSize: '1rem',
                    boxSizing: 'border-box'
                  }}
                  required
                />
              </div>

              <div className="form-group" style={{ marginBottom: '1.25rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: '#495057' }}>
                  Instructor <span style={{ color: '#dc3545' }}>*</span>
                </label>
                <input
                  type="text"
                  value={formData.instructor}
                  onChange={(e) => handleChange('instructor', e.target.value)}
                  placeholder="Enter instructor name"
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    fontSize: '1rem',
                    boxSizing: 'border-box'
                  }}
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', marginBottom: '1.25rem' }}>
                <div className="form-group">
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: '#495057' }}>
                    Day <span style={{ color: '#dc3545' }}>*</span>
                  </label>
                  <select
                    value={formData.day}
                    onChange={(e) => handleChange('day', e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      fontSize: '1rem',
                      boxSizing: 'border-box',
                      backgroundColor: 'white'
                    }}
                    required
                  >
                    {days.map((day) => (
                      <option key={day} value={day}>{day}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: '#495057' }}>
                    Start Time <span style={{ color: '#dc3545' }}>*</span>
                  </label>
                  <select
                    value={formData.start_time}
                    onChange={(e) => handleChange('start_time', e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      fontSize: '1rem',
                      boxSizing: 'border-box',
                      backgroundColor: 'white'
                    }}
                    required
                  >
                    {timeSlots.map((time) => (
                      <option key={time} value={time}>{time}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: '#495057' }}>
                    End Time <span style={{ color: '#dc3545' }}>*</span>
                  </label>
                  <select
                    value={formData.end_time}
                    onChange={(e) => handleChange('end_time', e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      fontSize: '1rem',
                      boxSizing: 'border-box',
                      backgroundColor: 'white'
                    }}
                    required
                  >
                    {timeSlots.map((time) => (
                      <option key={time} value={time}>{time}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.25rem' }}>
                <div className="form-group">
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: '#495057' }}>
                    Room
                  </label>
                  <input
                    type="text"
                    value={formData.room}
                    onChange={(e) => handleChange('room', e.target.value)}
                    placeholder="Enter room number"
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      fontSize: '1rem',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>

                <div className="form-group">
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: '#495057' }}>
                    Capacity
                  </label>
                  <input
                    type="number"
                    value={formData.capacity}
                    onChange={(e) => handleChange('capacity', e.target.value)}
                    placeholder="Enter capacity"
                    min="1"
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      fontSize: '1rem',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>
              </div>

              <div className="form-group" style={{ marginBottom: '1.5rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: '#495057' }}>
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => handleChange('description', e.target.value)}
                  placeholder="Enter schedule description (optional)"
                  rows={4}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    fontSize: '1rem',
                    fontFamily: 'inherit',
                    resize: 'vertical',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginTop: '2rem' }}>
                <button
                  type="button"
                  onClick={closeModal}
                  style={{
                    padding: '0.75rem 1.5rem',
                    backgroundColor: '#6c757d',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '1rem',
                    fontWeight: '500',
                    transition: 'background-color 0.2s'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#5a6268'}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#6c757d'}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  style={{
                    padding: '0.75rem 1.5rem',
                    backgroundColor: saving ? '#6c757d' : '#007bff',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: saving ? 'not-allowed' : 'pointer',
                    fontSize: '1rem',
                    fontWeight: '500',
                    transition: 'background-color 0.2s'
                  }}
                  onMouseEnter={(e) => {
                    if (!saving) e.currentTarget.style.backgroundColor = '#0056b3';
                  }}
                  onMouseLeave={(e) => {
                    if (!saving) e.currentTarget.style.backgroundColor = '#007bff';
                  }}
                >
                  {saving ? 'Saving...' : editing ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="announcement-content" style={{ marginTop: '2rem' }}>
        {loading ? (
          <p>Loading schedules...</p>
        ) : schedules.length === 0 ? (
          <p>No schedules available.</p>
        ) : (
          <div style={{ overflowX: 'visible' }}>
            <table style={{
              width: '100%',
              borderCollapse: 'collapse',
              backgroundColor: 'white',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
              borderRadius: '8px',
              overflow: 'hidden'
            }}>
              <thead>
                <tr style={{ backgroundColor: '#f8f9fa', borderBottom: '2px solid #dee2e6' }}>
                  <th style={{
                    padding: '1rem',
                    textAlign: 'left',
                    fontWeight: '600',
                    color: '#495057',
                    fontSize: '0.875rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px'
                  }}>Course</th>
                  <th style={{
                    padding: '1rem',
                    textAlign: 'left',
                    fontWeight: '600',
                    color: '#495057',
                    fontSize: '0.875rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px'
                  }}>Instructor</th>
                  <th style={{
                    padding: '1rem',
                    textAlign: 'center',
                    fontWeight: '600',
                    color: '#495057',
                    fontSize: '0.875rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    width: '100px'
                  }}>Day</th>
                  <th style={{
                    padding: '1rem',
                    textAlign: 'center',
                    fontWeight: '600',
                    color: '#495057',
                    fontSize: '0.875rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    width: '120px'
                  }}>Time</th>
                  <th style={{
                    padding: '1rem',
                    textAlign: 'left',
                    fontWeight: '600',
                    color: '#495057',
                    fontSize: '0.875rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    width: '100px'
                  }}>Room</th>
                  <th style={{
                    padding: '1rem',
                    textAlign: 'center',
                    fontWeight: '600',
                    color: '#495057',
                    fontSize: '0.875rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    width: '80px'
                  }}>Capacity</th>
                  {canManage && (
                    <th style={{
                      padding: '1rem',
                      textAlign: 'center',
                      fontWeight: '600',
                      color: '#495057',
                      fontSize: '0.875rem',
                      textTransform: 'uppercase',
                      letterSpacing: '0.5px',
                      width: '150px'
                    }}>Actions</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {schedules.map((schedule, index) => (
                  <tr
                    key={schedule.id}
                    style={{
                      borderBottom: index < schedules.length - 1 ? '1px solid #dee2e6' : 'none',
                      transition: 'background-color 0.2s'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f8f9fa'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'white'}
                  >
                    <td style={{
                      padding: '1rem',
                      fontWeight: '600',
                      color: '#212529',
                      fontSize: '0.95rem'
                    }}>{schedule.course_name}</td>
                    <td style={{
                      padding: '1rem',
                      color: '#495057',
                      fontSize: '0.9rem'
                    }}>{schedule.instructor}</td>
                    <td style={{
                      padding: '1rem',
                      textAlign: 'center',
                      color: '#495057',
                      fontSize: '0.9rem'
                    }}>{schedule.day}</td>
                    <td style={{
                      padding: '1rem',
                      textAlign: 'center',
                      color: '#495057',
                      fontSize: '0.9rem'
                    }}>
                      {schedule.start_time} - {schedule.end_time}
                    </td>
                    <td style={{
                      padding: '1rem',
                      color: '#495057',
                      fontSize: '0.9rem'
                    }}>{schedule.room || 'N/A'}</td>
                    <td style={{
                      padding: '1rem',
                      textAlign: 'center',
                      color: '#495057',
                      fontSize: '0.9rem'
                    }}>{schedule.capacity || 'N/A'}</td>
                    {canManage && (
                      <td style={{ padding: '1rem', textAlign: 'center' }}>
                        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
                          <button
                            type="button"
                            onClick={() => startEdit(schedule)}
                            style={{
                              padding: '0.375rem 0.75rem',
                              backgroundColor: '#007bff',
                              color: 'white',
                              border: 'none',
                              borderRadius: '4px',
                              cursor: 'pointer',
                              fontSize: '0.875rem',
                              fontWeight: '500',
                              transition: 'background-color 0.2s'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#0056b3'}
                            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#007bff'}
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDelete(schedule)}
                            style={{
                              padding: '0.375rem 0.75rem',
                              backgroundColor: '#dc3545',
                              color: 'white',
                              border: 'none',
                              borderRadius: '4px',
                              cursor: 'pointer',
                              fontSize: '0.875rem',
                              fontWeight: '500',
                              transition: 'background-color 0.2s'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#c82333'}
                            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#dc3545'}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default ScheduleManagement;
