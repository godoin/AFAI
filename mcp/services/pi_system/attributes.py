# System Imports
from datetime import datetime, timezone
import requests

# Module Imports
from services.pi_system.base import PISystem
from core.logger import logger
from core.models import UserResponse

class Attributes:
    """
    Handles PI Server 'Attributes' endpoints.
    
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
        endpoint: str = "attributes"
    ):
        """
        Retrieve an attribute.
        """
        if not web_id:
            logger.error(f"Invalid WebId: {web_id}", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=400)
        
        response = self.pi_system.send_request(
            method="GET", 
            endpoint=f"{endpoint}/{web_id}"
        )

        if not response:
            logger.error(f"Failed to retrieve attribute data using {web_id}", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=500)

        return UserResponse.success(message=f"Successfully accessed the web id: {web_id}", response=response.json(), code=response.status_code)
    
    def get_by_path(
        self,
        path: str,
        selected_fields: str = "Items.WebId;Items.Id;Items.Name;Items.Description;Items.Path",
        web_id_type: str = "",
        associations: str = "",
        endpoint: str = "attributes",
    ):
        if not path:
            logger.error("No path provided", exc_info=False)
            return UserResponse.error(message="No path provided", code=400)
        
        params = {
            "selectedFields": selected_fields,
            "webIdType": web_id_type,
            "associations": associations
        }
        
        response = self.pi_system.send_request(
            method="GET", 
            endpoint=endpoint,
            path=path, 
            params=params
        )
        
        if not response:
            logger.error(f"Failed to retrieve attributes using path: {path}", exc_info=False)
            return UserResponse.error(message="Unexpected error occured. Please check logs.", code=500)

        return UserResponse.success(message="Successfully accessed the attributes by path", response=response.json(), code=response.status_code)
    
    def set_value(
        self,
        web_id: str,
        value: any,
        endpoint: str = "attributes"
    ):
        """
        Set the value of a configuration item attribute. 
        
        For attributes with a data reference or non-configuration item attributes, consult the documentation for streams.
        """
        if not web_id:
            logger.error(f"Invalid WebId: {web_id}", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=50)

        payload = {
            "Value": value,
        }
        
        response = self.pi_system.send_request(
            method="PUT", 
            endpoint=f"{endpoint}/{web_id}/value", 
            data=payload
        )
        
        # logger.info(f"PI Attr Code: {response.status_code}")
        
        if not response:
            logger.error("Failed to send request to PI Server.", exc_info=False)
            return UserResponse.error(message="Failed to send request to PI Server.", code=500)

        if response.status_code == 400:
            logger.error("Malformed request. Please check your parameters.", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=response.status_code)

        if response.status_code == 409:
            logger.error("Operation not supported or incompatible units.", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=response.status_code)
        
        return UserResponse.success(message="Successfully updated the attribute value to PI Server.", code=response.status_code)

    def delete(self):
        pass