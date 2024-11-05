// src/components/Transfer.js

import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import './Transfer.css'; // Optional: Create this file for component-specific styles
import axiosInstance from '../axiosConfig';

const response = await axiosInstance.post('/transfer', { /* data */ });

function Transfer() {
  const [playlistId, setPlaylistId] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const navigate = useNavigate();

  const handleTransfer = async () => {
    if (!playlistId || !title) {
      setError('Spotify Playlist ID and YouTube Playlist Title are required.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await axios.post(
        'http://localhost:5000/transfer',
        {
          playlist_id: playlistId,
          youtube_title: title,
          youtube_description: description,
        },
        { withCredentials: true }
      );

      if (response.data.status === 'success') {
        navigate('/progress', { state: { details: response.data.details } });
      } else {
        setError(response.data.message || 'Transfer failed.');
      }
    } catch (err) {
      if (err.response && err.response.data && err.response.data.message) {
        setError(err.response.data.message);
      } else {
        setError('An error occurred during the transfer.');
      }
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="transfer-container">
      <h2>Transfer Spotify Playlist to YouTube</h2>
      <div className="form-group">
        <label>Spotify Playlist ID:</label>
        <input
          type="text"
          value={playlistId}
          onChange={(e) => setPlaylistId(e.target.value)}
          placeholder="Enter Spotify Playlist ID"
        />
      </div>
      <div className="form-group">
        <label>YouTube Playlist Title:</label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Enter YouTube Playlist Title"
        />
      </div>
      <div className="form-group">
        <label>YouTube Playlist Description (Optional):</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Enter YouTube Playlist Description"
        />
      </div>
      {error && <p className="error">{error}</p>}
      <button className="button" onClick={handleTransfer} disabled={loading}>
        {loading ? 'Transferring...' : 'Start Transfer'}
      </button>
    </div>
  );
}

export default Transfer;