#!/usr/bin/env python3
"""
Stand-alone epub renamer module
"""

import os
import os.path
import re
import zipfile
from xml.dom import minidom


def _discover_title(opf_xmldoc):
    return __discover_dc(opf_xmldoc, "title")


def __discover_dc(opf_xmldoc, name: str, first_only=True):
    value = None
    try:
        if first_only:
            node = opf_xmldoc.getElementsByTagName(name)[0].firstChild
            if node:
                value = node.nodeValue
        else:
            value = [
                n.firstChild.nodeValue
                for n in opf_xmldoc.getElementsByTagName(name)
                if n.firstChild
            ]
    except (KeyError, IndexError):
        pass
    if not value:
        tag_name = f"dc:{name}"
        try:
            if first_only:
                node = opf_xmldoc.getElementsByTagName(tag_name)[0].firstChild
                if node:
                    value = node.nodeValue
            else:
                value = [
                    n.firstChild.nodeValue
                    for n in opf_xmldoc.getElementsByTagName(tag_name)
                    if n.firstChild
                ]
        except (KeyError, IndexError):
            pass

    if first_only:
        return value.strip() if value else value
    else:
        return [v.strip() for v in value]


def iterate_all_tags(root):
    for node in root.childNodes:
        if node.nodeType != node.ELEMENT_NODE:
            continue

        yield node

        for subnode in iterate_all_tags(node):
            yield subnode


def _find_author_from_dom(xmldoc):
    # Only find a single author now with this algorithm but returning a list
    # because that's what caller expects
    authors = []

    # First non-empty child node is author after the author 'tag'
    found_author_tag = False

    for tag in iterate_all_tags(xmldoc):
        if not found_author_tag:
            if (
                tag.nodeName == "strong"
                and tag.childNodes
                and (tag.firstChild.nodeType == tag.firstChild.TEXT_NODE)
                and (tag.firstChild.data in ("Author", "Authors"))
            ):
                found_author_tag = True
        else:
            # Find all paragraph tags BEFORE we find another span tag. Those
            # are the author(s).
            if tag.nodeName == "span":
                break

            if (
                tag.nodeName == "p"
                and tag.childNodes
                and (tag.firstChild.nodeType == tag.firstChild.TEXT_NODE)
            ):

                data = tag.firstChild.data.strip()
                if data:
                    authors.append(data)

    return authors


def _discover_authors(opf_xmldoc, authors_html=None):
    authors = __discover_dc(opf_xmldoc, "creator", first_only=False)

    # We've found large portion of books from specific publishers that store
    # the authors in pr02.html in a very specific place.
    if not authors and authors_html is not None:
        authors = _find_author_from_dom(authors_html)

    # Slow and inefficient way to remove duplicates but maintain ordering just
    # in case the author order in epub is significant.
    unique_authors = []
    for author in authors:
        if author not in unique_authors:
            unique_authors.append(author)

    return unique_authors


def get_epub_metadata(filepath: str) -> dict:
    if not zipfile.is_zipfile(filepath):
        raise Exception(f"Unknown file {os.path.basename(filepath)}")

    try:
        zf = zipfile.ZipFile(
            filepath, "r", compression=zipfile.ZIP_DEFLATED, allowZip64=True
        )
        container = zf.read("META-INF/container.xml")
        container_xmldoc = minidom.parseString(container)

        opf_filepath = (
            container_xmldoc.getElementsByTagName("rootfile")[0]
            .attributes["full-path"]
            .value
        )

        opf_norm_path = os.path.normpath(opf_filepath)
        opf = zf.read(opf_filepath)
        # opf = zf.read(opf_norm_path)
        opf_xmldoc = minidom.parseString(opf)
    except IndexError:
        raise Exception(f"Cannot parse raw metadata from {os.path.basename(filepath)}")

    # This file is specific to the authors if it exists.
    authors_html = None
    try:
        authors_html = minidom.parseString(zf.read("OEBPS/pr02.html"))
    except KeyError:
        # Most books store authors using epub tags, so no worries.
        pass

    return {
        "title": _discover_title(opf_xmldoc),
        "authors": _discover_authors(opf_xmldoc, authors_html=authors_html),
    }


def clean_fname(name: str) -> str:
    s = re.sub(r"\s+", " ", str(name)).strip()
    return re.sub(r"(?u)[^-\w.\s]", "", s)


def sanitize_title(s: str) -> str:
    stopwords = ["the", "a", "at"]
    words = [w for w in s.split() if w.lower() not in stopwords]
    return " ".join(words)


def process_file(fname: str, dirpath: str):
    meta = get_epub_metadata(os.path.abspath(os.path.join(dirpath, fname)))
    # print(json.dumps(meta, indent=2))
    title = meta.get("title")
    author = meta.get("authors")[0]
    destname = clean_fname(f"{title} - {author}")
    if len(destname) > 254:
        destname = destname[:254]
    destname += ".epub"
    if not os.path.exists(os.path.join(dirpath, destname)):
        os.rename(os.path.join(dirpath, fname), os.path.join(dirpath, destname))
        print(f'"{fname}" ==> "{destname}"')


if __name__ == "__main__":
    for dirpath, _, fnames in os.walk("./"):
        for f in [f for f in fnames if f.lower().endswith(".epub")]:
            try:
                process_file(f, dirpath)
            except Exception:
                pass
