# carver.py
import time
import os
from config import FILE_SIGNATURES

def read_raw_bytes_shared(disk, offset, size, disk_lock):
    """Thread-safe raw sector aligned read from an open disk handle."""
    sector_size = 512
    start_sector = offset // sector_size
    sector_offset = offset % sector_size
    
    end_byte = sector_offset + size
    sectors_to_read = (end_byte + sector_size - 1) // sector_size
    
    with disk_lock:
        prev_pos = disk.tell()
        disk.seek(start_sector * sector_size)
        raw_data = disk.read(sectors_to_read * sector_size)
        disk.seek(prev_pos)
        
    return raw_data[sector_offset : sector_offset + size]

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

def scan_disk_worker(app_instance, drive_path, signatures):
    """Worker function that runs in a background thread to scan the disk virtually."""
    chunk_size = 8 * 1024 * 1024  # 8 MB scan step
    file_count = len(app_instance.virtual_files)
    current_scan_offset = getattr(app_instance, "resume_offset", 0)
    
    app_instance.msg_queue.put(("status", "Sektörler okunuyor..."))
    
    start_time = time.time() - getattr(app_instance, "elapsed_seconds", 0.0)
    total_paused_time = 0.0
    last_update_time = 0.0
    
    try:
        with open(drive_path, "rb") as disk:
            with app_instance.disk_lock:
                app_instance.active_disk_handle = disk
                
            buffer = b""
            buffer_start_offset = 0
            
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
                    with app_instance.disk_lock:
                        disk.seek(current_scan_offset)
                        chunk = disk.read(chunk_size)
                        current_scan_offset = disk.tell()
                    if not chunk:
                        break
                except Exception as e:
                    app_instance.msg_queue.put(("error", f"Okuma Hatası: {e}"))
                    break
                    
                buffer += chunk
                
                # Calculate progress metrics
                elapsed_time = time.time() - start_time - total_paused_time
                if elapsed_time <= 0:
                    elapsed_time = 0.001
                    
                total_size = app_instance.active_drive_size
                bytes_scanned = current_scan_offset
                
                # Speed (MB/s)
                speed_mb = (bytes_scanned / (1024 * 1024)) / elapsed_time
                
                # Percentage
                if total_size > 0:
                    pct = (bytes_scanned / total_size) * 100
                    if pct > 100: pct = 100.0
                else:
                    pct = 0.0
                    
                # ETA
                if pct > 0.1 and speed_mb > 0.01 and total_size > 0:
                    remaining_bytes = total_size - bytes_scanned
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
                    
                # Throttle progress updates to UI at most 3 times per second
                current_time = time.time()
                if current_time - last_update_time >= 0.3:
                    last_update_time = current_time
                    app_instance.msg_queue.put(("progress_update", {
                        "pct": pct,
                        "gb": bytes_scanned / (1024 * 1024 * 1024),
                        "total_gb": total_size / (1024 * 1024 * 1024) if total_size > 0 else 0.0,
                        "speed": speed_mb,
                        "elapsed": elapsed_str,
                        "eta": eta_str,
                        "offset": bytes_scanned,
                        "elapsed_seconds": elapsed_time
                    }))
                
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
                            
                            if sig["ext"] == ".mp4":
                                # Parse box sizes sequentially without loading stream into RAM
                                file_len = get_mp4_size(disk, absolute_start_offset, app_instance.disk_lock)
                            elif sig["ext"] == ".zip":
                                # Parse actual ZIP size using EOCD
                                file_len = get_zip_size(disk, absolute_start_offset, app_instance.disk_lock)
                            elif sig["footer"]:
                                # Search footer signature dynamically on disk
                                file_len = find_footer_offset(disk, absolute_start_offset, sig["footer"], app_instance.disk_lock)
                            else:
                                # For archives/others without footers (like RAR), default to 1MB
                                file_len = 1 * 1024 * 1024

                                
                            # Try to extract the original filename from the first 2KB of raw bytes
                            extracted_name = None
                            try:
                                header_bytes = read_raw_bytes_shared(disk, absolute_start_offset, 2048, app_instance.disk_lock)
                                extracted_name = extract_filename_from_bytes(header_bytes, sig["ext"])
                            except:
                                pass
                                
                            file_count += 1
                            fmt_name = sig["ext"].replace(".", "").lower()
                            
                            if extracted_name:
                                name_val = f"{extracted_name}{sig['ext']}"
                            else:
                                name_val = f"kurtarilan_{fmt_name}_{file_count}{sig['ext']}"
                                
                            file_meta = {
                                "id": file_count,
                                "name": name_val,
                                "offset": absolute_start_offset,
                                "size": file_len,
                                "ext": sig["ext"],
                                "category": sig["category"],
                                "type_name": sig["ext"].replace(".", "").upper()
                            }
                            app_instance.msg_queue.put(("recovered_file_meta", file_meta))
                            
                            # Slide buffer forward past header
                            buffer = buffer[start_idx + header_len:]
                            buffer_start_offset += start_idx + header_len
                            matched = True
                            break
                            
                    # Prune buffer to keep RAM usage under 1MB when not matching
                    if not matched:
                        overlap = 64 * 1024
                        if len(buffer) > overlap:
                            discard_len = len(buffer) - overlap
                            buffer = buffer[discard_len:]
                            buffer_start_offset += discard_len
    except PermissionError:
        app_instance.msg_queue.put(("error", "HATA: Yönetici yetkileri eksik veya disk erişime kapalı."))
    except Exception as e:
        app_instance.msg_queue.put(("error", f"Hata: {e}"))
        
    with app_instance.disk_lock:
        app_instance.active_disk_handle = None
        
    app_instance.is_scanning = False
    app_instance.msg_queue.put(("finished", f"Sanal tarama bitti! Toplam {file_count} dosya izi bulundu."))
