---
name: insurance-xhs-proposal
description: >-
  把保险经纪人的需求做成可挑选的小红书图文方案：一次给出4套切入角度不同的标题、封面图、封面文案与正文，逐项标注参考案例链接、借鉴点和保险事实依据或待核实标记；选定后按自然语言局部改稿，保留原稿、改稿与修改意见。当用户说“出几套图文方案/一次看4个版本/标题封面正文一起比/做个能挑的方案”时使用；单篇写稿或改稿走 insurance-xhs，只渲染卡片走 card-xiaohongshu。
layer: plan
---

# 保险小红书图文方案 · 四选一

> 一句话需求 → 4 套角度不同、带真实封面图、逐项可溯源、可改稿的图文方案。内容判断交给 insurance-xhs；本 SKILL 负责多方案编排、封面出图、分项溯源和版本留痕。

## 边界

- **本 SKILL**：一次出 4 套可比较的完整方案，含封面图、标题、封面文案、正文、溯源、事实状态、改稿记录。
- **insurance-xhs**：选题、标题、正文、人感、证据与风控的判断标准。本 SKILL 不复制、不改写这些规则。
- **card-xiaohongshu / card-design**：封面卡片的视觉与渲染管线。
- **skill-xhs-publisher**：发布。本 SKILL 只交工作草稿，不发布。

用户只要一篇成稿、只改标题、只做合规初查时，直接用 insurance-xhs，不走本流程。

## 输入

必需：主题（读者会搜的那句话）+ 必须包含的信息。

可选：目标人群、使用场景、语气、产品事实、画像、参考链接、截止时间。

允许一句话启动。缺什么按[接需求与补齐](references/intake.md)判断；能推断就写假设，不要求用户填表。

## 输出

```
outputs/<主题>/
├── 方案.json            # 单一真相源：4 套 + 溯源 + 事实 + 修改记录
├── 方案对比.html        # 4 套对比页，内嵌封面图
├── 修改记录.md
├── 选定方案_<标题>.md   # 用户选定后导出
├── 封面.png             # 选定方案的封面
├── covers/cover_set_1.png … cover_set_4.png
├── history/v1.json
└── assets/brief.md、covers.html、references/
```

字段与目录规范见[方案 JSON](references/plan-schema.md)和[产物与交付](references/deliverables.md)。

## 执行步骤

### 第 1 步 · 接需求

1. 先查：当前画像 `profiles/<画像>/`、历史产物 `outputs/`、用户本次原话。已有信息不重复问。
2. 提取：主题、必须包含、人群、场景、语气、产品事实、视觉偏好、参考链接。
3. 写 `outputs/<主题>/assets/brief.md`，用 3–5 行向用户确认“主题 / 必须包含 / 关键假设”，不逐条复述原话。
4. 进入第 2 步，不空等“完美需求”。

### 第 2 步 · 补齐信息

只问三类缺口，最多 3 个问题，一次问完：

- **事实**：产品名、责任、保额、保费、免赔、比例、等待期、健康告知、核保、续保；监管/政策文件的版本、地区、年度。
- **方向**：用户明确“必须写/不能写”的内容；主题本身有歧义。
- **红线**：点名产品、非标体/高龄/慢病、惠民保、收益或理财表达。

其余给默认假设并写明。用户回“继续/开”，按假设直接生成。判定表与追问示例见[接需求与补齐](references/intake.md)。

### 第 3 步 · 生成 4 套方案

1. 先读[4 套切入角度](references/angles.md)，定 4 张角度卡：读者处境、搜索意图、骨架、证据、承诺。4 套至少 3 种骨架，标题和封面主文案不能重复。
2. 再写内容。按下方协作表读 insurance-xhs：标题走 title-writing，正文走 writing-workflow + xhs-copy-craft + human-speech + emotion-and-opinion，重疾题材加 critical-illness-craft。
3. 每套交齐：角度、适合谁、标题（含备选）、封面文案、封面图、正文、标签、事实清单。
4. 封面必须真出图：读[封面出图](references/cover-render.md)，4 张 3:4、同一视觉体系、4 种骨架；HTML 路线渲染后跑 card_audit，FAIL 重渲。
5. 按[方案 JSON](references/plan-schema.md)写 `outputs/<主题>/方案.json`，然后跑：

```bash
python skills/builtin/insurance-xhs-proposal/scripts/build_plan.py check --plan "outputs/<主题>/方案.json"
python skills/builtin/insurance-xhs-proposal/scripts/build_plan.py render --plan "outputs/<主题>/方案.json"
```

`check` 有 ERROR 就先修 JSON，不带着问题渲染。

### 第 4 步 · 分项溯源

