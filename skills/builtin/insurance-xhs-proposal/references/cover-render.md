# 封面出图

4 套方案必须有 4 张**真的能打开的封面图**，不能只写封面文案，也不能用占位图。

## 一、规格

- 3:4 竖版，视口 1080×1440。
- PNG，非空；文件名 `covers/cover_set_1.png` … `cover_set_4.png`。
- 4 张同一账号视觉体系：同一配色、同一字体方案、同一水印位置。
- 4 张不同骨架：不能同一张底图只换一行字。

## 二、两条出图路线

### A. 卡片设计路线（默认）

适用于大多数账号。流程：

1. 读 [card-design](../../card-design/SKILL.md)，从 [styles.md](../../card-design/references/styles.md) 选 1 个风格，锁定字体与配色；4 张都用这一套。
2. 按 [card-recipes.md](../../card-design/references/card-recipes.md) 的封面骨架排版；正文不小于 28px，标题 96–140px，副文案 40–48px，信息点 34–40px。
3. 写一个 HTML，里面放 4 个 `.cover` 元素，每个 1080×1440；CSS 内联，不引外部字体/图片，中文用系统字体栈。
4. 渲染：

```bash
python skills/shared/scripts/render_card.py \
  --html "outputs/<主题>/assets/covers.html" \
  --out-dir "outputs/<主题>/covers" \
  --all ".cover" --prefix cover_set \
  --width 1080 --height 1440 --scale 1
```

默认 `--scale 2` 会输出 2160×2880（同样 3:4，更清晰）；要严格 1080×1440 就加 `--scale 1`。文件名会是 `cover_set_1.png` 到 `cover_set_4.png`。

5. 质检：

```bash
python skills/builtin/card-design/scripts/card_audit.py audit -f "outputs/<主题>/covers/cover_set_*.png"
```

有 FAIL 就按 `card-design/references/layout-laws.md` 的欠填修正阶梯补内容或换骨架，重渲到全 PASS。

### B. 纸面手绘路线（仅在明确要求时）

只有用户明确说“爱丽对标/纸面手绘信息图”，或当前画像 style 明确指定时才用。流程：

1. 读 `skills/shared/references/insurance-handdrawn-spec.md`，按它的规则写 JSON。
2. 封面页 `layout` 用 `overview`，恰好 4 个 panel；每行不超过 13 个字符；标题每行不超过 11 个字符。
3. 渲染：

```bash
python skills/shared/scripts/render_insurance_handdrawn.py "outputs/<主题>/assets/covers.json" "outputs/<主题>/covers"
```

4. 检查页数、1080×1440、无溢出、标题可读；脚本的 audit 只查技术，不查内容合规。

## 三、封面文案结构

| 位置 | 写什么 | 长度 |
|---|---|---|
| kicker | 系列标签，不冒充资质 | ≤8 字 |
| headline | 一个判断、问题或场景，2 行以内 | 6–14 字 |
| subline | 补充条件或阅读理由 | ≤24 字 |
| blocks | 3–4 个信息点，每点一个意思 | 每点 ≤14 字 |
| footer | 账号名 / “工作草稿 · 待确认” | ≤12 字 |

封面文案不是标题的复制：标题可以有搜索词和完整句，封面要在小图上 1 秒看懂。两者必须兑现同一个承诺。

## 四、4 张封面的骨架差异

| 套 | 骨架 | 视觉重点 |
|---|---|---|
| 1 搜索答案 | 问题 + 3 个判断点 | 编号清单，标题在上 |
| 2 反常识判断 | 一句判断 + 条件分叉 | 大字判断，左右/上下对照 |
| 3 场景代入 | 场景一句 + 三步动作 | 时间线或流程 |
| 4 算账对比 | 两列对比 / 账本 | 数字、条件、边界 |

如果第 5 套（政策/实录）替换了其中一套，用它的证据形态做骨架：文件一句 + 影响三条，或产物框 + 关键一步。

## 五、设计与风控底线

- 填满画幅：内容覆盖 ≥75% 画高，任何无理由空白带 >15% 判失败。
- 大标题用细字重，正文不用纯黑；不靠阴影、圆角、渐变堆高级感。
- 禁蓝紫科技渐变、渐变字、玻璃拟态、emoji 当图标、居中一切。
- 不用疾病恐吓图、医院实景偷拍、客户病历、身份证、保单原件。
- 不写“必买/必赔/人人都能买/保证续保/保证理赔”等承诺。
- 条件不能藏成读不清的小字；封面承诺的条件要在副文案或信息点里出现。
- 水印只放账号名或“工作草稿 · 待确认”，不冒用机构、资质或他人身份。

## 六、目视检查

渲染后必须打开 PNG 看一遍，逐项确认：

- 标题在手机小图上能读清，没有被裁切、溢出、压字。
- 中文标点、数字、百分号没有缺字或乱码。
- 4 张的配色、字体、边距一致，但骨架明显不同。
- 封面文案与标题、正文说同一件事。
- 没有把研究样本的封面、插画、头像、构图直接搬过来。

## 七、失败处理

- `render_card.py` 报未安装 playwright/chromium：先按提示安装；装不上就改走手绘路线（Pillow），或明确告诉用户“封面链路不可用”，暂停交付。
- 手绘脚本也失败：停下来说明原因，不要用纯文字卡、空白图或 AI 生图冒充封面。
- 渲染成功但 `card_audit` FAIL：按设计系统补内容或换骨架重渲，不交付 FAIL 的图。
- 4 张图有一张失败：只重渲那一张，不整套重来；最终 4 张必须齐全。
