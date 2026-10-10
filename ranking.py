""" ranking.py """
""" TF-IDF 検索エンジン。講義W4の SearchEngine をベースに、LogiKnow 用に調整したもの """

# W4版からの変更点
#   1. 検索対象の項目を LogiKnow のナレッジに合わせた（タイトル・本文・理由・キーワード・配送先）
#   2. タイトル加点を「重要語ごと」に判定する形に変えた
#      （query_processor の検索文字列は「元の質問＋関連語」と長いので、文字列全体での一致はまず起きないため）
#   3. 50文字未満の文書の減点を外した（ナレッジは短い文章が多いため）

from datetime import datetime

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class SearchEngine:
    """TF-IDFベースの検索エンジン（情報源ごとに1つ作る）"""

    def __init__(self):
        # 日本語は単語の間にスペースが無いので、2〜3文字のまとまり（文字N-gram）で比べる（W4と同じ）
        self.vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 3),
                                          max_features=5000, min_df=1, max_df=0.95, sublinear_tf=True)
        self.tfidf_matrix = None
        self.pages = []
        self.is_fitted = False

    def build_index(self, pages: list):
        """全ナレッジの TF-IDF インデックスを作る"""
        self.pages = pages
        if not pages:
            self.is_fitted = False
            return
        corpus = []
        for p in pages:
            # タイトル3倍・本文2倍・キーワード2倍の重み（W4と同じ考え方）
            corpus.append(" ".join([
                ((p.get("title") or "") + " ") * 3,
                ((p.get("content") or "") + " ") * 2,
                (p.get("reason") or "") + " ",
                ((p.get("keywords") or "").replace(",", " ") + " ") * 2,
                p.get("location") or "",
            ]))
        # 文書が1件だけだと max_df=0.95 で全部の語が消えるので、そのときは制限を外す
        self.vectorizer.set_params(max_df=1.0 if len(pages) == 1 else 0.95)
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
        self.is_fitted = True

    def search(self, query: str, top_n: int = 20) -> list:
        """TF-IDF で検索し、関連度の高い順に返す"""
        if not self.is_fitted or not query.strip():
            return []
        similarities = cosine_similarity(self.vectorizer.transform([query]), self.tfidf_matrix)[0]
        results = []
        for idx, base_score in enumerate(similarities):
            if base_score > 0.01:
                page = self.pages[idx].copy()
                page["relevance_score"] = round(float(self._final_score(page, base_score, query)) * 100, 1)
                page["base_score"] = round(float(base_score) * 100, 1)
                results.append(page)
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:top_n]

    def _final_score(self, page: dict, base_score: float, query: str) -> float:
        """タイトル一致・キーワード一致・新しさを加味した最終スコア"""
        score = base_score
        terms = [t for t in query.lower().split() if len(t) >= 2]   # 検索文字列を語に分ける

        # 1. タイトル加点：重要語がタイトルに含まれていれば上げる（1語で×1.4、2語以上で×1.6）
        title = (page.get("title") or "").lower()
        hits = sum(1 for t in set(terms) if t in title)
        if hits >= 2:
            score *= 1.6
        elif hits == 1:
            score *= 1.4

        # 2. キーワード加点：登録されたキーワードと一致すれば上げる
        keywords = [k.strip().lower() for k in (page.get("keywords") or "").split(",") if k.strip()]
        if any(t in keywords for t in terms):
            score *= 1.3

        # 3. 新しさ加点：90日以内は最大 +20%（W4と同じ）
        created = page.get("created_at") or ""
        if created:
            try:
                days_old = (datetime.now() - datetime.fromisoformat(created)).days
                if days_old <= 90:
                    score *= 1 + 0.2 * (90 - days_old) / 90
            except ValueError:
                pass
        return score
