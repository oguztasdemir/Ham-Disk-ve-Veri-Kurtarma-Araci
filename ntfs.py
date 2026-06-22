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
                    for cluster_idx in range(run_len):
                        if records_read >= max_records:
                            break
                        f.seek((lcn + cluster_idx) * cluster_size)
                        cluster_data = f.read(cluster_size)
                        if len(cluster_data) < cluster_size:
                            break
                            
                        # Each cluster contains multiple 1024-byte records
                        for record_idx in range(cluster_size // 1024):
                            rec_offset = record_idx * 1024
                            record = cluster_data[rec_offset : rec_offset + 1024]
                            if len(record) < 1024 or record[0:4] != b"FILE":
                                continue
                                
                            records_read += 1
                            flags = int.from_bytes(record[22:24], "little")
                            is_in_use = flags & 1
                            is_dir = flags & 2
                            
                            # Focus on deleted files
                            if is_in_use == 0 and is_dir == 0:
                                first_attr_offset = int.from_bytes(record[20:22], "little")
                                attr_offset = first_attr_offset
                                filename = None
                                file_size = 0
                                file_start_byte = 0
                                
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
                                            file_start_byte = (lcn + cluster_idx) * cluster_size + rec_offset + attr_offset + val_off
                                        else: # non-resident
                                            real_sz = int.from_bytes(record[attr_offset + 56 : attr_offset + 64], "little")
                                            file_size = real_sz
                                            r_offset = int.from_bytes(record[attr_offset + 32 : attr_offset + 34], "little")
                                            run_bytes = record[attr_offset + r_offset : attr_offset + a_len]
                                            data_runs = parse_run_list(run_bytes)
                                            if data_runs:
                                                file_start_byte = data_runs[0][0] * cluster_size
                                                
                                    attr_offset += a_len
                                    
                                if filename and file_start_byte > 0:
                                    filename = "".join(c for c in filename if c.isprintable() and c not in '\\/:*?"<>|')
                                    deleted_files[file_start_byte] = (filename, file_size)
        print(f"NTFS MFT Analizi bitti: Toplam {len(deleted_files)} silinmiş dosya meta verisi yüklendi.")
    except Exception as e:
        print(f"MFT okuma hatası: {e}")
    return deleted_files

def find_original_file_meta(app_instance, offset):
    if not hasattr(app_instance, "ntfs_deleted_files") or not app_instance.ntfs_deleted_files:
        return None
    # Direct offset match (highly accurate on cluster aligned records)
    if offset in app_instance.ntfs_deleted_files:
        return app_instance.ntfs_deleted_files[offset]
    # Cluster alignment offset check (within 4096 bytes / 1 cluster)
    for file_offset, meta in app_instance.ntfs_deleted_files.items():
        if abs(offset - file_offset) < 4096:
            return meta
    return None
