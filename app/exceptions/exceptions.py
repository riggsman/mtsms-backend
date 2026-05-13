from fastapi import HTTPException, status
from app.helpers.logger import logger

class InternalServerError(HTTPException):
    """Internal server error exception"""
    def __init__(self, detail: str = "Internal server error"):
        logger.error(f"Internal server error: {detail}")
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)

class NotFoundError(HTTPException):
    """Resource not found exception"""
    def __init__(self, detail: str = "Resource not found"):
        logger.error(f"Not found error: {detail}")
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ValidationError(HTTPException):
    """Validation error exception"""
    def __init__(self, detail: str = "Validation error"):
        logger.error(f"Validation error: {detail}")
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


class UnauthorizedError(HTTPException):
    """Unauthorized access exception"""
    def __init__(self, detail: str = "Unauthorized"):
        logger.error(f"Unauthorized error: {detail}")
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class ForbiddenError(HTTPException):
    """Forbidden access exception"""
    def __init__(self, detail: str = "Forbidden"):
        logger.error(f"Forbidden error: {detail}")
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class ConflictError(HTTPException):
    """Resource conflict exception"""
    def __init__(self, detail: str = "Resource conflict"):
        logger.error(f"Conflict error: {detail}")
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class BadRequestError(HTTPException):
    """Bad request exception"""
    def __init__(self, detail: str = "Bad request"):
        logger.error(f"Bad request error: {detail}")
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
