import json
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values
from mcp.server.mcpserver import MCPServer


PROJECT_DIR = Path(__file__).resolve().parent

# 支持两种启动方式：
# 1. MCP Client 显式传入环境变量
# 2. 使用 MCP Inspector 等工具直接启动时，从 .env 读取
file_env = dotenv_values(PROJECT_DIR / ".env")

ENTERPRISE_API_BASE_URL = (
    os.getenv("ENTERPRISE_API_BASE_URL")
    or file_env.get("ENTERPRISE_API_BASE_URL")
    or "http://127.0.0.1:9000"
).rstrip("/")


# 创建 MCP Server
mcp = MCPServer(
    "enterprise-business-tools",
    instructions=(
        "这是企业业务查询 MCP Server。"
        "可以查询员工、订单、发票和部门预算信息。"
    ),
)


async def request_enterprise_api(path: str) -> dict[str, Any]:
    """调用企业业务 API。"""

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{ENTERPRISE_API_BASE_URL}{path}"
        )
        response.raise_for_status()

        return response.json()


@mcp.tool()
async def get_employee(employee_id: str) -> str:
    """根据员工编号查询员工基本信息。"""

    data = await request_enterprise_api(
        f"/api/employees/{employee_id}"
    )

    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
async def get_order(order_id: str) -> str:
    """根据订单编号查询订单信息。"""

    data = await request_enterprise_api(
        f"/api/orders/{order_id}"
    )

    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
async def get_invoice(invoice_id: str) -> str:
    """根据发票编号查询发票信息。"""

    data = await request_enterprise_api(
        f"/api/invoices/{invoice_id}"
    )

    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
async def get_department_budget(
    department_id: str,
) -> str:
    """查询指定部门的月度预算和已使用预算。"""

    data = await request_enterprise_api(
        f"/api/departments/{department_id}/budget"
    )

    return json.dumps(data, ensure_ascii=False)


if __name__ == "__main__":
    # 不指定 transport 时，官方 SDK 默认使用 stdio。
    # MCP Client 启动这个文件后，会通过 stdin/stdout 与它通讯。
    mcp.run()