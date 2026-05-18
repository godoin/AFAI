# Imports
import requests

# Core Imports
from core.logger import logger
from core.models import UserResponse

# Services Imports
from services.pi_system.base import PISystem


class DataServer:
    """
    Handles PI Server 'DataServer' endpoints.

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
        endpoint: str = "dataservers"
    ) -> dict:
        """
        Retrieve a list of Data Servers known to this service.
        """
        response = self.pi_system.send_request(
            method="GET", 
            endpoint=endpoint
        )

        if not response:
            logger.error("Failed to retrieve data server list.", exc_info=False)
            return {}

        return response.json()

    def get(
        self, 
        web_id: str, 
        endpoint: str = "dataservers"
    ) -> dict:
        """
        Retrieve a Data Server.
        """
        if not web_id:
            logger.error("Failed to retrieve data server. Invalid WebId provided.", exc_info=False)
            return {}

        response = self.pi_system.send_request(
            method="GET", 
            endpoint=f"{endpoint}/{web_id}"
        )

        return response.json()

    def get_by_path(
        self,
        path: str,
        endpoint: str = "dataservers"
    ):
        if not path:
            logger.error("Failed to retrieve data server. No path provided.", exc_info=False)
            return
        
        response = self.pi_system.send_request(
            method="GET", 
            endpoint=endpoint,
            path=path
        )

        if not response:
            logger.error(f"Failed to retrieve data server using path: {path}", exc_info=False)
            return

        return response.json()

    def get_points(
        self, 
        web_id: str, 
        endpoint = "dataservers",
    ) -> dict:
        """
        Retrieve a list of points from the specified Data Server.
        """
        if not web_id:
            logger.error("Invalid WebId provided.", exc_info=False)
            return {}
        
        response = self.pi_system.send_request(
            method="GET", 
            endpoint=f"{endpoint}/{web_id}/points", 
        )
    
        if not response:
                logger.error(f"Failed to retrieve points from data server using web_id: {web_id}", exc_info=False)
                return {}
            
        return response.json()

