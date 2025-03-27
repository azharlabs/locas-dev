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
    // Get session ID from localStorage as a fallback
    const fallbackSessionId = localStorage.getItem('sessionId');
    
    // Use the provided session_id, then fallback to localStorage, then create an emergency one
    const finalSessionId = session_id || fallbackSessionId || `emergency_${Date.now()}`;
    
    if (!session_id) {
      console.error("Missing session_id in processQuery call, using fallback:", finalSessionId);
      // If we had to fall back to localStorage, make sure to alert
      if (finalSessionId !== session_id) {
        console.warn("SESSION CONTINUITY ISSUE: Using fallback session ID from localStorage");
      }
    }
    
    console.log("API request with session_id:", finalSessionId);
    
    // Always include session_id in the request payload
    const response = await axios.post(`${API_URL}/api/process-query`, {
      query,
      session_id: finalSessionId,
    });
    
    // Store the session ID from response in localStorage as an additional safeguard
    if (response.data.session_id) {
      localStorage.setItem('sessionId', response.data.session_id);
      console.log("Stored session ID in localStorage:", response.data.session_id);
    }
    
    console.log("API response with session_id:", response.data.session_id);
    return response.data;
  } catch (error) {
    console.error('Error processing query:', error);
    throw error;
  }
};

export const getChatHistory = async (session_id: string): Promise<ApiResponse> => {
  try {
    // Get fallback session ID from localStorage
    const fallbackSessionId = localStorage.getItem('sessionId');
    
    // Use the provided session_id or fall back to localStorage
    const finalSessionId = session_id || fallbackSessionId;
    
    // Validate session ID
    if (!finalSessionId) {
      console.error("%c[SESSION] Critical: Missing session_id in getChatHistory call", 
        "color:red; font-weight:bold");
      throw new Error("Session ID is required");
    }
    
    console.log("%c[SESSION] Fetching chat history for session: " + finalSessionId, 
      "color:blue; font-weight:bold");
    
    const response = await axios.get(`${API_URL}/api/get-history`, {
      params: { session_id: finalSessionId }
    });
    
    // If response includes a session ID, store it in localStorage
    if (response.data.session_id) {
      localStorage.setItem('sessionId', response.data.session_id);
    }
    
    console.log("%c[SESSION] Retrieved chat history with length: " + 
      (response.data.chat_history ? response.data.chat_history.length : 0), 
      "color:green; font-weight:bold");
    
    return response.data;
  } catch (error) {
    console.error('%c[SESSION] Error getting chat history:' + error, "color:red; font-weight:bold");
    throw error;
  }
};