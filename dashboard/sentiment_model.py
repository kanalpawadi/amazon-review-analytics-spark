"""
Score review text with the sentiment model trained in Spark (Phase 4a) - without Spark.

The Spark pipeline was:
    Phase 2:  title + text -> clean_text -> RegexTokenizer(\\s+, min length 2) -> StopWordsRemover
    Phase 4a: NGram(2) -> tokens + bigrams -> CountVectorizer -> IDF -> LogisticRegression
06a_dashboard_export.ipynb saved the vocabulary, IDF weights, LR weights and stop words into
sentiment_model.npz; this file repeats the same steps with numpy.
"""
import re

import numpy as np

CLASSES = ["negative", "neutral", "positive"]


def clean_text(title, text):
    """Same rules as clean_text() in 02_cleaning.ipynb."""
    c = f"{title or ''} {text or ''}"
    c = re.sub(r"<[^>]+>", " ", c)                    # HTML tags such as <br />
    c = re.sub(r"&#?[a-zA-Z0-9]+;", " ", c)           # HTML codes such as &#34;
    c = re.sub(r"https?://\S+|www\.\S+", " ", c)      # links
    c = c.lower()
    c = re.sub(r"n't\b", " not", c)                   # don't -> do not
    c = re.sub(r"[^a-z ]", " ", c)                    # keep letters only
    c = re.sub(r"\s+", " ", c)
    return c.strip()


class SentimentModel:
    def __init__(self, path):
        data = np.load(path)
        self.terms = data["vocab"].tolist()
        self.vocab = {term: i for i, term in enumerate(self.terms)}
        self.idf = data["idf"]
        self.coef = data["coef"]              # classes x vocabulary
        self.intercept = data["intercept"]
        self.stop_words = set(data["stop_words"].tolist())

    def tokens(self, title, text):
        return [w for w in clean_text(title, text).split() if len(w) >= 2 and w not in self.stop_words]

    def features(self, tokens):
        """Sparse TF-IDF features as {vocabulary index: value}."""
        terms = tokens + [f"{a} {b}" for a, b in zip(tokens, tokens[1:])]
        counts = {}
        for t in terms:
            j = self.vocab.get(t)
            if j is not None:
                counts[j] = counts.get(j, 0) + 1
        return {j: n * self.idf[j] for j, n in counts.items()}

    def predict(self, title, text=""):
        """Return class probabilities and the terms that pushed the prediction most."""
        feats = self.features(self.tokens(title, text))
        idx = np.fromiter(feats.keys(), dtype=int, count=len(feats))
        vals = np.fromiter(feats.values(), dtype=float, count=len(feats))
        logits = self.intercept + (self.coef[:, idx] @ vals if len(idx) else 0.0)
        p = np.exp(logits - logits.max())
        p = p / p.sum()
        best = int(p.argmax())
        contrib = sorted(((self.terms[j], float(self.coef[best, j] * v)) for j, v in feats.items()),
                         key=lambda x: -x[1])
        return {"probabilities": dict(zip(CLASSES, p.round(4).tolist())),
                "label": CLASSES[best],
                "top_terms": contrib[:8]}
