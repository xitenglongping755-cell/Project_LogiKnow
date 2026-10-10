"""LogiKnow（ロジノウ）― 物流版・暗黙知継承アプリ

使い方は2段構え（10/10 チームMTGで決定）
    ステップ1：配送前チェック … 行き先と時間を入れると、その行き先で気をつけることを新しい順に表示
    ステップ2：トラブル検索   … 配送中に困ったことを入力すると、4つの情報源から解決策を探す

処理の流れ
    app.py（入力）→ search_service.py → query_processor.py（質問の加工）
                  → ranking.py（情報源ごとの検索エンジン）→ app.py（表示）

streamlit run app.py
"""

from datetime import datetime, time

import pandas as pd
import streamlit as st

import database as db
from ranking import SearchEngine
from search_service import LAYERS, search_all_sources

st.set_page_config(
    page_title="LogiKnow v0.1",
    page_icon="🚚",
    layout="wide"
)

# 表示順は固定（10/10 MTGで決定）：報告書 → 経験値 → 現地ルール → マニュアル
DISPLAY = [
    ("report", "📄 トラブル報告（類似事例）"),
    ("experience", "🧓 ベテランの経験値"),
    ("local_rule", "📍 現地ルール"),
    ("manual", "📘 マニュアル"),
]
MIN_SCORE = 5.0          # トラブル検索で表示する関連度の下限（これ未満はほぼ無関係なので出さない）
RECENT_DAYS = 30         # 配送前チェックで表示する報告書・経験値の期間
TIME_BANDS = ["早朝", "日中", "夜間"]


# ── DB と検索エンジン（アプリ起動中は使い回す） ───────────────────────
@st.cache_resource
def get_conn():
    conn = db.connect()
    db.init_db(conn)        # DBが無ければ作って、サンプルデータを入れる
    return conn


@st.cache_resource
def get_engines():
    """情報源ごとに検索エンジンを1つずつ作る"""
    engines = {}
    for layer in LAYERS:
        engine = SearchEngine()
        engine.build_index(db.get_pages(get_conn(), layer))
        engines[layer] = engine
    return engines


def refresh_engines():
    """ナレッジを登録・評価したら、検索エンジンを作り直す"""
    get_engines.clear()


def to_band(t: time) -> str:
    """到着時刻を時間帯に変換する"""
    if 4 <= t.hour < 8:
        return "早朝"
    if 8 <= t.hour < 17:
        return "日中"
    return "夜間"


def days_ago(created: str) -> str:
    try:
        d = (datetime.now() - datetime.fromisoformat(created)).days
    except ValueError:
        return ""
    return "今日" if d == 0 else f"{d}日前"


conn = get_conn()
master = db.master()
LOCATIONS = master["locations"]

# ── ヘッダー ──────────────────────────────────────────────────
st.title("🚚  :blue[LogiKnow v0.1] ")
st.caption("ベテランの経験を、全員の経験に。— 物流版ナレッジ検索ツール")

# ── 今日の配送（全タブ共通の入力）────────────────────────────────
# スマホではサイドバーが隠れて見えないので、タブの上に置く。押すと開く。
st.session_state.setdefault("driver", master["drivers"][0])
st.session_state.setdefault("destination", LOCATIONS[0])
st.session_state.setdefault("arrival", time(9, 0))
_label_time = st.session_state["arrival"].strftime("%H:%M")
with st.expander(f"🚚 今日の配送：{st.session_state['destination']}　{_label_time}　{st.session_state['driver']}"):
    destination = st.selectbox("行き先", LOCATIONS, key="destination")
    arrival = st.time_input("到着予定時刻", step=1800, key="arrival")
    driver = st.selectbox("ドライバー", master["drivers"], key="driver")
band = to_band(arrival)

# ── サイドバー：DBの状態 ──────────────────────────────────────
with st.sidebar:
    st.header("DB の登録状況")
    s = db.stats(conn)
    st.metric("ナレッジ登録数", f"{sum(s['by_layer'].values())} 件")
    st.metric("未回答の質問", f"{s['open_questions']} 件")


# ── ナレッジ1件のカード ─────────────────────────────────────────
def entry_card(e, key, show_score=False):
    with st.container(border=True):
        st.markdown(f"**{e['title']}**")
        st.markdown(e["content"])
        if e["reason"]:
            st.markdown(f"**なぜ：** {e['reason']}")
        meta = [f"出典：{e['source']}"]
        if e["source_ref"]:
            meta.append(e["source_ref"])
        meta.append(f"📍{e['location']}" if e["location"] else "📍共通")
        if e["time_band"]:
            meta.append(f"🕐{e['time_band']}")
        if e["created_at"]:
            meta.append(f"登録：{days_ago(e['created_at'])}")
        if e["creator"]:
            meta.append(e["creator"])
        if show_score:
            meta.append(f"関連度 {e['relevance_score']}")
        st.caption("　".join(meta))
        if st.button(f"👍 役に立った（{e['helpful']}）", key=f"{key}_helpful_{e['id']}"):
            db.add_helpful(conn, e["id"])
            refresh_engines()
            st.toast("ありがとうございます。評価を記録しました")
            st.rerun()


