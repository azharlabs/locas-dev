import json
import httpx
from typing import Dict, Any, Optional, List, Union, Tuple

from openai import AsyncOpenAI
from models import ServiceConfig, LocationResults, LocationError, EnvResult
from services import PlacesService, EnvironmentService, OpenAIService
from assistant.analyzers import LandAnalyzer, LocalBusinessAnalyzer
from assistant.utils import ToolBuilder, ResultFormatter
from assistant.location_parser import LocationParser

class LocationAssistant:
    """
    Main assistant for analyzing locations and providing insights.
    """
    
    def __init__(self, openai_api_key: str, maps_api_key: str = "your_api_key"):
        """
        Initialize the location assistant.
        
        Args:
            openai_api_key: OpenAI API key
            maps_api_key: Google Maps API key
        """
        # Initialize services
        self.openai_service = OpenAIService(openai_api_key)
        self.places_service = PlacesService()
        self.env_service = EnvironmentService()
        
        # Store API keys
        self.openai_api_key = openai_api_key
        self.maps_api_key = maps_api_key
        
        # Initialize OpenAI client
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        
        # Initialize location parser
        self.location_parser = LocationParser(maps_api_key)
        
        # Initialize analyzers
        self.land_analyzer = LandAnalyzer(self.places_service, self.env_service, self.openai_service)
        self.business_analyzer = LocalBusinessAnalyzer(self.places_service, self.env_service, self.openai_service)
        
        # System prompts
        self.assistant_system_prompt = """
        You are a helpful location assistant that helps users find places near them and provides environmental information.
        
        When users ask about places, use the appropriate search function based on their request:
        - For finding places by category, use find_places
        - For comprehensive location analysis, use analyze_location_suitability
        - For business viability analysis, use analyze_business_viability
        
        When users ask about air quality or pollen, use the get_environmental_data function.
        
        Always format search results in a user-friendly way. If distances are available, 
        mention them to help the user understand how far places are from them.
        
        If the requested data is not available for a location, explain the issue in a helpful way.
        """
    
    async def process_query(self, user_query: str, latitude: Optional[float] = None, longitude: Optional[float] = None, maps_api_key: Optional[str] = None):
        """
        Process a user query with the given location.
        
        Args:
            user_query: The user's question or request
            latitude: The user's latitude (optional if location in query)
            longitude: The user's longitude (optional if location in query)
            maps_api_key: Optional Google Maps API key (uses default if not provided)
            
        Returns:
            Response string
        """
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        
        # Parse the user query to extract location information if not provided
        parsed_query, extracted_coordinates = await self._parse_query(user_query)
        
        # Log input parameters and extracted data
        logger.info(f"Query: {user_query}")
        logger.info(f"Input coordinates: lat={latitude}, lng={longitude}")
        logger.info(f"Extracted coordinates: {extracted_coordinates}")
        
        # Use extracted coordinates if no explicit coordinates provided
        if (latitude is None or longitude is None) and extracted_coordinates:
            latitude = extracted_coordinates.get('lat')
            longitude = extracted_coordinates.get('lng')
            logger.info(f"Using extracted coordinates: Latitude {latitude}, Longitude {longitude}")
        
        # If still no coordinates, use default (San Francisco)
        if latitude is None or longitude is None:
            logger.warning("No coordinates available, returning no valid address")
            return "no valid address"
            
        # Validate that coordinates are of correct type (float)
        try:
            latitude = float(latitude)
            longitude = float(longitude)
            logger.info(f"Validated coordinates: Latitude {latitude}, Longitude {longitude}")
        except (ValueError, TypeError) as e:
            logger.error(f"Coordinate validation error: {str(e)}")
            return "no valid address"
        
        # Create the HTTP client
        async with httpx.AsyncClient(timeout=30) as client:
            # Create the configuration
            config = ServiceConfig(
                api_key=maps_api_key or self.maps_api_key,
                http_client=client,
                max_result_retries=2
            )
            
            # Analyze the query to determine the best action
            if self._is_land_purchase_query(parsed_query):
                # For land purchase queries, use the comprehensive analysis
                print("Detected land purchase query, conducting comprehensive analysis...")
                return await self.land_analyzer.analyze_location(
                    latitude, longitude, parsed_query, None, config
                )
                
            # Check if it's a business query and get the business type
            business_check = self._is_business_query(parsed_query)
            if business_check["is_business"]:
                # For business viability queries
                business_type = business_check["business_type"]
                print(f"Detected {business_type} query, analyzing viability...")
                return await self.business_analyzer.analyze_location(
                    latitude, longitude, parsed_query, None, config, business_type
                )
            
            else:
                # For general queries, use the standard conversation flow
                return await self._handle_general_query(parsed_query, latitude, longitude, config)
    
    async def _parse_query(self, user_query: str) -> Tuple[str, Optional[Dict[str, float]]]:
        """
        Parse the user query to extract location information.
        
        Args:
            user_query: The full user query
            
        Returns:
            Tuple of (parsed_query, coordinates_dict)
        """
        # Use the location parser to extract location from query
        clean_query, coordinates = self.location_parser.parse_query(user_query)
        
        # If coordinates were extracted, use them
        if coordinates:
            print(f"Extracted coordinates from query: {coordinates}")
            return clean_query, coordinates
        
        # If neural processing is needed, we could use the OpenAI API to extract location
        # (Not implemented in this version)
        
        return user_query, None
    
    def _is_land_purchase_query(self, query: str) -> bool:
        """Check if the query is about land purchase."""
        query_lower = query.lower()
        return "buy" in query_lower and "land" in query_lower
    
    def _is_business_query(self, query: str) -> Dict[str, Any]:
        """
        Check if the query is about business viability and identify the business type.
        
        Args:
            query: The user query
            
        Returns:
            Dict with 'is_business' boolean and 'business_type' string if applicable
        """
        query_lower = query.lower()
        
        # Define common business types to check for
        business_types = {
            "tea stall": ["tea stall", "tea shop", "tea business"],
            "coffee shop": ["coffee shop", "cafe", "coffee business"],
            "restaurant": ["restaurant", "dining", "eatery", "food business"],
            "retail store": ["retail", "store", "shop", "boutique"],
            "grocery store": ["grocery", "supermarket", "food market"],
            "bakery": ["bakery", "pastry shop", "bread shop"],
        }
        
        # Check for general business terms
        general_business_terms = ["open", "start", "begin", "launch", "business", "shop", "store"]
        
        # Check for specific business types
        for business_type, keywords in business_types.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return {
                        "is_business": True,
                        "business_type": business_type
                    }
        
        # Check for general business queries
        for term in general_business_terms:
            if term in query_lower:
                return {
                    "is_business": True,
                    "business_type": "business"  # Generic business type
                }
                
        return {
            "is_business": False,
            "business_type": None
        }
    
    async def _handle_general_query(self, user_query: str, latitude: float, longitude: float, config: ServiceConfig) -> str:
        """Handle general queries using OpenAI function calling."""
        # Prepare the initial message
        full_query = f"{user_query} My location is {latitude}, {longitude}"
        messages = [
            {"role": "system", "content": self.assistant_system_prompt},
            {"role": "user", "content": full_query}
        ]
        
        # Create the tools
        tools = ToolBuilder.create_tools()
        
        # Initial conversation turns
        max_turns = 5
        current_turn = 0
        
        while current_turn < max_turns:
            current_turn += 1
            
            try:
                # Call the OpenAI API
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=0.7,
                    max_tokens=1000
                )
                
                # Get the assistant's message
                assistant_message = response.choices[0].message
                messages.append({"role": "assistant", "content": assistant_message.content or "", "tool_calls": assistant_message.tool_calls})
                
                # Check if there are any tool calls
                if assistant_message.tool_calls:
                    # Handle each tool call
                    for tool_call in assistant_message.tool_calls:
                        # Parse the tool call arguments
                        tool_args = json.loads(tool_call.function.arguments)
                        
                        # Call the tool
                        tool_result = await self._handle_tool_call(
                            tool_name=tool_call.function.name,
                            tool_args=tool_args,
                            config=config
                        )
                        
                        # Format the result
                        formatted_result = ResultFormatter.format_tool_result(tool_result)
                        
                        # Add the tool response to the conversation
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_call.function.name,
                            "content": formatted_result
                        })
                    
                    # Continue the conversation
                    continue
                else:
                    # No tool calls, we have a final answer
                    return assistant_message.content or "I couldn't generate a response."
            
            except Exception as e:
                # Handle any errors
                return f"Error processing your request: {str(e)}"
        
        # If we hit the max turns, return a failure message
        return "I'm sorry, I wasn't able to complete your request within the allowed number of turns."
    
    async def _handle_tool_call(self, tool_name: str, tool_args: Dict[str, Any], config: ServiceConfig) -> Union[LocationResults, EnvResult, LocationError]:
        """Handle a tool call from the model."""
        if tool_name == "find_places":
            return await self.places_service.find_places(
                latitude=tool_args.get("latitude"),
                longitude=tool_args.get("longitude"),
                place_type=tool_args.get("place_type"),
                radius=tool_args.get("radius"),
                keyword=tool_args.get("keyword"),
                config=config
            )
        elif tool_name == "analyze_location_suitability":
            # This would normally return a MultiLocationResults, but we'll just pass the query to the analyzer
            result = await self.land_analyzer.analyze_location(
                latitude=tool_args.get("latitude"),
                longitude=tool_args.get("longitude"),
                user_query="Can I buy land here?",
                radius=tool_args.get("radius"),
                config=config
            )
            # Convert the string result to LocationResults
            return LocationResults(
                places=[],
                total_found=1,
                search_term="land_analysis"
            )
        elif tool_name == "analyze_business_viability":
            # Get the business type from the args or use a default
            business_type = tool_args.get("business_type", "business")
            
            # Call the business analyzer
            result = await self.business_analyzer.analyze_location(
                latitude=tool_args.get("latitude"),
                longitude=tool_args.get("longitude"),
                user_query=f"Can I start a {business_type} here?",
                radius=tool_args.get("radius"),
                config=config,
                business_type=business_type
            )
            # Convert the string result to LocationResults
            return LocationResults(
                places=[],
                total_found=1,
                search_term=f"{business_type}_viability"
            )
        elif tool_name == "get_environmental_data":
            return await self.env_service.get_environmental_data(
                latitude=tool_args.get("latitude"),
                longitude=tool_args.get("longitude"),
                data_type=tool_args.get("data_type", "both"),
                config=config
            )
        else:
            return LocationError(f"Unknown tool: {tool_name}")