import os
import asyncio
import uuid
import datetime
import logging
from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from dotenv import load_dotenv
from functools import wraps

from assistant import LocationAssistant
from models import AppConfig
from services.redis_service import RedisService
from logging_config import configure_logger

# Configure logging
logger = configure_logger()

# Load environment variables
load_dotenv()

# Get configuration
config = AppConfig.from_env()
logger.info(f"Application configuration loaded: {config}")

# Initialize the redis service
redis_service = RedisService(
    host=os.environ.get("REDIS_HOST", "localhost"),
    port=int(os.environ.get("REDIS_PORT", 6379))
)
logger.info(f"Redis service initialized with host: {os.environ.get('REDIS_HOST', 'localhost')}, port: {os.environ.get('REDIS_PORT', 6379)}")

# Initialize the assistant
assistant = LocationAssistant(
    openai_api_key=config.openai_api_key,
    maps_api_key=config.maps_api_key
)
logger.info("Location Assistant initialized")

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
    # Set up logging
    import logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    try:
        # Get data from the request
        data = request.json
        logger.info(f"Received request data: {data}")
        
        # Extract the user query (required)
        if 'query' not in data:
            logger.error("No query provided in request")
            return jsonify({
                'status': 'error',
                'message': 'No query provided'
            }), 400
        
        user_query = data.get('query')
        logger.info(f"Processing query: {user_query}")
        
        # Use client-provided session ID
        session_id = data.get('session_id')
        if not session_id:
            # This should never happen now, but handle it gracefully if it does
            session_id = str(uuid.uuid4())
            logger.error(f"CRITICAL: Client didn't provide session ID, created emergency one: {session_id}")
        else:
            logger.info(f"Using client-provided session ID: {session_id}")
            
        # Clean up session_id value (sanitize it)
        try:
            # Ensure it's a string
            session_id = str(session_id).strip()
            
            # Validate session ID format - log warnings but don't reject IDs
            if len(session_id) < 8:
                logger.warning(f"Suspicious session ID format (too short): {session_id}")
            
            # Check for common session ID patterns
            if session_id.startswith(('session_', 'emergency_', 'fallback_')):
                logger.info(f"Recognized session ID pattern: {session_id[:10]}...")
            else:
                logger.warning(f"Unusual session ID pattern: {session_id[:10]}...")
                
        except Exception as e:
            logger.error(f"Error processing session ID: {str(e)}")
            
        # Initialize a new session if it doesn't exist yet
        session_data = redis_service.get_session(session_id)
        if not session_data:
            logger.info(f"Initializing new session in Redis: {session_id}")
            redis_service.save_session(session_id, {
                "created_at": str(datetime.datetime.now()),
                "chat_history": [],
                # Initialize with empty history - don't create a new session ID
            })
        
        # Get chat history and last location from Redis
        chat_history = redis_service.get_chat_history(session_id)
        last_location = redis_service.get_last_location(session_id)
        logger.info(f"Last location from session: {last_location}")
        
        # Check if query implies using the previous location
        use_previous_location = False
        location_referencing_phrases = ["there", "that location", "that place", "the same place", "same location"]
        if any(phrase in user_query.lower() for phrase in location_referencing_phrases) and last_location:
            use_previous_location = True
            logger.info("Query references previous location")
        
        # Extract coordinates from query for logging and debugging
        parsed_query, extracted_coordinates = await assistant._parse_query(user_query)
        if extracted_coordinates:
            logger.info(f"Extracted coordinates from query: {extracted_coordinates}")
        else:
            logger.info("No coordinates extracted from query")
        
        # Process the query - the location should be embedded in the query or from previous session
        try:
            # If coordinates were extracted from the query, use them directly
            if extracted_coordinates:
                lat = float(extracted_coordinates.get('lat'))
                lng = float(extracted_coordinates.get('lng'))
                logger.info(f"Using extracted coordinates: lat={lat}, lng={lng}")
                result = await assistant.process_query(user_query, latitude=lat, longitude=lng)
            # If query references previous location, use it
            elif use_previous_location and last_location:
                lat = float(last_location.get('latitude'))
                lng = float(last_location.get('longitude'))
                logger.info(f"Using previous location: lat={lat}, lng={lng}")
                result = await assistant.process_query(user_query, latitude=lat, longitude=lng)
            else:
                # Process normally, but this will likely return `no valid address`
                logger.info("No coordinates available, letting assistant extract them")
                result = await assistant.process_query(user_query)
            
            logger.info(f"Result: {result[:100]}...")
            
            # Check if we used no valid address
            if "no valid address" in result.lower():
                logger.warning(f"No valid location found for session {session_id}")
                return jsonify({
                    'status': 'warning',
                    'message': 'No location information found in query',
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
            if extracted_coordinates:
                location_data = {
                    "latitude": float(extracted_coordinates.get('lat')), 
                    "longitude": float(extracted_coordinates.get('lng'))
                }
                logger.info(f"Saving location to session: {location_data}")
                redis_service.save_location(session_id, location_data)
            
            # Return the successful result with the session ID
            # ALWAYS return the same session ID that was provided in the request
            # This is critical for maintaining session continuity
            logger.info(f"Successfully processed query for session {session_id}")
            return jsonify({
                'status': 'success',
                'result': result,
                'session_id': session_id  # Always echo back the same session ID
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
            logger.error("API called without session ID")
            return jsonify({
                'status': 'error',
                'message': 'No session ID provided - unable to retrieve chat history'
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
        logger.error("OPENAI_API_KEY environment variable is not set.")
        logger.error("Please create a .env file based on .env.example and add your API keys.")
    elif not redis_service.ping():
        logger.error("Cannot connect to Redis.")
        logger.error("Please ensure Redis is running and accessible.")
    else:
        # Run the app
        port = int(os.environ.get('PORT', 5000))
        logger.info(f"Starting Flask app on port {port}")
        app.run(host='0.0.0.0', port=port, debug=True)