import json
from openai import AsyncOpenAI
from typing import Dict, Any, List, Optional

class OpenAIService:
    """Service for interacting with OpenAI API."""
    
    def __init__(self, api_key: str):
        """Initialize with API key."""
        self.client = AsyncOpenAI(api_key=api_key)
        
        self.formatter_system_prompt = """
        You are a helpful assistant that formats environmental data into clear, readable messages.
        Your job is to take structured data about air quality and pollen forecasts and present it
        in a way that's informative, well-organized, and easy for people to understand.
        
        - Make the information scannable with bullet points or sections
        - Highlight key information that would be important to people with allergies or sensitivity to air pollution
        - Use plain language that anyone can understand
        - If there are health recommendations, make them clear and actionable
        """
        
        self.land_analysis_system_prompt = """
        You are a real estate location analyst providing insights about locations.
        Your analysis should be detailed, balanced, and objective, focusing on both 
        advantages and potential concerns for land purchase decisions.
        """
        
        self.business_analysis_system_prompt = """
        You are a small business location analyst specializing in retail and food service businesses.
        You provide insights about locations for business opportunities, with 
        consideration for foot traffic, competition, and business viability.
        """
    
    async def format_environmental_data(self, raw_data: Dict[str, Any]) -> str:
        """Format raw environmental data into a human-readable message."""
        if not raw_data or (not raw_data.get('air_quality') and not raw_data.get('pollen_forecast')):
            return "No environmental data available for this location."
        
        # Format the prompt with the raw data
        prompt = f"""
        Please format the following environmental data into a human-readable message:
        
        {json.dumps(raw_data, indent=2)}
        
        The message should be clear, informative, and easy to understand.
        Highlight key information and use formatting like bullet points to make it scannable.
        If there are health recommendations, make them prominent.
        """
        
        try:
            # Use OpenAI to format the message
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": self.formatter_system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
        except Exception as e:
            # Fallback formatting if the OpenAI call fails
            message_parts = []
            
            if air_data := raw_data.get('air_quality'):
                for idx in air_data.get('indexes', []):
                    message_parts.append(f"Air Quality: {idx.get('category', 'Unknown')} ({idx.get('aqi', 'N/A')})")
                    break
            
            if pollen_data := raw_data.get('pollen_forecast'):
                daily_info = pollen_data.get('dailyInfo', [])
                if daily_info and daily_info[0].get('pollenTypeInfo'):
                    pollen_levels = []
                    for p_type in daily_info[0]['pollenTypeInfo']:
                        level = p_type.get('indexInfo', {}).get('category', 'Unknown')
                        pollen_levels.append(f"{p_type.get('displayName', 'Unknown')}: {level}")
                    
                    if pollen_levels:
                        message_parts.append(f"Pollen Levels: {', '.join(pollen_levels)}")
            
            if not message_parts:
                return "Environmental data available but could not be formatted."
            
            return " | ".join(message_parts)
            
    async def analyze_land_purchase(self, latitude: float, longitude: float, user_query: str, location_data: str) -> str:
        """
        Analyze location data for land purchase suitability.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            user_query: The original user query
            location_data: Formatted location data to analyze
            
        Returns:
            Analysis as a string
        """
        analysis_prompt = f"""
        A user at coordinates ({latitude}, {longitude}) is asking: "{user_query}"
        
        They want to know if this is a good place to buy land.
        
        Here is data about the surrounding area:
        
        {location_data}
        
        Please provide a detailed analysis of the suitability of this location for land purchase. Consider:
        1. Proximity to essential services (schools, hospitals, police)
        2. Access to amenities (shopping, restaurants, parks)
        3. Transportation options
        4. Environmental factors
        5. Overall neighborhood profile
        
        Highlight both advantages and potential concerns. Be balanced and objective.
        Conclude with a summary assessment of whether this location would be good for land purchase.
        """
        
        try:
            analysis_response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": self.land_analysis_system_prompt},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            return analysis_response.choices[0].message.content
        except Exception as e:
            return f"Error generating land purchase analysis: {str(e)}"
    
    async def analyze_business_viability(self, latitude: float, longitude: float, 
                                  user_query: str, location_data: str, 
                                  business_type: str = "tea stall") -> str:
        """
        Analyze location data for business viability.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            user_query: The original user query
            location_data: Formatted location data to analyze
            business_type: Type of business to analyze
            
        Returns:
            Analysis as a string
        """
        analysis_prompt = f"""
        A user at coordinates ({latitude}, {longitude}) is asking: "{user_query}"
        
        They want to know if this is a good place to open a {business_type}.
        
        Here is data about the surrounding area:
        
        {location_data}
        
        Please provide a detailed analysis of the viability of opening a {business_type} at this location. Consider:
        1. Foot traffic generators (schools, offices, transit stations, etc.)
        2. Existing competition (other similar businesses)
        3. Demographics of the area
        4. Environmental factors
        5. Business potential
        
        Highlight both advantages and potential challenges. Be balanced and objective.
        Conclude with a summary assessment of whether this location would be good for a {business_type} business.
        """
        
        try:
            analysis_response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": self.business_analysis_system_prompt},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            return analysis_response.choices[0].message.content
        except Exception as e:
            return f"Error generating business viability analysis: {str(e)}"