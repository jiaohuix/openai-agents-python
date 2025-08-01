from __future__ import annotations

import os
from datetime import datetime
import asyncio
import time

from rich.console import Console

from agents import Runner,RunConfig , custom_span, gen_trace_id, trace

from .agents.planner_agent import WebSearchItem, WebSearchPlan, planner_agent
from .agents.search_agent import search_agent
from .agents.writer_agent import ReportData, writer_agent
from .printer import Printer

from .agents.config import CUSTOM_MODEL_PROVIDER



class ResearchManager:
    def __init__(self):
        self.console = Console()
        self.printer = Printer(self.console)

    async def run(self, query: str) -> None:

        self.printer.update_item(
            "starting",
            "Starting research...",
            is_done=True,
            hide_checkmark=True,
        )
        print("start query", query)
        search_plan = await self._plan_searches(query)
        print("search_plan",search_plan)
        search_results = await self._perform_searches(search_plan)
        print("search_results",search_results)
        report = await self._write_report(query, search_results)
        print("report",report)

        final_report = f"Report summary\n\n{report.short_summary}"
        self.printer.update_item("final_report", final_report, is_done=True)

        self.printer.end()

        print("\n\n=====REPORT=====\n\n")
        print(f"Report: {report.markdown_report}")
        print("\n\n=====FOLLOW UP QUESTIONS=====\n\n")
        follow_up_questions = "\n".join(report.follow_up_questions)
        print(f"Follow up questions: {follow_up_questions}")

        return report  # 返回报告对象

    async def _plan_searches(self, query: str) -> WebSearchPlan:
        self.printer.update_item("planning", "Planning searches...")
        print("query",query)
        result = await Runner.run(
            planner_agent,
            f"Query: {query}",
            run_config=RunConfig(model_provider=CUSTOM_MODEL_PROVIDER),
        )
        self.printer.update_item(
            "planning",
            f"Will perform {len(result.final_output.searches)} searches",
            is_done=True,
        )
        return result.final_output_as(WebSearchPlan)

    async def _perform_searches(self, search_plan: WebSearchPlan) -> list[str]:
        with custom_span("Search the web"):
            self.printer.update_item("searching", "Searching...")
            num_completed = 0
            # tasks = [asyncio.create_task(self._search(item)) for item in search_plan.searches]
            limit = 5
            tasks = [asyncio.create_task(self._search(item)) for item in search_plan.searches[:limit]]

            results = []
            for task in asyncio.as_completed(tasks):
                result = await task
                if result is not None:
                    results.append(result)
                num_completed += 1
                self.printer.update_item(
                    "searching", f"Searching... {num_completed}/{len(tasks)} completed"
                )
            self.printer.mark_item_done("searching")
            return results

    async def _search(self, item: WebSearchItem) -> str | None:
        input = f"Search term: {item.query}\nReason for searching: {item.reason}"
        try:
            result = await Runner.run(
                search_agent,
                input,
                run_config=RunConfig(model_provider=CUSTOM_MODEL_PROVIDER),
            )
            return str(result.final_output)
        except Exception as e:
            print(f"Search failed for '{item.query}': {e}")
            return None

    # async def _write_report(self, query: str, search_results: list[str]) -> ReportData:
    #     self.printer.update_item("writing", "Thinking about report...")
    #     input = f"Original query: {query}\nSummarized search results: {search_results}"
    #     result = Runner.run_streamed(
    #         writer_agent,
    #         input,
    #         run_config=RunConfig(model_provider=CUSTOM_MODEL_PROVIDER),

    #     )
    #     update_messages = [
    #         "Thinking about report...",
    #         "Planning report structure...",
    #         "Writing outline...",
    #         "Creating sections...",
    #         "Cleaning up formatting...",
    #         "Finalizing report...",
    #         "Finishing report...",
    #     ]

    #     last_update = time.time()
    #     next_message = 0
    #     async for _ in result.stream_events():
    #         if time.time() - last_update > 5 and next_message < len(update_messages):
    #             self.printer.update_item("writing", update_messages[next_message])
    #             next_message += 1
    #             last_update = time.time()

    #     self.printer.mark_item_done("writing")
    #     return result.final_output_as(ReportData)


    async def _write_report(self, query: str, search_results: list[str]) -> ReportData:
        self.printer.update_item("writing", "Writing report...")
        input = f"Original query: {query}\nSummarized search results: {search_results}"
        
        try:
            # 使用非流式调用避免兼容性问题
            result = await Runner.run(
                writer_agent,
                input,
                run_config=RunConfig(model_provider=CUSTOM_MODEL_PROVIDER),
            )
            self.printer.mark_item_done("writing")
            return result.final_output_as(ReportData)
        
        except Exception as e:
            print(f"Report generation failed: {e}")
            # 返回一个默认的报告
            self.printer.update_item("writing", "Report generation failed, creating fallback report", is_done=True)
            return ReportData(
                short_summary="报告生成失败，但搜索结果已获取。",
                markdown_report=f"# 搜索结果摘要\n\n原始查询：{query}\n\n搜索结果：\n\n" + "\n\n".join([f"- {result}" for result in search_results]),
                follow_up_questions=["请重试报告生成", "检查模型配置是否正确"]
            )


    async def save_report_to_file(self, query: str, report: ReportData) -> str:
        """保存报告到文件并返回文件路径"""
        # 创建reports目录
        reports_dir = "reports"
        os.makedirs(reports_dir, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = "".join(c for c in query[:50] if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = f"{timestamp}_{safe_query}.md"
        filepath = os.path.join(reports_dir, filename)
        
        # 保存报告
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# 研究报告\n\n")
            f.write(f"**查询**: {query}\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## 摘要\n\n{report.short_summary}\n\n")
            f.write(f"## 详细报告\n\n{report.markdown_report}\n\n")
            f.write(f"## 后续问题\n\n")
            for i, question in enumerate(report.follow_up_questions, 1):
                f.write(f"{i}. {question}\n")
        
        print(f"\n报告已保存到: {filepath}")
        return filepath