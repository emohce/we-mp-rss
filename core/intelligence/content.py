"""Immutable object references with an explicit legacy-read fallback."""
import hashlib

from .models import ArticleContentBlob


def prepare_objects(page, store):
    if store is None:
        return {}
    objects = {}
    for raw in page.articles:
        body = raw.get("content_html") or raw.get("content")
        if isinstance(body, str) and body.strip():
            encoded = body.encode("utf-8")
            if len(encoded) > 10 * 1024 * 1024:
                raise ValueError("article body exceeds 10 MiB")
            objects[str(raw.get("id") or "")] = store.put(encoded, suffix="html")
    return objects


def bind_objects(session, objects):
    for article_id, stored in objects.items():
        pointer = session.get(ArticleContentBlob, article_id)
        if pointer is None:
            pointer = ArticleContentBlob(article_id=article_id)
            session.add(pointer)
        pointer.content_hash = stored.content_hash
        pointer.storage_backend = stored.backend
        pointer.object_key = stored.key
        pointer.byte_size = stored.byte_size
        pointer.media_type = "text/html"


def resolve_content(session, article, *, store_factory=None):
    legacy = article.content_html or article.content or ""
    pointer = session.get(ArticleContentBlob, article.id)
    warning = ""
    if pointer is not None and store_factory is not None:
        try:
            store = store_factory()
            data = store.get(pointer.object_key)
            if len(data) != pointer.byte_size or hashlib.sha256(data).hexdigest() != pointer.content_hash:
                raise ValueError("stored content failed integrity check")
            return data.decode("utf-8"), "stored", ""
        except Exception:
            warning = "stored_content_unavailable"
    if legacy:
        return legacy, "legacy", warning
    return "", "unavailable" if pointer else "metadata_only", warning
