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
        Retrieves an element by WebId.
        """
        if not web_id:
            logger.error("No web_id provided", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=400)

        response = self.pi_system.send_request(
            method="GET",
            endpoint=f"{endpoint}/{web_id}"
        )

        if not response:
            logger.error(f"Failed to retrieve element using {web_id}", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=500)

        return UserResponse.success(
            message=f"Successfully accessed the element: {web_id}",
            response=response.json(),
            code=response.status_code
        )

    def get_by_path(
        self,
        path: str,
        endpoint: str = "elements",
        selected_fields: str = "Items.WebId;Items.Id;Items.Name;Items.Description;Items.Path;Items.IsConnected;Items.ServerVersion;Items.ServerTime",
        web_id_type: str = "IDOnly",
        associations: str = "None"
    ):
        """
        Retrieves an element by its full AF path.
        """
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
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=500)

        return UserResponse.success(
            message="Successfully accessed the element by path",
            response=response.json(),
            code=response.status_code
        )

    def get_attributes(
        self,
        web_id: str,
        name_filter: str = None,
        search_full_hierarchy: bool = False,
        show_excluded: bool = False,
        show_hidden: bool = False,
        associations: str = "DataReference",
        endpoint: str = "elements"
    ):
        """
        Retrieve all attributes of the specified element.

        Docs: GET elements/{webId}/attributes
        - associations="DataReference" returns the data reference plugin info
          alongside each attribute, which is required to check whether an
          attribute is linked to a PI Point or is a derived/config item.
        """
        if not web_id:
            logger.error("No web_id provided", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=400)

        params = {
            "searchFullHierarchy": str(search_full_hierarchy).lower(),
            "showExcluded": str(show_excluded).lower(),
            "showHidden": str(show_hidden).lower(),
            "sortField": "Name",
            "sortOrder": "Ascending",
            "maxCount": 1000,
            "associations": associations,
            "selectedFields": (
                "Items.WebId;Items.Name;Items.Description;Items.Path;"
                "Items.Type;Items.DefaultUnitsName;Items.DataReferencePlugIn;"
                "Items.ConfigString;Items.IsConfigurationItem;Items.HasChildren;"
                "Items.CategoryNames"
            )
        }

        if name_filter:
            params["nameFilter"] = name_filter

        response = self.pi_system.send_request(
            method="GET",
            endpoint=f"{endpoint}/{web_id}/attributes",
            params=params
        )

        if not response:
            logger.error(f"Failed to retrieve attributes for element {web_id}", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=500)

        return UserResponse.success(
            message=f"Successfully retrieved attributes for element: {web_id}",
            response=response.json(),
            code=response.status_code
        )

    def get_child_elements(
        self,
        web_id: str,
        template_name: str = None,
        search_full_hierarchy: bool = False,
        endpoint: str = "elements"
    ):
        """
        Retrieve child elements of the specified element.

        Docs: GET elements/{webId}/elements
        - Defaults to immediate children only (searchFullHierarchy=false).
        - Pass template_name to filter by a specific element template
          e.g. "Unit" to list only Unit elements under a PowerPlant.
        """
        if not web_id:
            logger.error("No web_id provided", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=400)

        params = {
            "searchFullHierarchy": str(search_full_hierarchy).lower(),
            "sortField": "Name",
            "sortOrder": "Ascending",
            "maxCount": 1000,
            "selectedFields": (
                "Items.WebId;Items.Name;Items.Description;Items.Path;"
                "Items.TemplateName;Items.HasChildren;Items.CategoryNames"
            )
        }

        if template_name:
            params["templateName"] = template_name

        response = self.pi_system.send_request(
            method="GET",
            endpoint=f"{endpoint}/{web_id}/elements",
            params=params
        )

        if not response:
            logger.error(f"Failed to retrieve child elements for element {web_id}", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=500)

        return UserResponse.success(
            message=f"Successfully retrieved child elements for element: {web_id}",
            response=response.json(),
            code=response.status_code
        )

    def get_analyses(
        self,
        web_id: str,
        endpoint: str = "elements"
    ):
        """
        Retrieve all analyses targeting the specified element.

        Docs: GET elements/{webId}/analyses
        - Returns analysis name, status (Enabled/Disabled), rule plugin
          (e.g. PerformanceEquation), time rule plugin, and template linkage.
        - Use this to verify that VC_Mag and VC_Phase analyses exist and are
          enabled before reading derived attribute values via get_stream_value.
        """
        if not web_id:
            logger.error("No web_id provided", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=400)

        params = {
            "sortField": "Name",
            "sortOrder": "Ascending",
            "maxCount": 1000,
            "selectedFields": (
                "Items.WebId;Items.Name;Items.Description;Items.Path;"
                "Items.Status;Items.AnalysisRulePlugInName;Items.TimeRulePlugInName;"
                "Items.IsConfigured;Items.HasTemplate;Items.TemplateName;"
                "Items.Priority;Items.PublishResults;Items.CategoryNames"
            )
        }

        response = self.pi_system.send_request(
            method="GET",
            endpoint=f"{endpoint}/{web_id}/analyses",
            params=params
        )

        if not response:
            logger.error(f"Failed to retrieve analyses for element {web_id}", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=500)

        return UserResponse.success(
            message=f"Successfully retrieved analyses for element: {web_id}",
            response=response.json(),
            code=response.status_code
        )

    def update(self):
        pass

    def delete(self):
        pass