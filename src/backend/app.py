import os
import asyncio
import uuid
from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from dotenv import load_dotenv
from functools import wraps

from assistant import LocationAssistant
from models import AppConfig
from services.redis_service import RedisService

# Load environment variables
load_dotenv()

# Get configuration
config = AppConfig.from_env()

# Initialize the redis service
redis_service = RedisService(
    host=os.environ.get("REDIS_HOST", "localhost"),
    port=int(os.environ.get("REDIS_PORT", 6379))
)

# Initialize the assistant
assistant = LocationAssistant(
    openai_api_key=config.openai_api_key,
    maps_api_key=config.maps_api_key
)

# Create Flask app
app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24).hex())

# Enable CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Helper function to run async functions in Flask
def async_route(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapped

# Serve the main page
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/process-query', methods=['POST'])
@async_route
async def process_query():
    """API endpoint to process location-based queries."""
    try:
        # Get data from the request
        data = request.json
        
        # Extract the user query (required)
        if 'query' not in data:
            return jsonify({
                'status': 'error',
                'message': 'No query provided'
            }), 400
        
        user_query = data.get('query')
        
        # Get or create session ID
        session_id = data.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Get chat history and last location from Redis
        chat_history = redis_service.get_chat_history(session_id)
        last_location = redis_service.get_last_location(session_id)
        
        # Check if query implies using the previous location
        use_previous_location = False
        location_referencing_phrases = ["there", "that location", "that place", "the same place", "same location"]
        if any(phrase in user_query.lower() for phrase in location_referencing_phrases) and last_location:
            use_previous_location = True
        
        # Process the query - the location should be embedded in the query or from previous session
        try:
            # If query references previous location, use it
            if use_previous_location and last_location:
                lat = last_location.get('latitude')
                lng = last_location.get('longitude')
                result = await assistant.process_query(user_query, latitude=lat, longitude=lng)
            else:
                # Process normally, extracting location from the query
                result = await assistant.process_query(user_query)
            
            # Check if we used default location (indicating no location was found)
            if "default location" in result.lower() or "san francisco" in result.lower():
                return jsonify({
                    'status': 'warning',
                    'message': 'No location information found in query, used default location',
                    'result': "The address was not found. Kindly include the address in your query to proceed.",
                    'session_id': session_id
                })
            
            # Add message to chat history
            redis_service.add_to_chat_history(
                session_id, 
                {"role": "user", "content": user_query}
            )
            redis_service.add_to_chat_history(
                session_id, 
                {"role": "assistant", "content": result}
            )
            
            # Save extracted location for future use
            # Get coordinates from the assistant's response or extracted data
            parsed_query, extracted_coordinates = await assistant._parse_query(user_query)
            if extracted_coordinates:
                redis_service.save_location(
                    session_id, 
                    {"latitude": extracted_coordinates.get('lat'), "longitude": extracted_coordinates.get('lng')}
                )
            
            # Return the successful result
            return jsonify({
                'status': 'success',
                'result': result,
                'session_id': session_id
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error processing query: {str(e)}',
                'session_id': session_id
            }), 500
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/api/get-history', methods=['GET'])
def get_chat_history():
    """API endpoint to retrieve chat history for a session."""
    try:
        # Get the session ID from the request
        session_id = request.args.get('session_id')
        
        if not session_id:
            return jsonify({
                'status': 'error',
                'message': 'No session ID provided'
            }), 400
        
        # Get the chat history from Redis
        chat_history = redis_service.get_chat_history(session_id)
        
        return jsonify({
            'status': 'success',
            'chat_history': chat_history,
            'session_id': session_id
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving chat history: {str(e)}'
        }), 500

if __name__ == '__main__':
    # Check for required API keys and services
    if not config.openai_api_key:
        print("Error: OPENAI_API_KEY environment variable is not set.")
        print("Please create a .env file based on .env.example and add your API keys.")
    elif not redis_service.ping():
        print("Error: Cannot connect to Redis.")
        print("Please ensure Redis is running and accessible.")
    else:
        # Run the app
        port = int(os.environ.get('PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=True)