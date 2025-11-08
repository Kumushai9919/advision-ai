from fastapi import HTTPException
from typing import Optional
from enum import Enum

class ErrorCode(str, Enum):
    """
    Enumeration of all possible error codes.
    """
    INVALID_IMAGE = "INVALID_IMAGE"
    INACTIVE_USER = "INACTIVE_USER"
    FACE_NOT_DETECTED = "FACE_NOT_DETECTED"
    FACE_NOT_FOUND = "FACE_NOT_FOUND"
    LOW_QUALITY = "LOW_QUALITY"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    FACE_ALREADY_EXISTS = "FACE_ALREADY_EXISTS"
    INVALID_FACE_ANGLE = "INVALID_FACE_ANGLE"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    USER_RELATED_WITH_ANOTHER_ORG = "USER_RELATED_WITH_ANOTHER_ORG"
    WORKER_UNAVAILABLE = "WORKER_UNAVAILABLE"
    ORG_NOT_FOUND = "ORG_NOT_FOUND"
    
class AppException(HTTPException):
    """
    Exception class for handling application-specific errors.
    """
    
    ERROR_CONFIGS = {
         ErrorCode.INVALID_IMAGE: {
            "status_code": 400,
            "message": "잘못된 이미지 형식입니다. (jpg, png, jpeg만 가능)"
        },
        ErrorCode.FACE_NOT_DETECTED: {
            "status_code": 400,
            "message": "얼굴을 찾을 수 없습니다. 다시 촬영해주세요."
        },
        ErrorCode.INACTIVE_USER: {
            "status_code": 403,
            "message": "비활성화된 사용자입니다. 관리자에게 문의해주세요."
        },
        ErrorCode.LOW_QUALITY: {
            "status_code": 400,
            "message": "이미지 품질이 부족합니다. 조명을 개선하고 다시 촬영해주세요."
        },
        ErrorCode.FACE_NOT_FOUND: {
            "status_code": 404,
            "message": "얼굴 이미지를 찾을 수 없습니다."
        },
        ErrorCode.USER_NOT_FOUND: {
            "status_code": 404,
            "message": "등록되지 않은 사용자입니다."
        },
        ErrorCode.FACE_ALREADY_EXISTS: {
            "status_code": 409,
            "message": "이미 등록된 얼굴입니다."
        },
        ErrorCode.INVALID_FACE_ANGLE: {
            "status_code": 422,
            "message": "얼굴 각도가 적절하지 않습니다. 정면에서 촬영해주세요."
        },
        ErrorCode.RATE_LIMIT_EXCEEDED: {
            "status_code": 429,
            "message": "요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요."
        },
        ErrorCode.INTERNAL_ERROR: {
            "status_code": 500,
            "message": "서버 오류가 발생했습니다. 관리자에게 문의해주세요."
        },
        ErrorCode.SERVICE_UNAVAILABLE: {
            "status_code": 503,
            "message": "서비스가 일시적으로 중단되었습니다. 잠시 후 다시 시도해주세요."
        },
        ErrorCode.USER_RELATED_WITH_ANOTHER_ORG: {
            "status_code": 400,
            "message": "사용자가 다른 조직과 연관되어 있습니다."
        },
        ErrorCode.WORKER_UNAVAILABLE: {
            "status_code": 503,
            "message": "작업자 서비스가 현재 사용 불가능합니다. 잠시 후 다시 시도해주세요."
        },
        ErrorCode.ORG_NOT_FOUND: {
            "status_code": 404,
            "message": "조직을 찾을 수 없습니다."
        }
    }
    
    def __init__(self, error_code: ErrorCode, message: Optional[str] = None):
        config = self.ERROR_CONFIGS.get(error_code, self.ERROR_CONFIGS[ErrorCode.INTERNAL_ERROR])
        
        error_response = {
            "success": False,
            "error": {
                "code": error_code.value,
                "message": message or config["message"]
            }
        }
        
        super().__init__(
            status_code=config["status_code"],
            detail=error_response
        )
        
class InvalidImageError(AppException):
    def __init__(self, message: Optional[str] = None):
        super().__init__(ErrorCode.INVALID_IMAGE, message)

class InactiveUserError(AppException):
    def __init__(self, message: Optional[str] = None):
        super().__init__(ErrorCode.INACTIVE_USER, message)

class FaceNotDetectedError(AppException):
    def __init__(self, message: Optional[str] = None):
        super().__init__(ErrorCode.FACE_NOT_DETECTED, message)

class LowQualityError(AppException):
    def __init__(self, message: Optional[str] = None):
        super().__init__(ErrorCode.LOW_QUALITY, message)


class FaceNotFoundError(AppException):
    def __init__(self, message: Optional[str] = None):
        super().__init__(ErrorCode.FACE_NOT_FOUND, message)

class OrgNotFoundError(AppException):
    def __init__(self, message: Optional[str] = None):
        super().__init__(ErrorCode.ORG_NOT_FOUND, message)

class UserNotFoundError(AppException):
    def __init__(self, message: Optional[str] = None):
        super().__init__(ErrorCode.USER_NOT_FOUND, message)


class FaceAlreadyExistsError(AppException):
    def __init__(self, message: Optional[str] = None):
        super().__init__(ErrorCode.FACE_ALREADY_EXISTS, message)


class InvalidFaceAngleError(AppException):
    def __init__(self, message: Optional[str] = None):
        super().__init__(ErrorCode.INVALID_FACE_ANGLE, message)


class RateLimitExceededError(AppException):
    def __init__(self, retry_after: Optional[int] = None, message: Optional[str] = None):
        headers = {"Retry-After": str(retry_after)} if retry_after else None
        super().__init__(ErrorCode.RATE_LIMIT_EXCEEDED, message, headers=headers)


class InternalError(AppException):
    def __init__(self, message: Optional[str] = None):
        super().__init__(ErrorCode.INTERNAL_ERROR, message)

class UserRelatedWithAnotherOrgError(AppException):
    def __init__(self, message: Optional[str] = None):
        super().__init__(ErrorCode.USER_RELATED_WITH_ANOTHER_ORG, message)

class WorkerError(AppException):
    def __init__(self, message: Optional[str] = None):
        super().__init__(ErrorCode.WORKER_UNAVAILABLE, message)

class ServiceUnavailableError(AppException):
    def __init__(self, message: Optional[str] = None):
        super().__init__(ErrorCode.SERVICE_UNAVAILABLE, message)