import requests

# Module Imports
from services.pi_system.base import PISystem

# Core Imports
from core.logger import logger
from core.models import UserResponse

class Elements:
    """
    Handles PI Server 'Element' endpoints.

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
        endpoint: str = "elements"
    ):
        """
        Retrieves an element using a web_id
        """
        if not web_id:
            logger.error("No web_id provided", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=400)
        
        response = self.pi_system.send_request(
            method="GET", 
            endpoint=f"{endpoint}/{web_id}", 
            params=params
        )

        if not response:
            logger.error(f"Failed to retrieve element using {web_id}", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=500)

        return UserResponse.success(message=f"Successfully accessed the element: {web_id}", response=response.json(), code=response.status_code)

    def get_by_path(
        self,
        path: str,
        endpoint: str = "elements",
        selected_fields: str = "Items.WebId;Items.Id;Items.Name;Items.Description;Items.Path;Items.IsConnected;Items.ServerVersion;Items.ServerTime",
        web_id_type: str = "IDOnly",
        associations: str = "None"
    ):
        if not path:
            logger.error("No path provided", exc_info=False)
            return UserResponse.error(message="No path provided", code=400)
        
        params = {
            "path": f"\\\\{self.pi_system.pi_server}\\{path}",
            "selectedFields": selected_fields,
            "webIdType": web_id_type,
            "associations": associations
        }

        response = self.pi_system.send_request(
            method="GET", 
            endpoint=endpoint, 
            params=params
        )
        
        if not response:
            logger.error(f"Failed to retrieve element using path: {path}", exc_info=False)
            return UserResponse.error(message="Unexpected error occured. Please check logs.", code=500)

        return UserResponse.success(message="Successfully accessed the element by path", response=response.json(), code=response.status_code)

    def update(self):
        pass

    def delete(self):
        pass
