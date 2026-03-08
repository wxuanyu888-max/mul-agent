"""Response - 统一响应格式"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class ApiResponse:
    """API 响应基类"""
    status: str
    route: Optional[str] = None
    data: Optional[Any] = None
    error_code: Optional[int] = None
    error_type: Optional[str] = None
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {"status": self.status}

        if self.route:
            result["route"] = self.route

        if self.status == "success":
            if self.data is not None:
                result["data"] = self.data
            # 兼容旧格式：使用 result 而不是 data
            if hasattr(self, 'result') and self.result is not None:
                result["result"] = self.result
        else:
            if self.error_code:
                result["error_code"] = self.error_code
            if self.error_type:
                result["error_type"] = self.error_type
            if self.message:
                result["message"] = self.message
            if self.details:
                result["details"] = self.details

        if self.metadata:
            result["metadata"] = self.metadata

        return result


def create_success_response(
    data: Any = None,
    route: str = None,
    message: str = None,
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """创建成功响应

    Args:
        data: 响应数据
        route: 路由名称
        message: 成功消息
        metadata: 元数据（如分页信息）

    Returns:
        标准化成功响应字典
    """
    response = {"status": "success"}

    if route:
        response["route"] = route

    if data is not None:
        response["data"] = data

    if message:
        response["message"] = message

    if metadata:
        response["metadata"] = metadata

    return response


def create_paginated_response(
    data: List[Any],
    total: int,
    page: int = 1,
    limit: int = 20,
    route: str = None
) -> Dict[str, Any]:
    """创建分页响应

    Args:
        data: 数据列表
        total: 总数
        page: 当前页码
        limit: 每页数量
        route: 路由名称

    Returns:
        标准化分页响应字典
    """
    return create_success_response(
        data=data,
        route=route,
        metadata={
            "pagination": {
                "total": total,
                "page": page,
                "limit": limit,
                "total_pages": (total + limit - 1) // limit,
                "has_next": page * limit < total,
                "has_prev": page > 1
            }
        }
    )


# 兼容旧格式的别名
def create_response(
    status: str,
    result: Any = None,
    error_code: int = None,
    error_type: str = None,
    message: str = None,
    route: str = None
) -> Dict[str, Any]:
    """创建响应（兼容旧格式）

    Args:
        status: 状态 (success/error)
        result: 响应数据
        error_code: 错误码
        error_type: 错误类型
        message: 错误消息
        route: 路由名称

    Returns:
        标准化响应字典
    """
    response = {"status": status}

    if route:
        response["route"] = route

    if status == "success":
        if result is not None:
            response["result"] = result
    else:
        if error_code:
            response["error_code"] = error_code
        if error_type:
            response["error_type"] = error_type
        if message:
            response["message"] = message

    return response
