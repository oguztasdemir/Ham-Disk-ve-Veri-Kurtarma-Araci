# carver.py
import time
import os
import queue
import threading
from config import FILE_SIGNATURES

def read_raw_bytes_shared(disk, offset, size, disk_lock):
    """Thread-safe raw sector aligned read from an open disk handle or a path string."""
    sector_size = 512
    start_sector = offset // sector_size
    sector_offset = offset % sector_size
    
    end_byte = sector_offset + size
    sectors_to_read = (end_byte + sector_size - 1) // sector_size
    
    if isinstance(disk, str):
        with disk_lock:
            try:
                with open(disk, "rb", buffering=0) as f:
                    f.seek(start_sector * sector_size)
                    raw_data = f.read(sectors_to_read * sector_size)
                return raw_data[sector_offset : sector_offset + size]
            except Exception as e:
                print(f"Hata disk okunurken (path): {e}")
                return b""
                
    with disk_lock:
        try:
            prev_pos = disk.tell()
            disk.seek(start_sector * sector_size)
            raw_data = disk.read(sectors_to_read * sector_size)
            disk.seek(prev_pos)
            return raw_data[sector_offset : sector_offset + size]
        except Exception as e:
            print(f"Hata disk okunurken (handle): {e}")
            return b""

def extract_filename_from_bytes(raw_bytes, ext):
    """Attempts to parse a meaningful name from document/archive metadata headers."""
    ext = ext.lower()
    try:
        if ext == ".pdf":
            # Search for /Title (Document Title)
            idx = raw_bytes.find(b"/Title")
            if idx != -1:
                start = raw_bytes.find(b"(", idx)
                end = raw_bytes.find(b")", start)
                if start != -1 and end != -1 and end > start:
                    title = raw_bytes[start+1:end].decode("utf-8", errors="ignore").strip()
                    title = "".join(c for c in title if c.isalnum() or c in "._- ")
                    if title:
                        return title
        elif ext == ".mp4":
            # Search for metadata title tag ©nam
            idx = raw_bytes.find(b"\xa9nam")
            if idx != -1:
                data_idx = raw_bytes.find(b"data", idx)
                if data_idx != -1 and data_idx - idx < 32:
                    len_val = int.from_bytes(raw_bytes[data_idx-4:data_idx], "big")
                    title_bytes = raw_bytes[data_idx+8 : data_idx+len_val]
                    title = title_bytes.decode("utf-8", errors="ignore").strip()
                    title = "".join(c for c in title if c.isalnum() or c in "._- ")
                    if title:
                        return title
        elif ext in [".zip", ".docx", ".xlsx", ".pptx"]:
            # Check local file entry for first file in the ZIP archive
            if raw_bytes.startswith(b"PK\x03\x04"):
                fn_len = int.from_bytes(raw_bytes[26:28], "little")
                if fn_len > 0 and fn_len < 256:
                    filename = raw_bytes[30:30+fn_len].decode("utf-8", errors="ignore").strip()
                    filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
                    if filename and "[Content_Types]" not in filename:
                        # Use the base name of the first file in the archive (e.g. invoice_archive)
                        name_only = os.path.splitext(os.path.basename(filename))[0]
                        if name_only:
                            return f"{name_only}_arsiv"
    except:
        pass
    return None

def get_mp4_size(disk, start_offset, disk_lock):
    """Walks the MP4 box headers to calculate the container size with zero memory overhead."""
    offset = start_offset
    total_size = 0
    try:
        while True:
            header = read_raw_bytes_shared(disk, offset, 8, disk_lock)
            if len(header) < 8:
                break
            box_size = int.from_bytes(header[0:4], "big")
            box_type = header[4:8]
            
            # Check if box type is valid ASCII
            if not all(32 <= b <= 126 for b in box_type):
                break
                
            if box_size == 1:
                large_header = read_raw_bytes_shared(disk, offset + 8, 8, disk_lock)
                if len(large_header) < 8:
                    break
                box_size = int.from_bytes(large_header, "big")
                offset += 16
            elif box_size == 0:
                break
            else:
                offset += 8
                
            if box_size < 8:
                break
                
            total_size = (offset - start_offset) + (box_size - 8)
            offset = start_offset + total_size
    except:
        pass
    # Default to 10MB if parsing fails
    return max(total_size, 10 * 1024 * 1024)

