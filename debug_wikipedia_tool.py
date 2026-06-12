import asyncio

from sdlc_demo.tools import WikipediaMcpContextParams, wikipedia_mcp_context


async def main():
    params = WikipediaMcpContextParams(
        concepts=[
            "Autenticación multifactor",
            "Auditoría informática",
            "Trazabilidad",
        ]
    )

    result = await wikipedia_mcp_context(params)

    print(result)


if __name__ == "__main__":
    asyncio.run(main())