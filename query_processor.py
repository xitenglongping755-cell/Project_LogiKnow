""" query_processor.py """
""" 質問を「検索しやすい言葉」に加工するためのファイル """
        # """..."""     → 複数行の文字列を記述する構文

# -------------------------------------------------------
# 全体構成 & このファイルで定義する辞書・リスト・関数

    # １：ライブラリのインポート
    # ２：物流用語 (辞書)       → RELATED_TERMS 
    # ３：物流重要語 (リスト)   → LOGISTICS_TERMS
    # ４：文章の整形 (関数)     → normalize_text
    # ５：重要語の抽出 (関数)   → extract_keywords
    # ６：関連語の展開 (関数)   → expand_keywords
    # ７：配送先の抽出 (関数)   → extract_location
    # ８：質問解析の統合 (関数) → process_question

# -------------------------------------------------------
# １：ライブラリのインポート

"""LogiKnow: 質問文の簡易解析（外部ライブラリ不要）"""

# 正規表現機能の読み込み（Python標準ライブラリより）
import re
        # re        → regular expression（正規表現）
        #             質問文に含まれる余分な空白や改行を整理

# 型ヒント機能の読み込み（typingという標準ライブラリより）
from typing import Optional
        # Optional  → 型ヒント
        # 例: Optional[str]     → 文字列 str または None を想定

# -------------------------------------------------------
# ２：物流用語辞書（関連語まとめて検索候補にするため）
    # ※ とりあえず今回はテキストベタ打ちで。将来ここを増強するかは検索精度みながら調整。

# キー：入力で見つけたい表現 / 値：検索に追加する関連語
RELATED_TERMS = {
    "受付": ["入構", "守衛", "受付窓口"],
    "入構": ["受付", "入場"],
    "守衛": ["受付", "警備室"],
    "バース": ["接車", "荷卸し場所"],
    "接車": ["バース"],
    "荷下ろし": ["荷卸し", "荷降ろし"],
    "荷卸し": ["荷下ろし", "荷降ろし"],
    "荷降ろし": ["荷下ろし", "荷卸し"],
    "個数": ["数量", "数量違い", "数量不足"],
    "数量": ["個数", "数量違い", "数量不足"],
    "数が合わない": ["数量違い", "数量不足", "個数"],
    "個数が合わない": ["数量違い", "数量不足", "個数"],
    "破損": ["荷物破損", "商品破損"],
    "荷姿": ["荷崩れ", "梱包"],
    "荷崩れ": ["荷姿", "梱包"],
    "遅延": ["延着", "到着遅れ"],
    "遅れる": ["遅延", "延着"],
    "クレーム": ["苦情", "顧客対応"],
    "怒っている": ["苦情", "クレーム"],
    "伝票": ["納品書", "受領書"],
    "検品": ["数量確認", "商品確認"],
    "駐車": ["待機", "駐車場"],
}
        # RELATED_TERMS  → 関連語の辞書を保存する変数名
        # {}             → 辞書を作る
        # :              → キーと値の区切り
        # []             → キーに対応する値（今回はリストで）

# -------------------------------------------------------
# ３：物流重要語リスト
    # ※ とりあえず今回はテキストベタ打ちで。将来ここを増強するかは検索精度みながら調整。

# 関連語をもたない重要語を登録
LOGISTICS_TERMS = [
    "物流センター", "配送センター", "倉庫", "工場", "正門", "裏門", 
    "入場", "警備室", "待機", "パレット", "フォークリフト", "納品", 
    "検収", "受領印", "積み忘れ", "誤配送", "事故", "故障", 
    "通行止め", "温度管理", "冷凍", "冷蔵", 
]

# -------------------------------------------------------
# ４：文章の整形：　normalize_text() の定義

def normalize_text(text: str) -> str:
    """ 余分な空白を整理する """
        # def               → 関数の定義
        # normalize_text    → 作成する関数名
        # text              → 関数が受け取る引数
        # : str             → 文字列を受け取る、という型ヒント
        # -> str            → 文字列を返す、という型ヒント

    return re.sub(r"\s+", " ", (text or "").strip())
        # text or ""        → text が空文字列や None なら、代わりに "" を使う
        # .strip()          → 文字列の先頭と末尾にある空白や改行を削除
        # re.sub(r"\s+", " ", ...)   → 連続空白を半角スペース1つに置換
                # re.sub()      → パターンに一致する文字列を置き換える
                # r"\s+"        → 連続する空白・改行・タブ
                # " "           → 半角スペース1つに置換
                # ...           → 処理対象の文字列

# -------------------------------------------------------
# ５：重要語の抽出：　extract_keywords() の定義