def show_results(results, key, show_score=False, empty_text=None):
    """4つの情報源の結果を、決まった順番で表示する"""
    for layer, heading in DISPLAY:
        items = results.get(layer, [])
        st.markdown(f"#### {heading}　<small>{len(items)}件</small>", unsafe_allow_html=True)
        if not items:
            st.caption((empty_text or {}).get(layer, "該当なし"))
        for e in items:
            entry_card(e, key=f"{key}_{layer}", show_score=show_score)


# ── タブ ──────────────────────────────────────────────────────
tab_pre, tab_search, tab_register, tab_question, tab_stats = st.tabs(
    ["🚚 配送前チェック", "🔍 トラブル検索", "📝 登録", "❓ 質問", "📊 活用状況"]
)

# ── ステップ1：配送前チェック ──────────────────────────────────
with tab_pre:
    st.subheader("配送前チェック")
    st.caption("エンジンをかける前に、行き先で気をつけることを確認しましょう。検索ワードは不要です。")
    st.info(f"**{destination}**　到着予定 {arrival.strftime('%H:%M')}（{band}）　※上の「今日の配送」で変更できます")

    pre = search_all_sources("", location=destination, engines=get_engines(), locations=LOCATIONS,
                             time_band=band, recent_days=RECENT_DAYS)
    total = sum(len(v) for v in pre.values())

    # 同じ条件での記録は1回だけ（画面の再実行のたびに数えないため）
    logged = st.session_state.setdefault("precheck_logged", set())
    if (driver, destination, band) not in logged:
        db.log_search(conn, "precheck", "", destination, total, driver)
        logged.add((driver, destination, band))

    st.markdown(f"**{destination}** の注意事項：{total} 件（新しい順）")
    show_results(pre, key="pre", empty_text={
        "report": f"直近{RECENT_DAYS}日のトラブル報告はありません",
        "experience": f"直近{RECENT_DAYS}日のベテランの経験値はありません",
        "local_rule": "この行き先の現地ルールは、まだ登録されていません",
        "manual": "マニュアルは「トラブル検索」で表示します",
    })

# ── ステップ2：トラブル検索 ────────────────────────────────────
with tab_search:
    st.subheader("トラブル検索")
    st.caption("配送中に困ったことを入力してください。言い回しが違っても関連語で探します。")
    with st.form("search"):
        q = st.text_input("何に困っていますか？", placeholder="例：数が合わないと言われた")
        use_dest = st.checkbox(f"行き先（{destination}・{band}）で絞り込む", value=True)
        submitted = st.form_submit_button("検索", type="primary")

    if submitted and q.strip():
        res = search_all_sources(q, location=destination if use_dest else "指定なし", engines=get_engines(),
                                 locations=LOCATIONS, time_band=band if use_dest else None)
        res = {layer: [e for e in items if e["relevance_score"] >= MIN_SCORE] for layer, items in res.items()}
        hits = sum(len(v) for v in res.values())
        db.log_search(conn, "search", q, destination if use_dest else "", hits, driver)
        st.session_state.last = {"q": q, "ids": {l: [e["id"] for e in v] for l, v in res.items()},
                                 "res": res, "asked": False}

    last = st.session_state.get("last")
    if last:
        hits = sum(len(v) for v in last["res"].values())
        st.markdown(f"**「{last['q']}」の検索結果：{hits} 件**（関連度の高い順）")
        if hits == 0:
            st.warning("まだこの質問に答えられるナレッジがありません。急ぎの場合は営業所へ連絡してください。")
        else:
            show_results(last["res"], key="srch", show_score=True)
        st.divider()
        if last["asked"]:
            st.success("ベテランに質問を送りました。「❓ 質問」タブで回答を待ちます。")
        elif st.button("🙋 解決しなかったら、ベテランに質問する", use_container_width=True):
            db.add_question(conn, last["q"], destination, band, driver)
            last["asked"] = True
            st.rerun()

