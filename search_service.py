""" search_service.py"""
""" query_processor.py と検索エンジンをつなぐファイル """

# -------------------------------------------------------
# 全体構成 & このファイルで定義する辞書・リスト・関数

    # １：ライブラリのインポート 
    # ２：検索対象の定義 (タプル)       →　LAYERS
    # ３：検索条件による絞り込み (関数) → _matches_filters()
    # ４：画面用データへの変換 (関数)   → _as_ui_entry()
    # ５：検索全体の実行 (関数)         → search_all_sources()

# -------------------------------------------------------
# １：ライブラリのインポート

"""LogiKnow: 3つの情報源を独立検索し、UI用の形式に整える """

# 型ヒント機能の読み込み（typingという標準ライブラリより）
from typing import Any, Mapping, Optional
        # Any           → どのような形でもよい、という型ヒント
        # Mapping       → 辞書のようにキーから値を取得できるデータ型
        # Optional      → 値が None でもよい、という型ヒント

# 質問解析の統合機能の読み込み
from query_processor import process_question
        # query_processor   → query_processor.py のラストでつくった関数


# -------------------------------------------------------
# ２：検索対象の定義

LAYERS = ("manual", "report", "experience")
        # "manual"      → 社内マニュアル
        # "report"      → クレーム・事故報告書
        # "experience"  → ベテラン経験知

        # () タプル      → 作成後に要素を変更できない
        #                → 今回の3種類は固定なので、タプルでOK
        # ※ [] リスト   → 作成後でも要素を変更できる

# -------------------------------------------------------
# ３：検索条件による絞り込み：　_matches_filters() の定義

# 1件の検索結果が、指定された条件に合うか判定する関数
def _matches_filters(entry: dict, category: str, location: str) -> bool:
    """ 指定されたカテゴリ・配送先で絞る。配送先が空の共通情報は残す """
        # def               → 関数の定義
        # _matches_filters  → 作成する関数名
        #   ※ 冒頭に "_" があるのは、主にこのファイル内部で使う関数、という慣習表記

        # entry             → 関数が受け取る引数
        # : dict            → 辞書を受け取る、という型ヒント
        # category          → 関数が受け取る引数
        # location          → 関数が受け取る引数
        # : str             → 文字列を受け取る、という型ヒント
        # -> bool           → 真偽値を返す、という型ヒント

    # 条件に合わない検索結果を除外
    if category and category != "すべて" and entry.get("category") != category:
        return False
            # category              → カテゴリが指定されている
            # category != "すべて"   → 「すべて」ではない
            # entry.get("category") != category     
            #                       → 検索結果のカテゴリが指定カテゴリと一致しない

    # 配送先が指定されているか確認
    if location and location != "指定なし":

        # 検索結果に登録されている配送先名を取得。未登録なら空文字列を使う
        entry_location = entry.get("location") or ""

        # 検索結果の配送先が空ではなく、指定された配送先とも異なる場合
        if entry_location and entry_location != location:
            
            # 別の配送先に関する情報なので除外
            return False
    
    # 以上の流れで除外されなかったもの = 条件に合う情報 として残す
    return True    

# -------------------------------------------------------
# ４：画面用データへの変換：　_as_ui_entry() の定義

def _as_ui_entry(raw: dict, layer: str) -> dict:
    """ W4の検索結果を、app.pyのentry_card()向けに変換 """
        # def               → 関数の定義
        # _as_ui_entry  → 作成する関数名
        #   ※ 冒頭に "_" があるのは、主にこのファイル内部で使う関数、という慣習表記

        # raw           → 検索エンジンが返した元データ1件
        # : dict        → 辞書を受け取る、という型ヒント
        # layer         → そのデータが manual, report, experience のどれに属するか示す
        # : str         → 文字列を受け取る、という型ヒント
        # -> dict       → 辞書を返す、という型ヒント


    # 情報源3つの英語キーと日本語表記名の対応表
    source_names = {
        "manual": "社内マニュアル",
        "report": "クレーム・事故報告書",
        "experience": "ベテランの経験知"
    }

    # app.py のUI画面が必要とするデータを1件ずつ作成
    return {

        # 情報源の種類
        "layer": layer,

        # 本文があれば本文、なければ説明、さらにはタイトル（なければ空文字列）
        "content": raw.get("content") or raw.get("description") or raw.get("title") or "",
                # ※ or     → 左から順番に確認し、最初に見つかった空でない値を使う

        # 理由・教訓を取得（なければ空文字列）
        "reason": raw.get("reason") or "",

        # 信頼度を取得（なければ「要確認」）
        "confidence": raw.get("confidence") or "要確認",

        # 出典名を取得（なければ情報源に応じた名称）
        "source": raw.get("source") or source_names[layer],

        # 出典文書番号やタイトルを取得（なければ空文字列）
        "source_ref": raw.get("source_ref") or raw.get("title") or "",

        # 配送先を取得（なければ空文字列）
        "location": raw.get("location") or "",

        # 登録者を取得（なければ空文字列）
        "creator": raw.get("creator") or "",

        # ベテランの同意数を取得（なければ数値 0）
        "endorse": raw.get("endorse") or 0,

        # 検索関連度を取得
        "relevance_score": raw.get("relevance_score", 0),

        # カテゴリを取得（なければ空文字列）
        "category": raw.get("category") or "",

        # DB上の識別IDを取得
        "id": raw.get("id"),
    }

