import os
import asyncio
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from functools import wraps

from assistant import LocationAssistant
from models import AppConfig

# Load environment variables
load_dotenv()

# Get configuration
config = AppConfig.from_env()

# Initialize the assistant
assistant = LocationAssistant(
    openai_api_key=config.openai_api_key,
    maps_api_key=config.maps_api_key
)

# Create Flask app
app = Flask(__name__, static_folder='static')

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
        
        # Process the query - the location should be embedded in the query
        try:
            # We'll pass the raw query to the assistant which will extract location information
            result = await assistant.process_query(user_query)
            
            # Check if we used no valid address (indicating no location was found)
            if "no valid address" in result.lower():
                return jsonify({
                    'status': 'warning',
                    'message': 'No location information found in query',
                    'result': "The address was not found. Kindly include the address in your query to proceed."
                })
            
            # Return the successful result
            return jsonify({
                'status': 'success',
                'result': result
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error processing query: {str(e)}'
            }), 500
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Server error: {str(e)}'
        }), 500

if __name__ == '__main__':
    # Check for required API keys
    if not config.openai_api_key:
        print("Error: OPENAI_API_KEY environment variable is not set.")
        print("Please create a .env file based on .env.example and add your API keys.")
    else:
        # Run the app
        port = int(os.environ.get('PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=True)