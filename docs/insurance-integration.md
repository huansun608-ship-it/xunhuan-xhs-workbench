# 保险内容主流程接入

2026-10-24，按用户确认，以已采集账号为教学研究样本推进保险写作工作台。

> 最新状态：2026-11-24 已升级到 v1.9.6，见文末「版本升级记录」。本文前半部分保留 10 月 24 日接入 v1.4.0 当时的记录，其中版本号、引用文件数量和「哈希核对」结论均已不适用于当前目录。

## 安装来源

源：本地维护的insurance-xhs v1.4.0资料；个人工作站源路径不随公开仓库发布。

项目安装路径：`skills/builtin/insurance-xhs/`。保留v1.4.0内容与全部引用文件，仅在项目副本的frontmatter增加`layer: produce`，使Easel技能库可归类展示。源包未修改。

`agents/workspace/AGENTS.md`增加保险范围的优先路由：保险小红书定位、选题、写稿、改稿、初查与复盘先读insurance-xhs；制作技能按需组合，不强制通用长稿、语气与视觉模板。

## 检查与试写

本机`/api/skills`已返回insurance-xhs，分类produce。references逐文件哈希核对一致。

验证任务使用「保险研究样板-索菲亚」，新对话试写家庭配置顺序。研究样本并非本人授权稿，不能冒用其身份和经历。已通过网页实际生成文章、五页图文文字及封面构思，并回读全部交付文件；执行记录列出insurance-xhs v1.4.0及writing-workflow、human-speech、evidence-and-value、compliance四份引用。成果在`outputs/保险Skill实测-家庭配置顺序-20261024/`。本次提示未直接点名技能文件，使用“项目保险内容主流程”触发；它只验证了这一个任务，后续仍需更短输入和其他题材的回归试跑。

## 后续维护

更新源技能版本时同步完整references，再核对路由及一篇实际生成结果。账号研究画像与技能分开；新增真实学员时建立本人确认的画像。本文不代表多用户权限、付费媒体、机构审核或发布功能已经验证。

## 版本升级记录

### 2026-11-24：v1.4.2 → v1.9.6

升级包来源为 `insurance-xhs-v1.9.6.zip`，整包解压后覆盖 `skills/builtin/insurance-xhs/`。

- 引用文件：12 个 Markdown → 28 个 Markdown 加 `bio-ending-cases.json`。
- 新增目录：`assets/research/critical-illness-20261122/`（34 篇正文、26 篇的 120 张原图、8 篇深拆、补充 6 篇深读，另附 manifest 与 checksums）。
- 新增方法文件：title-writing、title-sources、community-title-workflow、opening-craft、story-and-voice、story-voice-sources、xhs-copy-craft、emotion-and-opinion、student-writing、course-methodology、research-patterns、community-image-posts、critical-illness-craft、critical-illness-data-index、bio-ending-library、integration-review。
- 两处工作台适配：frontmatter 补 `layer: produce`；源包的 `metadata.version: "1.9.6"` 改为正文首行版本标注，因本仓库 `scripts/validate_skills.py` 只允许 `metadata.openclaw` 形式的 metadata。
- 已核对：`scripts/validate_skills.py` 通过（115 个技能合规）；全部 29 个引用文件的相对 Markdown 链接零断链；`critical-illness-data-index.md` 指向的 5 个数据文件与 `assets/<note-id>/` 图目录存在。
- 未验证：升级后尚未跑新的端到端试写，标题/开头/情绪观点三条新链路的实际生成质量待回归；技能内「50 篇研究完成」仍为未完成状态，索引自述 34 篇。
- 采集样本按用户确认随仓库入库，README 的范围声明已同步调整；权利人要求下架时删除对应条目。

`agents/workspace/AGENTS.md` 的保险路由与 `skills/shared/references/insurance-handdrawn-spec.md` 的视觉规则本次未改动，仍按原引用关系生效。
