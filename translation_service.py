import threading
import config
from term_base import TermBase
from translation_memory import TranslationMemory
from language_detector import LanguageDetector
from translation_engine import TranslationEngine
from text_processor import TextProcessor


class TranslationService:
    def __init__(self):
        self.lock = threading.RLock()
        self.term_base = TermBase()
        self.translation_memory = TranslationMemory()
        self.language_detector = LanguageDetector()
        self.translation_engine = TranslationEngine()
        self.text_processor = TextProcessor()

    def preload(self):
        print('Preloading common translation models...')
        self.translation_engine.preload_common_pairs()
        print('Preloading complete.')

    def _resolve_languages(self, text, source_lang, target_lang):
        detected = None
        if source_lang == 'auto' or not source_lang:
            detected, conf = self.language_detector.detect(text)
            source_lang = detected
        if source_lang == target_lang:
            return source_lang, target_lang, detected
        return source_lang, target_lang, detected

    def translate(self, text, source_lang='auto', target_lang='en',
                  use_term_base=True, use_memory=True,
                  save_to_memory=True, mark_preferred=False,
                  progress_callback=None):
        with self.lock:
            if text is None:
                return {
                    'translation': '',
                    'source_lang': source_lang,
                    'target_lang': target_lang,
                    'detected_lang': None,
                    'terms_applied': [],
                    'memory_hit': None,
                    'partial_matches': []
                }
            if self.text_processor.is_empty_or_numeric(text):
                source_lang_final, target_lang_final, detected = self._resolve_languages(text, source_lang, target_lang)
                return {
                    'translation': text,
                    'source_lang': source_lang_final,
                    'target_lang': target_lang_final,
                    'detected_lang': detected,
                    'terms_applied': [],
                    'memory_hit': None,
                    'partial_matches': []
                }
            source_lang_final, target_lang_final, detected = self._resolve_languages(text, source_lang, target_lang)
            if source_lang_final == target_lang_final:
                return {
                    'translation': text,
                    'source_lang': source_lang_final,
                    'target_lang': target_lang_final,
                    'detected_lang': detected,
                    'terms_applied': [],
                    'memory_hit': None,
                    'partial_matches': []
                }
            terms_applied = []
            if use_term_base:
                text_processed, terms_applied = self.term_base.apply_terms(text, source_lang_final)
            else:
                text_processed = text
            memory_hit = None
            partial_matches = []
            if use_memory:
                mem_result = self.translation_memory.lookup(text, source_lang_final, target_lang_final)
                if mem_result['hit']:
                    if mem_result['type'] == 'preferred':
                        return {
                            'translation': mem_result['entry']['target'],
                            'source_lang': source_lang_final,
                            'target_lang': target_lang_final,
                            'detected_lang': detected,
                            'terms_applied': terms_applied,
                            'memory_hit': mem_result,
                            'partial_matches': []
                        }
                    memory_hit = mem_result
                else:
                    partial_matches = self.translation_memory.find_similar(
                        text, source_lang_final, target_lang_final
                    )
            translated = self.text_processor.translate_long_text(
                text_processed,
                self.translation_engine.translate_single,
                source_lang_final,
                target_lang_final
            )
            if save_to_memory:
                clean_translation = self.text_processor.strip_term_tags(translated)
                self.translation_memory.add_entry(
                    source=text,
                    target=clean_translation,
                    source_lang=source_lang_final,
                    target_lang=target_lang_final,
                    preferred=mark_preferred
                )
            return {
                'translation': translated,
                'source_lang': source_lang_final,
                'target_lang': target_lang_final,
                'detected_lang': detected,
                'terms_applied': terms_applied,
                'memory_hit': memory_hit,
                'partial_matches': partial_matches
            }

    def translate_batch(self, items, source_lang='auto', target_lang='en',
                        use_term_base=True, use_memory=True,
                        save_to_memory=True, mark_preferred=False):
        results = []
        for item in items:
            text = item.get('text', '')
            item_id = item.get('id')
            try:
                result = self.translate(
                    text=text,
                    source_lang=source_lang if item.get('source_lang') is None else item.get('source_lang'),
                    target_lang=target_lang if item.get('target_lang') is None else item.get('target_lang'),
                    use_term_base=use_term_base,
                    use_memory=use_memory,
                    save_to_memory=save_to_memory,
                    mark_preferred=mark_preferred
                )
                results.append({
                    'id': item_id,
                    'success': True,
                    **result
                })
            except Exception as e:
                results.append({
                    'id': item_id,
                    'success': False,
                    'error': str(e),
                    'text': text
                })
        return results

    def detect_language(self, text):
        lang, conf = self.language_detector.detect(text)
        return {
            'language': lang,
            'confidence': conf,
            'supported': lang in config.SUPPORTED_LANGUAGES
        }

    def get_status(self):
        return {
            'model_available': self.translation_engine.is_available(),
            'loaded_models': list(self.translation_engine.pipelines.keys()),
            'term_count': len(self.term_base.terms),
            'memory_count': len(self.translation_memory.entries),
            'supported_languages': config.SUPPORTED_LANGUAGES
        }
