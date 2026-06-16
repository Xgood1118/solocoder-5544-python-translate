import json
import os
import re
import threading
import jieba
from difflib import SequenceMatcher
import config


class TermBase:
    def __init__(self):
        self.lock = threading.RLock()
        self.terms = []
        self._load()

    def _load(self):
        if os.path.exists(config.TERM_BASE_FILE):
            with open(config.TERM_BASE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.terms = data.get('terms', [])
        else:
            self.terms = []
            self._save()

    def _save(self):
        with open(config.TERM_BASE_FILE, 'w', encoding='utf-8') as f:
            json.dump({'terms': self.terms}, f, ensure_ascii=False, indent=2)

    def add_term(self, source, target, source_lang='auto', target_lang='auto', category='general'):
        with self.lock:
            for term in self.terms:
                if term['source'].lower() == source.lower() and term['source_lang'] == source_lang:
                    term['target'] = target
                    term['target_lang'] = target_lang
                    term['category'] = category
                    self._save()
                    return term
            new_term = {
                'id': len(self.terms) + 1,
                'source': source,
                'target': target,
                'source_lang': source_lang,
                'target_lang': target_lang,
                'category': category
            }
            self.terms.append(new_term)
            self._save()
            return new_term

    def remove_term(self, term_id):
        with self.lock:
            self.terms = [t for t in self.terms if t['id'] != term_id]
            self._save()

    def list_terms(self, category=None):
        with self.lock:
            if category:
                return [t for t in self.terms if t['category'] == category]
            return list(self.terms)

    def _edit_distance(self, s1, s2):
        if len(s1) < len(s2):
            return self._edit_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    def _find_matches(self, text, lang=None):
        matches = []
        text_lower = text.lower()
        for term in self.terms:
            if lang and term['source_lang'] != 'auto' and term['source_lang'] != lang:
                continue
            source_lower = term['source'].lower()
            exact_positions = []
            start = 0
            while True:
                pos = text_lower.find(source_lower, start)
                if pos == -1:
                    break
                exact_positions.append(pos)
                start = pos + 1
            for pos in exact_positions:
                matches.append({
                    'term': term,
                    'start': pos,
                    'end': pos + len(term['source']),
                    'original': text[pos:pos + len(term['source'])],
                    'match_type': 'exact'
                })
            if len(source_lower) >= 4:
                tokens = list(jieba.cut(text)) if self._is_chinese(text) else text.split()
                for i, token in enumerate(tokens):
                    token_lower = token.lower()
                    if abs(len(token_lower) - len(source_lower)) <= config.FUZZY_MATCH_THRESHOLD:
                        dist = self._edit_distance(token_lower, source_lower)
                        if 0 < dist <= config.FUZZY_MATCH_THRESHOLD:
                            current_pos = sum(len(t) for t in tokens[:i])
                            matches.append({
                                'term': term,
                                'start': current_pos,
                                'end': current_pos + len(token),
                                'original': token,
                                'match_type': 'fuzzy',
                                'edit_distance': dist
                            })
        return matches

    def _is_chinese(self, text):
        return bool(re.search(r'[\u4e00-\u9fff]', text))

    def apply_terms(self, text, source_lang=None):
        with self.lock:
            if not text or not self.terms:
                return text, []
            matches = self._find_matches(text, source_lang)
            if not matches:
                return text, []
            matches.sort(key=lambda m: (m['end'] - m['start']), reverse=True)
            used_ranges = []
            valid_matches = []
            for match in matches:
                overlap = False
                for used in used_ranges:
                    if not (match['end'] <= used['start'] or match['start'] >= used['end']):
                        overlap = True
                        break
                if not overlap:
                    used_ranges.append({'start': match['start'], 'end': match['end']})
                    valid_matches.append(match)
            valid_matches.sort(key=lambda m: m['start'])
            result_parts = []
            last_end = 0
            applied_terms = []
            for match in valid_matches:
                if match['start'] > last_end:
                    result_parts.append(text[last_end:match['start']])
                wrapped = f"<term>{match['term']['target']}</term>"
                result_parts.append(wrapped)
                applied_terms.append({
                    'original': match['original'],
                    'replacement': match['term']['target'],
                    'category': match['term'].get('category', 'general'),
                    'match_type': match['match_type']
                })
                last_end = match['end']
            if last_end < len(text):
                result_parts.append(text[last_end:])
            return ''.join(result_parts), applied_terms
