import os
from typing import Any
from urllib.parse import quote

import httpx
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer


load_dotenv()

ENTERPRISE_API_BASE_URL = os.getenv(
    "ENTERPRISE_API_BASE_URL",
    "http://127.0.0.1:9000",
)


# 使用官方 MCP Python SDK 创建 MCP Server
mcp = MCPServer(
    "enterprise-business-mcp",
    instructions=(
        "这是企业业务 MCP Server。"
        "提供员工档案、订单、发票和部门预算查询工具。"
        "所有业务数据来自企业业务 API。"
    ),
)


async def enterprise_get(path: str) -> dict[str, Any]:
    """通过 HTTP 请求独立的企业业务系统。"""

    try:
        async with httpx.AsyncClient(
            base_url=ENTERPRISE_API_BASE_URL,
            timeout=5.0,
        ) as client:
            response = await client.get(path)

            if response.status_code == 404:
                try:
                    detail = response.json().get(
                        "detail",
                        "没有找到对应的业务记录",
                    )
                except ValueError:
                    detail = "没有找到对应的业务记录"

                return {
                    "ok": False,
                    "error": detail,
                }

            response.raise_for_status()

            return {
                "ok": True,
                "data": response.json(),
            }

    except httpx.RequestError:
        return {
            "ok": False,
            "error": (
                "无法连接企业业务系统，"
                "请检查企业业务 API 是否已经启动"
            ),
        }

    except httpx.HTTPStatusError as exc:
        return {
            "ok": False,
            "error": (
                "企业业务系统请求失败，"
                f"HTTP 状态码：{exc.response.status_code}"
            ),
        }


@mcp.tool()
async def get_employee_profile(
    employee_id: str,
) -> dict[str, Any]:
    """查询企业员工档案。参数示例：E1001。"""

    encoded_id = quote(employee_id, safe="")

    return await enterprise_get(
        f"/api/employees/{encoded_id}"
    )


@mcp.tool()
async def get_order_status(
    order_id: str,
) -> dict[str, Any]:
    """查询企业订单信息和当前状态。参数示例：ORD20261001。"""

    encoded_id = quote(order_id, safe="")

    return await enterprise_get(
        f"/api/orders/{encoded_id}"
    )


@mcp.tool()
async def get_invoice_detail(
    invoice_id: str,
) -> dict[str, Any]:
    """查询企业发票详情、金额和审核状态。"""

    encoded_id = quote(invoice_id, safe="")

    return await enterprise_get(
        f"/api/invoices/{encoded_id}"
    )


@mcp.tool()
async def get_department_budget(
    department: str,
) -> dict[str, Any]:
    """查询部门预算。参数示例：销售部、研发部。"""

    encoded_department = quote(department, safe="")

    return await enterprise_get(
        f"/api/departments/{encoded_department}/budget"
    )


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8001,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
    )