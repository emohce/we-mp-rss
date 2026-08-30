"""Local persisted-content search. No query initiates a provider fetch."""
from sqlalchemy import func, inspect, literal_column, or_, select, table
from bs4 import BeautifulSoup

from core.models.article import Article
from .models import SearchDocument, utcnow


def index_article(session, article):
    source = " ".join(str(value or "") for value in (article.title, article.description,
                                                     article.content_html or article.content))
    soup = BeautifulSoup(source, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    document = session.get(SearchDocument, article.id)
    if document is None:
        document = SearchDocument(article_id=article.id)
        session.add(document)
    document.search_text = soup.get_text(" ", strip=True)
    document.updated_at = utcnow()


def search_predicate(session, query):
    query = query.strip()
    pattern = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    dialect = session.get_bind().dialect.name
    indexed = select(SearchDocument.article_id)
    if dialect == "sqlite" and len(query) >= 3 and inspect(session.connection()).has_table("int_search_fts"):
        phrase = '"' + query.replace('"', '""') + '"'
        indexed = select(literal_column("article_id")).select_from(table("int_search_fts")).where(
            literal_column("int_search_fts").match(phrase))
    elif dialect == "postgresql" and all(ord(ch) < 128 for ch in query) and any(ch.isalnum() for ch in query):
        indexed = indexed.where(func.to_tsvector("simple", SearchDocument.search_text).op("@@")(
            func.plainto_tsquery("simple", query)))
    else:
        indexed = indexed.where(SearchDocument.search_text.ilike(pattern, escape="\\"))
    missing_index = ~select(SearchDocument.article_id).where(SearchDocument.article_id == Article.id).correlate(Article).exists()
    legacy = or_(*(column.ilike(pattern, escape="\\") for column in (
        Article.title, Article.description, Article.content, Article.content_html)))
    return or_(Article.id.in_(indexed), missing_index & legacy)
