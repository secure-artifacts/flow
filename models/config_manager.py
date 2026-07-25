# -*- coding: utf-8 -*-
import json
from pathlib import Path

class ConfigManager:
    """Manages application-wide settings in .app_config.json."""
    
    CONFIG_FILE_NAME = ".app_config.json"
    
    DEFAULT_MAX_BATCH_POINTS = 50
    DEFAULT_CHAR_DURATION_RULES = [
        {"max_chars": 50, "duration": 4},
        {"max_chars": 100, "duration": 6},
        {"max_chars": 140, "duration": 8},
        {"max_chars": 180, "duration": 10}
    ]
    DEFAULT_DURATION_POINTS_RULES = [
        {"duration": 4, "points": 7},
        {"duration": 6, "points": 10},
        {"duration": 8, "points": 12},
        {"duration": 10, "points": 15}
    ]
    
    DEFAULT_FORCED_SPLIT_MARKER = "///"
    
    def __init__(self, workspace_dir):
        self.workspace_dir = Path(workspace_dir)
        self.config_path = self.workspace_dir / self.CONFIG_FILE_NAME
        
        self.base_path = ""
        self.max_batch_points = self.DEFAULT_MAX_BATCH_POINTS
        self.forced_split_marker = self.DEFAULT_FORCED_SPLIT_MARKER
        self.char_duration_rules = [dict(r) for r in self.DEFAULT_CHAR_DURATION_RULES]
        self.duration_points_rules = [dict(r) for r in self.DEFAULT_DURATION_POINTS_RULES]
        
        self.load()

    def load(self):
        """Loads configuration from .app_config.json."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.base_path = data.get("base_path", self.base_path)
                    self.max_batch_points = data.get("max_batch_points", self.DEFAULT_MAX_BATCH_POINTS)
                    self.forced_split_marker = data.get("forced_split_marker", self.DEFAULT_FORCED_SPLIT_MARKER)
                    
                    char_rules = data.get("char_duration_rules")
                    if char_rules and isinstance(char_rules, list):
                        self.char_duration_rules = char_rules
                    else:
                        self.char_duration_rules = [dict(r) for r in self.DEFAULT_CHAR_DURATION_RULES]
                        
                    dur_rules = data.get("duration_points_rules")
                    if dur_rules and isinstance(dur_rules, list):
                        self.duration_points_rules = dur_rules
                    else:
                        self.duration_points_rules = [dict(r) for r in self.DEFAULT_DURATION_POINTS_RULES]
            except Exception as e:
                print(f"Error loading config: {e}")

    def save(self):
        """Saves current configuration to .app_config.json."""
        data = {
            "base_path": self.base_path,
            "max_batch_points": self.max_batch_points,
            "forced_split_marker": self.forced_split_marker,
            "char_duration_rules": self.char_duration_rules,
            "duration_points_rules": self.duration_points_rules
        }
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def reset_to_defaults(self):
        self.max_batch_points = self.DEFAULT_MAX_BATCH_POINTS
        self.char_duration_rules = [dict(r) for r in self.DEFAULT_CHAR_DURATION_RULES]
        self.duration_points_rules = [dict(r) for r in self.DEFAULT_DURATION_POINTS_RULES]
        self.save()

    def get_duration_for_length(self, length):
        """Calculates duration in seconds for a given character length."""
        sorted_rules = sorted(self.char_duration_rules, key=lambda x: x["max_chars"])
        for r in sorted_rules:
            if length <= r["max_chars"]:
                return r["duration"]
        if sorted_rules:
            return sorted_rules[-1]["duration"]
        return 10

    def get_duration_label(self, length):
        """Calculates duration label (e.g. '4s', '6s', '超时 (>10s)') for a length."""
        sorted_rules = sorted(self.char_duration_rules, key=lambda x: x["max_chars"])
        for r in sorted_rules:
            if length <= r["max_chars"]:
                return f"{r['duration']}s"
        if sorted_rules:
            max_dur = sorted_rules[-1]["duration"]
            return f"超时 (>{max_dur}s)"
        return "10s"

    def get_max_chars(self):
        """Returns the maximum character threshold defined in char_duration_rules."""
        if self.char_duration_rules:
            return max(r["max_chars"] for r in self.char_duration_rules)
        return 180

    def get_points_for_duration(self, duration):
        """Calculates points cost for a given duration in seconds."""
        for r in self.duration_points_rules:
            if r["duration"] == duration:
                return r["points"]
        return 7
