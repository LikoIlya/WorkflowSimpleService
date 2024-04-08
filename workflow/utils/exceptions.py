from fastapi import status
from fastapi.responses import JSONResponse


class EdgeValidationError(ValueError):
    """Custom exception for edge validation errors."""


class NodeValidationError(ValueError):
    """Custom exception for node validation errors."""


class GraphValidationError(ValueError):
    """Custom exception for graph validation errors."""


def raise_validation_errors(
    message: str,
    exception: (
        NodeValidationError | EdgeValidationError | GraphValidationError
    ),
):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"message": message, "details": exception},
    )
