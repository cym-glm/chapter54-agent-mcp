import asyncio
import json
import os
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI
from mcp import Client


load_dotenv()

MCP_SERVER_URL = os.getenv(
    "MCP_SERVER_URL",
    "http://127.0.0.1:8001/mcp",
)

SYSTEM_PROMPT = """
你是一个企业业务助手。

你可以通过 MCP 工具查询员工、订单、发票和部门预算。

请遵守以下规则：

1. 当用户询问具体员工、订单、发票或预算信息时，
   应优先调用相应的 MCP 工具。
2. 不要编造员工信息、订单状态、发票金额或预算数字。
3. 只能依据工具返回的业务数据回答具体业务事实。
4. 如果工具返回错误，应该如实告知用户。
5. 如果用户的问题需要多个业务信息，
   可以连续调用多个工具后再进行汇总。
6. 查询预算只用于信息查询，不代表审批通过。
7. 最终使用清晰、自然的中文回答用户。
"""


def create_llm() -> ChatOpenAI:
    """创建支持工具调用的大模型客户端。"""

    api_key = os.getenv("LLM_API_KEY")

    if not api_key:
        raise RuntimeError(
            "请先在 .env 中配置 LLM_API_KEY"
        )

    return ChatOpenAI(
        api_key=api_key,
        base_url=os.getenv(
            "LLM_BASE_URL",
            "https://api.deepseek.com",
        ),
        model=os.getenv(
            "LLM_MODEL",
            "deepseek-chat",
        ),
        temperature=0,
    )


def convert_mcp_tool_to_model_tool(
    tool: Any,
) -> dict[str, Any]:
    """将 MCP 工具 Schema 转换为大模型 Tool Calling 格式。"""

    parameters = tool.input_schema or {
        "type": "object",
        "properties": {},
    }

    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or tool.name,
            "parameters": parameters,
        },
    }


def mcp_result_to_payload(result: Any) -> Any:
    """提取 MCP 工具调用结果。"""

    text_blocks = [
        block_text
        for block in result.content
        if (block_text := getattr(block, "text", None))
    ]

    if result.is_error:
        return {
            "ok": False,
            "error": text_blocks or ["MCP 工具调用失败"],
        }

    if result.structured_content is not None:
        return result.structured_content

    return {
        "content": "\n".join(text_blocks),
    }


async def run_agent(question: str) -> str:
    """Agent 主流程：发现工具、调用工具、汇总结果。"""

    llm = create_llm()

    # 通过官方 MCP Client 连接独立 MCP Server。
    async with Client(MCP_SERVER_URL) as mcp_client:

        # 第一步：动态发现 MCP Server 提供的工具。
        tool_result = await mcp_client.list_tools()

        mcp_tools = tool_result.tools

        if not mcp_tools:
            return "MCP Server 没有提供可用工具。"

        print("\n已发现 MCP 工具：")

        for tool in mcp_tools:
            print(f"- {tool.name}: {tool.description}")

        # 第二步：将工具 Schema 提供给大模型。
        model_tools = [
            convert_mcp_tool_to_model_tool(tool)
            for tool in mcp_tools
        ]

        tool_names = {
            tool.name
            for tool in mcp_tools
        }

        llm_with_tools = llm.bind_tools(model_tools)

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=question),
        ]

        # 限制工具调用轮数，避免无限循环。
        max_tool_rounds = 8

        for _ in range(max_tool_rounds):
            ai_message = await llm_with_tools.ainvoke(
                messages
            )

            messages.append(ai_message)

            tool_calls = ai_message.tool_calls

            # 模型没有继续请求工具时，返回最终回答。
            if not tool_calls:
                if isinstance(ai_message.content, str):
                    return ai_message.content

                return json.dumps(
                    ai_message.content,
                    ensure_ascii=False,
                    default=str,
                )

            # 一个模型响应可能包含多个工具调用。
            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call.get("args") or {}
                tool_call_id = tool_call["id"]

                print(
                    f"\n正在调用 MCP 工具：{tool_name}"
                )
                print(
                    "调用参数：",
                    json.dumps(
                        tool_args,
                        ensure_ascii=False,
                    ),
                )

                # 只允许调用本次发现的 MCP 工具。
                if tool_name not in tool_names:
                    payload = {
                        "ok": False,
                        "error": "请求的工具不在当前 MCP 工具列表中",
                    }
                else:
                    try:
                        # 第三步：通过真实 MCP Client 调用工具。
                        result = await mcp_client.call_tool(
                            tool_name,
                            arguments=tool_args,
                        )

                        payload = mcp_result_to_payload(
                            result
                        )

                    except Exception as exc:
                        payload = {
                            "ok": False,
                            "error": (
                                "MCP 工具调用失败："
                                f"{type(exc).__name__}"
                            ),
                        }

                # 第四步：把工具结果交回大模型。
                messages.append(
                    ToolMessage(
                        content=json.dumps(
                            payload,
                            ensure_ascii=False,
                            default=str,
                        ),
                        tool_call_id=tool_call_id,
                    )
                )

        return (
            "本次任务超过最大工具调用轮数，"
            "请缩小查询范围后重试。"
        )


async def main():
    question = input(
        "请输入企业业务问题："
    ).strip()

    if not question:
        print("问题不能为空。")
        return

    answer = await run_agent(question)

    print("\n========== Agent 回答 ==========")
    print(answer)


if __name__ == "__main__":
    asyncio.run(main())