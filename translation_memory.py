import json
import os
import re
import time
import threading
from difflib import SequenceMatcher
from datetime import datetime, timedelta
import config


class TranslationMemory:
    def __init__(self):
        self.lock = threading.RLock()
        self.entries = []
        self._load()

    def _load(self):
        if os.path.exists(config.TRANSLATION_MEMORY_FILE):
            with open(config.TRANSLATION_MEMORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.entries = data.get('entries', [])
        else:
            self.entries = []
            self._save()
        self._clean_expired()

    def _save(self):
        with open(config.TRANSLATION_MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump({'entries': self.entries}, f, ensure_ascii=False, indent=2)

    def _normalize(self, text):
        text = text.lower()
        text = re.sub(r'\s+', '', text)
        text = re.sub(r'[^\w\s]', '', text)
        return text

    def _clean_expired(self):
        now = datetime.now().timestamp()
        new_entries = []
        changed = False
        for entry in self.entries:
            if entry.get('preferred') and entry.get('expires_at'):
                if now > entry['expires_at']:
                    entry['preferred'] = False
                    entry.pop('expires_at', None)
                    changed = True
            new_entries.append(entry)
        if changed:
            self.entries = new_entries
            self._save()

    def add_entry(self, source, target, source_lang, target_lang, preferred=False, metadata=None):
        with self.lock:
            norm_source = self._normalize(source)
            for entry in self.entries:
                if (entry['norm_source'] == norm_source and
                    entry['source_lang'] == source_lang and
                    entry['target_lang'] == target_lang):
                    entry['target'] = target
                    entry['source'] = source
                    entry['updated_at'] = datetime.now().timestamp()
                    if preferred:
                        entry['preferred'] = True
                        entry['expires_at'] = (datetime.now() + timedelta(days=config.PREFERRED_TTL_DAYS)).timestamp()
                    if metadata:
                        entry['metadata'] = metadata
                    self._save()
                    return entry
            new_entry = {
                'id': len(self.entries) + 1,
                'source': source,
                'target': target,
                'norm_source': norm_source,
                'source_lang': source_lang,
                'target_lang': target_lang,
                'preferred': preferred,
                'created_at': datetime.now().timestamp(),
                'updated_at': datetime.now().timestamp(),
                'metadata': metadata or {}
            }
            if preferred:
                new_entry['expires_at'] = (datetime.now() + timedelta(days=config.PREFERRED_TTL_DAYS)).timestamp()
            self.entries.append(new_entry)
            self._save()
            return new_entry

    def mark_preferred(self, entry_id):
        with self.lock:
            for entry in self.entries:
                if entry['id'] == entry_id:
                    entry['preferred'] = True
                    entry['expires_at'] = (datetime.now() + timedelta(days=config.PREFERRED_TTL_DAYS)).timestamp()
                    entry['updated_at'] = datetime.now().timestamp()
                    self._save()
                    return entry
            return None

    def lookup(self, text, source_lang, target_lang):
        with self.lock:
            self._clean_expired()
            norm_text = self._normalize(text)
            for entry in self.entries:
                if (entry['norm_source'] == norm_text and
                    entry['source_lang'] == source_lang and
                    entry['target_lang'] == target_lang):
                    if entry.get('preferred'):
                        return {
                            'hit': True,
                            'type': 'preferred',
                            'entry': entry
                        }
            for entry in self.entries:
                if (entry['norm_source'] == norm_text and
                    entry['source_lang'] == source_lang and
                    entry['target_lang'] == target_lang):
                    return {
                        'hit': True,
                        'type': 'exact',
                        'entry': entry
                    }
            return {'hit': False}

    def find_similar(self, text, source_lang, target_lang, threshold=None):
        with self.lock:
            if threshold is None:
                threshold = config.PARTIAL_MATCH_THRESHOLD
            self._clean_expired()
            norm_text = self._normalize(text)
            results = []
            for entry in self.entries:
                if entry['source_lang'] != source_lang or entry['target_lang'] != target_lang:
                    continue
                ratio = SequenceMatcher(None, norm_text, entry['norm_source']).ratio()
                if ratio >= threshold:
                    results.append({
                        'similarity': ratio,
                        'entry': entry
                    })
            results.sort(key=lambda x: x['similarity'], reverse=True)
            return results

    def list_entries(self, source_lang=None, target_lang=None, preferred_only=False):
        with self.lock:
            self._clean_expired()
            results = self.entries
            if source_lang:
                results = [e for e in results if e['source_lang'] == source_lang]
            if target_lang:
                results = [e for e in results if e['target_lang'] == target_lang]
            if preferred_only:
                results = [e for e in results if e.get('preferred')]
            return list(results)