# ── 登録 ──────────────────────────────────────────────────────
with tab_register:
    st.subheader("ナレッジを登録")
    kinds = {"ベテランの経験値": "experience", "現地ルール": "local_rule",
             "トラブル報告": "report", "マニュアル": "manual"}
    kind = st.radio("種類", list(kinds), horizontal=True)
    layer = kinds[kind]
    if layer in ("experience", "local_rule"):
        st.caption(f"登録者：{driver}（上の「今日の配送」で変更できます）")
    with st.form("register", clear_on_submit=True):
        title = st.text_input("タイトル", placeholder="例：数が合わないときはまず荷台の奥を確認")
        content = st.text_area("内容（どうする）")
        reason = st.text_area("理由・教訓（なぜ）")
        loc = st.selectbox("配送先", ["（共通）"] + LOCATIONS,
                           index=(LOCATIONS.index(destination) + 1) if layer == "local_rule" else 0)
        tb = st.selectbox("時間帯", ["（問わない）"] + TIME_BANDS)
        category = st.selectbox("カテゴリ", master["categories"])
        keywords = st.text_input("キーワード（カンマ区切り・任意）", placeholder="例：数量,個数")
        source_ref = st.text_input("出典（任意）", placeholder="例：運行マニュアル 第4章／報告書 R-0912")
        ok = st.form_submit_button("登録する", type="primary")
    if ok:
        if not title.strip() or not content.strip():
            st.error("タイトルと内容を入力してください。")
        elif layer == "local_rule" and loc == "（共通）":
            st.error("現地ルールは配送先を選んでください。")
        else:
            db.add_knowledge(conn, layer, title.strip(), content.strip(), reason.strip(), category,
                             "" if loc == "（共通）" else loc, "" if tb == "（問わない）" else tb,
                             keywords.strip(), source_ref.strip(),
                             driver if layer in ("experience", "local_rule") else "")
            refresh_engines()
            st.success(f"「{kind}」に登録しました。ありがとうございます！")

# ── 質問（答えが見つからなかったもの） ──────────────────────────
with tab_question:
    st.subheader("ベテランへの質問")
    st.caption("LogiKnowで答えが見つからなかった質問です。ベテランの回答は、そのまま経験値として登録されます。")
    questions = db.open_questions(conn)
    if not questions:
        st.success("未回答の質問はありません。")
    for item in questions:
        with st.container(border=True):
            st.markdown(f"**Q. {item['question']}**")
            st.caption(f"質問者：{item['asked_by']}　📍{item['location'] or '共通'}　🕐{item['time_band'] or '－'}"
                       f"　{days_ago(item['asked_at'])}")
            with st.expander("回答する"):
                with st.form(f"answer{item['id']}"):
                    answerer = st.selectbox("回答者", master["veterans"])
                    a_title = st.text_input("タイトル", value=item["question"])
                    a_content = st.text_area("どうする")
                    a_reason = st.text_area("なぜ")
                    if st.form_submit_button("回答を登録", type="primary"):
                        if a_content.strip():
                            kid = db.add_knowledge(conn, "experience", a_title.strip(), a_content.strip(),
                                                   a_reason.strip(), "", item["location"] or "",
                                                   item["time_band"] or "", "", "質問への回答", answerer)
                            db.answer_question(conn, item["id"], kid)
                            refresh_engines()
                            st.rerun()
                        else:
                            st.error("「どうする」を入力してください。")

# ── 活用状況・効果測定 ─────────────────────────────────────────
with tab_stats:
    st.subheader("活用状況・効果測定")
    s = db.stats(conn)
    c1, c2 = st.columns(2)
    c1.metric("ナレッジ登録数", f"{sum(s['by_layer'].values())} 件")
    c2.metric("配送前チェック", f"{s['prechecks']} 回")
    c3, c4 = st.columns(2)
    c3.metric("トラブル検索", f"{s['searches']} 回")
    c4.metric("検索で見つかった割合", f"{s['hits'] / s['searches']:.0%}" if s["searches"] else "–")
    st.metric("未回答の質問", f"{s['open_questions']} 件")

    st.markdown("**情報源ごとの登録数**")
    names = dict(DISPLAY)
    st.bar_chart(pd.DataFrame({"件数": [s["by_layer"].get(l, 0) for l, _ in DISPLAY]},
                              index=[names[l] for l, _ in DISPLAY]))

    st.markdown("**よく検索された言葉**（見つからなかった回数が多い＝ナレッジが足りない）")
    if s["top_queries"]:
        st.dataframe(pd.DataFrame(s["top_queries"]), hide_index=True, use_container_width=True)
    else:
        st.caption("まだ検索されていません")

    st.markdown("**役に立ったナレッジ**")
    if s["top_helpful"]:
        for h in s["top_helpful"]:
            st.caption(f"👍 {h['helpful']}　{h['title']}（{names.get(h['layer'], h['layer'])}）")
    else:
        st.caption("まだ評価されていません")

# ── フッター ──────────────────────────────────────────────────
st.divider()
st.caption("© LogiKnow — テクゼロンロジスティクス")
