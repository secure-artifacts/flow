# -*- coding: utf-8 -*-
import os
import shutil
import re
from pathlib import Path

class VideoChecker:
    """Service to check generated video completeness and relocate video files,
    strictly scoped to specific project directories and identifiers.
    """

    @staticmethod
    def get_file_size_str(filepath):
        try:
            size_bytes = os.path.getsize(filepath)
            if size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.1f} KB"
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        except Exception:
            return "未知"

    @staticmethod
    def is_matching_video_file(filename, seq_num):
        """Strictly checks if a video filename matches a segment index (seq_num).
        Ensures digit boundaries to prevent false positives like matching 106 for index 6.
        """
        ext = Path(filename).suffix.lower()
        if ext not in ['.mp4', '.mov', '.webm', '.avi']:
            return False

        stem = Path(filename).stem
        
        # Exact match: "01", "1"
        if stem.strip() == f"{seq_num:02d}" or stem.strip() == str(seq_num):
            return True

        # Boundary regex match:
        pattern = re.compile(rf'(?:^|[_\-\s\(\[])0*{seq_num}(?=[_\-\s\.\)\]]|$)', re.IGNORECASE)
        return bool(pattern.search(stem))

    @staticmethod
    def find_project_folders(search_dir, project_id, index, col1_name):
        """Finds subdirectories in search_dir that specifically belong to this project."""
        if not search_dir or not search_dir.exists() or not search_dir.is_dir():
            return []

        idx_prefix = f"{index:02d}_"
        matched = []

        try:
            for entry in search_dir.iterdir():
                if entry.is_dir():
                    name_lower = entry.name.lower()
                    pid_lower = project_id.lower()
                    
                    # 1. Exact match on project_id or project_id without suffix
                    if name_lower == pid_lower or name_lower == pid_lower.replace("-flow", ""):
                        matched.append(entry)
                        continue
                        
                    # 2. Match index prefix (e.g. "02_") and col1_name
                    if entry.name.startswith(idx_prefix):
                        if not col1_name or col1_name.lower() in name_lower:
                            matched.append(entry)
                            continue
                            
                    # 3. Match folder containing full project_id string
                    if pid_lower in name_lower or pid_lower.replace("-flow", "") in name_lower:
                        matched.append(entry)
                        continue
        except Exception as e:
            print(f"Error finding project folders in {search_dir}: {e}")

        return matched

    @staticmethod
    def check_project_videos(project_model, project_path, custom_search_dir=None):
        """Scans disk for generated video files STRICTLY scoped to the target project directory/name.
        Will NOT pick up random videos from other projects.
        """
        if not project_model or not project_model.spanish_segments:
            return {
                "total_segments": 0,
                "found_count": 0,
                "missing_count": 0,
                "completion_rate": 0.0,
                "segments_detail": [],
                "primary_search_dir": ""
            }

        segments = project_model.spanish_segments
        total_segments = len(segments)
        project_id = project_model.project_id
        index = getattr(project_model, "index", 1)
        col1_name = getattr(project_model, "col1_name", "")
        
        # 1. Target videos directory inside project folder
        target_videos_dir = Path(project_path) / "downloads" / "videos"
        target_videos_dir.mkdir(parents=True, exist_ok=True)

        # 2. Base search bases
        chrome_downloads = Path.home() / "Downloads"
        default_flow_dir = chrome_downloads / "Flow"
        
        base_search_dirs = []
        if custom_search_dir:
            cd = Path(custom_search_dir)
            if cd.exists():
                base_search_dirs.append(cd)
        if default_flow_dir.exists():
            base_search_dirs.append(default_flow_dir)
        if chrome_downloads.exists():
            base_search_dirs.append(chrome_downloads)

        # 3. Locate SPECIFIC project folders matching project_id / index + col1_name
        project_scoped_dirs = [target_videos_dir]
        for b_dir in base_search_dirs:
            # If b_dir is already the project folder itself (e.g. user selected Downloads/Flow/02_衣服-flow)
            b_name = b_dir.name.lower()
            if b_name == project_id.lower() or (b_name.startswith(f"{index:02d}_") and (not col1_name or col1_name.lower() in b_name)):
                if b_dir.resolve() not in [p.resolve() for p in project_scoped_dirs]:
                    project_scoped_dirs.append(b_dir)
            else:
                # Find matching project subfolders inside b_dir
                matched_subfolders = VideoChecker.find_project_folders(b_dir, project_id, index, col1_name)
                for sf in matched_subfolders:
                    if sf.resolve() not in [p.resolve() for p in project_scoped_dirs]:
                        project_scoped_dirs.append(sf)

        # 4. Match segment files STRICTLY inside project_scoped_dirs
        segments_detail = []
        found_count = 0

        for idx, seg in enumerate(segments):
            seq_num = idx + 1
            idx_str = f"{seq_num:02d}"
            text = seg.get("text", "")
            download_name = f"{idx_str}.mp4"
            target_path = target_videos_dir / download_name

            found_file = None
            
            # A. Check if target_path already exists inside project
            if target_path.exists() and target_path.is_file():
                found_file = target_path
            else:
                # B. Search strictly inside this project's scoped directories
                for p_dir in project_scoped_dirs:
                    if not p_dir.exists() or not p_dir.is_dir():
                        continue
                        
                    # Check exact 01.mp4 in this project's folder
                    direct_file = p_dir / download_name
                    if direct_file.exists() and direct_file.is_file():
                        found_file = direct_file
                        break
                        
                    # Scan files inside this project's folder
                    try:
                        for entry in p_dir.iterdir():
                            if entry.is_file() and VideoChecker.is_matching_video_file(entry.name, seq_num):
                                found_file = entry
                                break
                    except Exception:
                        pass

                    if found_file:
                        break

                # C. If not in project folder, check flat files in base_search_dirs ONLY IF filename starts with project_id or index+col1
                if not found_file:
                    idx_prefix = f"{index:02d}_"
                    for b_dir in base_search_dirs:
                        if not b_dir.exists() or not b_dir.is_dir():
                            continue
                        try:
                            for entry in b_dir.iterdir():
                                if entry.is_file():
                                    fname_lower = entry.name.lower()
                                    # Ensure flat file explicitly starts with project_id or index prefix
                                    if fname_lower.startswith(project_id.lower()) or entry.name.startswith(idx_prefix):
                                        if VideoChecker.is_matching_video_file(entry.name, seq_num):
                                            found_file = entry
                                            break
                        except Exception:
                            pass
                        if found_file:
                            break

            if found_file:
                found_count += 1
                file_size = VideoChecker.get_file_size_str(found_file)
                segments_detail.append({
                    "index": seq_num,
                    "text": text,
                    "download_name": download_name,
                    "found": True,
                    "source_path": found_file,
                    "target_path": target_path,
                    "already_in_target": (found_file.resolve() == target_path.resolve()),
                    "file_size": file_size
                })
            else:
                segments_detail.append({
                    "index": seq_num,
                    "text": text,
                    "download_name": download_name,
                    "found": False,
                    "source_path": None,
                    "target_path": target_path,
                    "already_in_target": False,
                    "file_size": "-"
                })

        missing_count = total_segments - found_count
        completion_rate = (found_count / total_segments * 100.0) if total_segments > 0 else 0.0

        primary_dir_str = str(project_scoped_dirs[1]) if len(project_scoped_dirs) > 1 else str(target_videos_dir)

        return {
            "total_segments": total_segments,
            "found_count": found_count,
            "missing_count": missing_count,
            "completion_rate": completion_rate,
            "segments_detail": segments_detail,
            "target_videos_dir": str(target_videos_dir),
            "primary_search_dir": primary_dir_str
        }

    @staticmethod
    def relocate_found_videos(report):
        """Relocates (moves) all found videos from external directories (e.g. Downloads/Flow/01_project-flow)
        into the project's target videos folder.
        """
        details = report.get("segments_detail", [])
        moved_count = 0
        already_count = 0
        error_msgs = []

        for item in details:
            if not item.get("found") or not item.get("source_path"):
                continue

            src = Path(item["source_path"])
            dst = Path(item["target_path"])

            if src.resolve() == dst.resolve():
                already_count += 1
                continue

            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                item["source_path"] = dst
                item["already_in_target"] = True
                moved_count += 1
            except Exception as e:
                error_msgs.append(f"移动 {src.name} 失败: {e}")

        return {
            "moved_count": moved_count,
            "already_count": already_count,
            "errors": error_msgs
        }
