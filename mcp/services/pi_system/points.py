# Imports
from services.pi_system.base import PISystem
from core.logger import logger
from core.models import UserResponse

class Points:
    """
    Handles PI Server 'Points' endpoints.

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
        tag_name: str, 
        endpoint: str = "points"
    ):
        """
        Retrieves point data by tag name.
        """
        if not tag_name:
            logger.error("Failed to retrieve point data. No tag name provided.", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=400)

        response = self.pi_system.send_request(
            method="GET", 
            endpoint=f"{endpoint}/{tag_name}"
        )

        if not response:
            logger.error(f"Failed to retrieve point data using {tag_name}", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=500)

        return UserResponse.success(message=f"Successfully accessed the tag name: {tag_name}", response=response.json(), code=response.status_code)

    def get_by_path(self):
        pass

    def update(self):
        pass

    def delete(self):
        pass
