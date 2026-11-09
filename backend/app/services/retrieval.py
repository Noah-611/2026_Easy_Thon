# 용도: 검토된 공식 자료에서 태그와 TF-IDF로 관련 문서 조각을 찾는다.
import json
from pathlib import Path
from urllib.parse import urlparse

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.app.config import ROOT
from backend.app.schemas import Signal, Source

OFFICIAL_HOSTS = {"www.fsc.go.kr", "www.korea.kr", "www.boho.or.kr", "www.kisa.or.kr",
                  "risc.kisa.or.kr", "spam.kisa.or.kr", "eiec.kdi.re.kr", "www.fss.or.kr"}


class KnowledgeBase:
    def __init__(self, path: Path = ROOT / "data/knowledge"):
        self.sources = {s["source_id"]: s for s in json.loads((path / "sources.json").read_text())}
        self.chunks = [json.loads(line) for line in (path / "chunks.jsonl").read_text().splitlines() if line.strip()]
        for source in self.sources.values():
            url = urlparse(source["url"])
            if url.scheme != "https" or url.hostname not in OFFICIAL_HOSTS or not source.get("checked_at"):
                raise ValueError("knowledge source not reviewed")
        if any(c["source_id"] not in self.sources for c in self.chunks):
            raise ValueError("unknown knowledge source")
        self.vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 5))
        self.matrix = self.vectorizer.fit_transform([c["text"] for c in self.chunks]) if self.chunks else None

    def retrieve(self, signals: list[Signal]) -> list[dict]:
        if self.matrix is None:
            return []
        candidates = []
        for signal in signals:
            query = " ".join([signal.reason, *(e.quote for e in signal.evidence)])
            evidence_text = " ".join(e.quote for e in signal.evidence)
            scores = cosine_similarity(self.vectorizer.transform([query]), self.matrix)[0]
            for chunk, score in zip(self.chunks, scores):
                context_terms = chunk.get("required_context_terms", [])
                if context_terms and not any(term in evidence_text for term in context_terms):
                    continue
                if signal.tag.value in chunk["signal_tags"] and score >= 0.10:
                    source = self.sources[chunk["source_id"]]
                    candidates.append({"signal_id": signal.id, "score": float(score), **chunk,
                                       "publisher": source["publisher"], "title": source["title"]})
        # At most three chunks across the request; keep all relevant signal associations.
        candidates.sort(key=lambda c: c["score"], reverse=True)
        chosen = list(dict.fromkeys(c["chunk_id"] for c in candidates))[:3]
        return [c for c in candidates if c["chunk_id"] in chosen][:12]

    def public_source(self, chunk: dict) -> Source:
        s = self.sources[chunk["source_id"]]
        return Source(id=s["source_id"], chunk_id=chunk["chunk_id"], title=s["title"],
                      publisher=s["publisher"], url=s["url"], checked_at=s["checked_at"], excerpt=chunk["text"])