def get_zip_size(disk, start_offset, disk_lock, max_search=20 * 1024 * 1024):
    """Scans forward for ZIP EOCD signature (PK\x05\x06) to compute precise ZIP file sizes."""
    eocd_sig = b"\x50\x4b\x05\x06"
    chunk_size = 2 * 1024 * 1024
    bytes_searched = 0
    overlap = len(eocd_sig) - 1
    buffer = b""
    
    try:
        while bytes_searched < max_search:
            chunk = read_raw_bytes_shared(disk, start_offset + bytes_searched, chunk_size, disk_lock)
            if not chunk:
                break
            
            buffer = buffer[-overlap:] + chunk if buffer else chunk
            idx = 0
            while True:
                idx = buffer.find(eocd_sig, idx)
                if idx == -1:
                    break
                
                buffer_start = start_offset + bytes_searched - (overlap if bytes_searched > 0 else 0)
                eocd_offset = buffer_start + idx
                
                # Read EOCD record
                eocd_record = read_raw_bytes_shared(disk, eocd_offset, 22, disk_lock)
                if len(eocd_record) >= 22:
                    cd_size = int.from_bytes(eocd_record[12:16], "little")
                    cd_offset = int.from_bytes(eocd_record[16:20], "little")
                    comment_len = int.from_bytes(eocd_record[20:22], "little")
                    
                    expected_eocd_offset = start_offset + cd_offset + cd_size
                    if expected_eocd_offset == eocd_offset:
                        return cd_offset + cd_size + 22 + comment_len
                idx += 1
            bytes_searched += len(chunk)
    except:
        pass
    return 1024 * 1024  # Default to 1MB if parsing fails


def find_footer_offset(disk, start_offset, footer_sig, disk_lock, max_search_size=100 * 1024 * 1024):
    """Scans forward on disk for a footer signature using sector-aligned reads, avoiding memory bloat."""
    chunk_size = 4 * 1024 * 1024  # 4 MB scan window
    bytes_searched = 0
    overlap = len(footer_sig) - 1
    buffer = b""
    
    try:
        while bytes_searched < max_search_size:
            chunk = read_raw_bytes_shared(disk, start_offset + bytes_searched, chunk_size, disk_lock)
            if not chunk:
                break
            
            buffer = buffer[-overlap:] + chunk if buffer else chunk
            idx = buffer.find(footer_sig)
            if idx != -1:
                # Found the footer. Calculate precise offset relative to file start
                buffer_start = start_offset + bytes_searched - (overlap if bytes_searched > 0 else 0)
                absolute_found = buffer_start + idx
                return absolute_found + len(footer_sig) - start_offset
            
            bytes_searched += len(chunk)
    except:
        pass
    return max_search_size  # Cap at max search size if not found

def producer_read_segment_loop(disk, read_queue, app_instance, chunk_size, start_offset, end_offset, worker_lock):
    current_offset = start_offset
    with app_instance.segment_lock:
        progress = app_instance.segment_progress.get(start_offset, 0)
        current_offset += progress
        
    while app_instance.is_scanning:
        if app_instance.scan_paused:
            time.sleep(0.1)
            continue
            
        if current_offset >= end_offset:
            read_queue.put((None, None))
            break
            
        try:
            with worker_lock:
                disk.seek(current_offset)
                to_read = chunk_size
                if current_offset + chunk_size > end_offset:
                    to_read = end_offset - current_offset
                    if to_read <= 0:
                        read_queue.put((None, None))
                        break
                        
                chunk = disk.read(to_read)
                actual_offset = current_offset
                current_offset = disk.tell()
                
            if not chunk:
                read_queue.put((None, None))
                break
                
            read_queue.put((actual_offset, chunk))
        except Exception as e:
            read_queue.put(("error", str(e)))
            break

