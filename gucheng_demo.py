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
        level = r["intent_level"]
        flag = "🔴 转人工" if r["need_human"] else "⚪️ 自动回复"
        rows.append(f"""
        <div class="dm">
          <div class="dm-head">
            <span class="dm-q">👤 {html.escape(msg)}</span>
            <span class="pill pill-{level}">{level} · {flag}</span>
          </div>
          <div class="reply">💬 {html.escape(r['reply'])}</div>
        </div>""")
    dm_html = "\n".join(rows)

    css = """
* { box-sizing:border-box; }
body { margin:0; padding:32px 16px; background:#f1f5f9;
  font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif; color:#1e293b; }
.card { max-width:880px; margin:0 auto; background:#fff; border-radius:14px;
  box-shadow:0 4px 16px rgba(15,23,42,.08); padding:28px; }
.head { display:flex; justify-content:space-between; align-items:center;
  border-bottom:1px solid #e2e8f0; padding-bottom:16px; gap:12px; flex-wrap:wrap; }
.head h2 { font-size:20px; font-weight:700; margin:0; color:#0f172a; }
.tag-merchant { background:#dcfce7; color:#15803d; font-size:13px; padding:4px 12px; border-radius:999px; }
.tag-demo { background:#fef3c7; color:#b45309; font-size:12px; padding:4px 10px; border-radius:999px; margin-left:6px; }
.concl { font-size:14px; color:#475569; margin:16px 0 4px; }
.concl b { color:#0f172a; }
.funnel { display:flex; align-items:stretch; gap:4px; margin:20px 0 0; }
.stage { flex:1; padding:14px 8px; border-radius:10px; text-align:center; }
.stage .lbl { display:block; font-size:12px; color:#64748b; }
.stage .num { display:block; font-size:23px; font-weight:700; margin-top:2px; }
.s-blue { background:#eff6ff; } .s-blue .num { color:#2563eb; }
.s-indigo { background:#eef2ff; } .s-indigo .num { color:#4f46e5; }
.s-amber { background:#fffbeb; } .s-amber .num { color:#d97706; }
.climax { background:#059669; box-shadow:0 2px 8px rgba(5,150,105,.3); }
.climax .lbl { color:#d1fae5; } .climax .num { color:#fff; }
.arrow { display:flex; flex-direction:column; justify-content:center; align-items:center; padding:0 2px; }
.arrow span { color:#94a3b8; font-size:18px; line-height:1; }
.arrow small { color:#94a3b8; font-size:10px; }
.attr { margin-top:12px; background:#f8fafc; border:1px dashed #cbd5e1; border-radius:8px;
  padding:10px 14px; font-size:13px; color:#475569; }
.attr b { color:#0f172a; }
.evidence { display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-top:22px;
  border-top:1px solid #e2e8f0; padding-top:20px; }
.ev-h { font-size:11px; font-weight:600; color:#64748b; letter-spacing:.05em;
  text-transform:uppercase; margin:0 0 8px; }
.note { font-size:14px; color:#334155; background:#fffbeb; border-radius:10px; padding:16px; line-height:1.7; }
.dm-list { display:flex; flex-direction:column; gap:12px; }
.dm { border:1px solid #eef2f7; border-radius:10px; padding:14px; }
.dm-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; gap:8px; }
.dm-q { font-size:13px; color:#475569; }
.pill { font-size:11px; padding:2px 8px; border-radius:999px; white-space:nowrap; }
.pill-high { background:#fee2e2; color:#b91c1c; }
.pill-medium { background:#fef3c7; color:#b45309; }
.pill-low { background:#f1f5f9; color:#475569; }
.reply { font-size:13px; color:#1e293b; background:#f8fafc; border-radius:8px; padding:12px; }
.soul { font-size:12px; color:#94a3b8; font-style:italic; margin-top:22px; }
@media (max-width:680px) {
  .funnel { flex-direction:column; }
  .arrow span { display:inline-block; transform:rotate(90deg); }
  .evidence { grid-template-columns:1fr; }
}
"""

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>古城直客 · AI 内容转化看板</title>
  <style>{css}</style>
</head>
<body>
  <div class="card">
    <div class="head">
      <h2>古城直客 · AI 内容转化看板 (Beta)</h2>
      <div>
        <span class="tag-merchant">香格里拉·某设计师民宿</span>
        <span class="tag-demo">样板演示数据</span>
      </div>
    </div>

    <p class="concl">本周 <b>47,832 次曝光</b> 沉淀 2,140 次互动 → <b>11 单真实直客</b> → <b>¥472 分成</b>,每单可逆向归因到具体笔记。</p>

    <div class="funnel">
      <div class="stage s-blue"><span class="lbl">内容互动</span><span class="num">2,140</span></div>
      <div class="arrow"><span>→</span><small>6.4%</small></div>
      <div class="stage s-indigo"><span class="lbl">高意向私信</span><span class="num">138</span></div>
      <div class="arrow"><span>→</span><small>8.0%</small></div>
      <div class="stage s-amber"><span class="lbl">直客成交</span><span class="num">11 单</span></div>
      <div class="arrow"><span>→</span><small>¥43/单</small></div>
      <div class="stage climax"><span class="lbl">本周分成</span><span class="num">¥472</span></div>
    </div>

    <div class="attr">📌 成交归因 · TOP 笔记:<b>#3「日照金山」</b> 5 单 · <b>#7「包车向导」</b> 4 单 · <b>#1「壁炉咖啡」</b> 2 单 —— 单条内容的成交贡献可追溯</div>

    <div class="evidence">
      <div>
        <h3 class="ev-h">证据① AI 自有账号种草笔记</h3>
        <div class="note">{note_html}</div>
      </div>
      <div>
        <h3 class="ev-h">证据② 私信意向识别 · 合规留资</h3>
        <div class="dm-list">{dm_html}</div>
      </div>
    </div>

    <p class="soul">★ 灵魂:别人只看赞藏,我们独占"哪条笔记真正带来成交"的转化归因数据壁垒——见上方成交归因。</p>
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
