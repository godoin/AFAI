# Module Imports
from services.pi_system.base import PISystem
from core.logger import logger
from core.models import UserResponse

class AssetDatabases:
    """
    Handles PI Server 'AssetDatabase' endpoints.
    
    For docs see the following: 
    - https://docs.aveva.com/bundle/pi-web-api-reference/page/help/controllers

    TODO: Add sessions.
    """

    def __init__(
        self, 
        pi_system: PISystem
    ):
        self.pi_system = pi_system

    def get(
        self, 
        web_id: str,
        endpoint: str = "assetdatabases",
    ):
        """
        Retrieves point data by tag name.
        """
        if not web_id:
            logger.error("No web_id provided", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=400)

        response = self.pi_system.send_request(
            method="GET", 
            endpoint=f"{endpoint}/{web_id}", 
        )

        if not response:
            logger.error(f"Failed to retrieve asset databases using {web_id}", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.",code=500)

        return UserResponse.success(message=f"Successfully accessed the asset databases: {web_id}", response=response.json(), code=response.status_code)
    
    def get_by_path(
        self,
        path: str,
        endpoint: str = "assetdatabases",
    ):
        if not path:
            logger.error("Failed to retrieve asset databases. No path provided.", exc_info=False)
            return UserResponse.error(message="No path provided", code=400)
        
        response = self.pi_system.send_request(
            method="GET",
            endpoint=endpoint,
            path=path
        )
        
        if not response:
            logger.error(f"Failed to retrieve asset databases using path: {path}", exc_info=False)
            return UserResponse.error(message="Unexpected error occured. Please check logs.", code=500)

        return UserResponse.success(message=f"Successfully accessed the asset database by {path}", response=response.json(), code=response.status_code)


    def get_elements(
        self,
        web_id: str, 
        endpoint: str = "assetdatabases",
        name_filter: str = None,
        description_filter: str = None,
        category_name: str = None,
        template_name: str = None,
        element_type: str = "Any",
        search_full_hierarchy: bool = False,
    ) -> dict:
        """
        Retrieve elements based on the specified conditions. By default, this method selects immediate children of the specified asset database.
        """
        if not web_id:
            logger.error("Failed to retrieve elements. Invalid WebId provided.", exc_info=False)
            return {}

        params = {
            "maxCount": 1000,
            "sortField": "Name",
            "sortOrder": "Ascending"
        }
        
        response = self.pi_system.send_request(
            method="GET",
            endpoint=f"{endpoint}/{web_id}/elements",
            params=params
        )
        
        if not response:
            logger.error(f"Failed to retrieve elements using {web_id}", exc_info=False)
            return {}

        return response.json()

    def update(self):
        pass

    def delete(self):
        pass
    
    def export(self):
        pass