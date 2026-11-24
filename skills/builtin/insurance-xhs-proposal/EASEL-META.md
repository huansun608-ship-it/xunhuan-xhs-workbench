# Easel SKILL 元数据

| 字段 | 值 |
|---|---|
| **SKILL 名称** | insurance-xhs-proposal |
| **所属层** | plan |
| **来源** | 本项目自研；编排 insurance-xhs 与 card-design / card-xiaohongshu |
| **功能描述** | 把一句话需求做成 4 套角度不同的小红书图文方案：标题、封面图、封面文案、正文、分项溯源、事实状态、改稿留痕与导出 |
| **核心脚本** | `scripts/build_plan.py`（标准库；check / render / export / snapshot） |
| **依赖** | insurance-xhs（内容判断）、card-design + card-xiaohongshu（封面 HTML 路线）、render_insurance_handdrawn.py（手绘路线）、manifest.py（登记） |
| **profile_aware** | true |
| **自包含** | 无画像可用；封面需 playwright+chromium 或 Pillow 手绘路线 |

## 设计说明

- **不复制写作规则**：选题、标题、正文、人感、证据、风控全部读 insurance-xhs，避免两套规则漂移。
- **4 套是结构契约**：角度卡先定，标题/封面/正文后写；脚本硬检查 4 套、标题与封面主文案重复、3 套同骨架、分项溯源缺失。
- **封面必须真出图**：默认走 card-design + card-xiaohongshu 的 HTML→截图；仅在明确“纸面手绘/爱丽对标”时走手绘脚本。
- **溯源分两类**：表达溯源给案例链接与借鉴点；事实依据给条款/文件/版本/地区，没有就标待核实。
- **改稿留痕**：改前快照，`revisions` 记录意见、改动、保留、未采纳原因；导出件永远是工作草稿。

## 验证

- `check` 对缺封面、缺溯源、编造 URL、事实状态非法等硬拦。
- `render` 生成内嵌封面的单文件 HTML，可直接预览/打印。
- `export` 输出选定方案 Markdown、封面副本与修改记录。
- 未跑真实发布；本 SKILL 不发布。
