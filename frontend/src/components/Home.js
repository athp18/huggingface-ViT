// src/components/Home.js

import React from 'react';
import './Home.css'; // Optional: Create this file for component-specific styles

function Home() {
  const handleSpotifyAuth = () => {
    window.location.href = 'http://localhost:5000/auth/spotify';
  };

  const handleYouTubeAuth = () => {
    window.location.href = 'http://localhost:5000/auth/youtube';
  };

  return (
    <div className="container">
      <h1>Spotify to YouTube Playlist Transfer</h1>
      <div className="auth-buttons">
        <button className="button spotify" onClick={handleSpotifyAuth}>
          Authenticate with Spotify
        </button>
        <button className="button youtube" onClick={handleYouTubeAuth}>
          Authenticate with YouTube
        </button>
      </div>
    </div>
  );
}

export default Home;