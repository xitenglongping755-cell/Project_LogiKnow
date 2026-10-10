""" database.py """
""" DB（SQLite）の読み書きの窓口。★プロトタイプ用の仮実装。DB担当の設計が決まったら差し替える """

# -------------------------------------------------------
# 全体構成
    # １：ライブラリのインポートと設定
    # ２：接続と初期化（DBが無ければ schema.sql で作り、サンプルデータを入れる）
    # ３：ナレッジの読み書き
    # ４：質問・検索ログ・集計

# -------------------------------------------------------
# １：ライブラリのインポートと設定

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).parent
DB_PATH = BASE / "logiknow.db"                       # .gitignore で除外済み（起動時に自動で作る）
SCHEMA_PATH = BASE / "schema.sql"
SAMPLE_PATH = BASE / "data" / "sample_knowledge.json"   # サンプルデータ（すべて架空）


def now():
    return datetime.now().isoformat(timespec="seconds")


# -------------------------------------------------------
# ２：接続と初期化

def connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row      # 結果を「列名で取り出せる形」にする
    return conn


def init_db(conn):
    """テーブルを作り、ナレッジが空ならサンプルデータを入れる"""
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    if conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0] == 0:
        load_sample(conn)
    conn.commit()


def load_sample(conn):
    """サンプルデータを入れる。日付は「今日から何日前か」で持っているので、いつ起動しても直近のデータになる"""
    data = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    for k in data["knowledge"]:
        created = (datetime.now() - timedelta(days=k.get("days_ago", 0))).isoformat(timespec="seconds")
        conn.execute(
            """INSERT INTO knowledge (layer, title, content, reason, category, location, time_band,
                                      keywords, source_ref, creator, created_at, helpful)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (k["layer"], k["title"], k["content"], k.get("reason", ""), k.get("category", ""),
             k.get("location", ""), k.get("time_band", ""), k.get("keywords", ""),
             k.get("source_ref", ""), k.get("creator", ""), created, k.get("helpful", 0)),
        )


def master():
    """ドライバー名・配送先・カテゴリの一覧（サンプルデータの master）"""
    return json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))["master"]


# -------------------------------------------------------
# ３：ナレッジの読み書き

def get_pages(conn, layer):
    """1つの情報源のナレッジを、検索エンジン（ranking.py）に渡す形で返す"""
    rows = conn.execute("SELECT * FROM knowledge WHERE layer = ? ORDER BY id", (layer,)).fetchall()
    return [dict(r) for r in rows]


def add_knowledge(conn, layer, title, content, reason="", category="", location="", time_band="",
                  keywords="", source_ref="", creator=""):
    cur = conn.execute(
        """INSERT INTO knowledge (layer, title, content, reason, category, location, time_band,
                                  keywords, source_ref, creator, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (layer, title, content, reason, category, location, time_band, keywords, source_ref, creator, now()),
    )
    conn.commit()
    return cur.lastrowid


def add_helpful(conn, knowledge_id):
    """「役に立った」を1つ増やす（知見の評価）"""
    conn.execute("UPDATE knowledge SET helpful = helpful + 1 WHERE id = ?", (knowledge_id,))
    conn.commit()


# -------------------------------------------------------
# ４：質問・検索ログ・集計

def add_question(conn, question, location, time_band, asked_by):
    conn.execute("INSERT INTO questions (question, location, time_band, asked_by, asked_at) VALUES (?,?,?,?,?)",
                 (question, location, time_band, asked_by, now()))
    conn.commit()


def open_questions(conn):
    return [dict(r) for r in conn.execute("SELECT * FROM questions WHERE status = 'open' ORDER BY id DESC")]


def answer_question(conn, question_id, knowledge_id):
    conn.execute("UPDATE questions SET status = 'answered', answer_id = ? WHERE id = ?", (knowledge_id, question_id))
    conn.commit()


def log_search(conn, mode, query, location, hit_count, driver):
    conn.execute("INSERT INTO search_logs (mode, query, location, hit_count, driver, created_at) VALUES (?,?,?,?,?,?)",
                 (mode, query, location, hit_count, driver, now()))
    conn.commit()


def stats(conn):
    """活用状況・効果測定の数字"""
    one = lambda sql: conn.execute(sql).fetchone()[0] or 0
    return {
        "by_layer": {r["layer"]: r["n"] for r in conn.execute("SELECT layer, COUNT(*) AS n FROM knowledge GROUP BY layer")},
        "searches": one("SELECT COUNT(*) FROM search_logs WHERE mode = 'search'"),
        "hits": one("SELECT COUNT(*) FROM search_logs WHERE mode = 'search' AND hit_count > 0"),
        "prechecks": one("SELECT COUNT(*) FROM search_logs WHERE mode = 'precheck'"),
        "open_questions": one("SELECT COUNT(*) FROM questions WHERE status = 'open'"),
        "top_queries": [dict(r) for r in conn.execute(
            """SELECT query AS 検索語, COUNT(*) AS 回数, SUM(hit_count = 0) AS 見つからなかった回数
               FROM search_logs WHERE mode = 'search' GROUP BY query ORDER BY 回数 DESC LIMIT 10""")],
        "top_helpful": [dict(r) for r in conn.execute(
            "SELECT title, layer, helpful FROM knowledge WHERE helpful > 0 ORDER BY helpful DESC LIMIT 5")],
    }