def extract_keywords(question: str) -> list[str]:
    """ 辞書内の表現を質問から抽出する """
        # def               → 関数の定義
        # extract_keywords  → 作成する関数名
        # question          → 関数が受け取る引数
        # : str             → 文字列を受け取る、という型ヒント
        # -> list[str]      → 文字列のリストを返す、という型ヒント

    # 質問文を整形
    question = normalize_text(question)
        # normalize_text    → ※ 先ほど４章で作成した文字整形関数

    # 関連語・重要語を集合化
    terms = sorted(set(RELATED_TERMS) | set(LOGISTICS_TERMS), key=len, reverse=True)
        # set(RELATED_TERMS)    → 辞書のキーだけ取り出して集合にする
        # set(LOGISTICS_TERMS)  → 重要語リストを集合にする
        # |                     → 2つの集合を結合（重複語は1つになる）

        # sorted(..., key=len, reverse=True)    → 文字数の長い順に並べる 
                # key=len       → 並べ替え基準＝文字数
                # reverse=True  → 大きい順に  ※ sorted() のデフォルトは逆 

    # 質問文に含まれる重要語だけをリストに入れて返す
    return [term for term in terms if term in question]
    
        # ※ ↓ この内容を書き換えたもの
        # keywords = []
        # for term in terms:
        #   if term in question:
        #       keywords.append(term)
        # return keywords 

# -------------------------------------------------------
# ６：関連語の展開：　expand_keywords() の定義

def expand_keywords(keywords: list[str]) -> list[str]:
    """ 抽出後とその関連語を重複なしで返す（1段階のみ展開） """
        # def               → 関数の定義
        # expand_keywords   → 作成する関数名
        # keywords          → 関数が受け取る引数
        # : list[str]       → 文字列のリストを受け取る、という型ヒント
        # -> list[str]      → 文字列のリストを返す、という型ヒント

    # 検索候補語を保存する空リスト用意
    expanded = []

    # 抽出済みの重要語を1つずつ取り出す
    for term in keywords:

        # 元の重要語をリストに追加
        expanded.append(term)

        # 抽出済み重要語に対する関連語があれば、関連語リストを返す
        expanded.extend(RELATED_TERMS.get(term, []))
            # extend()      → リスト内の要素を1つずつ追加する
            #                 ※ append() だと、リストを1つの要素として追加

            # (term, [])    → 辞書に term が存在すれば、対応する関連語リストを返す。
            #                 存在しなければ空リスト [] を返す

    # 重複を削除する処理  ※ リスト → 辞書（重複削除）→ リスト
    return list(dict.fromkeys(expanded))
            # dict.fromkeys()   → リストの要素を辞書のキーに変換する
            #                     ※辞書のキーは重複できない → 同じ語が1つになる
            # list()            → 辞書をまたリストに戻す 

# -------------------------------------------------------
# ７：配送先の抽出：　extract_location() の定義

def extract_location(question: str, locations: Optional[list[str]] = None) -> Optional[str]:
    """ 配送先マスタに登録済みの名称が質問中にあれば返す """
        # def               → 関数の定義
        # extract_location  → 作成する関数名
        # question          → 関数が受け取る引数（ドライバーの質問文）
        # : str             → 文字列を受け取る、という型ヒント
        # locations         → 関数が受け取る引数（登録済み配送先リスト）
        # : Optional[list[str]] = None      → 配送先リストを渡しても渡さなくてもよい
        #                                     （省略した場合は None になる）
        # -> Optional[str]      → 配送先名の文字列、または None 、という型ヒント

    # 質問文の空白を整理
    question = normalize_text(question)
    
    # 配送先名を文字列の長い順に並べる
    candidates = sorted(locations or [], key=len, reverse=True)
        # sorted(..., key=len, reverse=True)    → 文字数の長い順に並べる 
                # key=len       → 並べ替え基準＝文字数
                # reverse=True  → 大きい順に  ※ sorted() のデフォルトは逆 

    # 質問文に含まれる配送先名1つを返す
    return next((loc for loc in candidates if loc and loc in question), None)
            # for loc in candidates     → 配送先を1つずつ調べる
            # if loc                    → 配送先が空でないことを確認
            # loc in question           → 質問文に配送先名が含まれるか確認
            # next(...)                 → 最初に見つかったものを返す
            # None                      → 1件も見つからなければ返す値

        # ※ ↓ この内容を書き換えたもの
        # for loc in candidates:
        #   if loc and loc in question:
        #       return loc
        # return None

# -------------------------------------------------------
# ８：質問解析の統合：　process_question() の定義

def process_question(question: str, locations: Optional[list[str]] = None) -> dict:
    """質問解析結果。元の質問も残し、辞書未登録の語を検索で失わない"""
        # def               → 関数の定義
        # process_question  → 作成する関数名
        # question          → 関数が受け取る引数（ドライバーの質問文）
        # : str             → 文字列を受け取る、という型ヒント
        # locations         → 関数が受け取る引数（登録済み配送先リスト）
        # : Optional[list[str]] = None      → 配送先リストを渡しても渡さなくてもよい
        #                                     （省略した場合は None になる）
        # -> dict           → 解析結果を辞書で返す、という型ヒント

    # 質問文を整形して original に保存
    original = normalize_text(question)

    # 質問文から重要語を抽出
    keywords = extract_keywords(original)

    # 重要語を関連語に展開
    expanded = expand_keywords(keywords)

    # 元の質問を必ず含める。追加語は関連文書を拾うための補助語
    search_query = " ".join([original] + expanded) if original else ""
            # [original] + expanded     → 元の質問文と関連語リストを結合
            # " ".join(...)             → リスト内の文字列を半角スペースでつなぐ
            # if original else ""       → 質問文が空なら、検索文字列も空にする

    # 解析結果を辞書として返す
    return {
        "original_question": original,
        "keywords": keywords,
        "expanded_keywords": expanded,
        "location": extract_location(original, locations),
        "search_query": search_query,
    }

