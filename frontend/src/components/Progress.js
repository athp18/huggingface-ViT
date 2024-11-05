// src/components/Progress.js

import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import './Progress.css'; // Optional: Create this file for component-specific styles

function Progress() {
  const location = useLocation();
  const navigate = useNavigate();
  const details = location.state?.details;

  const handleBack = () => {
    navigate('/');
  };

  if (!details) {
    return (
      <div className="progress-container">
        <h2>No Transfer Details Available</h2>
        <button className="button" onClick={handleBack}>
          Back to Home
        </button>
      </div>
    );
  }

  return (
    <div className="progress-container">
      <h2>Transfer Complete</h2>
      <div className="summary">
        <p><strong>Total Tracks:</strong> {details.total_tracks}</p>
        <p><strong>Added Videos:</strong> {details.added_videos}</p>
        <p><strong>Instrumentals Not Found:</strong> {details.not_found}</p>
      </div>
      {details.errors.length > 0 && (
        <div className="errors">
          <h3>Errors:</h3>
          <ul>
            {details.errors.map((error, index) => (
              <li key={index}>{error}</li>
            ))}
          </ul>
        </div>
      )}
      <button className="button" onClick={handleBack}>
        Back to Home
      </button>
    </div>
  );
}

export default Progress;