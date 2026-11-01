"""Phát hiện chủ đề (BT-02) và phân loại xu hướng (BT-04) trên dữ liệu đã làm sạch.

Theo QD-05: xu hướng là xu hướng chủ đề của cộng đồng - chỉ đếm theo chủ đề/ngày, không theo tác giả.

Cách làm (baseline có thể giải thích được, chỉ dùng scikit-learn):
1. Gom bài theo category (từ khóa/video nguồn); mỗi nhóm đủ dữ liệu: TF-IDF 1-2 gram + NMF -> chủ đề.
2. Đếm số bài mỗi ngày cho từng chủ đề (chuỗi thời gian độ quan tâm).
3. So 3 ngày gần nhất với tối đa 7 ngày trước đó:
     chưa có bài trước đó và >= 5 bài gần đây -> Mới nổi; tăng >= 50% -> Đang tăng;
     giảm >= 50% -> Đang giảm; còn lại -> Ổn định; dữ liệu < 2 ngày -> Chưa đủ dữ liệu.
4. Chiều cảm xúc: (tích cực - tiêu cực) gần đây so với trước đó, lệch > 0.15 -> Tích cực hóa / Tiêu cực hóa.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta

STOPWORDS = set("""
và là của có cho không được những các này đó thì mà với một người trong khi cũng rất đã đang sẽ lại ra vào lên
nhưng nên vì nếu như để bị còn thế gì ai nào đâu vậy ạ ơi nhé nha à ừ thôi quá lắm rồi mình tôi bạn anh em chị
ad video clip kênh xem xxngườidùng xxsđt xxemail thấy biết nói làm đi về từ theo hơn nữa chứ hay hả luôn mới cái
con nó họ chúng ta mọi ở tại sao vì vậy thật đúng có_thể cần phải muốn
""".split())

MIN_DOCS = 20
RECENT_DAYS, PREV_DAYS = 3, 7


def make_vectorizer(**kw):
    from sklearn.feature_extraction.text import TfidfVectorizer
    return TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=0.9, token_pattern=r"(?u)\b[^\W\d_]{2,}\b",
                           stop_words=list(STOPWORDS), **kw)


def _topics_for_group(texts: list[str], k: int | None = None) -> tuple[list[list[str]], list[int]]:
    from sklearn.decomposition import NMF

    vec = make_vectorizer()
    x = vec.fit_transform(texts)
    k = k or max(2, min(8, len(texts) // 40))  # mặc định: khoảng 1 chủ đề / 40 bài, từ 2 tới 8
    k = min(k, x.shape[1] - 1) if x.shape[1] > 2 else 1
    if k < 2:
        return [[w for w, _ in Counter(" ".join(texts).split()).most_common(6)]], [0] * len(texts)
    nmf = NMF(n_components=k, init="nndsvda", random_state=42, max_iter=400)
    w = nmf.fit_transform(x)
    vocab = vec.get_feature_names_out()
    keywords = [[vocab[i] for i in comp.argsort()[::-1][:6]] for comp in nmf.components_]
    return keywords, w.argmax(axis=1).tolist()


def classify_trend(daily: dict[date, int]) -> tuple[str, float]:
    days = sorted(daily)
    if len(days) < 2:
        return "Chưa đủ dữ liệu", 0.0
    last = days[-1]
    recent_start = last - timedelta(days=RECENT_DAYS - 1)
    prev_start = max(days[0], recent_start - timedelta(days=PREV_DAYS))
    prev_days = (recent_start - prev_start).days
    recent = sum(c for d, c in daily.items() if d >= recent_start)
    prev = sum(c for d, c in daily.items() if prev_start <= d < recent_start)
    if prev_days <= 0:
        return "Chưa đủ dữ liệu", 0.0
    recent_avg, prev_avg = recent / RECENT_DAYS, prev / prev_days
    if prev == 0:
        return ("Mới nổi", 1.0) if recent >= 5 else ("Chưa đủ dữ liệu", 0.0)
    growth = (recent_avg - prev_avg) / prev_avg
    if growth >= 0.5:
        return "Đang tăng", growth
    if growth <= -0.5:
        return "Đang giảm", growth
    return "Ổn định", growth


def sentiment_shift(rows: list[tuple[date, str | None]], last_day: date) -> str:
    recent_start = last_day - timedelta(days=RECENT_DAYS - 1)

    def polarity(items):
        labeled = [s for s in items if s]
        if len(labeled) < 5:
            return None
        return (labeled.count("Tích cực") - labeled.count("Tiêu cực")) / len(labeled)

    r = polarity([s for d, s in rows if d >= recent_start])
    p = polarity([s for d, s in rows if d < recent_start])
    if r is None or p is None:
        return "Chưa đủ dữ liệu"
    return "Tích cực hóa" if r - p > 0.15 else "Tiêu cực hóa" if r - p < -0.15 else "Ổn định"


def hashtag_trends(rows: list[tuple[list[str], date, str | None]], top: int = 20) -> list[dict]:
    """T-22: tần suất hashtag theo ngày + phân loại xu hướng bằng cùng luật với chủ đề.
    rows: [(danh sách hashtag của bài, ngày, category)] -> top hashtag theo số bài 3 ngày gần nhất."""
    daily: dict[str, Counter] = defaultdict(Counter)
    cats: dict[str, Counter] = defaultdict(Counter)
    for tags, day, cat in rows:
        for t in tags:
            daily[t][day] += 1
            cats[t][cat or "Chung"] += 1
    if not daily:
        return []
    last = max(d for c in daily.values() for d in c)
    recent_start = last - timedelta(days=RECENT_DAYS - 1)
    out = []
    for tag, series in daily.items():
        label, growth = classify_trend(series)
        out.append({"hashtag": tag, "total": sum(series.values()), "recent": sum(c for d, c in series.items() if d >= recent_start),
                    "trend_label": label, "growth": round(float(growth), 4), "category": cats[tag].most_common(1)[0][0]})
    return sorted(out, key=lambda x: (-x["recent"], -x["total"]))[:top]


def analyze(posts: list[dict]) -> list[dict]:
    """posts: [{text, day: date, category, sentiment: 'Tích cực'|'Tiêu cực'|'Trung tính'|None}]
    -> danh sách chủ đề kèm chuỗi theo ngày và phân loại xu hướng."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for p in posts:
        groups[p.get("category") or "Chung"].append(p)
    topics = []
    for category, items in groups.items():
        if len(items) < MIN_DOCS:
            continue
        keywords, assign = _topics_for_group([p["text"] for p in items])
        for t_idx, kw in enumerate(keywords):
            members = [p for p, a in zip(items, assign) if a == t_idx]
            if not members:
                continue
            daily = Counter(p["day"] for p in members)
            label, growth = classify_trend(daily)
            sents = [p["sentiment"] for p in members if p["sentiment"]]
            share = lambda name: round(sents.count(name) / len(sents), 4) if sents else 0.0  # noqa: E731
            daily_sent = defaultdict(Counter)
            for p in members:
                daily_sent[p["day"]][p["sentiment"]] += 1
            topics.append({
                "category": category, "topic_index": t_idx, "keywords": ", ".join(kw), "size": len(members),
                "trend_label": label, "growth": round(float(growth), 4),
                "sentiment_shift": sentiment_shift([(p["day"], p["sentiment"]) for p in members], max(daily)),
                "positive_share": share("Tích cực"), "negative_share": share("Tiêu cực"), "neutral_share": share("Trung tính"),
                "daily": [{"day": d, "count": c, "positive": daily_sent[d]["Tích cực"], "negative": daily_sent[d]["Tiêu cực"]}
                          for d, c in sorted(daily.items())],
            })
    return topics
