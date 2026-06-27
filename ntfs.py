import os
import time

def parse_run_list(run_list_bytes):
    runs = []
    idx = 0
    prev_lcn = 0
    while idx < len(run_list_bytes):
        b = run_list_bytes[idx]
        if b == 0:
            break
        idx += 1
        len_size = b & 0x0F
        offset_size = (b >> 4) & 0x0F
        
        if idx + len_size + offset_size > len(run_list_bytes):
            break
            
        len_bytes = run_list_bytes[idx : idx + len_size]
        run_len = int.from_bytes(len_bytes, "little")
        idx += len_size
        
        offset_bytes = run_list_bytes[idx : idx + offset_size]
        if offset_size > 0:
            val = int.from_bytes(offset_bytes, "little")
            # Sign extend
            if offset_bytes[-1] & 0x80:
                val -= (1 << (offset_size * 8))
            lcn = prev_lcn + val
            prev_lcn = lcn
        else:
            lcn = 0 # sparse
            
        idx += offset_size
        runs.append((lcn, run_len))
    return runs

def scan_ntfs_deleted_files(drive_path, disk_lock):
    deleted_files = {}
    all_records = {}
    raw_files = []
    try:
        # We need admin privileges to open physical drives on Windows
        with disk_lock:
            with open(drive_path, "rb", buffering=0) as f:
                # Read boot sector
                f.seek(0)
                boot = f.read(512)
                if len(boot) < 512 or boot[3:11] != b"NTFS    ":
                    print("Seçilen disk NTFS dosya sistemi kullanmıyor.")
                    return deleted_files
                    
                bytes_per_sector = int.from_bytes(boot[11:13], "little")
                sectors_per_cluster = boot[13]
                cluster_size = bytes_per_sector * sectors_per_cluster
                mft_cluster = int.from_bytes(boot[48:56], "little")
                
                mft_offset = mft_cluster * cluster_size
                f.seek(mft_offset)
                mft_record = f.read(1024)
                if len(mft_record) < 1024 or mft_record[0:4] != b"FILE":
                    print("MFT başlangıç kaydı okunamadı.")
                    return deleted_files
                    
                # Parse $MFT run list from its data attribute (0x80)
                first_attr = int.from_bytes(mft_record[20:22], "little")
                offset = first_attr
                mft_runs = []
                while offset < 1024:
                    if offset + 8 > 1024:
                        break
                    attr_type = int.from_bytes(mft_record[offset:offset+4], "little")
                    if attr_type == 0xFFFFFFFF:
                        break
                    attr_len = int.from_bytes(mft_record[offset+4:offset+8], "little")
                    if attr_len <= 0 or offset + attr_len > 1024:
                        break
                        
                    if attr_type == 0x80: # $DATA
                        non_resident = mft_record[offset+8]
                        if non_resident == 1:
                            run_offset = int.from_bytes(mft_record[offset+32:offset+34], "little")
                            run_list_bytes = mft_record[offset + run_offset : offset + attr_len]
                            mft_runs = parse_run_list(run_list_bytes)
                        break
                    offset += attr_len
                    
                if not mft_runs:
                    # Contiguous fallback
                    mft_runs = [(mft_cluster, 20000)] # Read up to 20,000 clusters
                    
                print(f"NTFS MFT tablosu çözümleniyor... ({len(mft_runs)} veri bloğu bulundu)")
                
                records_read = 0
                max_records = 200000 # Cap records to scan quickly
                
                for lcn, run_len in mft_runs:
                    if records_read >= max_records:
                        break
                    
                    chunk_clusters = 512  # Read in 2 MB chunks (assuming 4KB clusters)
                    cluster_idx = 0
                    while cluster_idx < run_len and records_read < max_records:
                        to_read_clusters = min(chunk_clusters, run_len - cluster_idx)
                        read_size = to_read_clusters * cluster_size
                        f.seek((lcn + cluster_idx) * cluster_size)
                        run_data = f.read(read_size)
                        if not run_data:
                            break
                        
                        # Process records in the read buffer (each record is 1024 bytes)
                        for record_offset in range(0, len(run_data), 1024):
                            if records_read >= max_records:
                                break
                            record = run_data[record_offset : record_offset + 1024]
                            if len(record) < 1024 or record[0:4] != b"FILE":
                                continue
                                
                            records_read += 1
                            flags = int.from_bytes(record[22:24], "little")
                            is_in_use = flags & 1
                            is_dir = flags & 2
                            
                            # MFT attributes parsing
                            first_attr_offset = int.from_bytes(record[20:22], "little")
                            attr_offset = first_attr_offset
                            filename = None
                            parent_num = 0
                            modified_time_raw = 0
                            file_size = 0
                            file_start_byte = 0
                            
                            record_disk_offset = (lcn + cluster_idx) * cluster_size + record_offset
                            
                            while attr_offset < 1024:
                                if attr_offset + 8 > 1024:
                                    break
                                a_type = int.from_bytes(record[attr_offset : attr_offset + 4], "little")
                                if a_type == 0xFFFFFFFF:
                                    break
                                a_len = int.from_bytes(record[attr_offset + 4 : attr_offset + 8], "little")
                                if a_len <= 0 or attr_offset + a_len > 1024:
                                    break
                                    
                                if a_type == 0x30: # $FILE_NAME
                                    val_offset = int.from_bytes(record[attr_offset + 20 : attr_offset + 22], "little")
                                    fn_val_offset = attr_offset + val_offset
                                    if fn_val_offset + 60 < 1024:
                                        parent_num = int.from_bytes(record[fn_val_offset : fn_val_offset + 6], "little")
                                        modified_time_raw = int.from_bytes(record[fn_val_offset + 16 : fn_val_offset + 24], "little")
                                        name_len = record[fn_val_offset + 56]
                                        name_bytes = record[fn_val_offset + 58 : fn_val_offset + 58 + name_len * 2]
                                        try:
                                            filename = name_bytes.decode("utf-16-le", errors="ignore")
                                        except:
                                            pass
                                elif a_type == 0x80: # $DATA
                                    res = record[attr_offset + 8]
                                    if res == 0: # resident
                                        val_len = int.from_bytes(record[attr_offset + 16 : attr_offset + 20], "little")
                                        val_off = int.from_bytes(record[attr_offset + 20 : attr_offset + 22], "little")
                                        file_size = val_len
                                        file_start_byte = record_disk_offset + attr_offset + val_off
                                    else: # non-resident
                                        real_sz = int.from_bytes(record[attr_offset + 56 : attr_offset + 64], "little")
                                        file_size = real_sz
                                        r_offset = int.from_bytes(record[attr_offset + 32 : attr_offset + 34], "little")
                                        run_bytes = record[attr_offset + r_offset : attr_offset + a_len]
                                        data_runs = parse_run_list(run_bytes)
                                        if data_runs:
                                            file_start_byte = data_runs[0][0] * cluster_size
                                            
                                attr_offset += a_len
                                
                            if filename:
                                filename = "".join(c for c in filename if c.isprintable() and c not in '\\/:*?"<>|').strip()
                                record_num = int.from_bytes(record[44:48], "little")
                                if is_dir:
                                    all_records[record_num] = {"name": filename, "parent": parent_num, "is_dir": True}
                                elif is_in_use == 0 and file_start_byte > 0:
                                    raw_files.append({
                                        "offset": file_start_byte,
                                        "name": filename,
                                        "size": file_size,
                                        "parent": parent_num,
                                        "modified_raw": modified_time_raw
                                    })
                                    
                        cluster_idx += to_read_clusters
                                    
        # Reconstruct paths and times after MFT scan finishes
        for f_info in raw_files:
            path_parts = []
            curr = f_info["parent"]
            visited = set()
            while curr in all_records and curr not in visited:
                visited.add(curr)
                meta = all_records[curr]
                if curr == 5 or meta["name"] in ["$", "$MFT", "$Root"]:
                    break
                path_parts.append(meta["name"])
                curr = meta["parent"]
            custom_path = "/".join(reversed(path_parts)) if path_parts else None
            
            date_str = "-"
            unix_time = None
            raw_time = f_info["modified_raw"]
            if raw_time > 0:
                try:
                    unix_time = (raw_time - 116444736000000000) / 10000000.0
                    if 0 < unix_time < 2000000000:
                        date_str = time.strftime("%d.%m.%Y %H:%M", time.localtime(unix_time))
                    else:
                        unix_time = None
                except:
                    unix_time = None
                    
            deleted_files[f_info["offset"]] = {
                "name": f_info["name"],
                "size": f_info["size"],
                "custom_path": custom_path,
                "date": date_str,
                "modified_epoch": unix_time
            }
            
        print(f"NTFS MFT Analizi bitti: Toplam {len(deleted_files)} silinmiş dosya meta verisi yüklendi.")
    except Exception as e:
        print(f"MFT okuma hatası: {e}")
    return deleted_files

def find_original_file_meta(app_instance, offset, file_ext=None):
    if not hasattr(app_instance, "ntfs_deleted_files") or not app_instance.ntfs_deleted_files:
        return None
        
    # 1. Direct offset match (highly accurate)
    if offset in app_instance.ntfs_deleted_files:
        return app_instance.ntfs_deleted_files[offset]
        
    # 2. Proximity check with extension match (range: 256 KB)
    best_match = None
    min_diff = 262144
    
    for file_offset, meta in app_instance.ntfs_deleted_files.items():
        diff = abs(offset - file_offset)
        if diff < min_diff:
            # If extension is provided, make sure it matches
            if file_ext:
                meta_name = meta.get("name", "").lower()
                if not meta_name.endswith(file_ext.lower()):
                    continue
            best_match = meta
            min_diff = diff
            
    return best_match
