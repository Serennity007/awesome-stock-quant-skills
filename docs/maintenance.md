# 持续更新怎样工作

本次维护基准：2026-10-24。第三方文件仍是收录时的快照，不能因本次文档更新就标为最新版本。

## 每周巡检

[`upstream-watch.yml` 模板](workflows/upstream-watch.yml) 配置为每周一 UTC 02:23（北京时间 10:23），也可手动运行。当前授权缺少 GitHub `workflow` 权限，新工作流尚未部署。模板需要复制到 `.github/workflows/` 并通过具有相应权限的凭据推送到默认分支，定时触发才生效；GitHub 调度可能延迟，长期无活动仓库的定时任务可能被停用。报告放在对应 Actions run 的 summary 和 `upstream-status` artifact，不自动改源码或提交报告。

本地从仓库根目录执行（只用 Python 标准库）：

```bash
python scripts/check_upstreams.py
```

可选 `GITHUB_TOKEN` 仅发往 `api.github.com`；无 token 也可查询公开仓库，受匿名额度限制。脚本读取每个 `skills/*/SOURCE.md`，核对默认分支最新提交、许可证 SPDX 元数据、归档状态，同时查询 PyPI 的 AKShare 版本。任一抓取失败，仍写出报告并非零退出，不把失败显示成正常。

首次核对建立远程观察基准。后续本地运行默认比较同目录上次 JSON；Actions 使用缓存保存前次巡检，对失败来源保留最近一次成功观察的 head，缓存不可用时从新基准开始。迁移报告时可用 `--previous path/to/latest.json --out-dir path/to/output`。

许多旧 `SOURCE.md` 没有提交号。报告将其标为 `snapshot-unpinned`，无法反推其精确镜像版本。`head-changed-since-check` 只说明两次观察间 head 不同；新增 star 不作为更新信号；许可证元数据差异只是待复核项。

## 发现更新之后

1. 对比上游 diff，阅读实际许可证和变更说明；确认转载范围。
2. 在工作分支更新目标目录，保留署名、许可证，给 `SOURCE.md` 补上明确提交号与同步日期。
3. 检查调用参数、字段名与单位；跑目标 skill 的小样例。无法联网时明确标注仅做了离线检查。
4. 运行离线质量检查。文档只写已验证的能力，历史运行日期与本次验证日期分开。

新增资源应先确认可复用价值与许可；框架、应用和仅索引项目继续保留链接，不自动拉进 `skills/`。

## 官方参考

- [AKShare 项目概览](https://akshare.akfamily.xyz/introduction.html)：2026-10-24 查阅时文档说明接口会随数据源页面变化而维护，使用方式应查最新文档；版本更新本身不代表所有接口可用。
- [GitHub Repository API](https://docs.github.com/en/rest/repos/repos#get-a-repository)：元数据与许可证字段。
- [GitHub List commits API](https://docs.github.com/en/rest/commits/commits#list-commits)：不传 sha 时查询默认分支。
- [GitHub schedule 触发说明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)：默认分支、调度与停用条件。

## 启用模板

先确认 GitHub 凭据允许更新 Actions 工作流，再从仓库根目录执行：

```bash
mkdir -p .github/workflows
cp docs/workflows/quality.yml .github/workflows/quality.yml
cp docs/workflows/upstream-watch.yml .github/workflows/upstream-watch.yml
```

提交这些文件并推送至默认分支后，质量检查可随 push / pull_request 运行，巡检可手动或定时运行。模板未部署期间，本地命令仍可直接使用。原有 daily-report 工作流保持原样。
