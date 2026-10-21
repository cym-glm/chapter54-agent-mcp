import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI
from mcp import Client, StdioServerParameters


PROJECT_DIR = Path(__file__).resolve().parent

load_dotenv(PROJECT_DIR / ".env")


def build_server_params():
    """构造 stdio MCP Server 的启动参数。"""

    api_base_url = os.getenv(
        "ENTERPRISE_API_BASE_URL",
        "http://127.0.0.1:9000",
    )

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
            # 子进程只获得本案例需要的 API 地址
            "ENTERPRISE_API_BASE_URL": api_base_url,
        },
    )


def convert_mcp_tool_to_llm_tool(tool):
    """将 MCP 工具定义转换为 OpenAI 兼容的工具格式。"""

    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.input_schema,
        },
    }


def result_to_text(result) -> str:
    """把 MCP 工具结果转换为大模型可以读取的文本。"""

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

    return "\n".join(texts) or "工具没有返回文本。"


async def run_agent(question: str):
    api_key = os.getenv("LLM_API_KEY")

    if not api_key:
        raise RuntimeError(
            "请先在 .env 中配置 OPENAI_API_KEY"
        )

    llm = ChatOpenAI(
        model=os.getenv("LLM_MODEL", "deepseek-chat"),
        api_key=api_key,
        base_url=os.getenv("LLM_BASE_URL") or None,
        temperature=0,
    )

    server_params = build_server_params()

    # 进入上下文后，Client 会启动 MCP Server 子进程
    async with Client(server_params) as client:

        # 第一步：从 MCP Server 动态发现工具
        tools_result = await client.list_tools()
        mcp_tools = tools_result.tools

        if not mcp_tools:
            raise RuntimeError("MCP Server 没有提供任何工具")

        # 第二步：把 MCP 工具描述提供给大模型
        llm_tools = [
            convert_mcp_tool_to_llm_tool(tool)
            for tool in mcp_tools
        ]

        llm_with_tools = llm.bind_tools(llm_tools)

        messages = [
            SystemMessage(
                content=(
                    "你是一个企业数据分析 Agent。"
                    "当用户询问员工、订单、发票或部门预算时，"
                    "应根据问题选择合适的工具。"
                    "必须根据工具实际返回的数据回答，"
                    "不能编造查询结果。"
                )
            ),
            HumanMessage(content=question),
        ]

        # 第三步：执行 Agent 工具调用循环
        max_rounds = 8

        for _ in range(max_rounds):
            response = await llm_with_tools.ainvoke(messages)

            messages.append(response)

            # 大模型不再请求调用工具，说明本轮可以输出最终回答
            if not response.tool_calls:
                print("\nAgent 回答：")
                print(response.content)
                return

            # 第四步：由 MCP Client 执行大模型选择的工具
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                print(
                    f"\n调用 MCP 工具：{tool_name}"
                    f"\n参数：{tool_args}"
                )

                try:
                    result = await client.call_tool(
                        tool_name,
                        tool_args,
                    )

                    tool_output = result_to_text(result)

                    if result.is_error:
                        tool_output = f"工具执行失败：{tool_output}"

                except Exception as exc:
                    tool_output = (
                        f"工具调用异常："
                        f"{type(exc).__name__}: {exc}"
                    )

                messages.append(
                    ToolMessage(
                        content=tool_output,
                        tool_call_id=tool_call["id"],
                    )
                )

        print("已达到最大工具调用轮数，请尝试简化问题。")


if __name__ == "__main__":
    question = input("请输入你的问题：").strip()

    if question:
        asyncio.run(run_agent(question))