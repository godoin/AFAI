# Module Imports
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
        Retrieves a PI point by tag name.

        Note: tag_name is passed as the path segment here, not a WebId.
        Use get_by_path if you have a full \\PIServer\\TagName path.
        Use search if you need to find tags by pattern.
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

        return UserResponse.success(
            message=f"Successfully accessed the tag: {tag_name}",
            response=response.json(),
            code=response.status_code
        )

    def get_by_path(
        self,
        path: str,
        endpoint: str = "points"
    ):
        """
        Retrieves a PI point by its full PI path.

        Docs: GET points?path=\\PIServer\\TagName
        - Use this when you have a full PI path from a tag list or a prior
          tool response, rather than a WebId.
        - Returns WebId, PointType, EngineeringUnits, Descriptor, and Span/Zero
          — same shape as get(), useful for confirming a tag's properties before
          linking it to an AF attribute.
        - Per the docs: prefer WebId lookups (get()) when the WebId is already
          known. Use this only when path is all you have.

        Expected path format: \\\\PI-SYSTEM\\TagName
        e.g. \\\\PI-SYSTEM\\Cebu_PlantA_Unit1_VA_Mag
        """
        if not path:
            logger.error("No path provided", exc_info=False)
            return UserResponse.error(message="No path provided.", code=400)

        params = {
            "path": path,
            "selectedFields": (
                "WebId;Id;Name;Path;Descriptor;PointClass;"
                "PointType;EngineeringUnits;Step;Future;Span;Zero;DisplayDigits"
            )
        }

        response = self.pi_system.send_request(
            method="GET",
            endpoint=endpoint,
            params=params
        )

        if not response:
            logger.error(f"Failed to retrieve point using path: {path}", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=500)

        return UserResponse.success(
            message=f"Successfully retrieved point by path: {path}",
            response=response.json(),
            code=response.status_code
        )

    def get_attributes(
        self,
        web_id: str,
        name_filter: str = None,
        endpoint: str = "points"
    ):
        """
        Get the attributes (properties) of a PI point by WebId.

        Docs: GET points/{webId}/attributes
        - Returns low-level tag properties such as pointtype, engunits,
          typicalvalue, descriptor, compdev, compmax, excdev, scan, etc.
        - name_filter lets you narrow to specific attributes e.g. "engunits"
          or "pointtype" without pulling everything.
        - Use this to verify tag configuration matches what the tag list specifies
          before linking the tag to an AF attribute via set_attribute_value.

        Common attribute names to check:
          pointtype   — Float32, Int32, String, Digital, Timestamp
          engunits    — engineering units string (e.g. "V", "bar", "A")
          descriptor  — human-readable tag description
          typicalvalue — expected mid-range value for the tag
        """
        if not web_id:
            logger.error("No web_id provided", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=400)

        params = {
            "selectedFields": "Items.Name;Items.Value"
        }

        if name_filter:
            params["nameFilter"] = name_filter

        response = self.pi_system.send_request(
            method="GET",
            endpoint=f"{endpoint}/{web_id}/attributes",
            params=params
        )

        if not response:
            logger.error(f"Failed to retrieve attributes for point {web_id}", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=500)

        return UserResponse.success(
            message=f"Successfully retrieved attributes for point: {web_id}",
            response=response.json(),
            code=response.status_code
        )

    def search(
        self,
        query: str,
        data_server_web_id: str = None,
        max_count: int = 100,
        endpoint: str = "points"
    ):
        """
        Search for PI points by query string.

        Docs: GET points/search
        - query follows PI Point Query syntax. Common patterns:
            "Tag:=Cebu_*"              — all tags starting with Cebu_
            "Tag:=*_VA_Mag"            — all VA_Mag tags across all locations
            "Tag:=Cebu_PlantA_Unit1_*" — all tags for a specific unit
            "Tag:=*_Unit1_*"           — all Unit1 tags across all plants
        - data_server_web_id scopes the search to a specific PI Data Archive.
          If omitted, searches across all known data servers.
        - max_count caps results — default 100, API max is 1000.
        - Use this during bulk tag verification to confirm which proposed tags
          from the tag list already exist before attempting data ref assignment.
        """
        if not query:
            logger.error("No query provided for point search", exc_info=False)
            return UserResponse.error(message="No query provided.", code=400)

        params = {
            "query": query,
            "maxCount": min(max_count, 1000),
            "selectedFields": (
                "Items.WebId;Items.Name;Items.Path;Items.Descriptor;"
                "Items.PointType;Items.EngineeringUnits;Items.Step"
            )
        }

        if data_server_web_id:
            params["dataServerWebId"] = data_server_web_id

        response = self.pi_system.send_request(
            method="GET",
            endpoint=f"{endpoint}/search",
            params=params
        )

        if not response:
            logger.error(f"Failed to search points using query: {query}", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=500)

        return UserResponse.success(
            message=f"Successfully searched points with query: {query}",
            response=response.json(),
            code=response.status_code
        )

    def update(self):
        pass

    def delete(self):
        pass