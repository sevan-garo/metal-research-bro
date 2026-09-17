"""search_zotero tool, via pyzotero talking to the local Zotero desktop app.

Local mode (`local=True`) talks directly to Zotero's own local API at
http://localhost:23119/api instead of the network Zotero Web API — no API key
to manage, and library data never leaves the machine (see docs/adr/0009).
Requires Zotero > Settings > Advanced > "Allow other applications on this
computer to communicate with Zotero" to be enabled.
"""

from functools import lru_cache

from pyzotero import zotero

from agent.state import RetrievedChunk

LOCAL_LIBRARY_ID = "0"
LOCAL_LIBRARY_TYPE = "user"

# Exclude attachments (PDFs, snapshots): they carry no citable text of their
# own, and the local API's itemType filter does not support the Web API's
# "-attachment && -note" boolean syntax (verified empirically — the combined
# form silently fails to filter at all). Notes are filtered client-side below.
EXCLUDED_ITEM_TYPE = "-attachment"


@lru_cache(maxsize=1)
def get_client() -> zotero.Zotero:
    return zotero.Zotero(library_id=LOCAL_LIBRARY_ID, library_type=LOCAL_LIBRARY_TYPE, local=True)


def _authors_from_creators(creators: list[dict]) -> str:
    names = []
    for creator in creators:
        if "lastName" in creator:
            names.append(creator["lastName"])
        elif "name" in creator:
            names.append(creator["name"])
    return ", ".join(names)


def _item_to_chunk(item: dict) -> RetrievedChunk:
    data = item.get("data", {})
    title = data.get("title") or "Untitled"
    authors = _authors_from_creators(data.get("creators", []))
    abstract = data.get("abstractNote", "")

    return RetrievedChunk(
        document_id=item.get("key", ""),
        title=title,
        text=abstract if abstract else f"{title} ({authors})" if authors else title,
        section="abstract" if abstract else None,
        page=None,
        source="zotero",
        score=1.0,
        doi=data.get("DOI") or None,
    )


def search_zotero(query: str, filters: dict | None = None) -> list[RetrievedChunk]:
    client = get_client()
    filters = filters or {}

    params: dict = {
        "q": query,
        "qmode": filters.get("qmode", "titleCreatorYear"),
        "itemType": EXCLUDED_ITEM_TYPE,
        "limit": filters.get("limit", 10),
    }
    if tag := filters.get("tag"):
        params["tag"] = tag

    collection_key = filters.get("collection")
    items = client.collection_items(collection_key, **params) if collection_key else client.items(**params)

    return [_item_to_chunk(item) for item in items if item.get("data", {}).get("itemType") != "note"]