def scan_disk_worker(app_instance, drive_path, signatures):
    """Worker function that runs in a background thread to scan the disk virtually in segments."""
    chunk_size = 128 * 1024 * 1024  # 128 MB scan step
    
    # Ensure MFT table is loaded exactly once
    with app_instance.segment_lock:
        mft_already_loaded = hasattr(app_instance, "ntfs_deleted_files")
        if not mft_already_loaded:
            app_instance.ntfs_deleted_files = None
            
    if not mft_already_loaded:
        try:
            from ntfs import scan_ntfs_deleted_files
            app_instance.msg_queue.put(("status", "Silinmiş dosya isimleri taranıyor..."))
            mft_data = scan_ntfs_deleted_files(drive_path, app_instance.disk_lock)
            with app_instance.segment_lock:
                app_instance.ntfs_deleted_files = mft_data
        except Exception as e:
            print(f"NTFS meta veri ayıklama hatası: {e}")
            with app_instance.segment_lock:
                app_instance.ntfs_deleted_files = {}

    app_instance.msg_queue.put(("status", "Sektörler okunuyor..."))
    
    start_time = time.time() - getattr(app_instance, "elapsed_seconds", 0.0)
    total_paused_time = 0.0
    last_update_time = 0.0
    
    def send_progress(current_bytes):
        nonlocal last_update_time
        current_time = time.time()
        if current_time - last_update_time >= 0.3:
            last_update_time = current_time
            elapsed_time = current_time - start_time - total_paused_time
            if elapsed_time <= 0:
                elapsed_time = 0.001
                
            total_size = app_instance.active_drive_size
            scan_start = getattr(app_instance, "scan_start_offset", 0)
            scan_end = getattr(app_instance, "scan_end_offset", total_size)
            range_size = scan_end - scan_start
            if range_size <= 0:
                range_size = total_size
            
            with app_instance.segment_lock:
                total_scanned_bytes = sum(app_instance.segment_progress.values())
            
            # Speed (MB/s)
            speed_mb = (total_scanned_bytes / (1024 * 1024)) / elapsed_time
            
            # Percentage
            if range_size > 0:
                pct = (total_scanned_bytes / range_size) * 100
                if pct > 100: pct = 100.0
            else:
                pct = 0.0
                
            # ETA
            if pct > 0.1 and speed_mb > 0.01 and range_size > 0:
                remaining_bytes = range_size - total_scanned_bytes
                remaining_seconds = remaining_bytes / (speed_mb * 1024 * 1024)
                
                eta_hours = int(remaining_seconds // 3600)
                eta_mins = int((remaining_seconds % 3600) // 60)
                eta_secs = int(remaining_seconds % 60)
                if eta_hours > 0:
                    eta_str = f"{eta_hours} sa {eta_mins} dk"
                elif eta_mins > 0:
                    eta_str = f"{eta_mins} dk {eta_secs} sn"
                else:
                    eta_str = f"{eta_secs} sn"
            else:
                eta_str = "Hesaplanıyor..."
                
            # Elapsed formatted
            el_hours = int(elapsed_time // 3600)
            el_mins = int((elapsed_time % 3600) // 60)
            el_secs = int(elapsed_time % 60)
            if el_hours > 0:
                elapsed_str = f"{el_hours:02d}:{el_mins:02d}:{el_secs:02d}"
            else:
                elapsed_str = f"{el_mins:02d}:{el_secs:02d}"
                
            app_instance.msg_queue.put(("progress_update", {
                "pct": pct,
                "gb": total_scanned_bytes / (1024 * 1024 * 1024),
                "total_gb": range_size / (1024 * 1024 * 1024) if range_size > 0 else 0.0,
                "speed": speed_mb,
                "elapsed": elapsed_str,
                "eta": eta_str,
                "offset": scan_start + total_scanned_bytes,
                "elapsed_seconds": elapsed_time
            }))

    try:
        worker_lock = threading.Lock()
        # Open separate handle per worker for true parallel seek/read operations
        with open(drive_path, "rb", buffering=0) as disk:
            
            while app_instance.is_scanning:
                segment = None
                with app_instance.segment_lock:
                    if app_instance.scan_segments:
                        segment = app_instance.scan_segments.pop(0)
                        
                if not segment:
                    break
                    
                segment_start, segment_end = segment
                
                # Make sure segment key is initialized in progress mapping
                with app_instance.segment_lock:
                    if segment_start not in app_instance.segment_progress:
                        app_instance.segment_progress[segment_start] = 0
                
                # Scale queue capacity to respect memory bounds
                worker_count = int(getattr(app_instance, "active_worker_count", 1))
                queue_max = max(2, 32 // worker_count)
                read_queue = queue.Queue(maxsize=queue_max)
                
                # Start segment reader thread
                reader_thread = threading.Thread(
                    target=producer_read_segment_loop, 
                    args=(disk, read_queue, app_instance, chunk_size, segment_start, segment_end, worker_lock), 
                    daemon=True
                )
                reader_thread.start()
                
                buffer = b""
                buffer_start_offset = segment_start
                
                while app_instance.is_scanning:
                    # Pause control
                    if app_instance.scan_paused:
                        pause_start = time.time()
                        while app_instance.scan_paused and app_instance.is_scanning:
                            time.sleep(0.2)
                        total_paused_time += (time.time() - pause_start)
                        
                    if not app_instance.is_scanning:
                        break
                        
                    try:
                        # Fetch next pre-read chunk from queue
                        try:
                            chunk_offset, chunk = read_queue.get(timeout=0.2)
                        except queue.Empty:
                            continue
                            
                        if chunk_offset == "error":
                            app_instance.msg_queue.put(("error", f"Okuma Hatası: {chunk}"))
                            break
                        if chunk_offset is None:
                            # End of segment
                            break
                    except Exception as e:
                        app_instance.msg_queue.put(("error", f"Hata: {e}"))
                        break
                        
                    buffer += chunk
                    
                    # Update this segment's progress
                    scanned_in_segment = chunk_offset + len(chunk) - segment_start
                    with app_instance.segment_lock:
                        app_instance.segment_progress[segment_start] = scanned_in_segment
                        
                    send_progress(chunk_offset + len(chunk))
                    
                    matched = True
                    while matched and app_instance.is_scanning:
                        while app_instance.scan_paused and app_instance.is_scanning:
                            time.sleep(0.2)
                            
                        matched = False
                        for sig in signatures:
                            header = sig["header"]
                            header_len = len(header)
                            
                            if sig["ext"] == ".mp4":
                                idx = buffer.find(b"ftyp")
                                if idx >= 4:
                                    start_idx = idx - 4
                                else:
                                    start_idx = -1
                            else:
                                start_idx = buffer.find(header)
                                
                            if start_idx != -1:
                                # File found! Find size dynamically and memory-efficiently
                                absolute_start_offset = buffer_start_offset + start_idx
                                file_len = 0
                                
                                # Query original MFT metadata
                                from ntfs import find_original_file_meta
                                original_meta = find_original_file_meta(app_instance, absolute_start_offset)
                                
                                if original_meta:
                                    original_name, original_size = original_meta
                                    file_len = original_size
                                else:
                                    if sig["ext"] == ".mp4":
                                        # Parse box sizes sequentially without loading stream into RAM
                                        file_len = get_mp4_size(disk, absolute_start_offset, worker_lock)
                                    elif sig["ext"] == ".zip":
                                        # Parse actual ZIP size using EOCD
                                        file_len = get_zip_size(disk, absolute_start_offset, worker_lock)
                                    elif sig["footer"]:
                                        # Search footer signature inside the memory buffer first to avoid disk seeks/reads
                                        footer_sig = sig["footer"]
                                        footer_idx_in_buf = buffer.find(footer_sig, start_idx + header_len)
                                        if footer_idx_in_buf != -1:
                                            file_len = footer_idx_in_buf + len(footer_sig) - start_idx
                                        else:
                                            # Fallback to reading disk with a strict cap based on extension
                                            limit_map = {".jpg": 8 * 1024 * 1024, ".png": 12 * 1024 * 1024, ".pdf": 20 * 1024 * 1024}
                                            max_search = limit_map.get(sig["ext"], 15 * 1024 * 1024)
                                            file_len = find_footer_offset(disk, absolute_start_offset, footer_sig, worker_lock, max_search_size=max_search)
                                    else:
                                        # For archives/others without footers (like RAR), default to 1MB
                                        file_len = 1 * 1024 * 1024
                                    
                                # Try to extract the original filename from the first 2KB of raw bytes
                                extracted_name = None
                                is_previewable = False
                                file_ext = sig["ext"]
                                file_category = sig["category"]
                                
                                try:
                                    header_bytes = read_raw_bytes_shared(disk, absolute_start_offset, 2048, worker_lock)
                                    extracted_name = extract_filename_from_bytes(header_bytes, sig["ext"])
                                    
                                    # If it's a zip, detect if it's actually an MS Office document
                                    if sig["ext"] == ".zip" and header_bytes.startswith(b"PK\x03\x04"):
                                        if b"word/" in header_bytes:
                                            file_ext = ".docx"
                                            file_category = "Belge"
                                        elif b"xl/" in header_bytes:
                                            file_ext = ".xlsx"
                                            file_category = "Belge"
                                        elif b"ppt/" in header_bytes:
                                            file_ext = ".pptx"
                                            file_category = "Belge"
                                    
                                    # Validate previewable state using the already loaded header bytes
                                    if file_ext in [".jpg", ".jpeg", ".png"]:
                                        try:
                                            import io
                                            from PIL import Image
                                            Image.open(io.BytesIO(header_bytes))
                                            is_previewable = True
                                        except:
                                            pass
                                except:
                                    pass
                                    
                                with app_instance.disk_lock:
                                    app_instance.total_recovered_count += 1
                                    file_count = app_instance.total_recovered_count
                                    
                                fmt_name = file_ext.replace(".", "").lower()
                                
                                if original_meta:
                                    name_val = original_name
                                elif extracted_name:
                                    name_val = f"{extracted_name}{file_ext}"
                                else:
                                    name_val = f"kurtarilan_{fmt_name}_{file_count}{file_ext}"
                                    
                                file_meta = {
                                    "id": file_count,
                                    "name": name_val,
                                    "offset": absolute_start_offset,
                                    "size": file_len,
                                    "ext": file_ext,
                                    "category": file_category,
                                    "type_name": file_ext.replace(".", "").upper(),
                                    "is_previewable": is_previewable
                                }
                                app_instance.msg_queue.put(("recovered_file_meta", file_meta))
                                
                                # Slide buffer forward past header
                                buffer = buffer[start_idx + header_len:]
                                buffer_start_offset += start_idx + header_len
                                
                                scanned_in_segment = buffer_start_offset - segment_start
                                with app_instance.segment_lock:
                                    app_instance.segment_progress[segment_start] = scanned_in_segment
                                    
                                send_progress(buffer_start_offset)
                                matched = True
                                break
                                
                        # Prune buffer to keep RAM usage under 1MB when not matching
                        if not matched:
                            overlap = 64 * 1024
                            if len(buffer) > overlap:
                                discard_len = len(buffer) - overlap
                                buffer = buffer[discard_len:]
                                buffer_start_offset += discard_len
                                
                # Mark segment as completely scanned when done
                with app_instance.segment_lock:
                    app_instance.segment_progress[segment_start] = segment_end - segment_start
                    
    except PermissionError:
        app_instance.msg_queue.put(("error", "HATA: Yönetici yetkileri eksik veya disk erişime kapalı."))
    except Exception as e:
        app_instance.msg_queue.put(("error", f"Hata: {e}"))
        
    with app_instance.disk_lock:
        # Check if any other workers are still running
        running_workers = False
        # If active_disk_handle is cleared here, it might interfere with other threads,
        # but since they all open their own handles, we don't have to clear active_disk_handle
        # unless it is the last thread finishing.
        pass
        
    # Wait until all workers finish to send finished message
    with app_instance.segment_lock:
        # Check if all segments are completed
        all_done = True
        for start, prog in app_instance.segment_progress.items():
            # Find the segment size
            for seg_start, seg_end in app_instance.scan_segments:
                if seg_start == start:
                    if prog < (seg_end - seg_start):
                        all_done = False
                        break
            if not all_done:
                break
                
    if all_done:
        app_instance.is_scanning = False
        # Get count
        with app_instance.disk_lock:
            total_cnt = app_instance.total_recovered_count
        app_instance.msg_queue.put(("finished", f"Sanal tarama bitti! Toplam {total_cnt} dosya izi bulundu."))
