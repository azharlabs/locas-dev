import { useState, useRef, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import Layout from '../components/Layout';
import ChatMessage from '../components/ChatMessage';
import ChatInput from '../components/ChatInput';
import TypingIndicator from '../components/TypingIndicator';
import { processQuery, getChatHistory, ApiResponse, ChatHistoryItem } from '../lib/api';
import { FaMapMarkerAlt } from 'react-icons/fa';

type Message = {
  text: string;
  sender: 'user' | 'assistant';
};

export default function Home() {
  const { data: session } = useSession();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const sessionInitialized = useRef<boolean>(false);

  // Load or create session on initial load only
  useEffect(() => {
    // Only run this once
    if (sessionInitialized.current) return;
    
    // Function to create a new session ID
    const createNewSession = () => {
      const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
      console.log("Created new session ID:", newSessionId);
      setSessionId(newSessionId);
      
      // CRITICAL: Always store in localStorage for persistence across renders
      localStorage.setItem('sessionId', newSessionId);
      
      // Log this important action for debugging
      console.log("%c[SESSION] Created new session ID in localStorage", "color: green; font-weight: bold");
      
      return newSessionId;
    };
    
    try {
      // Try to get session from localStorage first - this is the source of truth
      const storedSessionId = localStorage.getItem('sessionId');
      
      if (storedSessionId) {
        console.log("%c[SESSION] Found existing session ID in localStorage: " + storedSessionId, 
          "color: blue; font-weight: bold");
        
        // Set state with localStorage value
        setSessionId(storedSessionId);
        
        // Validate the session ID by trying to load history
        loadChatHistory(storedSessionId)
          .then(success => {
            console.log("%c[SESSION] Successfully validated session: " + storedSessionId, 
              "color: green; font-weight: bold");
          })
          .catch(error => {
            console.error("%c[SESSION] Error with stored session, creating new one: " + error, 
              "color: red; font-weight: bold");
            createNewSession();
          });
      } else {
        // Create a new session ID on first load if none exists
        console.log("%c[SESSION] No session found in localStorage, creating new one", 
          "color: orange; font-weight: bold");
        createNewSession();
      }
    } catch (error) {
      console.error("%c[SESSION] Error initializing session, creating emergency session: " + error, 
        "color: red; font-weight: bold");
      createNewSession();
    }
    
    // Add event listener for storage changes to keep session in sync across tabs
    window.addEventListener('storage', (event) => {
      if (event.key === 'sessionId' && event.newValue !== sessionId) {
        console.log("%c[SESSION] Session ID changed in another tab, updating", 
          "color: purple; font-weight: bold");
        setSessionId(event.newValue);
      }
    });
    
    sessionInitialized.current = true;
  }, []);

  // Scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Save session ID to localStorage when it changes
  useEffect(() => {
    if (sessionId) {
      localStorage.setItem('sessionId', sessionId);
    }
  }, [sessionId]);

  // Load chat history from the server
  const loadChatHistory = async (sid: string) => {
    try {
      setIsLoading(true);
      console.log("Loading chat history for session:", sid);
      const response = await getChatHistory(sid);
      
      if (response.status === 'success' && response.chat_history) {
        console.log("Loaded chat history:", response.chat_history.length, "messages");
        const loadedMessages = response.chat_history.map((item: ChatHistoryItem) => ({
          text: item.content,
          sender: item.role
        }));
        setMessages(loadedMessages);
      } else {
        console.log("No chat history found or error:", response.status);
      }
    } catch (error) {
      console.error('Error loading chat history:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async (text: string) => {
    // Add user message
    const userMessage: Message = { text, sender: 'user' };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // Force read from localStorage before sending request to ensure we have latest value
    // This is crucial for session continuity across component re-renders
    const storedSessionId = localStorage.getItem('sessionId');
    
    // If we have a valid session in localStorage but state doesn't match, update state
    if (storedSessionId && storedSessionId !== sessionId) {
      console.warn("Session ID state doesn't match localStorage, correcting");
      setSessionId(storedSessionId);
    }
    
    // Ensure we have a session ID before sending the request
    if (!sessionId && !storedSessionId) {
      console.error("No session ID available in state or localStorage");
      // Generate one if somehow we don't have one at all
      const newSessionId = `emergency_session_${Date.now()}`;
      setSessionId(newSessionId);
      localStorage.setItem('sessionId', newSessionId);
      console.log("Created emergency session ID:", newSessionId);
    } else {
      console.log("Sending request with session ID:", sessionId || storedSessionId);
    }
    
    try {
      // Always use the most reliable session ID we have (localStorage takes precedence)
      const finalSessionId = storedSessionId || sessionId;
      const response = await processQuery(text, finalSessionId);
      
      // Verify and update session ID state if needed
      if (response.session_id) {
        if (response.session_id !== sessionId) {
          console.log("Updating session ID state to match response:", response.session_id);
          setSessionId(response.session_id);
        }
      }
      
      // Add assistant message
      if (response.status === 'success') {
        const assistantMessage: Message = { 
          text: response.result || 'No result received', 
          sender: 'assistant' 
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } else {
        const errorMessage: Message = { 
          text: response.message || 'Sorry, there was an error processing your query.', 
          sender: 'assistant' 
        };
        setMessages((prev) => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage: Message = { 
        text: 'Sorry, there was an error connecting to the server. Please try again later.', 
        sender: 'assistant' 
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Layout>
      <div className="mx-0 sm:mx-12 md:mx-24 lg:mx-48 xl:mx-64 h-full">
        <div className="flex h-full flex-col bg-white overflow-hidden">
          <div className="flex-1 overflow-y-auto px-5 py-4">
            {messages.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center text-center">
                <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-primary-100">
                  <FaMapMarkerAlt className="text-2xl text-primary-600" />
                </div>
                <h2 className="mb-2 text-2xl font-bold text-gray-800">
                  Locas
                </h2>
                <p className="mb-4 max-w-lg text-gray-600">
                  Ask questions about any location to get insights on land suitability, business viability, and more.
                </p>
                <div className="grid max-w-lg gap-2 text-left text-sm text-gray-600">
                  <p className="rounded-lg border border-gray-200 bg-gray-50 p-3 shadow-sm">
                    • "Can I buy land at 37.7749, -122.4194?"
                  </p>
                  <p className="rounded-lg border border-gray-200 bg-gray-50 p-3 shadow-sm">
                    • "Is there a park near Times Square, New York?"
                  </p>
                  <p className="rounded-lg border border-gray-200 bg-gray-50 p-3 shadow-sm">
                    • "Can I open a restaurant here? https://maps.google.com/?q=34.0522,-118.2437"
                  </p>
                </div>
              </div>
            ) : (
              messages.map((message, index) => (
                <ChatMessage key={index} message={message} />
              ))
            )}
            {isLoading && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </div>
          
          {session ? (
            <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
          ) : (
            <div className="p-4 text-center">
              <p className="text-gray-600">Please sign in to use the Locas</p>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}