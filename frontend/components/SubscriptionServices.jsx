import React, { useState, useEffect } from 'react';
import { api } from '../utils/api';
import './Dashboard.css';

const SubscriptionServices = () => {
  const [services, setServices] = useState([]);
  const [serviceConfigs, setServiceConfigs] = useState({}); // Cached state: { serviceId: { subscription_type: is_enabled } }
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [pageSize] = useState(10);
  const [total, setTotal] = useState(0);
  const [filterActive, setFilterActive] = useState(null);
  const [updating, setUpdating] = useState(false);

  // Using api utility instead of getAuthHeaders

  const fetchServices = async () => {
    setLoading(true);
    setError('');
    try {
      let url = `http://localhost:8000/api/v1/admin/subscription-services?page=${page}&page_size=${pageSize}`;
      if (filterActive !== null) {
        url += `&is_active=${filterActive}`;
      }

      const response = await api.get(url);

      if (!response.ok) {
        throw new Error('Failed to fetch subscription services');
      }

      const data = await response.json();
      setServices(data.items || []);
      setTotal(data.total || 0);
      setTotalPages(data.total_pages || 1);
    } catch (err) {
      console.error('Error fetching subscription services:', err);
      setError(err.message || 'Failed to load subscription services');
    } finally {
      setLoading(false);
    }
  };

  // Load cached state from localStorage on mount
  useEffect(() => {
    const cached = localStorage.getItem('serviceConfigs');
    if (cached) {
      try {
        setServiceConfigs(JSON.parse(cached));
      } catch (e) {
        console.error('Error parsing cached service configs:', e);
      }
    }
  }, []);

  useEffect(() => {
    fetchServices();
  }, [page, filterActive]);

  // Fetch and cache service configurations when services are loaded
  useEffect(() => {
    if (services.length > 0) {
      fetchServiceConfigurations();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [services.length]);

  const fetchServiceConfigurations = async () => {
    try {
      const response = await api.get('/api/v1/admin/service-configurations?page=1&page_size=1000');

      if (response.ok) {
        const data = await response.json();
        const configs = {};
        
        // Parse configurations and build state map
        (data.items || []).forEach((config) => {
          // Extract subscription_type from configuration_key
          if (config.configuration_key && config.configuration_key.startsWith('subscription_type_')) {
            const subscriptionType = config.configuration_key.replace('subscription_type_', '');
            let isEnabled = false;
            
            try {
              const value = JSON.parse(config.configuration_value || '{}');
              isEnabled = value.is_enabled || config.is_active || false;
            } catch {
              isEnabled = config.is_active || false;
            }
            
            // Find matching service by name
            services.forEach((service) => {
              if (service.name === config.service_name) {
                if (!configs[service.id]) {
                  configs[service.id] = {};
                }
                configs[service.id][subscriptionType] = isEnabled;
              }
            });
          }
        });
        
        // Merge with existing cached state (preserve any local changes)
        setServiceConfigs((prevConfigs) => {
          const mergedConfigs = {
            ...prevConfigs,
            ...configs,
          };
          localStorage.setItem('serviceConfigs', JSON.stringify(mergedConfigs));
          return mergedConfigs;
        });
      }
    } catch (err) {
      console.error('Error fetching service configurations:', err);
    }
  };

  const formatPrice = (price, currency) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
    }).format(price);
  };

  const formatBillingPeriod = (period) => {
    return period
      .split('-')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const getToggleState = (serviceId, subscriptionType) => {
    return serviceConfigs[serviceId]?.[subscriptionType] || false;
  };

  const handleToggleChange = async (serviceId, subscriptionType, isEnabled) => {
    // Optimistically update local state
    const newConfigs = {
      ...serviceConfigs,
      [serviceId]: {
        ...(serviceConfigs[serviceId] || {}),
        [subscriptionType]: isEnabled,
      },
    };
    setServiceConfigs(newConfigs);
    localStorage.setItem('serviceConfigs', JSON.stringify(newConfigs));

    setUpdating(true);
    try {
      const response = await api.put(
        '/api/v1/admin/service-configurations',
        {
          configurations: [
            {
              service_id: serviceId,
              subscription_type: subscriptionType,
              is_enabled: isEnabled,
            },
          ],
        }
      );

      if (!response.ok) {
        // Revert on error
        setServiceConfigs(serviceConfigs);
        localStorage.setItem('serviceConfigs', JSON.stringify(serviceConfigs));
        throw new Error('Failed to update service configuration');
      }

      // Refresh configurations from server to ensure sync
      await fetchServiceConfigurations();
    } catch (err) {
      console.error('Error updating service configuration:', err);
      setError(err.message || 'Failed to update configuration');
      // Revert on error
      setServiceConfigs(serviceConfigs);
      localStorage.setItem('serviceConfigs', JSON.stringify(serviceConfigs));
    } finally {
      setUpdating(false);
    }
  };

  const renderFeatures = (features) => {
    if (!features || typeof features !== 'object') {
      return <span style={{ color: '#999', fontStyle: 'italic' }}>No features specified</span>;
    }

    if (Array.isArray(features)) {
      return (
        <ul style={{ margin: 0, paddingLeft: '1.5rem' }}>
          {features.map((feature, idx) => (
            <li key={idx}>{typeof feature === 'string' ? feature : JSON.stringify(feature)}</li>
          ))}
        </ul>
      );
    }

    return (
      <ul style={{ margin: 0, paddingLeft: '1.5rem' }}>
        {Object.entries(features).map(([key, value]) => (
          <li key={key}>
            <strong>{key}:</strong> {typeof value === 'object' ? JSON.stringify(value) : String(value)}
          </li>
        ))}
      </ul>
    );
  };

  return (
    <div className="dashboard-main">
      <div className="dashboard-header">
        <h1>Subscription Services</h1>
        <p style={{ marginTop: '0.5rem', color: '#555' }}>
          Manage subscription services available to tenants.
        </p>
      </div>

      <div className="dashboard-content">
        {/* Filters */}
        <div className="dashboard-section" style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <label style={{ fontWeight: 600 }}>Filter by Status:</label>
            <select
              value={filterActive === null ? 'all' : filterActive ? 'active' : 'inactive'}
              onChange={(e) => {
                const value = e.target.value;
                setFilterActive(value === 'all' ? null : value === 'active');
                setPage(1);
              }}
              style={{
                padding: '0.5rem 0.75rem',
                borderRadius: '4px',
                border: '1px solid #ccc',
                fontSize: '0.9rem',
              }}
            >
              <option value="all">All</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="error-message" style={{ marginBottom: '1rem' }}>
            {error}
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <p>Loading subscription services...</p>
          </div>
        )}

        {/* Services Table */}
        {!loading && (
          <div className="dashboard-section">
            <div style={{ overflowX: 'auto' }}>
              <table
                style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  backgroundColor: '#fff',
                  borderRadius: '4px',
                  overflow: 'hidden',
                }}
              >
                <thead>
                  <tr style={{ backgroundColor: '#4CAF50', color: '#fff' }}>
                    <th style={{ padding: '0.75rem', textAlign: 'left', borderBottom: '2px solid #2e7d32' }}>
                      Name
                    </th>
                    <th style={{ padding: '0.75rem', textAlign: 'left', borderBottom: '2px solid #2e7d32' }}>
                      Description
                    </th>
                    <th style={{ padding: '0.75rem', textAlign: 'left', borderBottom: '2px solid #2e7d32' }}>
                      Price
                    </th>
                    <th style={{ padding: '0.75rem', textAlign: 'left', borderBottom: '2px solid #2e7d32' }}>
                      Billing Period
                    </th>
                    <th style={{ padding: '0.75rem', textAlign: 'left', borderBottom: '2px solid #2e7d32' }}>
                      Status
                    </th>
                    <th style={{ padding: '0.75rem', textAlign: 'left', borderBottom: '2px solid #2e7d32' }}>
                      Features
                    </th>
                    <th style={{ padding: '0.75rem', textAlign: 'left', borderBottom: '2px solid #2e7d32' }}>
                      Created
                    </th>
                    <th style={{ padding: '0.75rem', textAlign: 'left', borderBottom: '2px solid #2e7d32' }}>
                      Subscription Types
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {services.length === 0 ? (
                    <tr>
                      <td colSpan="8" style={{ padding: '2rem', textAlign: 'center', color: '#999' }}>
                        No subscription services found.
                      </td>
                    </tr>
                  ) : (
                    services.map((service) => (
                      <tr
                        key={service.id}
                        style={{
                          borderBottom: '1px solid #e0e0e0',
                          transition: 'background-color 0.2s',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#f5f5f5')}
                        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#fff')}
                      >
                        <td style={{ padding: '0.75rem', fontWeight: 600 }}>
                          {service.name}
                        </td>
                        <td style={{ padding: '0.75rem', maxWidth: '300px' }}>
                          {service.description || (
                            <span style={{ color: '#999', fontStyle: 'italic' }}>No description</span>
                          )}
                        </td>
                        <td style={{ padding: '0.75rem', fontWeight: 600, color: '#2e7d32' }}>
                          {formatPrice(service.price, service.currency)}
                        </td>
                        <td style={{ padding: '0.75rem' }}>
                          {formatBillingPeriod(service.billing_period)}
                        </td>
                        <td style={{ padding: '0.75rem' }}>
                          <span
                            style={{
                              padding: '0.25rem 0.75rem',
                              borderRadius: '12px',
                              fontSize: '0.85rem',
                              fontWeight: 600,
                              backgroundColor: service.is_active ? '#e8f5e9' : '#ffebee',
                              color: service.is_active ? '#2e7d32' : '#c62828',
                            }}
                          >
                            {service.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                        <td style={{ padding: '0.75rem', maxWidth: '300px', fontSize: '0.9rem' }}>
                          {renderFeatures(service.features)}
                        </td>
                        <td style={{ padding: '0.75rem', fontSize: '0.85rem', color: '#666' }}>
                          {service.created_at
                            ? new Date(service.created_at).toLocaleDateString()
                            : 'N/A'}
                        </td>
                        <td style={{ padding: '0.75rem' }}>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                            {['freemium', 'premium'].map((type) => (
                              <label
                                key={type}
                                style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '0.5rem',
                                  cursor: updating ? 'not-allowed' : 'pointer',
                                  opacity: updating ? 0.6 : 1,
                                }}
                              >
                                <input
                                  type="checkbox"
                                  checked={getToggleState(service.id, type)}
                                  onChange={(e) =>
                                    handleToggleChange(service.id, type, e.target.checked)
                                  }
                                  disabled={updating}
                                  style={{
                                    width: '18px',
                                    height: '18px',
                                    cursor: updating ? 'not-allowed' : 'pointer',
                                  }}
                                />
                                <span style={{ textTransform: 'capitalize', fontSize: '0.85rem' }}>
                                  {type}
                                </span>
                              </label>
                            ))}
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginTop: '1.5rem',
                  padding: '1rem',
                  backgroundColor: '#f8f9fa',
                  borderRadius: '4px',
                }}
              >
                <div style={{ color: '#666' }}>
                  Showing {services.length} of {total} services
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    style={{
                      padding: '0.5rem 1rem',
                      backgroundColor: page === 1 ? '#ccc' : '#4CAF50',
                      color: '#fff',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: page === 1 ? 'not-allowed' : 'pointer',
                    }}
                  >
                    Previous
                  </button>
                  <span style={{ padding: '0.5rem 1rem', alignSelf: 'center' }}>
                    Page {page} of {totalPages}
                  </span>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    style={{
                      padding: '0.5rem 1rem',
                      backgroundColor: page === totalPages ? '#ccc' : '#4CAF50',
                      color: '#fff',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: page === totalPages ? 'not-allowed' : 'pointer',
                    }}
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default SubscriptionServices;
