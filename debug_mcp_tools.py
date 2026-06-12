import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    command = str(Path(sys.executable).parent / "wikipedia-mcp.exe")

    print(f"Usando comando MCP: {command}")

    server_params = StdioServerParameters(
        command=command,
        args=[
            "--transport",
            "stdio",
            "--language",
            "es",
        ],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_response = await session.list_tools()

            print("\nTools encontradas:\n")

            for tool in tools_response.tools:
                print(f"- {tool.name}")

                if tool.description:
                    print(f"  Description: {tool.description[:300]}")

                schema = getattr(tool, "inputSchema", None)

                if schema:
                    print("  Input schema:")
                    print(json.dumps(schema, indent=2, ensure_ascii=False))

                print()


if __name__ == "__main__":
    asyncio.run(main())