# Module Imports
from services.pi_system.base import PISystem
from core.logger import logger
from core.models import UserResponse

class StreamSet(PISystem):
    """
    Handles PI Server 'Streamset' endpoints.
    
    For docs see the following: 
    - https://docs.aveva.com/bundle/pi-web-api-reference/page/help/controllers

    TODO: Add sessions.
    """

    def __init__(self, pi_system):
        self.pi_system = pi_system

    def get_channel(
        self, 
        web_id: str, 
        params: str = None
    ):
        """
        Opens a channel that will send messages about any value changes 
        for the attributes of an Element, Event Frame, or Attribute.
        """
        url = f"{self.pi_system.base_url}/streamsets/{web_id}/channel"
        response = requests.get(url, params=params, auth=self.pi_system.auth, stream=True)
        
        if not response:
            logger.error("Failed to send request to PI Server.", exc_info=False)
            return UserResponse.error(message="Failed to send request to PI Server.")
        
        return UserResponse.success(message="Successfully opened a channel.", code=response.status_code, response=response)
    
    def get_value(self):
        pass
    
    def get_values(self):
        pass