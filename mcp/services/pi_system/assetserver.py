# Module Imports
import requests
from services.pi_system.base import PISystem
from core.logger import logger
from core.models import UserResponse

class AssetServer:
    """
    Handles PI Server 'AssetServer' endpoints.
    
    For docs see the following: 
    - https://docs.aveva.com/bundle/pi-web-api-reference/page/help/controllers

    TODO: Add sessions.
    """

    def __init__(
        self, 
        pi_system: PISystem
    ):
        self.pi_system = pi_system

    def lists(
        self, 
        endpoint: str = "assetservers",
    ) -> dict:
        """
        Retrieve a list of all Asset Servers known to this service.
        """
        response = self.pi_system.send_request(
            method="GET", 
            endpoint=endpoint, 
        )

        if not response:
            logger.error("Failed to retrieve asset server list.", exc_info=False)
            return

        return response.json()

    def get(
        self, 
        web_id: str, 
        endpoint: str = "assetservers",
    ) -> dict:
        """
        Retrieve a Asset Server.
        """
        if not web_id:
            logger.error(f"Invalid WebId: {web_id}", exc_info=False)
            return {}

        response = self.pi_system.send_request(
            method="GET", 
            endpoint=f"{endpoint}/{web_id}",
        )

        if not response:
            logger.error(f"Failed to retrieve asset server using {web_id}", exc_info=False)
            return

        return response.json()
    
    def get_by_path(self):
        pass