# -------------------------------------------------------
# ５：検索全体の実行：　search_all_sources() の定義

def search_all_sources(
        question: str,
        category: str = "すべて",
        location: str = "指定なし",
        *,
        engines: Mapping[str, Any],
        locations: Optional[list[str]] = None,
        top_n: int = 20,
    ) -> dict[str, list[dict]]:
    """ 各情報源の SearchEngine.search() を個別に呼ぶ """

            # question      → ドライバーが入力した質問
            # category      → 検索対象カテゴリ（省略すると「すべて」）
            # location      → 配送先（省略すると「指定なし」）
            #  *            → これ以降の引数は、名前を指定して渡す
            # engines       → 3種類の検索エンジンを保存した辞書
            # locations     → 配送先名のマスタリスト
            # top_n         → 情報源ごとに返す最大件数（初期値20）
            # -> dict[str, list[dict]]  → 辞書を返し、その値は辞書のリスト

    if not question.strip() and location =="指定なし":
            # question.strip()  → 質問文の前後の空白を削除
            # location == "指定なし"    → 配送先も指定されていない場合

        # 質問も配送先も未指定なら、検索しない（空リストを返す）
        return {layer: [] for layer in LAYERS}

        # ※ ↓ 通常の for 文の場合
        # result = {}
        # for layer in LAYERS:
        #     result[layer] = []
        # return result
    
    # 重要語抽出、関連語展開、配送先抽出、をまとめて実行
    parsed = process_question(question, locations)
            # process_question()    → ※ query_processor.py で作った関数

    # 検索に使用する配送先を決める（条件演算子）
    effective_location = location if location != "指定なし" else (parsed["location"] or "指定なし")
            # 1. 画面で配送先を指定していれば、その値を使う
            # 2. 指定していなければ、質問文から抽出した配送先を使う
            # 3. どちらもなければ「指定なし」
    
    # 最終的な検索結果を保存する空の辞書を作る
    result = {}

    # 検索エンジンを3回呼び出す
    for layer in LAYERS:
        
        # 指定された情報源の検索エンジンが存在するか確認
        if layer not in engines:

            # 存在しなければエラーを発生させる
            raise ValueError(f"検索エンジンが未設定です： {layer}")
                    # raise     → 意図的に例外を発生させる命令
                    # f"..."    → 変数の値を文字列に埋め込む f文字列
        
        # 現在処理中の検索エンジンを取り出す
        engine = engines[layer]

        # 質問解析で作った検索文字列が存在するか確認
        if parsed["search_query"]:
            candidates = engine.search(parsed["search_query"], top_n=max(top_n, len(engine.pages)))
                    # parsed["search_query"]    → 検索文字列
                    # engine.pages              → 検索エンジンが保有している登録情報
                    # len(engine.pages)         → 登録情報の件数
                    # max(top_n, len(engine.pages)) →　大きい方の数値を使う

        # 検索文字列が空の場合
        else:
            # 検索エンジンが保持している登録情報を、検索候補としてそのまま取得
            candidates = list(engine.pages)

        # 検索候補を1件ずつ確認し、条件に合うものだけを残す
        filtered = [e for e in candidates if _matches_filters(e, category, effective_location)]

        # ※ ↓ 通常の for 文の場合 
        # filtered = []
        # for e in candidates:
        #     if _matches_filters(e, category, effective_location):
        #         filtered.append(e)

        # 検索結果はW4で関連度順。配送先のみの検索は登録順
        result[layer] = [_as_ui_entry(e, layer) for e in filtered[:top_n]]
                # filtered[:top_n]          → 先頭から最大 top_n 件を取得
                # _as_ui_entry(e, layer)    → 各データをUI表示用に変換
                # result[layer] = ...       → 現在の情報源の検索結果として保存

    # 最後に3種類の検索結果をまとめて返す
    return result
