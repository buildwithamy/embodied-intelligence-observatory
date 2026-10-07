import hashlib
import logging
from urllib.parse import quote

from bs4 import BeautifulSoup

from .models import Candidate, Evidence

logger = logging.getLogger(__name__)


def deepen(candidate: Candidate, client) -> None:
    url = "https://arxiv.org/html/" + candidate.arxiv_id if candidate.arxiv_id else candidate.url
    try:
        html = client.get_text(url)
        soup = BeautifulSoup(html, "html.parser")
        for element in soup(["script", "style", "nav", "header", "footer"]):
            element.decompose()
        body = soup.find("article") or soup.find("main") or soup.body or soup
        text = body.get_text(" ", strip=True)
        if len(text) < 400 or text.lstrip().startswith(("Access Denied", "Just a moment")):
            raise ValueError("insufficient body")
        # Remove oversized reference lists and preserve the actual research sections.
        text = text.split("References")[0][:60000]
        eid = "body-" + hashlib.sha256(url.encode()).hexdigest()[:12]
        if eid not in {e.id for e in candidate.evidence}:
            candidate.evidence.append(Evidence(id=eid, url=url, source="arxiv" if candidate.arxiv_id
                                               else candidate.sources[0], kind="paper_full_text"
                                               if candidate.arxiv_id else "official_body", text=text))
        candidate.notes.append("已获取原文正文；正文仍需内容审核")
    except Exception as exc:
        # Exception class only: third-party exceptions may include credentials or headers.
        candidate.notes.append("正文获取失败（" + type(exc).__name__ + "）；不能视为全文深读")
        logger.warning("research failed candidate=%s error=%s", candidate.id, type(exc).__name__)
    if candidate.arxiv_id and not candidate.abstract:
        try:
            import xml.etree.ElementTree as ET

            xml = client.get_text("https://export.arxiv.org/api/query?id_list=" + quote(candidate.arxiv_id))
            root = ET.fromstring(xml)
            ns = {"a": "http://www.w3.org/2005/Atom"}
            entry = root.find("a:entry", ns)
            if entry is None or entry.findtext("a:title", "", ns).strip() == "Error":
                raise ValueError("arxiv metadata missing")
            candidate.abstract = " ".join(entry.findtext("a:summary", "", ns).split())
            candidate.authors = [a.findtext("a:name", "", ns) for a in entry.findall("a:author", ns)]
            candidate.evidence.append(Evidence(id="abstract-" + candidate.arxiv_id, url=candidate.url,
                                               source="arxiv", kind="paper_abstract", text=candidate.abstract))
        except Exception as exc:
            logger.warning("metadata failed candidate=%s error=%s", candidate.id, type(exc).__name__)
