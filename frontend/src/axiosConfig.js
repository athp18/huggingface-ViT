// src/axiosConfig.js

import axios from 'axios';

const axiosInstance = axios.create({
  baseURL: 'http://localhost:5000',
  withCredentials: true, // Send cookies with each request
});

export default axiosInstance;