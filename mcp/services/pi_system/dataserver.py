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
        Retrieve a Data Server by WebId.
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
        """
        Retrieve a Data Server by path.
        """
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
        endpoint: str = "dataservers"
    ) -> dict:
        """
        Retrieve a list of points from the specified Data Server.
        """
        if not web_id:
            logger.error("Invalid WebId provided.", exc_info=False)
            return {}

        response = self.pi_system.send_request(
            method="GET",
            endpoint=f"{endpoint}/{web_id}/points"
        )

        if not response:
            logger.error(f"Failed to retrieve points from data server using web_id: {web_id}", exc_info=False)
            return {}

        return response.json()

    def create_point(
        self,
        web_id: str,
        name: str,
        point_type: str,
        descriptor: str = "",
        engineering_units: str = "",
        point_class: str = "classic",
        step: bool = False,
        future: bool = False,
        display_digits: int = -5,
        endpoint: str = "dataservers"
    ):
        """
        Create a new PI point (tag) on the specified Data Server.

        Docs: POST dataservers/{webId}/points
        Returns 201 on success with a Location header pointing to the new point.

        GUARDRAILS — this method must only be called when ALL of the following
        are true:
          1. The BA has explicitly requested this tag be created in the
             current conversation turn.
          2. get_point or search_points has already confirmed the tag does NOT
             exist — never create a tag that already exists.
          3. The Proposed New Tagname has passed naming convention validation:
             no spaces, no special characters except underscore, follows
             Location_Plant_Unit_Attribute pattern, Location/Plant/Unit match
             AF element names exactly (case-sensitive).
          4. No more than one create_point call per conversation turn without
             BA confirmation in between (GUARDRAILS rule G4).

        Arguments:
            web_id          WebId of the Data Server (from list_data_servers)
            name            PI tag name — must pass naming convention validation
            point_type      Float32 | Float64 | Int16 | Int32 | String |
                            Digital | Timestamp
            descriptor      Human-readable description (maps to tag list
                            Description column)
            engineering_units  e.g. "V", "bar", "A", "spm" — must match
                            eng_units column from the tag list exactly
            point_class     Always "classic" unless BA specifies otherwise
            step            True for stepped (held) values; False for
                            interpolated. Default False.
            future          Allow future-dated values. Default False.
            display_digits  Decimal places for display. Default -5 (auto).
        """
        if not web_id:
            logger.error("No web_id provided for create_point.", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=400)

        if not name:
            logger.error("No tag name provided for create_point.", exc_info=False)
            return UserResponse.error(message="Tag name is required.", code=400)

        if not point_type:
            logger.error("No point_type provided for create_point.", exc_info=False)
            return UserResponse.error(message="Point type is required.", code=400)

        valid_point_types = {"Float32", "Float64", "Int16", "Int32", "String", "Digital", "Timestamp"}
        if point_type not in valid_point_types:
            logger.error(f"Invalid point_type '{point_type}'. Must be one of: {valid_point_types}", exc_info=False)
            return UserResponse.error(
                message=f"Invalid point type '{point_type}'. Must be one of: {', '.join(sorted(valid_point_types))}",
                code=400
            )

        payload = {
            "Name": name,
            "Descriptor": descriptor,
            "PointClass": point_class,
            "PointType": point_type,
            "EngineeringUnits": engineering_units,
            "Step": step,
            "Future": future,
            "DisplayDigits": display_digits
        }

        response = self.pi_system.send_request(
            method="POST",
            endpoint=f"{endpoint}/{web_id}/points",
            data=payload
        )

        if not response:
            logger.error(f"Failed to create point '{name}' on data server {web_id}.", exc_info=False)
            return UserResponse.error(message="Unexpected error occurred. Please check logs.", code=500)

        if response.status_code == 400:
            logger.error(f"Malformed request creating point '{name}'. Check parameters.", exc_info=False)
            return UserResponse.error(message="Malformed request. Please check logs.", code=400)

        if response.status_code == 409:
            logger.error(f"Conflict creating point '{name}' — tag may already exist.", exc_info=False)
            return UserResponse.error(
                message=f"Tag '{name}' may already exist or there is a conflict. Verify with get_point before retrying.",
                code=409
            )

        # 201 Created — no body, but Location header holds the new point URL
        location = response.headers.get("Location", "")
        return UserResponse.success(
            message=f"Successfully created PI tag '{name}'. Location: {location}",
            response={"Name": name, "Location": location},
            code=response.status_code
        )