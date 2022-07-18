#!/usr/bin/env python3
import os
import os.path
import re
from ebooklib import epub


def get_epub_metadata(fname: str) -> (str, str):
    book = epub.read_epub(fname)
    title = book.get_metadata('DC', 'title')[0][0]
    author = book.get_metadata('DC', 'creator')[0][0]
    return sanitize_title(title), author


def clean_fname(name: str) -> str:
    s = re.sub(r'\s+', ' ', str(name)).strip()
    return re.sub(r'(?u)[^-\w.\s]', '', s)


def sanitize_title(s: str) -> str:
    stopwords = ['the', 'a', 'at']
    words = [w for w in s.split() if w.lower() not in stopwords]
    return ' '.join(words)


def process_file(fname: str, dirpath: str):
    title, author = get_epub_metadata(os.path.join(dirpath, fname))
    # print(json.dumps(meta, indent=2))
    destname = clean_fname(f'{title} - {author}')
    if len(destname) > 254:
        destname = destname[:254]
    destname += '.epub'
    if not os.path.exists(os.path.join(dirpath, destname)):
        os.rename(os.path.join(dirpath, fname), os.path.join(dirpath, destname))
        print(f'"{fname}" ==> "{destname}"')


if __name__ == '__main__':
    for dirpath, dnames, fnames in os.walk('./'):
        for f in [f for f in fnames if f.lower().endswith('.epub')]:
            try:
                print(f)
                process_file(f, dirpath)
            except Exception:
                pass
