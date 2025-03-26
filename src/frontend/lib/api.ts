import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000';

export const processQuery = async (query: string) => {
  try {
    const response = await axios.post(`${API_URL}/api/process-query`, {
      query,
    });
    
    return response.data;
  } catch (error) {
    console.error('Error processing query:', error);
    throw error;
  }
};