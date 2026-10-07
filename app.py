"""LogiKnow（ロジノウ）― 物流版・暗黙知継承AI  UIモック

見た目だけのapp.py。DB・検索などの処理は持たない（他メンバーが別ファイルで実装予定）。
画面に出ているデータはすべて表示確認用のダミー。

streamlit run app.py
"""

from datetime import date

import streamlit as st

st.set_page_config(
    page_title="LogiKnow v0.1",
    page_icon="🚚",
    layout="wide"
)

MVP_CATEGORY = "C. トラブル一次対応"
LAYERS = [  # 3層回答構成
    ("manual", "✅ 推奨対応", "社内マニュアル出典"),
    ("report", "📄 類似事例", "クレーム・事故報告書出典"),
    ("experience", "🧓 ベテランの注意", "経験知出典"),
]

# ── ダミーデータ（表示確認用。実装時にDB・検索処理の結果に置き換える） ───────
DUMMY_CATEGORIES = [MVP_CATEGORY]
DUMMY_LOCATIONS = ["北関東物流センター", "東部食品センター"]
DUMMY_DRIVERS = ["山田 一郎", "鈴木 正夫", "佐藤 健二", "田中 美咲"]
DUMMY_VETERANS = ["山田 一郎", "鈴木 正夫", "佐藤 健二"]
DUMMY_ENTRIES = [
    {"layer": "manual", "content": "（サンプル）推奨対応の本文がここに入ります。",
     "reason": "（サンプル）理由がここに入ります。", "confidence": "高",
     "source": "社内マニュアル", "source_ref": "運行マニュアル 第◯章", "location": "", "creator": "", "endorse": 0},
    {"layer": "report", "content": "（サンプル）類似事例の本文がここに入ります。",
     "reason": "（サンプル）教訓がここに入ります。", "confidence": "高",
     "source": "クレーム・事故報告書", "source_ref": "報告書 #◯◯", "location": "北関東物流センター", "creator": "", "endorse": 0},
    {"layer": "experience", "content": "（サンプル）ベテランの注意の本文がここに入ります。",
     "reason": "（サンプル）理由がここに入ります。", "confidence": "要確認",
     "source": "ベテランの経験知", "source_ref": "配送終了ヒアリング", "location": "", "creator": "山田 一郎", "endorse": 1},
]
DUMMY_GAPS = [
    {"query": "（サンプル）答えられなかった質問がここに入ります。", "asker": "匿名",
     "asked_at": "2026-10-01", "assignee": "鈴木 正夫", "tenure": 28},
]
DUMMY_LOG = [
    {"日時": "2026-10-01 09:00", "質問者": "匿名", "質問": "（サンプル）質問文", "ヒット数": 3, "結果": "解決"},
    {"日時": "2026-10-01 10:30", "質問者": "匿名", "質問": "（サンプル）質問文", "ヒット数": 0, "結果": "未解決"},
]


# ── ヘッダー ──────────────────────────────────────────────────
st.title("🚚  :blue[LogiKnow v0.1] ")
st.caption("ベテランの経験を、全員の経験に。— 物流版ナレッジ検索ツール")

# ── サイドバー ────────────────────────────────────────────────
with st.sidebar:
    st.header("DB の登録状況")
    st.metric("ナレッジ登録数", "– 件")   # TODO: 登録件数
    st.metric("未回答の質問", "– 件")     # TODO: 未回答ギャップ件数


def confidence_badge(level):
    return ":green[信頼度：高]" if level == "高" else ":orange[信頼度：要確認]"


def entry_card(e, key):
    """ナレッジ1件のカード。"""
    with st.container(border=True):
        st.markdown(e["content"])
        if e["reason"]:
            st.markdown(f"**なぜ：** {e['reason']}")
        meta = [confidence_badge(e["confidence"]), f"出典：{e['source']}", e["source_ref"]]
        if e["location"]:
            meta.append(f"📍{e['location']}")
        if e["layer"] == "experience":
            meta.append(f"登録：{e['creator']}／同意 {e['endorse']}名")
        st.caption("　".join(meta))
        if e["layer"] == "experience":
            with st.popover("👍 自分もそう思う（同意）"):
                st.selectbox("同意するベテラン", DUMMY_VETERANS, key=f"who_{key}")
                st.button("同意する", key=f"endorse_{key}", type="primary")  # TODO: 同意を記録


# ── タブ ──────────────────────────────────────────────────────
tab_search, tab_register, tab_gap, tab_stats = st.tabs(
    ["🔍 検索", "📝 登録", "❓ 質問", "📊 活用状況・効果測定"]
)

