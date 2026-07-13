# -*- coding: utf-8 -*-
import re

class TextProcessor:
    """Handles text cleaning and smart segmentation for Spanish content."""
    
    @staticmethod
    def clean_text(text):
        """Cleans input text according to user rules:
        - Removes all emojis and symbols (like '👉', '📖', '✨')
        - Removes double quotes (", “, ”)
        - Converts emoji numbers (e.g. 3️⃣) to normal numbers
        """
        if not text:
            return ""
            
        # 1. Replace emoji numbers (like 3️⃣) with normal numbers
        # Match digit followed by optional variation selector U+FE0F and enclosing keycap U+20E3
        text = re.sub(r'(\d)\uFE0F?\u20E3', r'\1', text)
        
        # 2. Remove all other emojis and icons:
        # - Characters with code point > 0xFFFF (covers almost all modern emojis like 👉, 📖)
        # - Characters in the Miscellaneous Symbols block (0x2600-0x26FF) and Dingbats (0x2700-0x27BF)
        cleaned_chars = []
        for c in text:
            code = ord(c)
            if 0x2600 <= code <= 0x27BF or code > 0xFFFF:
                continue
            cleaned_chars.append(c)
        text = "".join(cleaned_chars)
        
        # 3. Remove quotes (double quotes, smart quotes)
        text = text.replace('"', '').replace('“', '').replace('”', '')
        
        # 4. Clean up spacing
        text = re.sub(r' +', ' ', text)
        
        return text.strip()

    @staticmethod
    def _split_long_chunk(chunk, max_len=180):
        """Splits a single chunk that is longer than max_len into sub-chunks.
        Tries to split by comma first, then by space (words).
        """
        if len(chunk) <= max_len:
            return [chunk]
            
        parts = chunk.split(', ')
        sub_chunks = []
        current = ""
        
        for i, p in enumerate(parts):
            # Append comma back if it's not the last element
            item = p + "," if i < len(parts) - 1 else p
            test = (current + " " + item).strip() if current else item
            
            if len(test) <= max_len:
                current = test
            else:
                if current:
                    sub_chunks.append(current)
                
                # If a single item is still > max_len, split by space (words)
                if len(item) > max_len:
                    words = item.split(' ')
                    word_current = ""
                    for w in words:
                        if not w:
                            continue
                        test_w = (word_current + " " + w).strip() if word_current else w
                        if len(test_w) <= max_len:
                            word_current = test_w
                        else:
                            if word_current:
                                sub_chunks.append(word_current)
                            word_current = w
                    current = word_current
                else:
                    current = item
                    
        if current:
            sub_chunks.append(current)
            
        return sub_chunks

    @staticmethod
    def segment_spanish_text(text):
        """Segments cleaned Spanish text prioritizing 10s (141-180 characters) chunks.
        Rules:
        - Must cut at line breaks or punctuation (., ?, !, ;, :)
        - Hard limit: No segment can exceed 180 characters (10s max duration).
        - L <= 100 -> 6s
        - 101 <= L <= 140 -> 8s
        - 141 <= L <= 180 -> 10s
        """
        cleaned = TextProcessor.clean_text(text)
        if not cleaned:
            return []
            
        initial_chunks = []
        # Split by newline or sentence-ending punctuation (., ?, !, ;, :) but keep the punctuation.
        pattern = re.compile(r'([^.!?;\n\r]+[.!?;\n\r]*)')
        matches = pattern.findall(cleaned)
        
        for m in matches:
            trimmed = m.strip()
            if trimmed:
                initial_chunks.append(trimmed)

        # Stage 1: Enforce hard limit on raw chunks by pre-splitting anything > 180 characters
        raw_chunks = []
        for chunk in initial_chunks:
            if len(chunk) > 180:
                raw_chunks.extend(TextProcessor._split_long_chunk(chunk, max_len=180))
            else:
                raw_chunks.append(chunk)

        # Stage 2: Greedy Merging up to 180 characters
        segments = []
        current_segment = ""
        
        for chunk in raw_chunks:
            test_segment = (current_segment + " " + chunk).strip() if current_segment else chunk
            if len(test_segment) <= 180:
                current_segment = test_segment
            else:
                if current_segment:
                    segments.append(current_segment)
                current_segment = chunk

        if current_segment:
            segments.append(current_segment)
            
        # Assign durations (guaranteed to be <= 10s because all lengths are <= 180)
        results = []
        for seg in segments:
            length = len(seg)
            if length <= 50:
                duration_val = 4
            elif length <= 100:
                duration_val = 6
            elif length <= 140:
                duration_val = 8
            else:
                duration_val = 10
                
            results.append({
                "text": seg,
                "length": length,
                "duration": duration_val
            })
            
        return results
