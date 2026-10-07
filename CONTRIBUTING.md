# 贡献指南

新增来源先在config/sources.yaml说明官方身份、API/RSS/网页格式、出版日期、类别、可靠性、历史窗口与失败方式。不要一次接入大量脆弱网页。

Collector必须独立隔离失败，保留原始URL、获取时间、完整来源与Evidence；未知日期不能用抓取日期代替。新解析器添加离线fixture测试，原始fixture说明是否synthetic，不能当真实周报数据。

修改Prompt/评分权重使用普通diff，不能把主观判断藏在分散代码中。运行ruff与pytest；重要变更再用真实周和Dry Run验证。

反馈勘误请提供期次、原句、原始来源、建议修订；修订规则见docs/editorial_policy.md。不要提交API Key、敏感headers或公司内部课程资料。

不接受V0.1中的定时调度、自动推送或自动分发功能；需维护者另行明确开启自动化阶段。