# ── 検索タブ ───────────────────────────────────────────────────
with tab_search:
    st.subheader("困ったときに検索")
    st.caption("関連ワードにてまずここで検索。")
    with st.form("search"):
        col_search, col_cat, col_loc = st.columns([3, 1, 1])
        with col_search:
            q = st.text_input("何に困っていますか？", placeholder="例：個数が違う／荷姿が崩れていた／お客様が怒っている")
        with col_cat:
            cat = st.selectbox("カテゴリ", ["すべて"] + DUMMY_CATEGORIES, index=1)
        with col_loc:
            loc = st.selectbox("配送先", ["指定なし"] + DUMMY_LOCATIONS)
        submitted = st.form_submit_button("検索", type="primary")
        st.caption("配送先だけ選んで検索すると、その配送先のナレッジを一覧で表示します。")

    if submitted and (q.strip() or loc != "指定なし"):
        # TODO: 検索処理を呼び、結果を受け取る。いまは常にダミー結果を表示
        title = f"「{q}」の検索結果" if q.strip() else f"📍 {loc} のナレッジ"
        st.markdown(f"**📊 {title}：{len(DUMMY_ENTRIES)} 件**（表示サンプル）")
        for layer, heading, origin in LAYERS:
            st.markdown(f"#### {heading}　<small>{origin}</small>", unsafe_allow_html=True)
            for i, e in enumerate(x for x in DUMMY_ENTRIES if x["layer"] == layer):
                entry_card(e, key=f"{layer}{i}")
        st.divider()
        st.markdown("**この回答で解決しましたか？**")
        c1, c2 = st.columns(2)
        c1.button("✅ 解決した", use_container_width=True)        # TODO: 自己解決を記録
        c2.button("❌ 解決しなかった", use_container_width=True)  # TODO: 未解決を記録・ベテランへの質問を作成
        with st.expander("0件のときの表示（サンプル）"):
            st.warning("まだこの質問に答えられるナレッジがありません。")
            st.info("この質問は「ギャップ」として記録し、**◯◯** さんに次の配送終了時に聞いておきます。"
                    "急ぎの場合は営業所へ連絡してください。")

# ── 登録タブ ───────────────────────────────────────────────────
with tab_register:
    mode = st.radio("登録の種類", ["配送終了ヒアリング（ドライバー）", "マニュアル・報告書の取り込み（管理部門）"],
                    horizontal=True, label_visibility="collapsed")

    if mode.startswith("配送終了"):
        st.subheader("配送終了ヒアリング")
        st.info("💬 ベテランへの質問が ◯ 件届いています。「❓ 質問」タブから答えてもらえると助かります。")
        st.caption("今日の配送で「次の人に伝えたいこと」を1つだけ教えてください。声でも文字でもOKです。")
        st.audio_input("🎤 音声で入力（β）")  # TODO: 文字起こしして「気づいたこと」欄へ反映
        with st.form("report"):
            c1, c2 = st.columns(2)
            c1.selectbox("運転者名", DUMMY_DRIVERS)
            c2.date_input("運行日", value=date.today())
            c1.text_input("納品先（任意）", placeholder="例：北関東物流センター")
            c2.text_input("カテゴリ（自由タグ）", value=MVP_CATEGORY)
            st.text_area("気づいたこと（こうする）", placeholder="例：数が合わないときは、まず荷台の奥を確認する")
            st.text_area("なぜそうするのか（理由）", placeholder="例：積み残しより荷台内の見落としの方が多いから")
            st.form_submit_button("登録する", type="primary")  # TODO: ナレッジを登録
    else:
        st.subheader("マニュアル・報告書の取り込み")
        st.caption("社内マニュアル・クレーム／事故／ヒヤリハット報告書を構造化して登録します。")
        with st.form("import"):
            st.radio("情報源", ["社内マニュアル", "クレーム・事故報告書"], horizontal=True)
            st.text_input("カテゴリ（自由タグ）", value=MVP_CATEGORY)
            st.text_area("内容（推奨対応／事例の概要）")
            st.text_area("理由・教訓")
            c1, c2 = st.columns(2)
            c1.text_input("関連する納品先（任意）")
            c2.text_input("出典（文書名・報告書番号）")
            st.form_submit_button("登録", type="primary")  # TODO: マニュアル・報告書を登録

# ── 質問タブ ──────────────────────────────────────────────────
with tab_gap:
    st.subheader("ベテランへの質問（ギャップ）")
    st.caption("LogiKnowが答えられなかった質問です。ベテランに答えてもらい、次の人のナレッジにします。")
    for i, g in enumerate(DUMMY_GAPS):  # TODO: 未回答の質問一覧
        with st.container(border=True):
            st.markdown(f"**Q. {g['query']}**")
            st.caption(f"質問者：{g['asker']}　{g['asked_at']}　／　担当：{g['assignee']}（勤続{g['tenure']}年）")
            with st.expander("回答する"):
                with st.form(f"gap{i}"):
                    st.selectbox("回答者", DUMMY_VETERANS)
                    st.text_area("こうする")
                    st.text_area("なぜ")
                    st.form_submit_button("回答を登録", type="primary")  # TODO: 回答をナレッジとして登録

# ── 活用状況・効果測定タブ ──────────────────────────────────────
with tab_stats:
    st.subheader("ドライバー別の活用状況")
    st.caption("登録したナレッジが何回検索で役立ったかを表示します（プラスの実績のみ）。")
    st.selectbox("ドライバー", DUMMY_DRIVERS)
    c1, c2, c3 = st.columns(3)   # TODO: 選んだドライバーの実績
    c1.metric("登録数", "–")
    c2.metric("検索で表示された回数", "–")
    c3.metric("他のベテランの同意", "–")
    with st.container(border=True):
        st.markdown("（サンプル）登録したナレッジの本文がここに入ります。")
        st.caption(f"🔍 ◯回表示　👍 同意 ◯名　{confidence_badge('高')}")

    st.divider()
    st.subheader("効果測定（全体）")
    c1, c2, c3, c4 = st.columns(4)  # TODO: 全体の集計値
    c1.metric("ナレッジ登録件数", "–")
    c2.metric("検索ヒット率", "–")
    c3.metric("自己解決率", "–")
    c4.metric("未回答ギャップ", "–")
    st.markdown("**質問ログ**")
    st.dataframe(DUMMY_LOG, hide_index=True, use_container_width=True)  # TODO: 質問ログ

# ── フッター ──────────────────────────────────────────────────
st.divider()
st.caption("© LogiKnow — テクゼロンロジスティクス")
