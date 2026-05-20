# Module Imports
from services.pi_system.base import PISystem
from core.logger import logger
from core.models import UserResponse


class ElementTemplates:
    """
    Handles PI Server 'ElementTemplate' endpoints.

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
        endpoint: str = "elementtemplates"
    ):
        """
        Retrieves an element template by WebId.
        """
        if not web_id:
            logger.error("No web_id provided", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=400)

        response = self.pi_system.send_request(
            method="GET",
            endpoint=f"{endpoint}/{web_id}"
        )

        if not response:
            logger.error(f"Failed to retrieve element template using {web_id}", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=500)

        return UserResponse.success(
            message=f"Successfully accessed the element template: {web_id}",
            response=response.json(),
            code=response.status_code
        )

    def get_by_path(
        self,
        path: str,
        endpoint: str = "elementtemplates",
        selected_fields: str = "Items.WebId;Items.Id;Items.Name;Items.Description;Items.Path;Items.IsConnected;Items.ServerVersion;Items.ServerTime",
        web_id_type: str = "IDOnly",
        associations: str = "None"
    ):
        """
        Retrieves an element template by its full AF path.
        """
        if not path:
            logger.error("No path provided", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=400)

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
            logger.error(f"Failed to retrieve element template using path: {path}", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=500)

        return UserResponse.success(
            message="Successfully accessed the element template by path",
            response=response.json(),
            code=response.status_code
        )

    def get_attribute_templates(
        self,
        web_id: str,
        show_inherited: bool = False,
        show_descendants: bool = False,
        endpoint: str = "elementtemplates"
    ):
        """
        Get all attribute templates defined on an element template.

        Docs: GET elementtemplates/{webId}/attributetemplates
        - show_inherited=True includes attribute templates from base/parent templates.
        - show_descendants=True includes nested child attribute templates, not just
          the immediate children of the template.
        - Returns DataReferencePlugIn and ConfigString per attribute template, so you
          can confirm what data reference is expected before inspecting live elements.
          For example, checking that VA_Mag is defined as "PI Point" on the Unit
          template before verifying individual Unit element attributes.
        """
        if not web_id:
            logger.error("No web_id provided", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=400)

        params = {
            "showInherited": str(show_inherited).lower(),
            "showDescendants": str(show_descendants).lower(),
            "maxCount": 1000,
            "selectedFields": (
                "Items.WebId;Items.Name;Items.Description;Items.Path;"
                "Items.Type;Items.DefaultUnitsName;Items.DataReferencePlugIn;"
                "Items.ConfigString;Items.IsConfigurationItem;Items.HasChildren;"
                "Items.CategoryNames;Items.DefaultValue"
            )
        }

        response = self.pi_system.send_request(
            method="GET",
            endpoint=f"{endpoint}/{web_id}/attributetemplates",
            params=params
        )

        if not response:
            logger.error(f"Failed to retrieve attribute templates for element template {web_id}", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=500)

        return UserResponse.success(
            message=f"Successfully retrieved attribute templates for element template: {web_id}",
            response=response.json(),
            code=response.status_code
        )

    def get_analysis_templates(
        self,
        web_id: str,
        endpoint: str = "elementtemplates"
    ):
        """
        Get all analysis templates attached to an element template.

        Docs: GET elementtemplates/{webId}/analysistemplates
        - Returns the analysis rule plugin (e.g. PerformanceEquation), time rule
          plugin, and whether CreateEnabled is true — meaning new elements based
          on this template will automatically get this analysis created.
        - Use this alongside get_element_analyses to cross-check: the template
          defines what analyses should exist; get_element_analyses confirms whether
          they actually do on a live element.
        """
        if not web_id:
            logger.error("No web_id provided", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=400)

        params = {
            "selectedFields": (
                "Items.WebId;Items.Name;Items.Description;Items.Path;"
                "Items.AnalysisRulePlugInName;Items.TimeRulePlugInName;"
                "Items.CreateEnabled;Items.HasTarget;Items.TargetName;"
                "Items.CategoryNames;Items.HasNotificationTemplate"
            )
        }

        response = self.pi_system.send_request(
            method="GET",
            endpoint=f"{endpoint}/{web_id}/analysistemplates",
            params=params
        )

        if not response:
            logger.error(f"Failed to retrieve analysis templates for element template {web_id}", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=500)

        return UserResponse.success(
            message=f"Successfully retrieved analysis templates for element template: {web_id}",
            response=response.json(),
            code=response.status_code
        )

    def update(self):
        pass

    def delete(self):
        pass