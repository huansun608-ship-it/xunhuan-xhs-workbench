# 方案 JSON 字段

`方案.json` 是单一真相源：对比页、导出 Markdown、修改记录都从它生成。不要手改 `方案对比.html`。

## 一、顶层

```json
{
  "schema": 1,
  "topic": "主题（人类可读，和目录名一致）",
  "created": "2026-11-24",
  "profile": "画像名，可空",
  "brief": {
    "must_include": "必须包含的信息，一条字符串或列表",
    "audience": "目标人群；不写年龄/疾病标签时说明",
    "scenario": "使用场景",
    "tone": "语气",
    "product_facts": ["用户提供的产品事实，注明来源"],
    "assumptions": ["缺省假设 1", "缺省假设 2"]
  },
  "style": {
    "route": "card 或 handdrawn",
    "style_name": "卡片设计系统的风格名",
    "palette": "锁定配色名或 hex",
    "font": "字体方案"
  },
  "sets": [],
  "revisions": [],
  "selected": null
}
```

## 二、每套方案

```json
{
  "id": 1,
  "angle": {
    "name": "搜索答案",
    "reader_situation": "正在比较两种方案的人",
    "search_intent": "读者实际会搜的那句话",
    "skeleton": "攻略清单型",
    "evidence": "条款与官方资料",
    "promise": "点开后能得到的具体答案",
    "why_it_fits": "为什么这套角度适合当前材料"
  },
  "title": {
    "text": "标题正文",
    "alternatives": ["备选 1", "备选 2"],
    "refs": [],
    "refs_note": "无对标样本（原创）"
  },
  "cover": {
    "copy": {
      "kicker": "系列标签，≤8 字",
      "headline": "封面主文案，6–14 字",
      "subline": "副文案，≤24 字",
      "blocks": ["信息点 1", "信息点 2", "信息点 3"],
      "footer": "账号名或‘工作草稿 · 待确认’"
    },
    "image": "covers/cover_set_1.png",
    "refs": [],
    "refs_note": "无对标样本（原创）"
  },
  "body": {
    "text": "正文全文，保留换行",
    "tags": ["标签1", "标签2"],
    "refs": [],
    "refs_note": "无对标样本（原创）"
  },
  "facts": [],
  "status": "draft"
}
```

字段要求：

- `id`：1–4，唯一；`build_plan.py export --set` 用它。
- `angle.name / reader_situation / skeleton`：不能空。
- `title.text`：一条；备选放 `alternatives`，不要另起一套。
- `cover.copy.headline`：不能空；`blocks` 3–4 条，每条一个信息点。
- `cover.image`：相对方案目录的路径，如 `covers/cover_set_1.png`；必须是已渲染的非空 PNG。
- `body.text`：正文全文；标签放 `tags`，不写进正文。
- `status`：`draft` / `待确认` / `已确认`，默认 `draft`。

## 三、溯源

`title`、`cover`、`body` 各自带 `refs` 与 `refs_note`：

```json
{
  "refs": [
    {
      "kind": "案例",
      "title": "原帖标题",
      "author": "作者",
      "date": "2026-05-28",
      "url": "https://…",
      "borrowed": "借鉴的具体动作",
      "not_borrowed": "不搬的身份/结论/数字",
      "checked": "已看正文与封面"
    }
  ],
  "refs_note": "补充说明；没有案例时写‘无对标样本（原创）’"
}
```

硬规则：

- 每个位置要么有 `refs`，要么 `refs_note` 非空；两者都空，`check` 报错。
- 每条 ref 必须有 `title`、`url`（http/https）、`borrowed`。
- 没有公开链接的截图、口头参考，写进 `refs_note`，不要伪造 URL。
- 方法文档标 `kind: 方法`，不冒充案例。

## 四、事实

```json
{
  "statement": "要核对的保险事实",
  "status": "已核",
  "basis": "文件 + 条款/页码 + 版本/日期 + 地区",
  "next_step": "",
  "impact": "若为假，正文哪句要改"
}
```

- `status` 只能是 `已核` / `待核实` / `不适用`。
- `已核` 必须有 `basis`。
- `待核实` 必须有 `next_step`，写清查什么、找谁、看哪一条。
- 正文里标“（待核实）”的句子，表里必须有对应行。

## 五、修改记录

```json
{
  "round": 1,
  "at": "2026-11-24 11:20",
  "set": 2,
  "instruction": "用户的原话意见",
  "changed": ["title", "cover.copy.headline"],
  "preserved": ["body", "tags"],
  "snapshot": "history/v1.json",
  "note": "未采纳的部分及原因",
  "status": "待确认"
}
```

规则：

- 每轮一条；`set` 用套号，跨套修改可写 `"all"`。
- 改前先 `snapshot`；`snapshot` 指改前版本，不覆盖旧快照。
- `changed` 写实际动过的字段；`preserved` 写明确没动的部分。
- `instruction` 保留用户原话，不改写成自己的总结。
- `status` 默认 `待确认`；用户确认后才写 `已确认`。

## 六、selected

用户选定后写套号：

```json
"selected": 2
```

`export` 用 `--set` 指定；`selected` 只作记录，不强制。

## 七、检查命令

```bash
python skills/builtin/insurance-xhs-proposal/scripts/build_plan.py check --plan "outputs/<主题>/方案.json"
```

`check` 会拦：

- 不是正好 4 套、id 重复。
- 标题/封面主文案重复，或 3 套同骨架。
- 缺标题、封面主文案、封面图、正文。
- 封面图不存在、疑似空文件，或 PNG 不是 3:4。
- 标题/封面/正文没有溯源。
- ref 缺 title/url/borrowed，或 url 不是 http(s)。
- 事实状态非法，已核缺 basis，待核实缺 next_step。

警告不拦：标题超过 24 字、正文少于 300 字、2 套同骨架、读者处境完全相同、ref 没写 checked、封面 PNG 宽度低于 1080px。
