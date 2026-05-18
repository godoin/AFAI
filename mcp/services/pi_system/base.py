# System Imports
import requests
from urllib.parse import urlencode
from datetime import datetime, timezone

# Module Imports
from core.logger import logger
from core.models import UserResponse

class PISystem:
    """
    Base class for handling common PI System API operations.
    
    For docs see the following:
    - https://docs.aveva.com/bundle/pi-web-api-reference/page/help/controllers

    TODO: Add sessions.
    """

    def __init__(
        self, 
        base_url: str, 
        pi_server: str, 
        username: str, 
        password: str
    ):
        self.base_url = base_url
        self.pi_server = pi_server
        self.auth = (username, password)
        self.verify_cert = False
        self.headers = {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }

    def verify_connection(
        self
    ):
        try:
            response = requests.get(
                url=self.base_url,
                auth=self.auth,
                headers=self.headers,
                verify=self.verify_cert
            )
            response.raise_for_status()
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"PI connection request error: {e}", exc_info=False)
            return False

        except Exception as e:
            logger.error(f"Unexpected PI error: {e}", exc_info=False)
            return False

    def send_request(
        self, 
        method: str, 
        endpoint: str, 
        path: str = None,
        params: dict = None, 
        data: str = None
    ):
        """
        Handles HTTP requests for PI Server endpoints.
        """
        try:
            query_string = urlencode(params, safe=';') if params else ""

            if path:
                url = f"{self.base_url}/{endpoint}?path={path}"
            elif path and params:
                url = f"{self.base_url}/{endpoint}?path={path}" + (f"&{query_string}" if query_string else "")
            else:
                url = f"{self.base_url}/{endpoint}"

            # print(f"Request URL: {url}")
            
            response = requests.request(
                method=method, 
                url=url, 
                auth=self.auth, 
                headers=self.headers, 
                json=data, 
                verify=self.verify_cert
            )
            response.raise_for_status()
            
            return response
        except Exception as e:
            logger.error(f"Unexpected error occurred: {e}", exc_info=False)
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error in {method} request to {url}: {e}", exc_info=False)
            return

    def send_request_by_path(
        self, 
        method: str, 
        path: str, 
        data: str = None
    ):
        """
        Sends a request using a full PI path without requiring an endpoint.
        """
        try:
            # print(f"Full Path Request URL: {path}")
            
            response = requests.request(
                method=method,
                url=path,
                auth=self.auth,
                headers=self.headers,
                json=data,
                verify=self.verify_cert
            )
            response.raise_for_status()

            return response.json() 
        except Exception as e:
            logger.error(f"Unexpected error occurred: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error in {method} request to {url}: {e}", exc_info=False)
            return

    def send_batch_request(
        self, 
        batch_request: dict
    ):
        """
        Handles batch request for PI Server endpoints.
        """
        try:
            url = f"{self.base_url}/batch"
            response = requests.post(
                url, 
                json=batch_request, 
                auth=self.auth, 
                headers=self.headers, 
                verify=self.verify_cert
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Unexpected error occurred: {e}", exc_info=False)
            return
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error in occurred: {e}", exc_info=False)
            return
    
    def batch_by_elements(
        self, 
        database_path: str,
        template_name: str
    ):
        try:
            # print(f"Database Resource URL: {self.base_url}/assetdatabases?path=\\\\{self.pi_server}\{database_path}&selectedFields=WebId;Path;Links")

            batch_request = {
                "database": {
                    "Method": "GET",
                    "Resource": f"{self.base_url}/assetdatabases?path={database_path}&selectedFields=WebId;Path;Links"
                },

                "elements": {
                    "Method": "GET",
                    "Resource": f"{{0}}?templateName={template_name}&searchFullHierarchy=true&selectedFields=Items.WebId;Items.Name;Items;Items.Links",
                    "ParentIds": ["database"],
                    "Parameters": ["$.database.Content.Links.Elements"]
                },
            }
            return self.send_batch_request(batch_request)
        except Exception as e:
            logger.error(f"Unexpected error occurred: {e}", exc_info=False)
            return

    def get_data_from_database(
        self, 
        database_path: str, 
        template_name: str
    ):
        """
        Get all elements based on a database path given a template name.
        """
        try:
            # print(f"Database Resource URL: {self.base_url}/assetdatabases?path=\\\\{self.pi_server}\{database_path}&selectedFields=WebId;Path;Links")
            
            batch_request = {
                "database": {
                    "Method": "GET",
                    "Resource": f"{self.base_url}/assetdatabases?path={database_path}&selectedFields=WebId;Path;Links"
                },
                "elements": {
                    "Method": "GET",
                    "Resource": f"{{0}}?templateName={template_name}&searchFullHierarchy=true&selectedFields=Items.WebId;Items.Name;Items;Items.Links",
                    "ParentIds": ["database"],
                    "Parameters": ["$.database.Content.Links.Elements"]
                },
                "attributes": {
                    "Method": "GET",
                    "RequestTemplate": {
                        "Resource": "{0}?searchFullHierarchy=true&selectedFields=Items.WebId;Items.Path"
                    },
                    "ParentIds": ["elements"],
                    "Parameters": ["$.elements.Content.Items[*].Links.Attributes"]
                }
            }
            return self.send_batch_request(batch_request)
        except Exception as e:
            logger.error(f"Unexpected error occurred: {e}", exc_info=False)
            return
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error in occurred: {e}", exc_info=False)
            return

    def get_all_elements(
        self, 
        database_path: str, 
    ):
        """
        Get all elements based on a database path given a template name.
        """
        try:
            # print(f"Database Resource URL: {self.base_url}/assetdatabases?path=\\\\{self.pi_server}\{database_path}&selectedFields=WebId;Path;Links")
            
            batch_request = {
                "database": {
                    "Method": "GET",
                    "Resource": f"{self.base_url}/assetdatabases?path={database_path}&selectedFields=WebId;Path;Links"
                },
                "locations": {
                    "Method": "GET",
                    "Resource": "{0}?templateName=" + "Location" + "&searchFullHierarchy=true&selectedFields=Items.WebId;Items.Name;Items.Description;Items.TemplateName;Items.Path;Items.HasChildren;Items.CategoryNames",
                    "ParentIds": ["database"],
                    "Parameters": ["$.database.Content.Links.Elements"]
                },
                "power_plants": {
                    "Method": "GET",
                    "Resource": "{0}?templateName=" + "PowerPlant" + "&searchFullHierarchy=true&selectedFields=Items.WebId;Items.Name;Items.Description;Items.TemplateName;Items.Path;Items.HasChildren;Items.CategoryNames",
                    "ParentIds": ["database"],
                    "Parameters": ["$.database.Content.Links.Elements"]
                },
                "units": {
                    "Method": "GET",
                    "Resource": "{0}?templateName=" + "Unit" + "&searchFullHierarchy=true&selectedFields=Items.WebId;Items.Name;Items.Description;Items.TemplateName;Items.Path;Items.HasChildren;Items.CategoryNames",
                    "ParentIds": ["database"],
                    "Parameters": ["$.database.Content.Links.Elements"]
                },
            }
            return self.send_batch_request(batch_request)
        except Exception as e:
            logger.error(f"Unexpected error occurred: {e}", exc_info=False)
            return
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error in occurred: {e}", exc_info=False)
            return
    
    def get_details(self):
        return (
            self.base_url,
            self.pi_server,
            self.auth
        ) 