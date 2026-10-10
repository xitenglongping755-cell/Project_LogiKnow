-- schema.sql
-- LogiKnow のテーブル設計（★プロトタイプ用の仮設計。DB担当の設計が決まったら差し替える）

-- ナレッジ（4つの情報源を1つのテーブルにまとめ、layer 列で区別する）
CREATE TABLE IF NOT EXISTS knowledge (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    layer       TEXT NOT NULL CHECK (layer IN ('manual', 'report', 'local_rule', 'experience')),
    title       TEXT NOT NULL,              -- タイトル（検索で一致すると順位が上がる）
    content     TEXT NOT NULL,              -- 本文（どうする）
    reason      TEXT,                       -- 理由・教訓（なぜ）
    category    TEXT,                       -- カテゴリ（例：C. トラブル一次対応）
    location    TEXT,                       -- 配送先（空＝どこでも使える情報）
    time_band   TEXT,                       -- 時間帯（早朝・日中・夜間。空＝時間帯を問わない）
    keywords    TEXT,                       -- キーワード（カンマ区切り）
    source_ref  TEXT,                       -- 出典（マニュアル第◯章、報告書番号など）
    creator     TEXT,                       -- 登録者
    created_at  TEXT NOT NULL,              -- 登録日時（配送前チェックの「新しい順」に使う）
    helpful     INTEGER NOT NULL DEFAULT 0  -- 「役に立った」の数（知見の評価）
);

-- 答えが見つからなかった質問（ベテランに答えてもらう）
CREATE TABLE IF NOT EXISTS questions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    question    TEXT NOT NULL,
    location    TEXT,
    time_band   TEXT,
    asked_by    TEXT,
    asked_at    TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'open',   -- open / answered
    answer_id   INTEGER REFERENCES knowledge(id)
);

-- 検索の記録（活用状況・効果測定に使う）
CREATE TABLE IF NOT EXISTS search_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mode        TEXT NOT NULL,              -- precheck（配送前チェック）/ search（トラブル検索）
    query       TEXT,
    location    TEXT,
    hit_count   INTEGER NOT NULL,
    driver      TEXT,
    created_at  TEXT NOT NULL
);
