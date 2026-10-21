import asyncio
import json
from pathlib import Path

from dotenv import dotenv_values
from mcp import Client, StdioServerParameters


PROJECT_DIR = Path(__file__).resolve().parent
file_env = dotenv_values(PROJECT_DIR / ".env")

API_BASE_URL = (
    file_env.get("ENTERPRISE_API_BASE_URL")
    or "http://127.0.0.1:9000"
)


def build_server_params():
    return StdioServerParameters(
        command="uv",
        args=[
            "run",
            "--project",
            str(PROJECT_DIR),
            "python",
            str(PROJECT_DIR / "stido_mcp_server.py"),
        ],
        env={
            "ENTERPRISE_API_BASE_URL": API_BASE_URL,
        },
    )


def result_to_text(result) -> str:
    if result.structured_content is not None:
        return json.dumps(
            result.structured_content,
            ensure_ascii=False,
        )

    texts = [
        block.text
        for block in result.content
        if getattr(block, "text", None) is not None
    ]

    return "\n".join(texts)


async def main():
    server_params = build_server_params()

    # Client 进入上下文时会启动 MCP Server 子进程
    async with Client(server_params) as client:
        # 发现 MCP Server 提供的工具
        tools_result = await client.list_tools()

        print("发现的 MCP 工具：")
        for tool in tools_result.tools:
            print(f"- {tool.name}: {tool.description}")

        # 直接调用 MCP 工具
        result = await client.call_tool(
            "get_employee",
            {"employee_id": "E1001"},
        )

        print("\n员工查询结果：")
        print(result_to_text(result))

        if result.is_error:
            raise RuntimeError("MCP 工具调用失败")


if __name__ == "__main__":
    asyncio.run(main())