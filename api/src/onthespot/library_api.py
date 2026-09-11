## LOCAL LIBRARY ENDPOINTS
@app.get("/library")
async def get_library(
    q: str = "",
    sort: str = "artist",
    sort_descending: bool = False,
    duplicates_only: bool = False,
    missing_artwork: bool = False,
    failed_metadata: bool = False,
    file_format: str = "",
    artist: str = "",
    genre: str = "",
    date_from: int = 0,
    date_to: int = 0,
):
    return scan_library(
        q,
        sort,
        sort_descending,
        duplicates_only,
        missing_artwork,
        failed_metadata,
        file_format,
        artist,
        genre,
        date_from,
        date_to,
    )


@app.post("/library/scan")
async def scan_local_library(
    q: str = "",
    sort: str = "artist",
    sort_descending: bool = False,
    duplicates_only: bool = False,
    missing_artwork: bool = False,
    failed_metadata: bool = False,
    file_format: str = "",
    artist: str = "",
    genre: str = "",
    date_from: int = 0,
    date_to: int = 0,
):
    return scan_library(
        q,
        sort,
        sort_descending,
        duplicates_only,
        missing_artwork,
        failed_metadata,
        file_format,
        artist,
        genre,
        date_from,
        date_to,
    )


@app.get("/library/missing")
async def get_missing_library_items(q: str = ""):
    return {"items": missing_items(q)}


@app.post("/library/verify")
async def verify_library_files(request: LibraryVerify):
    targets = request.paths
    if not targets:
        snapshot = scan_library()
        targets = [item.get("path", "") for item in snapshot.get("items", [])]
    results = []
    for path in targets:
        try:
            results.append(verify_file(path))
        except ValueError as exc:
            results.append(
                {"path": path, "valid": False, "reason": str(exc), "size": 0}
            )
    corrupt = [item for item in results if not item.get("valid")]
    return {
        "checked": len(results),
        "healthy": len(results) - len(corrupt),
        "corrupt": len(corrupt),
        "items": results,
    }


@app.get("/library/file")
async def get_library_file(path: str):
    if not is_allowed_path(path):
        raise HTTPException(status_code=404, detail="Library file not found")
    media_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=os.path.basename(path))


@app.post("/library/open")
async def open_library_item(request: LibraryOpen):
    if not is_allowed_path(request.path):
        raise HTTPException(status_code=404, detail="Library file not found")
    try:
        if request.action == "play":
            open_item(request.path)
        else:
            open_item(os.path.dirname(os.path.abspath(request.path)))
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"success": True}


@app.post("/library/rename")
async def rename_library_item(request: LibraryRename):
    try:
        return {"success": True, "item": rename_file(request.path, request.new_name)}
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/library/metadata")
async def update_library_metadata(request: LibraryMetadata):
    try:
        changes = request.model_dump(exclude={"path"}, exclude_none=True)
        return {"success": True, "item": update_metadata(request.path, changes)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/library/cover")
async def update_library_cover(path: str = Form(...), cover: UploadFile = File(...)):
    try:
        data = await cover.read()
        return {"success": True, "item": update_cover(path, data)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/library/cover")
async def get_library_cover(path: str):
    try:
        data, mime = read_cover(path)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=404, detail="Cover art is unavailable") from exc
    return Response(
        content=data, media_type=mime, headers={"Cache-Control": "public, max-age=3600"}
    )


@app.post("/library/m3u")
async def create_library_m3u(request: LibraryM3U):
    try:
        path = write_m3u(request.name, request.paths)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"success": True, "path": path}


@app.post("/library/requeue")
async def requeue_missing_library_item(request: LibraryPath):
    target = os.path.normcase(os.path.abspath(os.path.expanduser(request.path)))
    record = next(
        (
            item
            for item in missing_items()
            if os.path.normcase(os.path.abspath(item.get("path", ""))) == target
        ),
        None,
    )
    if record is None:
        raise HTTPException(
            status_code=404, detail="No missing indexed download matches that file"
        )
    source_url = record.get("source_url")
    if not source_url:
        raise HTTPException(
            status_code=400,
            detail="This library entry has no source URL to re-download",
        )

    local_id = format_local_id(record.get("source_id") or source_url)
    item = {
        "local_id": local_id,
        "item_url": source_url,
        "item_service": record.get("source_service", "generic"),
        "item_type": record.get("source_type", "track"),
        "item_id": record.get("source_id") or source_url,
        "parent_category": "library",
        "available": True,
        "item_status": ItemStatus.WAITING,
        "name": record.get("title", ""),
        "artist": record.get("artist", ""),
        "album": record.get("album", ""),
        "playlist_name": record.get("playlist_name", ""),
        "playlist_by": record.get("playlist_by", ""),
        "playlist_number": record.get("playlist_number", ""),
        "queue_position": 0,
        "priority": 0,
    }
    with download_queue_lock:
        item["queue_position"] = (
            max(
                [entry.get("queue_position", -1) for entry in download_queue.values()],
                default=-1,
            )
            + 1
        )
        download_queue[local_id] = item
    pending.put_nowait(item)
    notification_hook(
        "Added missing file", f"Queued {item['name'] or source_url} for re-download."
    )
    return {"success": True, "local_id": local_id, "item": item}


@app.delete("/library/missing")
async def remove_missing_library_items(request: LibraryPaths):
    removed = remove_missing_items(request.paths)
    if request.paths and not removed:
        raise HTTPException(
            status_code=404,
            detail="No missing indexed downloads match the selected entries",
        )
    if removed:
        notification_hook(
            "Library entries removed",
            f"Removed {removed} missing file entr{'y' if removed == 1 else 'ies'} from the library index.",
        )
    return {"success": True, "removed": removed}
