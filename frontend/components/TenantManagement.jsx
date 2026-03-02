import React, { useState, useEffect } from 'react';
import './Dashboard.css';

const TenantManagement = () => {
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [editing, setEditing] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    category: 'HI',
    domain: '',
    is_active: true,
    admin_username: '',
    admin_password: '',
    must_change_password: false,
  });
  const [logoFile, setLogoFile] = useState(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [total, setTotal] = useState(0);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return {
      'Authorization': `Bearer ${token}`,
    };
  };

  useEffect(() => {
    loadTenants();
  }, [page, pageSize]);

  const loadTenants = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(
        `http://localhost:8000/api/v1/tenants?page=${page}&page_size=${pageSize}`,
        {
          headers: getAuthHeaders(),
        }
      );

      if (!response.ok) {
        throw new Error('Failed to load tenants');
      }

      const data = await response.json();
      setTenants(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error('Error loading tenants:', err);
      setError(err.message || 'Failed to load tenants');
    } finally {
      setLoading(false);
    }
  };

  const startEdit = (tenant) => {
    setEditing(tenant);
    setFormData({
      name: tenant.name || '',
      category: tenant.category || 'HI',
      domain: tenant.domain || '',
      is_active: tenant.is_active !== undefined ? tenant.is_active : true,
      admin_username: tenant.admin_username || '',
      admin_password: '',
      must_change_password: false,
    });
    setLogoFile(null);
    setShowModal(true);
    setError('');
    setSuccess('');
  };

  const closeModal = () => {
    setShowModal(false);
    setEditing(null);
    setFormData({
      name: '',
      category: 'HI',
      domain: '',
      is_active: true,
      admin_username: '',
      admin_password: '',
      must_change_password: false,
    });
    setLogoFile(null);
    setError('');
    setSuccess('');
  };

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      // Validate file type
      const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/svg+xml', 'image/webp'];
      if (!validTypes.includes(file.type)) {
        setError('Invalid file type. Please upload an image (JPEG, PNG, SVG, or WebP)');
        return;
      }
      // Validate file size (5MB max)
      if (file.size > 5 * 1024 * 1024) {
        setError('File size exceeds 5MB limit');
        return;
      }
      setLogoFile(file);
      setError('');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');

    try {
      // Create FormData for multipart/form-data
      const formDataToSend = new FormData();

      // Only include fields that are not empty/null
      if (formData.name && formData.name.trim()) {
        formDataToSend.append('name', formData.name.trim());
      }
      if (formData.category) {
        formDataToSend.append('category', formData.category);
      }
      if (formData.domain && formData.domain.trim()) {
        formDataToSend.append('domain', formData.domain.trim());
      }
      if (formData.is_active !== undefined && formData.is_active !== null) {
        formDataToSend.append('is_active', formData.is_active.toString());
      }
      if (formData.admin_username && formData.admin_username.trim()) {
        formDataToSend.append('admin_username', formData.admin_username.trim());
      }
      if (formData.admin_password && formData.admin_password.trim()) {
        formDataToSend.append('admin_password', formData.admin_password.trim());
      }
      if (formData.must_change_password !== undefined && formData.must_change_password !== null) {
        formDataToSend.append('must_change_password', formData.must_change_password.toString());
      }
      if (logoFile) {
        formDataToSend.append('logo', logoFile);
      }

      const response = await fetch(
        `http://localhost:8000/api/v1/tenants/${editing.id}`,
        {
          method: 'PUT',
          headers: {
            ...getAuthHeaders(),
            // Don't set Content-Type - let browser set it with boundary for multipart/form-data
          },
          body: formDataToSend,
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || errorData.message || 'Failed to update tenant');
      }

      const updatedTenant = await response.json();
      setSuccess('Tenant updated successfully!');
      
      // Reload tenants after a short delay
      setTimeout(() => {
        closeModal();
        loadTenants();
      }, 1500);
    } catch (err) {
      console.error('Error updating tenant:', err);
      setError(err.message || 'Failed to update tenant');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (tenant) => {
    if (!window.confirm(`Are you sure you want to delete tenant "${tenant.name}"?`)) {
      return;
    }

    try {
      const response = await fetch(
        `http://localhost:8000/api/v1/tenants/${tenant.id}`,
        {
          method: 'DELETE',
          headers: getAuthHeaders(),
        }
      );

      if (!response.ok) {
        throw new Error('Failed to delete tenant');
      }

      await loadTenants();
      setSuccess('Tenant deleted successfully!');
    } catch (err) {
      console.error('Error deleting tenant:', err);
      setError(err.message || 'Failed to delete tenant');
    }
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="dashboard-main">
      <div className="dashboard-header">
        <h1>Tenant Management</h1>
        <p style={{ marginTop: '0.5rem', color: '#555' }}>
          Manage system tenants and their configurations.
        </p>
      </div>

      {error && !showModal && (
        <div className="error-message" style={{ marginBottom: '1rem' }}>
          {error}
        </div>
      )}
      {success && !showModal && (
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

      <div className="dashboard-content">
        {loading ? (
          <div>Loading tenants...</div>
        ) : (
          <>
            <div className="table-container-wrapper">
              <div className="table-container">
                <table className="lecturer-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Name</th>
                      <th>Category</th>
                      <th>Domain</th>
                      <th>Status</th>
                      <th>Logo</th>
                      <th>Admin Username</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tenants.length === 0 ? (
                      <tr>
                        <td colSpan="8" className="no-data">
                          No tenants found
                        </td>
                      </tr>
                    ) : (
                      tenants.map((tenant) => (
                        <tr key={tenant.id}>
                          <td>{tenant.id}</td>
                          <td>{tenant.name}</td>
                          <td>{tenant.category}</td>
                          <td>{tenant.domain || 'N/A'}</td>
                          <td>
                            <span
                              style={{
                                padding: '0.25rem 0.5rem',
                                borderRadius: '4px',
                                backgroundColor: tenant.is_active ? '#e8f5e9' : '#ffebee',
                                color: tenant.is_active ? '#2e7d32' : '#c62828',
                                fontSize: '0.875rem',
                              }}
                            >
                              {tenant.is_active ? 'Active' : 'Inactive'}
                            </span>
                          </td>
                          <td>
                            {tenant.logo_url ? (
                              <img
                                src={`http://localhost:8000${tenant.logo_url}`}
                                alt="Tenant Logo"
                                style={{
                                  width: '40px',
                                  height: '40px',
                                  objectFit: 'cover',
                                  borderRadius: '4px',
                                }}
                              />
                            ) : (
                              'No logo'
                            )}
                          </td>
                          <td>{tenant.admin_username || 'N/A'}</td>
                          <td className="actions-cell">
                            <button
                              className="btn-edit"
                              onClick={() => startEdit(tenant)}
                            >
                              Edit
                            </button>
                            <button
                              className="btn-delete"
                              onClick={() => handleDelete(tenant)}
                            >
                              Delete
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Pagination */}
            <div className="pagination" style={{ marginTop: '1rem' }}>
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="btn-pagination"
              >
                Previous
              </button>
              <span className="page-info">
                Page {page} of {totalPages} ({total} total)
              </span>
              <button
                onClick={() => setPage(page + 1)}
                disabled={page >= totalPages}
                className="btn-pagination"
              >
                Next
              </button>
            </div>
          </>
        )}
      </div>

      {/* Edit Modal */}
      {showModal && (
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
          }}
          onClick={closeModal}
        >
          <div
            style={{
              backgroundColor: 'white',
              padding: '2rem',
              borderRadius: '8px',
              maxWidth: '600px',
              width: '90%',
              maxHeight: '90vh',
              overflow: 'auto',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2 style={{ marginTop: 0 }}>Edit Tenant</h2>

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

            <form onSubmit={handleSubmit}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>
                    Name *
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => handleChange('name', e.target.value)}
                    required
                    style={{
                      width: '100%',
                      padding: '0.5rem',
                      borderRadius: '4px',
                      border: '1px solid #ccc',
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>
                    Category *
                  </label>
                  <select
                    value={formData.category}
                    onChange={(e) => handleChange('category', e.target.value)}
                    required
                    style={{
                      width: '100%',
                      padding: '0.5rem',
                      borderRadius: '4px',
                      border: '1px solid #ccc',
                    }}
                  >
                    <option value="HI">Higher Institution (HI)</option>
                    <option value="SI">Secondary Institution (SI)</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>
                    Domain
                  </label>
                  <input
                    type="text"
                    value={formData.domain}
                    onChange={(e) => handleChange('domain', e.target.value)}
                    placeholder="tenant-domain"
                    style={{
                      width: '100%',
                      padding: '0.5rem',
                      borderRadius: '4px',
                      border: '1px solid #ccc',
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                      type="checkbox"
                      checked={formData.is_active}
                      onChange={(e) => handleChange('is_active', e.target.checked)}
                    />
                    <span>Active</span>
                  </label>
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>
                    Admin Username
                  </label>
                  <input
                    type="text"
                    value={formData.admin_username}
                    onChange={(e) => handleChange('admin_username', e.target.value)}
                    placeholder="Leave empty to keep current"
                    style={{
                      width: '100%',
                      padding: '0.5rem',
                      borderRadius: '4px',
                      border: '1px solid #ccc',
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>
                    Admin Password
                  </label>
                  <input
                    type="password"
                    value={formData.admin_password}
                    onChange={(e) => handleChange('admin_password', e.target.value)}
                    placeholder="Leave empty to keep current"
                    style={{
                      width: '100%',
                      padding: '0.5rem',
                      borderRadius: '4px',
                      border: '1px solid #ccc',
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                      type="checkbox"
                      checked={formData.must_change_password}
                      onChange={(e) => handleChange('must_change_password', e.target.checked)}
                    />
                    <span>Must Change Password</span>
                  </label>
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>
                    Logo
                  </label>
                  <input
                    type="file"
                    accept="image/jpeg,image/jpg,image/png,image/svg+xml,image/webp"
                    onChange={handleFileChange}
                    style={{
                      width: '100%',
                      padding: '0.5rem',
                      borderRadius: '4px',
                      border: '1px solid #ccc',
                    }}
                  />
                  {logoFile && (
                    <p style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: '#555' }}>
                      Selected: {logoFile.name}
                    </p>
                  )}
                </div>
              </div>

              <div
                style={{
                  display: 'flex',
                  gap: '1rem',
                  marginTop: '1.5rem',
                  justifyContent: 'flex-end',
                }}
              >
                <button
                  type="button"
                  onClick={closeModal}
                  style={{
                    padding: '0.5rem 1.5rem',
                    backgroundColor: '#6c757d',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  style={{
                    padding: '0.5rem 1.5rem',
                    backgroundColor: '#007bff',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: saving ? 'default' : 'pointer',
                    opacity: saving ? 0.7 : 1,
                  }}
                >
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default TenantManagement;