- 每套的标题、封面、正文**各自**带 `refs`：来源标题、作者、日期、链接、借鉴点、不搬什么、核对到哪一步。
- 来源优先级：本地研究包 → 本次实时检索 → 用户给的链接/截图 → 方法文档（标“方法”）→ 无对标样本（原创）。
- 保险事实单独列 `facts`：`已核`（文件 + 条款/页码 + 版本/地区）/ `待核实`（查什么、找谁、影响哪句）/ `不适用`。
- 研究样本只证明表达方式，不证明其保险结论、身份或转化；高互动不等于正确。
- 禁止编链接、点赞、作者、日期、原帖结论；禁止用“业内都知道”代替依据。

完整格式、来源选择与禁止项见[分项溯源](references/traceability.md)。

### 第 5 步 · 选择与修改

1. 用户选定一套（如“第 2 套”）后，先复述“改什么 / 不改什么”，再动笔。
2. 改前快照，再改：

```bash
python skills/builtin/insurance-xhs-proposal/scripts/build_plan.py snapshot --plan "outputs/<主题>/方案.json" --label v1
```

3. 只改用户指定范围，其余逐字保留；在 `revisions` 记意见、改动、保留、未采纳原因。
4. 封面文案变了就重渲封面并重跑 audit；事实变了就重核 `facts`；然后重跑 `check` 与 `render`。
5. 在方案 JSON 写 `selected: <套号>`，对比页会标出选定项；用户确认后再导出：

```bash
python skills/builtin/insurance-xhs-proposal/scripts/build_plan.py export --plan "outputs/<主题>/方案.json" --set 2
```

导出件标“工作草稿 · 待人工确认”，不说“审核通过”。

## 交付前自检

- 4 套齐全；标题、封面主文案不重复；至少 3 种骨架。
- 4 张封面非空、3:4、能打开；HTML 路线 card_audit 全 PASS。
- 标题/封面/正文都有溯源：真实链接或“无对标样本”，没有编造。
- 所有具体产品结论都进事实表；待核实项有下一步和影响句。
- 修改记录能追到原稿快照；对比页、导出件、manifest 指向同一版。

## 与 insurance-xhs 协作

| 任务 | 先读 insurance-xhs 的 |
|---|---|
| 选题与角度 | [SKILL.md](../insurance-xhs/SKILL.md)、[搜索与选题](../insurance-xhs/references/topics.md)、[社区标题工作流](../insurance-xhs/references/community-title-workflow.md) |
| 标题 | [标题统一写法](../insurance-xhs/references/title-writing.md)、[标题来源](../insurance-xhs/references/title-sources.md) |
| 正文 | [写作流程](../insurance-xhs/references/writing-workflow.md)、[小红书表达](../insurance-xhs/references/xhs-copy-craft.md)、[人感检查](../insurance-xhs/references/human-speech.md)、[情绪与观点](../insurance-xhs/references/emotion-and-opinion.md) |
| 证据与实用性 | [证据与实用性](../insurance-xhs/references/evidence-and-value.md) |
| 风控与初查 | [内容风控](../insurance-xhs/references/content-risk-rules.md)、[合规初查](../insurance-xhs/references/compliance.md) |
| 重疾题材 | [重疾险表达边界](../insurance-xhs/references/critical-illness-craft.md)、[研究数据索引](../insurance-xhs/references/critical-illness-data-index.md) |
| 整组图文交流 | [社区中的图文交流](../insurance-xhs/references/community-image-posts.md) |

冲突时：事实与风控以 insurance-xhs 和项目最新要求为准；4 套结构、溯源字段、改稿留痕按本 SKILL 执行。

## Profile 感知

- **有 Profile**：从 identity 取账号名做封面水印；从 style 取配色/风格/语气；从 audience 取人群与场景；从 preferences 取红线。4 套都用同一账号视觉体系。
- **无 Profile**：按通用模式写，封面水印用“工作草稿 · 待确认”；不补造身份、经历、城市、从业年限、客户数和理赔结果。
- 画像只影响表达与视觉，不改变事实状态；没有依据的产品结论仍标待核实。

## 一句话启动示例

“主题：百万医疗险续保；必须包含：续保条件和停售风险；人群：30–40 岁家庭；场景：搜索比较；语气：克制。出 4 套图文方案，每套带封面和参考案例。”

收到后按第 1–2 步解析；缺产品条款只问一次，没有就标待核实，不空等。

## 不要做的事

- 不要 4 套只换标题同义词，或 4 张封面只换一行字。
- 不要用 AI 生图做文字封面；不要用占位图、空白图、纯文字卡冒充封面。
- 不要为了凑“故事”编客户、编对话、编理赔结果。
- 不要把研究样本的封面、配图、正文直接当自己的稿子；引用时保留来源，二创另写。
- 不要在没有条款时写具体责任、价格、保额、核保或理赔结论。
- 不要在用户未选定前导出“终稿”，也不要说“已通过审核/保证合规”。
