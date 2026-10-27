"""Optional worker-only inspection of current Woo-hosted certificate originals."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import cast
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests

from linker_engine.publication import MANIFEST_URL

from .canonical import Json, Object
from .certificate_declarations import inspect_certificate
from .errors import InvalidInput, VersionUnavailable
from .storage import Blobs

# Explicit inspection resource policy, not a product or certification limit.
# Over-policy files retain their source link and receive no inferred result.
MAX_PDF_BYTES = 16 * 1024 * 1024
MAX_DOCUMENTS = 20


class InspectionUnavailable(Exception):
    pass


def download_certificate(document: Object) -> bytes:
    parts = urlsplit(cast(str, document["url"]))
    authorities = [
        urlsplit(MANIFEST_URL),
        urlsplit(os.environ.get("LINKER_PUBLICATION_URL", MANIFEST_URL)),
    ]
    if (
        parts.username
        or parts.password
        or not any(
            (parts.scheme, parts.netloc) == (base.scheme, base.netloc)
            for base in authorities
        )
        or not parts.path.startswith("/wp-content/uploads/")
    ):
        raise InspectionUnavailable("source_origin")
    query = dict(parse_qsl(parts.query))
    query["linker_document_sha256"] = cast(str, document["blob_sha256"])
    url = urlunsplit(parts._replace(query=urlencode(query), fragment=""))
    with requests.Session() as session:
        session.trust_env = False
        with session.get(
            url,
            stream=True,
            allow_redirects=False,
            timeout=(5, 10),
            headers={"Accept": "application/pdf", "Cache-Control": "no-cache"},
        ) as response:
            if response.status_code != 200:
                raise InspectionUnavailable("source_unavailable")
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_content(chunk_size=65536):
                size += len(chunk)
                if size > MAX_PDF_BYTES:
                    raise InspectionUnavailable("resource_limit")
                chunks.append(chunk)
            return b"".join(chunks)


def inspect_report_certificates(
    source: Object,
    blobs: Blobs,
    guard: Callable[[], None],
    *,
    load: Callable[[Object], bytes] = download_certificate,
) -> Object:
    """Attach derived declarations and exact originals to the report source.

    Permission belongs to the enclosing report's before/after Woo checks.
    Existing content-addressed bytes are reused; neither a new source nor an
    additional maintenance surface is introduced. No network runs in HTTP.
    """
    evidence = source.get("certificates")
    if not isinstance(evidence, dict):
        raise InvalidInput("certificate inspection requires an equipment result")
    inspections: dict[str, Json] = {}
    dependencies: Object = {}
    for index, document in enumerate(cast(list[Object], evidence["documents"])):
        guard()
        identity = cast(str, document["document_id"])
        if index >= MAX_DOCUMENTS:
            inspections[identity] = {"status": "resource_limit"}
            continue
        try:
            try:
                content = blobs.read(cast(str, document["blob_sha256"]))
            except VersionUnavailable:
                content = load(document)
            if len(content) > MAX_PDF_BYTES:
                raise InspectionUnavailable("resource_limit")
            review = inspect_certificate(content, document)
            # inspect_certificate checks bytes before they may be retained.
            dependencies[f"certificate.{identity}.raw"] = blobs.put(content)
            inspections[identity] = review
        except (requests.RequestException, InspectionUnavailable) as error:
            inspections[identity] = {
                "status": "resource_limit"
                if isinstance(error, InspectionUnavailable)
                and str(error) == "resource_limit"
                else "unavailable"
            }
    evidence["inspections"] = inspections
    return dependencies
