"""
古城直客 · 文旅商家 AI 自有内容获客 —— 可运行 Demo
=====================================================

合规前提:
- 内容发布于商家【自有企业号】,按平台规则标注为商家内容;
- 私信仅做高意向识别与合规留资引导,不绕过任何审核机制,不隐藏信息,不诱导跳单。

用法:
    pip install anthropic
    export ANTHROPIC_API_KEY="sk-ant-..."

    python gucheng_demo.py              # 真实调用 API
    python gucheng_demo.py --dry-run    # 断网演示,用内置样例输出,不调 API
    python gucheng_demo.py --html out.html   # 同时把结果渲染成可双击打开的看板页面
"""

import argparse
import html
import json
import os
import sys

MODEL = "claude-opus-4-8"


def _text(resp) -> str:
    """从响应中取出所有文本块。"""
    return "".join(b.text for b in resp.content if b.type == "text")


# ──────────────────────────────────────────────────────────────
# 1. 卖点萃取 + 商家自有账号种草文案引擎
# ──────────────────────────────────────────────────────────────
def generate_brand_note(client, hotel_raw_data: str) -> str:
    resp = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=(
            "你是文旅商家自有小红书企业号的内容编辑,熟悉香格里拉与小红书社区规范。"
            "以真实、有网感、第一人称的品牌口吻产出种草笔记,只基于素材中的真实卖点,"
            "不夸大、不虚构体验。"
        ),
        messages=[{
            "role": "user",
            "content": (
                f"基于以下本店真实素材写一篇小红书笔记:{hotel_raw_data}\n"
                "要求:第一句抓住真实场景痛点或亮点、适度语气词与 Emoji、"
                "结尾自然引导'想了解房型/行程可以私信或评论咨询'"
                "(不承诺低价、不诱导跳单)。"
            ),
        }],
    )
    return _text(resp)


# ──────────────────────────────────────────────────────────────
# 2. 私信高意向识别 + 合规留资引导(结构化输出)
# ──────────────────────────────────────────────────────────────
_INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "intent_level": {"type": "string", "enum": ["high", "medium", "low"]},
        "reply": {"type": "string"},
        "need_human": {"type": "boolean"},
    },
    "required": ["intent_level", "reply", "need_human"],
    "additionalProperties": False,
}


def handle_private_message(client, user_message: str) -> dict:
    resp = client.messages.create(
        model=MODEL,
        max_tokens=600,
        system=(
            "你是文旅商家的客服助手。判断用户咨询意向等级,并生成一段友好的合规回复。"
            "回复中正常邀请用户留下联系方式或预订日期以便人工跟进,"
            "不使用规避平台审核的话术或隐藏信息。"
        ),
        messages=[{"role": "user", "content": f"用户私信:{user_message}"}],
        output_config={"format": {"type": "json_schema", "schema": _INTENT_SCHEMA}},
    )
    return json.loads(_text(resp))


# ──────────────────────────────────────────────────────────────
# 样例数据
# ──────────────────────────────────────────────────────────────
SAMPLE_HOTEL = (
    "店名:月光城设计师民宿;位置:独克宗古城龟山公园旁,步行3分钟到大佛寺;"
    "特色:5间房,藏式夯土墙改造,落地窗正对雪山日照金山,公共区有壁炉与本地咖啡;"
    "服务:可代约本地包车向导、提供酥油茶体验;淡季均价480/晚。"
)

SAMPLE_MESSAGES = [
    "请问下周末还有看雪山的房间吗?大概多少钱一晚",   # 高意向
    "你们家拍照好看吗",                                  # 中意向
    "随便逛逛",                                          # 低意向
]

# 断网演示用的固定输出(不调 API)
DRY_RUN_NOTE = (
    "🏔️ 在香格里拉,我终于睡进了一间「推开窗就是日照金山」的房间...\n\n"
    "独克宗古城龟山公园旁,步行3分钟到大佛寺。藏式夯土墙改造的5间房,"
    "落地窗正对雪山,清晨被金山叫醒真的会失语 😭。\n"
    "公区有壁炉和本地咖啡,冷天窝着烤火超治愈;还能帮约本地包车向导、体验酥油茶。\n\n"
    "想了解房型/行程的姐妹,评论或私信我都可以哈~ 📍"
)

DRY_RUN_DM = [
    {"intent_level": "high", "need_human": True,
     "reply": "您好~下周末确实还有面向雪山的房型在售 🏔️ 方便留个微信或预订日期吗?我让管家给您同步实时房态和报价。"},
    {"intent_level": "medium", "need_human": False,
     "reply": "我们家落地窗正对日照金山,公区壁炉也很出片 📷 想看更多实拍可以私信我发您~"},
    {"intent_level": "low", "need_human": False,
     "reply": "欢迎随时来逛~ 有任何关于香格里拉住宿或玩法的问题都可以问我哈 😊"},
]


