import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000';

export interface ChatHistoryItem {
  role: 'user' | 'assistant';
  content: string;
}

export interface ApiResponse {
  status: 'success' | 'error' | 'warning';
  result?: string;
  message?: string;
  session_id?: string;
  chat_history?: ChatHistoryItem[];
}

export const processQuery = async (query: string, session_id?: string): Promise<ApiResponse> => {
  try {
    const response = await axios.post(`${API_URL}/api/process-query`, {
      query,
      session_id,
    });
    
    return response.data;
  } catch (error) {
    console.error('Error processing query:', error);
    throw error;
  }
};

export const getChatHistory = async (session_id: string): Promise<ApiResponse> => {
  try {
    const response = await axios.get(`${API_URL}/api/get-history`, {
      params: { session_id }
    });
    
    return response.data;
  } catch (error) {
    console.error('Error getting chat history:', error);
    throw error;
  }
};