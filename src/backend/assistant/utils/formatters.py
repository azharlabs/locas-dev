from typing import Dict, Any, Union

from models import LocationResults, EnvResult, LocationError, MultiLocationResults

class ResultFormatter:
    """Formatters for converting results to human-readable text."""
    
    @staticmethod
    def format_tool_result(result: Union[LocationResults, EnvResult, LocationError, MultiLocationResults]) -> str:
        """
        Format any result type to a human-readable string.
        
        Args:
            result: The result to format
            
        Returns:
            Formatted string representation
        """
        if isinstance(result, LocationResults):
            return ResultFormatter.format_location_results(result)
        elif isinstance(result, MultiLocationResults):
            return ResultFormatter.format_multi_location_results(result)
        elif isinstance(result, EnvResult):
            return result.message
        elif isinstance(result, LocationError):
            return f"Error: {result.error_message}"
        else:
            return f"Unexpected result type: {type(result)}"
    
    @staticmethod
    def format_location_results(result: LocationResults) -> str:
        """Format location results into a readable string."""
        places_text = "\n".join([
            f"- {place.name}: {place.address}" + 
            (f" (Rating: {place.rating}/5)" if place.rating else "") 
            for place in result.places
        ])
        return f"Found {result.total_found} {result.search_term}:\n{places_text}"
    
    @staticmethod
    def format_multi_location_results(result: MultiLocationResults) -> str:
        """Format multi-location results into a readable string."""
        parts = [f"Analysis results for location (Lat: {result.location.get('latitude')}, Lng: {result.location.get('longitude')}):\n"]
        
        for category, loc_result in result.category_results.items():
            if category == "environmental_message":
                # Skip this as it's not a LocationResults object
                continue
                
            if category == "environmental" and "environmental_message" in result.category_results:
                # Use the pre-formatted environmental message
                parts.append(f"\nEnvironmental Data:\n{result.category_results['environmental_message']}")
                continue
            
            # Format this category's results
            if loc_result.total_found > 0:
                category_name = category.replace('_', ' ').title()
                parts.append(f"\n{category_name} ({loc_result.total_found}):")
                
                # Add top 3 places in this category
                places = loc_result.places[:3]
                for place in places:
                    place_info = f"- {place.name}: {place.address}"
                    if place.rating:
                        place_info += f" (Rating: {place.rating}/5)"
                    parts.append(place_info)
                
                if loc_result.total_found > 3:
                    parts.append(f"  ...and {loc_result.total_found - 3} more")
        
        return "\n".join(parts)