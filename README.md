# 古城直客 · 文旅商家 AI 自有内容获客网络

> AI 早期机会验证项目(方向 3 · 内容 AI)— 张紫翊 · 2026-06

替滇西北古城文旅带(大理 / 丽江 / 腾冲 / 香格里拉)的体验型实体商家,用 AI 批量运营
**小红书企业号自有内容 + 合规私域**,按真实直客 / 复购分成,帮他们降低对 OTA 单一渠道的依赖。

**合规前提:** 内容发布于商家自有企业号、按平台规则标注为商家内容;私信仅做高意向识别与
留资引导,不绕过任何审核机制、不隐藏信息、不诱导跳单。

## 仓库内容

| 文件 | 说明 |
|---|---|
| `gucheng_demo.py` | 可运行 Demo:种草文案生成 + 私信意向识别,串成完整获客流程 |
| `dashboard_sample.html` | AI 转化看板(漏斗式),可直接双击打开 |

## 快速开始

```bash
pip install -r requirements.txt

# 断网演示:不调 API,用内置样例输出(评审现场最稳)
python3 gucheng_demo.py --dry-run

# 顺便生成可双击打开的看板页面
python3 gucheng_demo.py --dry-run --html dashboard.html

# 真实调用 API(需先设置 key)
export ANTHROPIC_API_KEY="sk-ant-..."
python3 gucheng_demo.py --html dashboard.html
```

## 工作流核心

- `generate_brand_note()` — 卖点萃取 + 商家自有账号种草文案引擎(`claude-opus-4-8`)
- `handle_private_message()` — 私信意向分级(high/medium/low)+ 合规留资引导,
  结构化输出 `{intent_level, reply, need_human}`

转化看板以漏斗呈现「曝光 → 高意向私信 → 直客成交 → 分成」,每条成交可逆向归因到具体笔记。

## 技术栈

Python · 官方 [`anthropic`](https://pypi.org/project/anthropic/) SDK · Claude `claude-opus-4-8` · Tailwind CSS