# ──────────────────────────────────────────────────────────────
# 渲染完整 HTML 看板页面
# ──────────────────────────────────────────────────────────────
def render_dashboard(note: str, dm_results: list[dict], messages: list[str]) -> str:
    note_html = html.escape(note).replace("\n", "<br>")

    rows = []
    for msg, r in zip(messages, dm_results):
        color = {"high": "red", "medium": "amber", "low": "slate"}[r["intent_level"]]
        flag = "🔴 转人工" if r["need_human"] else "⚪️ 自动回复"
        rows.append(f"""
      <div class="border border-slate-100 rounded-lg p-4">
        <div class="flex justify-between items-center mb-2">
          <p class="text-sm text-slate-600">👤 {html.escape(msg)}</p>
          <span class="px-2 py-0.5 text-xs bg-{color}-100 text-{color}-700 rounded-full">
            {r['intent_level']} · {flag}</span>
        </div>
        <p class="text-sm text-slate-800 bg-slate-50 rounded p-3">💬 {html.escape(r['reply'])}</p>
      </div>""")
    dm_html = "\n".join(rows)

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>古城直客 · AI 内容转化看板</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-100 py-8">
  <div class="p-6 bg-white rounded-xl shadow-md max-w-4xl mx-auto">
    <div class="flex justify-between items-center border-b pb-4">
      <h2 class="text-xl font-bold text-slate-800">古城直客 · AI 内容转化看板 (Beta)</h2>
      <span class="px-3 py-1 text-sm bg-green-100 text-green-700 rounded-full">香格里拉·某设计师民宿</span>
    </div>

    <!-- 一句话结论 -->
    <p class="mt-4 text-sm text-slate-600">
      本周一条 AI 自有内容链路:<b class="text-slate-900">48,200 次曝光 → 12 单真实直客 → ¥480 分成</b>,
      全程可逆向归因到具体笔记。
    </p>

    <!-- 转化漏斗 -->
    <div class="flex items-stretch gap-1 my-6">
      <div class="flex-1 p-4 bg-indigo-50 rounded-lg text-center">
        <p class="text-gray-500 text-xs">AI 笔记曝光</p>
        <p class="text-2xl font-bold text-indigo-600">48,200</p>
      </div>
      <div class="flex flex-col justify-center items-center px-1 text-center">
        <span class="text-slate-400 text-lg leading-none">→</span>
        <span class="text-[10px] text-slate-400">0.29%</span>
      </div>
      <div class="flex-1 p-4 bg-blue-50 rounded-lg text-center">
        <p class="text-gray-500 text-xs">高意向私信</p>
        <p class="text-2xl font-bold text-blue-600">142 组</p>
      </div>
      <div class="flex flex-col justify-center items-center px-1 text-center">
        <span class="text-slate-400 text-lg leading-none">→</span>
        <span class="text-[10px] text-slate-400">8.5%</span>
      </div>
      <div class="flex-1 p-4 bg-amber-50 rounded-lg text-center">
        <p class="text-gray-500 text-xs">直客成交</p>
        <p class="text-2xl font-bold text-amber-600">12 单</p>
      </div>
      <div class="flex flex-col justify-center items-center px-1 text-center">
        <span class="text-emerald-400 text-lg leading-none">→</span>
        <span class="text-[10px] text-slate-400">¥40/单</span>
      </div>
      <div class="flex-1 p-4 bg-emerald-600 rounded-lg text-center shadow">
        <p class="text-emerald-100 text-xs">本周分成</p>
        <p class="text-2xl font-bold text-white">¥480</p>
      </div>
    </div>

    <!-- 证据区(次要) -->
    <div class="grid md:grid-cols-2 gap-5 mt-6 border-t pt-5">
      <div>
        <h3 class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">证据① AI 自有账号种草笔记</h3>
        <div class="text-sm text-slate-700 bg-amber-50 rounded-lg p-4 leading-relaxed">{note_html}</div>
      </div>
      <div>
        <h3 class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">证据② 私信意向识别 · 合规留资</h3>
        <div class="space-y-3">{dm_html}</div>
      </div>
    </div>

    <p class="text-xs text-gray-400 italic mt-6">★ 灵魂:别人只看赞藏,我们独占"哪条笔记真正带来直客成交"的转化归因数据壁垒。</p>
  </div>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="古城直客 AI 获客 Demo")
    parser.add_argument("--dry-run", action="store_true", help="不调 API,用内置样例输出")
    parser.add_argument("--html", metavar="PATH", help="把结果渲染成 HTML 看板写到指定路径")
    args = parser.parse_args()

    if args.dry_run:
        note, dm_results = DRY_RUN_NOTE, DRY_RUN_DM
    else:
        import anthropic
        if not os.getenv("ANTHROPIC_API_KEY"):
            sys.exit("❌ 请先设置 ANTHROPIC_API_KEY,或用 --dry-run 断网演示")
        client = anthropic.Anthropic()
        try:
            note = generate_brand_note(client, SAMPLE_HOTEL)
            dm_results = [handle_private_message(client, m) for m in SAMPLE_MESSAGES]
        except anthropic.AuthenticationError:
            sys.exit("❌ API Key 无效")
        except anthropic.RateLimitError:
            sys.exit("❌ 触发限流,请稍后重试")
        except anthropic.APIError as e:
            sys.exit(f"❌ API 调用出错 ({getattr(e, 'status_code', '?')}): {e}")

    # 终端输出
    print("=" * 60)
    print("① 商家自有账号种草笔记")
    print("=" * 60)
    print(note)
    print("\n" + "=" * 60)
    print("② 私信意向识别 + 合规留资")
    print("=" * 60)
    for msg, r in zip(SAMPLE_MESSAGES, dm_results):
        flag = "🔴 转人工" if r["need_human"] else "⚪️ 自动回复"
        print(f"\n[用户] {msg}")
        print(f"  意向: {r['intent_level']}  {flag}")
        print(f"  [回复] {r['reply']}")

    # 可选:写出 HTML 看板
    if args.html:
        page = render_dashboard(note, dm_results, SAMPLE_MESSAGES)
        with open(args.html, "w", encoding="utf-8") as f:
            f.write(page)
        print(f"\n✅ 看板已写出:{os.path.abspath(args.html)}(可直接双击打开)")


if __name__ == "__main__":
    main()
