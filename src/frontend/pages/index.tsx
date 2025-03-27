import { useState, useRef, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import Layout from '../components/Layout';
import ChatMessage from '../components/ChatMessage';
import ChatInput from '../components/ChatInput';
import TypingIndicator from '../components/TypingIndicator';
import { processQuery, getChatHistory, ApiResponse, ChatHistoryItem } from '../lib/api';
import { FaLock } from 'react-icons/fa';

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

  // Load session from localStorage on initial load
  useEffect(() => {
    const storedSessionId = localStorage.getItem('sessionId');
    if (storedSessionId) {
      setSessionId(storedSessionId);
      loadChatHistory(storedSessionId);
    }
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
      const response = await getChatHistory(sid);
      
      if (response.status === 'success' && response.chat_history) {
        const loadedMessages = response.chat_history.map((item: ChatHistoryItem) => ({
          text: item.content,
          sender: item.role
        }));
        setMessages(loadedMessages);
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

    try {
      // Process the query with session ID if available
      const response = await processQuery(text, sessionId);
      
      // Store session ID if received and not already set
      if (response.session_id && !sessionId) {
        setSessionId(response.session_id);
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
                  <FaLock className="text-2xl text-primary-600" />
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