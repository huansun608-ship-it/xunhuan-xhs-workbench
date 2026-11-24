# 产物、改稿留痕与交付

## 一、目录

一个方案项目一个目录，成品放根，中间件进 `assets/`：

```
outputs/<主题>/
├── 方案.json                 # 单一真相源
├── 方案对比.html             # 4 套对比页，内嵌封面
├── 修改记录.md               # 每轮意见、改动、保留、快照
├── 选定方案_<标题>.md        # 用户选定后导出
├── 封面.png                  # 选定方案的封面副本
├── covers/
│   ├── cover_set_1.png
│   ├── cover_set_2.png
│   ├── cover_set_3.png
│   └── cover_set_4.png
├── history/
│   └── v1.json               # 改稿前快照
├── assets/
│   ├── brief.md
│   ├── covers.html           # 卡面 HTML（中间件）
│   └── references/           # 检索结果、用户给的链接清单
└── .easel.json
```

主题用人类可读的具体名字，不用 `xhs`、`test`、`方案` 这类泛名。

## 二、方案对比页

由脚本生成，不手写：

```bash
python skills/builtin/insurance-xhs-proposal/scripts/build_plan.py render --plan "outputs/<主题>/方案.json"
```

页面必须让用户一眼看到：

- 4 张封面图（不是链接、不是占位图）。
- 每套的角度、骨架、标题、封面文案、正文。
- 标题/封面/正文各自的溯源，展开可见。
- 事实清单及“已核/待核实”标记。
- 修改记录。

## 三、改稿留痕

每轮修改前先快照：

```bash
python skills/builtin/insurance-xhs-proposal/scripts/build_plan.py snapshot --plan "outputs/<主题>/方案.json" --label v1
```

然后在 `方案.json` 的 `revisions` 追加一条，再改内容。规则：

- 一轮只记一条；同一轮里用户提了多句，合并成一条 `instruction`。
- `changed` 写实际动过的字段；`preserved` 写明确没动的部分。
- 未采纳的意见写进 `note`，说明原因，不静默丢掉。
- 快照只增不改；要覆盖同名快照必须显式确认。
- 原稿永远保留在 `history/` 和 `revisions` 的 `snapshot` 指向里。

`修改记录.md` 由导出时生成，格式：

```md
## 第 1 轮 · 方案 2

- 意见：用户原话
- 改动：标题、封面主文案
- 保留：正文、标签
- 快照：history/v1.json
- 状态：待确认
- 说明：未采纳的部分及原因
```

## 四、导出

用户选定后才导出：

```bash
python skills/builtin/insurance-xhs-proposal/scripts/build_plan.py export --plan "outputs/<主题>/方案.json" --set 2
```

导出内容：

- 选定方案的标题、封面文案、正文、标签。
- 事实清单（含待核实项）。
- 分项溯源（标题/封面/正文）。
- 该套的修改记录。
- 封面复制为项目根的 `封面.png`；需要单独放目录时再加 `--out`。

导出文件顶部标“工作草稿，待人工确认”，不写“审核通过”“保证合规”。

## 五、登记

收尾用 manifest 登记，供内容库展示和下游取用：

```bash
python skills/shared/scripts/manifest.py record --topic <主题> --layer plan \
  --skill insurance-xhs-proposal --outputs 方案.json,方案对比.html,选定方案_<标题>.md \
  --summary "4 套角度，封面已渲染，待核实 X 条"
```

```bash
python skills/shared/scripts/manifest.py meta --topic <主题> \
  --title "<主题>" --platform 小红书 --kind cards --status draft \
  --tags "保险,图文方案" --cover 封面.png \
  --deliverables 方案对比.html,方案.json,选定方案_<标题>.md
```

有画像时补 `--profile <画像>`；`--outputs` 和 `--deliverables` 用逗号分隔，路径相对项目目录。

## 六、交付话术

给用户的最终回复控制在 5 块：

1. 一句话说明 4 套的差别（不是四段长文）。
2. 推荐哪套、为什么（材料、人群、场景各一句）。
3. 4 张封面的位置和对比页路径。
4. 待核实清单：哪几条、找谁补。
5. 下一步：选哪套、怎么改；提醒发布前按机构要求报备与审核。

不要把整篇正文贴进对话；让用户打开对比页看。

## 七、交付前自检

- 4 套齐全，标题/封面主文案不重复，骨架至少 3 种。
- 4 张封面非空、3:4、能打开；`card_audit` 全 PASS（HTML 路线）。
- 每个位置的溯源都有链接或“无对标样本”说明；没有编造。
- 事实清单覆盖所有具体产品结论；待核实项有下一步。
- 修改记录能追溯到原稿快照。
- 对比页、导出文件、manifest 三处指向同一版方案。
