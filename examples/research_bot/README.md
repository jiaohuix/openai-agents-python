# Research bot

This is a simple example of a multi-agent research bot. To run it:

```bash
python -m examples.research_bot.main
```

## Architecture

The flow is:

1. User enters their research topic
2. `planner_agent` comes up with a plan to search the web for information. The plan is a list of search queries, with a search term and a reason for each query.
3. For each search item, we run a `search_agent`, which uses the Web Search tool to search for that term and summarize the results. These all run in parallel.
4. Finally, the `writer_agent` receives the search summaries, and creates a written report.

## Suggested improvements

If you're building your own research bot, some ideas to add to this are:

1. Retrieval: Add support for fetching relevant information from a vector store. You could use the File Search tool for this.
2. Image and file upload: Allow users to attach PDFs or other files, as baseline context for the research.
3. More planning and thinking: Models often produce better results given more time to think. Improve the planning process to come up with a better plan, and add an evaluation step so that the model can choose to improve its results, search for more stuff, etc.
4. Code execution: Allow running code, which is useful for data analysis.

## Issues Encountered

1. **WebSearchTool问题**: websearchtool使用不了，自己创建了tool来替代原有的搜索功能
2. **输入处理**: input需要自己输入query，没有交互式界面
3. **格式规范**: json格式约定了output format，但是提示词没有指定（planner、writer），导致输出不一致
4. **报告保存**: 输出报告没写到markdown文件，只在控制台显示
5. **模型配置**: 自定义模型集成和配置
6. **提示词优化**: planner需要在中文输入时候有几个英文子查询；writer在输出时需要和query语言保持一致
7. **调试信息**: 删除trace_id，简化输出日志
8. **路径问题**: 相对目录问题，需要使用 `python -m examples.research_bot.main` 来正确运行

## TODO

1. **系统架构**: 结构设计合理化，提高代码可维护性
2. **API开发**: 开发api接口，支持外部调用
3. **功能增强**: 连入mcp，和更好的search工具，支持更高并发；添加web-fetch工具，具体查看网页内容而不仅仅是摘要
