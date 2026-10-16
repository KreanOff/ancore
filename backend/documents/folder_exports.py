"""Private Drive and Office folder exports from access-scoped querysets."""
from collections import defaultdict
from pathlib import PurePosixPath
from shutil import copyfileobj
from tempfile import SpooledTemporaryFile
from zipfile import ZIP_DEFLATED, ZipFile

from django.core.exceptions import SuspiciousFileOperation
from django.utils.text import get_valid_filename

from .models import WorkspaceDocument
from .rich_text import docx_bytes


def _safe_name(value, fallback):
    try:
        return get_valid_filename(value).strip(' .') or fallback
    except SuspiciousFileOperation:
        return fallback


def _unique_name(value, used):
    """Reserve file and directory names together, including on case-insensitive disks."""
    name, number = value, 2
    path = PurePosixPath(value)
    while name.casefold() in used:
        name = f'{path.stem} ({number}){path.suffix}'
        number += 1
    used.add(name.casefold())
    return name


def folder_archive(folder, folders, documents):
    children = defaultdict(list)
    for pk, parent_id, name in folders.order_by('pk').values_list('pk', 'parent_id', 'name'):
        children[parent_id].append((pk, name))
    root_name = _safe_name(folder.name, 'Folder')
    paths = {folder.pk: root_name}
    names = defaultdict(set)
    pending = [folder.pk]
    # Iterative traversal also guards against malformed cycles and foreign parents.
    while pending:
        parent_id = pending.pop()
        for pk, name in children[parent_id]:
            if pk in paths:
                continue
            name = _unique_name(_safe_name(name, 'Folder'), names[parent_id])
            paths[pk] = f'{paths[parent_id]}/{name}'
            pending.append(pk)

    output = SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode='w+b')
    try:
        with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
            for path in paths.values():
                archive.writestr(f'{path}/', b'')
            for item in documents.filter(folder_id__in=paths).order_by('pk').iterator():
                kind = getattr(item, 'kind', None)
                if kind == WorkspaceDocument.Kind.TEXT:
                    filename = _safe_name(item.title[:200], 'Dokument') + '.docx'
                elif kind == WorkspaceDocument.Kind.BOARD:
                    filename = _safe_name(item.title[:230], 'Tablica') + '.excalidraw'
                else:
                    filename = _safe_name(item.filename, 'Dokument')
                filename = _unique_name(filename, names[item.folder_id])
                path = f'{paths[item.folder_id]}/{filename}'
                if kind == WorkspaceDocument.Kind.TEXT:
                    archive.writestr(path, docx_bytes(item.content))
                elif kind == WorkspaceDocument.Kind.BOARD:
                    archive.writestr(path, item.content.encode())
                else:
                    if not item.file:
                        raise FileNotFoundError('Brak pliku dokumentu.')
                    with item.file.open('rb') as source, archive.open(path, 'w', force_zip64=True) as target:
                        copyfileobj(source, target, length=64 * 1024)
        output.seek(0)
        return output, f'{root_name}.zip'
    except Exception:
        output.close()
        raise
