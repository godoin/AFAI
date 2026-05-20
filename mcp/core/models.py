from typing import Any


class UserResponse:
    """
    Standardised response envelope for all service layer methods.

    Every method in services/pi_system/ returns one of these dicts so that
    app.py (and future callers) always handle a consistent shape:

        {
            "success": bool,
            "title":   str,
            "message": str,
            "code":    int | str,
            "response": Any
        }

    The class is stateless — both methods are static factories.
    """

    def __init__(self):
        pass

    @staticmethod
    def success(
        message: str,
        title: str = "Success",
        response: Any = None,
        code: int = 200,
    ) -> dict:
        """
        Return a success envelope.

        Args:
            message:  Human-readable description of what succeeded.
            title:    Short label shown in logs / UI. Default "Success".
            response: The raw API payload (dict, list, str). Defaults to "N/A"
                      when the operation produces no body (e.g. 201 Created).
            code:     HTTP status code returned by PI Web API.
        """
        return {
            "success": True,
            "title": title,
            "message": message,
            "code": code,
            "response": response if response is not None else "N/A",
        }

    @staticmethod
    def error(
        message: str,
        title: str = "Error",
        code: Any = "N/A",
        response: Any = "N/A",
    ) -> dict:
        """
        Return an error envelope.

        Args:
            message:  Human-readable description of what failed.
            title:    Short label shown in logs / UI. Default "Error".
            code:     HTTP status code, or "N/A" for pre-request failures
                      (e.g. missing parameter caught before the call is made).
            response: Raw error body from PI Web API, if any.
        """
        return {
            "success": False,
            "title": title,
            "message": message,
            "code": code,
            "response": response,
        }


class AttributesResult:
    """
    Placeholder for a typed result model for Attributes responses.
    Extend when the service layer is ready to return structured objects
    instead of raw dicts.
    """
    pass


class PointsResult:
    """
    Placeholder for a typed result model for Points responses.
    """
    pass


class ElementsResult:
    """
    Placeholder for a typed result model for Elements responses.
    """
    pass


class AssetsResult:
    """
    Placeholder for a typed result model for Asset Server / Database responses.
    """
    pass