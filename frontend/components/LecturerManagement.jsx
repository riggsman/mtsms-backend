import React, { useState, useEffect } from 'react';
import './LecturerManagement.css';

const LecturerManagement = () => {
  const [teachers, setTeachers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    fetchTeachers();
  }, [page, pageSize]);

  const fetchTeachers = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const tenantName = localStorage.getItem('tenantName') || 'riggstech';
      
      const response = await fetch(
        `http://localhost:8000/api/v1/teachers?page=${page}&page_size=${pageSize}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'X-Tenant-Name': tenantName,
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch teachers');
      }

      const data = await response.json();
      setTeachers(data.items || []);
      setTotal(data.total || 0);
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching teachers:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading">Loading lecturers...</div>;
  }

  if (error) {
    return <div className="error">Error: {error}</div>;
  }

  return (
    <div className="lecturer-management">
      <div className="page-header">
        <h1>Lecturer Management</h1>
        <button className="btn-primary">Add New Lecturer</button>
      </div>

      <div className="table-container-wrapper">
        <div className="table-container">
          <table className="lecturer-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Employee ID</th>
                <th>Name</th>
                <th>Email</th>
                <th>Phone</th>
                <th>Department</th>
                <th>Qualification</th>
                <th>Specialization</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {teachers.length === 0 ? (
                <tr>
                  <td colSpan="9" className="no-data">
                    No lecturers found
                  </td>
                </tr>
              ) : (
                teachers.map((teacher) => (
                  <tr key={teacher.id}>
                    <td>{teacher.id}</td>
                    <td>{teacher.employee_id}</td>
                    <td className="name-cell">
                      {teacher.firstname} {teacher.middlename ? teacher.middlename + ' ' : ''}{teacher.lastname}
                    </td>
                    <td>{teacher.email}</td>
                    <td>{teacher.phone}</td>
                    <td>{teacher.department_id}</td>
                    <td className="wrap">{teacher.qualification || 'N/A'}</td>
                    <td className="wrap">{teacher.specialization || 'N/A'}</td>
                    <td className="actions-cell">
                      <button className="btn-edit">Edit</button>
                      <button className="btn-delete">Delete</button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      <div className="pagination">
        <button 
          onClick={() => setPage(p => Math.max(1, p - 1))} 
          disabled={page === 1}
          className="btn-pagination"
        >
          Previous
        </button>
        <span className="page-info">
          Page {page} of {Math.ceil(total / pageSize)} ({total} total)
        </span>
        <button 
          onClick={() => setPage(p => p + 1)} 
          disabled={page >= Math.ceil(total / pageSize)}
          className="btn-pagination"
        >
          Next
        </button>
      </div>
    </div>
  );
};

export default LecturerManagement;
