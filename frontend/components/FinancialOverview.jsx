import React from 'react';
import './Dashboard.css';

const FinancialOverview = () => {
  // Static demo data for now – wire to backend when endpoints are ready
  const summaryCards = [
    { label: 'Total Revenue (This Term)', value: '₦12,450,000', sub: '+8.2% vs last term' },
    { label: 'Outstanding Fees', value: '₦3,200,000', sub: '54 students owing' },
    { label: 'Total Expenses (This Term)', value: '₦7,850,000', sub: 'Including salaries & operations' },
    { label: 'Net Position', value: '₦4,600,000', sub: 'Healthy cash flow' },
  ];

  const feeByClass = [
    { level: 'JSS 1', expected: '₦1,800,000', collected: '₦1,500,000', outstanding: '₦300,000' },
    { level: 'JSS 2', expected: '₦1,650,000', collected: '₦1,420,000', outstanding: '₦230,000' },
    { level: 'SS 1', expected: '₦2,300,000', collected: '₦1,900,000', outstanding: '₦400,000' },
    { level: 'SS 3', expected: '₦2,700,000', collected: '₦2,300,000', outstanding: '₦400,000' },
  ];

  const recentTransactions = [
    { date: '2026-02-20', type: 'Fee Payment', ref: 'INV-2026-001', amount: '₦120,000', status: 'Completed' },
    { date: '2026-02-19', type: 'Salary', ref: 'PAY-2026-014', amount: '₦850,000', status: 'Completed' },
    { date: '2026-02-18', type: 'Facility Maintenance', ref: 'EXP-2026-009', amount: '₦210,000', status: 'Pending' },
    { date: '2026-02-17', type: 'Fee Payment', ref: 'INV-2026-002', amount: '₦95,000', status: 'Completed' },
  ];

  return (
    <div className="dashboard-main">
      <div className="dashboard-header">
        <h1>Financial Overview</h1>
        <p style={{ marginTop: '0.5rem', color: '#555' }}>
          High-level summary of revenue, expenses, and outstanding fees.
        </p>
      </div>

      <div className="dashboard-content">
        {/* Summary cards */}
        <div className="dashboard-section">
          <div className="section-header">
            <h2>Key Metrics</h2>
          </div>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '1rem',
            }}
          >
            {summaryCards.map((card, idx) => (
              <div
                key={idx}
                style={{
                  background: '#f8fdf8',
                  borderRadius: '8px',
                  padding: '1rem 1.25rem',
                  border: '1px solid #e0e0e0',
                }}
              >
                <div style={{ fontSize: '0.85rem', color: '#666' }}>{card.label}</div>
                <div
                  style={{
                    marginTop: '0.5rem',
                    fontSize: '1.4rem',
                    fontWeight: 600,
                    color: '#2e7d32',
                  }}
                >
                  {card.value}
                </div>
                <div style={{ marginTop: '0.25rem', fontSize: '0.8rem', color: '#777' }}>
                  {card.sub}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Fee collection by class */}
        <div className="dashboard-section">
          <div className="section-header">
            <h2>Fee Collection by Class</h2>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Class / Level</th>
                  <th>Expected Fees</th>
                  <th>Collected</th>
                  <th>Outstanding</th>
                </tr>
              </thead>
              <tbody>
                {feeByClass.map((row, idx) => (
                  <tr key={idx}>
                    <td>{row.level}</td>
                    <td>{row.expected}</td>
                    <td>{row.collected}</td>
                    <td>{row.outstanding}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recent transactions */}
        <div className="dashboard-section">
          <div className="section-header">
            <h2>Recent Transactions</h2>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Type</th>
                  <th>Reference</th>
                  <th>Amount</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {recentTransactions.map((tx, idx) => (
                  <tr key={idx}>
                    <td>{tx.date}</td>
                    <td>{tx.type}</td>
                    <td>{tx.ref}</td>
                    <td>{tx.amount}</td>
                    <td>{tx.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FinancialOverview;

