# System Imports
from datetime import datetime, timezone

# Module Imports
from core.logger import logger
from services.pi_system.base import PISystem
from core.models import UserResponse

class Streams:
    """
    Handles PI Server 'Streams' endpoints.

    For docs see the following:
    - https://docs.aveva.com/bundle/pi-web-api-reference/page/help/controllers

    TODO: Add sessions.
    """

    def __init__(
        self, 
        pi_system: PISystem
    ):
        self.pi_system = pi_system

    def get_value(
        self, 
        web_id: str, 
        endpoint: str = "streams"
    ):
        """
        Returns the latest value of the stream.
        """
        if not web_id:
            logger.error(f"Invalid WebId: {web_id}", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=400)

        response = self.pi_system.send_request("GET", f"{endpoint}/{web_id}/value")
        
        if not response:
            logger.error("Failed to send request to PI Server.", exc_info=False)
            return UserResponse.error(message="Failed to send request to PI Server.", code=500)

        return UserResponse.success(message="Successfully accessed the stream value", response=response.json(), code=response.status_code)

    def update_value(
        self, 
        web_id: str, 
        value: any, 
        endpoint: str = "streams"
    ):
        """
        Updates a value for the specified stream.
        """
        if not web_id:
            logger.error(f"Invalid WebId: {web_id}", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=400)

        payload = {
            "Value": value,
        }

        response = self.pi_system.send_request("POST", f"{endpoint}/{web_id}/value", data=payload)

        if not response:
            logger.error("Failed to send request to PI Server.", exc_info=False)
            return UserResponse.error(message="Failed to send request to PI Server.", code=500)

        if response.status_code == 400:
            logger.error("Malformed request. Please check your parameters.", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=response.status_code)
        if response.status_code == 409:
            logger.error("Operation not supported or incompatible units.", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=response.status_code)

        return UserResponse.success(message="Successfully updated the value to PI Server.", code=response.status_code)
