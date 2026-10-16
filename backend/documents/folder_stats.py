"""Folder summaries built from access-scoped Drive or Office querysets."""
from django.db.models import Sum


def set_folder_summaries(rows, folders, documents, *, library_scoped=False):
    visible = {row['item'].pk: row['item'] for row in rows if row['kind'] == 'folder'}
    if not visible:
        return
    for item in visible.values():
        item.total_size = 0
        item.has_files = False
    folder_fields = ['pk', 'parent_id']
    document_fields = ['folder_id']
    if library_scoped:
        library_ids = {item.library_id for item in visible.values()}
        folders = folders.filter(library_id__in=library_ids)
        documents = documents.filter(library_id__in=library_ids)
        folder_fields.append('library_id')
        document_fields.append('library_id')
    parents = {entry['pk']: entry for entry in folders.values(*folder_fields)}
    summaries = documents.filter(
        deleted_at__isnull=True, folder_id__in=parents,
    ).order_by().values(*document_fields).annotate(total=Sum('file_size'))
    # Include descendants without crossing inaccessible parents or Drive libraries.
    for entry in summaries:
        folder_id, seen = entry['folder_id'], set()
        while folder_id in parents and folder_id not in seen:
            parent = parents[folder_id]
            if library_scoped and parent['library_id'] != entry['library_id']:
                break
            seen.add(folder_id)
            if folder_id in visible:
                visible[folder_id].total_size += entry['total']
                # Presence is independent of size, including empty native documents.
                visible[folder_id].has_files = True
            folder_id = parent['parent_id']
