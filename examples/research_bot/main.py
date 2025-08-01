import asyncio

from .manager import ResearchManager


async def main() -> None:
    manager = ResearchManager()

    query = input("What would you like to research? \n")
    # query = "什么是上下文工程，和提示词工程有什么区别"

    report = await manager.run(query)

    # 保存报告到文件
    await manager.save_report_to_file(query, report)



if __name__ == "__main__":
    asyncio.run(main())
