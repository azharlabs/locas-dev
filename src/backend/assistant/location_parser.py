import re
from typing import Dict, Optional, Tuple
import googlemaps
from geopy.geocoders import Nominatim

class LocationParser:
    """Parser for extracting location information from user queries."""
    
    def __init__(self, google_maps_api_key: str):
        """
        Initialize the location parser.
        
        Args:
            google_maps_api_key: Google Maps API key for geocoding
        """
        self.google_maps_api_key = google_maps_api_key
        self.gmaps = None
        self.geolocator = None
        
        # Initialize geocoding clients if API key is provided
        if google_maps_api_key and google_maps_api_key != "your_api_key":
            self.gmaps = googlemaps.Client(key=google_maps_api_key)
        
        # Nominatim as fallback geocoder
        self.geolocator = Nominatim(user_agent="location_assistant")
    
    def parse_query(self, user_query: str) -> Tuple[str, Optional[Dict[str, float]]]:
        """
        Parse the user query to extract the actual query and location coordinates.
        
        Args:
            user_query: The full user query which may include location information
            
        Returns:
            Tuple containing (clean_query, coordinates_dict)
            - clean_query: User query with location information removed
            - coordinates_dict: Dictionary with 'lat' and 'lng' keys, or None if no location found
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Parsing query: {user_query}")
        
        # Check for Google Maps URL patterns
        url_pattern = r'(https?://(?:www\.)?google\.com/maps[^\s]+)'
        url_match = re.search(url_pattern, user_query)
        
        coordinates = None
        clean_query = user_query
        
        if url_match:
            # Extract URL and get coordinates
            maps_url = url_match.group(1)
            logger.info(f"Found Google Maps URL: {maps_url}")
            coordinates = self.extract_coordinates_from_maps_url(maps_url)
            
            # Remove the URL from the query
            clean_query = user_query.replace(maps_url, "").strip()
        else:
            # Look for coordinate patterns like "lat, lng" or full addresses
            # This is a simple regex to detect coordinate patterns
            coord_pattern = r'(-?\d+\.\d+),\s*(-?\d+\.\d+)'
            coord_matches = list(re.finditer(coord_pattern, user_query))
            
            if coord_matches:
                # Use the last match if there are multiple (most likely to be coordinates)
                match = coord_matches[-1]
                lat = float(match.group(1))
                lng = float(match.group(2))
                
                logger.info(f"Found coordinate pattern: {lat}, {lng}")
                
                # Verify the coordinates are in valid range
                if abs(lat) <= 90 and abs(lng) <= 180:
                    coordinates = {'lat': lat, 'lng': lng}
                    logger.info(f"Valid coordinates: {coordinates}")
                    
                    # Remove the coordinates from the query
                    clean_query = user_query[:match.start()] + user_query[match.end():].strip()
                else:
                    logger.warning(f"Invalid coordinates: {lat}, {lng} - outside valid range")
            else:
                # Try to extract location from the query as an address
                logger.info("No coordinates found, trying to extract address")
                address_candidates = self.extract_potential_addresses(user_query)
                logger.info(f"Address candidates: {address_candidates}")
                
                for address in address_candidates:
                    coordinates = self.extract_coordinates_from_search(address)
                    if coordinates:
                        logger.info(f"Found coordinates for address '{address}': {coordinates}")
                        # Remove the address from the query
                        clean_query = user_query.replace(address, "").strip()
                        break
        
        if coordinates:
            logger.info(f"Extracted coordinates: {coordinates}")
        else:
            logger.warning("No coordinates could be extracted from query")
            
        return clean_query, coordinates
    
    def extract_coordinates_from_maps_url(self, url: str) -> Optional[Dict[str, float]]:
        """
        Extract coordinates from a Google Maps URL
        
        Args:
            url: Google Maps URL
            
        Returns:
            Dictionary with lat, lng keys or None if extraction failed
        """
        try:
            # Pattern 1: URLs with @lat,lng format
            pattern_at = r'@(-?\d+\.\d+),(-?\d+\.\d+)'
            match_at = re.search(pattern_at, url)
            
            if match_at:
                return {
                    'lat': float(match_at.group(1)),
                    'lng': float(match_at.group(2))
                }
            
            # Pattern 2: URLs with ?q=lat,lng format
            pattern_query = r'[?&]q=(-?\d+\.\d+),(-?\d+\.\d+)'
            match_query = re.search(pattern_query, url)
            
            if match_query:
                return {
                    'lat': float(match_query.group(1)),
                    'lng': float(match_query.group(2))
                }
            
            # Pattern 3: URLs with ll=lat,lng format
            pattern_ll = r'[?&]ll=(-?\d+\.\d+),(-?\d+\.\d+)'
            match_ll = re.search(pattern_ll, url)
            
            if match_ll:
                return {
                    'lat': float(match_ll.group(1)),
                    'lng': float(match_ll.group(2))
                }
            
            # If no patterns matched but it's a valid Google Maps URL, 
            # we could use the Google Maps API to resolve the URL
            # This would require extra API calls and possibly additional permissions
            
            return None
        except Exception as e:
            print(f"Error extracting coordinates from URL: {e}")
            return None
    
    def extract_coordinates_from_search(self, search_text: str) -> Optional[Dict[str, float]]:
        """
        Extract coordinates from a search text (address or direct coordinates)
        
        Args:
            search_text: Address or coordinates string
            
        Returns:
            Dictionary with lat, lng keys or None if extraction failed
        """
        try:
            # Try to parse as direct coordinates first
            coord_pattern = r'^(-?\d+\.?\d*),\s*(-?\d+\.?\d*)$'
            match = re.search(coord_pattern, search_text.strip())
            
            if match:
                return {
                    'lat': float(match.group(1)),
                    'lng': float(match.group(2))
                }
            
            # Use geocoding to convert address to coordinates
            if self.gmaps:
                # Try Google Maps geocoding first
                geocode_result = self.gmaps.geocode(search_text)
                if geocode_result and len(geocode_result) > 0:
                    location = geocode_result[0]['geometry']['location']
                    return {
                        'lat': location['lat'],
                        'lng': location['lng']
                    }
            
            # Fallback to Nominatim geocoding
            if self.geolocator:
                location = self.geolocator.geocode(search_text)
                if location:
                    return {
                        'lat': location.latitude,
                        'lng': location.longitude
                    }
            
            return None
        except Exception as e:
            print(f"Error extracting coordinates from search: {e}")
            return None
    
    def extract_potential_addresses(self, text: str) -> list:
        """
        Extract potential addresses from text.
        This is a simplified implementation - a more robust solution would use NER.
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of potential address strings
        """
        # Simple approach: look for common address patterns
        # In a real implementation, you might use a more sophisticated NLP approach
        
        # Split by common separators
        parts = re.split(r'[,;]|\bat\b|\bin\b|\bnear\b', text)
        
        # Filter out very short parts
        candidates = [part.strip() for part in parts if len(part.strip()) > 10]
        
        # Add the full text as a fallback candidate
        if text.strip() not in candidates:
            candidates.append(text.strip())
        
        return candidates