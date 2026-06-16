import os
import re
import threading
import config


class LanguageDetector:
    def __init__(self):
        self.lock = threading.Lock()
        self.model = None
        self._init_model()

    def _init_model(self):
        try:
            import fasttext
            if os.path.exists(config.FASTTEXT_MODEL_PATH):
                self.model = fasttext.load_model(config.FASTTEXT_MODEL_PATH)
                return
            model_url = 'https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin'
            model_dir = os.path.dirname(config.FASTTEXT_MODEL_PATH)
            os.makedirs(model_dir, exist_ok=True)
            try:
                import urllib.request
                print(f'Downloading fastText language detection model from {model_url}...')
                urllib.request.urlretrieve(model_url, config.FASTTEXT_MODEL_PATH)
                self.model = fasttext.load_model(config.FASTTEXT_MODEL_PATH)
                print('fastText model loaded successfully.')
            except Exception as e:
                print(f'Failed to download fastText model: {e}. Will use heuristic detection.')
                self.model = None
        except ImportError:
            print('fastText not installed. Will use heuristic detection.')
            self.model = None
        except Exception as e:
            print(f'Error loading fastText: {e}. Will use heuristic detection.')
            self.model = None

    def _heuristic_detect(self, text):
        if not text or not text.strip():
            return 'en', 0.5
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        japanese_chars = len(re.findall(r'[\u3040-\u30ff\u31f0-\u31ff]', text))
        korean_chars = len(re.findall(r'[\uac00-\ud7af]', text))
        cyrillic_chars = len(re.findall(r'[\u0400-\u04ff]', text))
        arabic_chars = len(re.findall(r'[\u0600-\u06ff]', text))
        thai_chars = len(re.findall(r'[\u0e00-\u0e7f]', text))
        devanagari_chars = len(re.findall(r'[\u0900-\u097f]', text))
        greek_chars = len(re.findall(r'[\u0370-\u03ff]', text))
        hebrew_chars = len(re.findall(r'[\u0590-\u05ff]', text))
        alphabetic_chars = len(re.findall(r'[a-zA-Z]', text))
        total_chars = max(1, len(re.sub(r'\s+', '', text.strip())))
        ideographic_score = max(
            chinese_chars / total_chars * 1.5,
            japanese_chars / total_chars * 1.5,
            korean_chars / total_chars * 1.5
        )
        if chinese_chars > 0:
            score = chinese_chars / total_chars
            if score >= 0.05:
                return 'zh', min(score * 1.3, 0.98)
        if japanese_chars > 0:
            score = japanese_chars / total_chars
            if score >= 0.05:
                return 'ja', min(score * 1.3, 0.98)
        if korean_chars > 0:
            score = korean_chars / total_chars
            if score >= 0.05:
                return 'ko', min(score * 1.3, 0.98)
        scores = {
            'zh': chinese_chars / total_chars,
            'ja': japanese_chars / total_chars,
            'ko': korean_chars / total_chars,
            'ru': cyrillic_chars / total_chars,
            'ar': arabic_chars / total_chars,
            'th': thai_chars / total_chars,
            'hi': devanagari_chars / total_chars,
            'el': greek_chars / total_chars,
            'he': hebrew_chars / total_chars,
        }
        if cyrillic_chars > alphabetic_chars and cyrillic_chars > 0:
            return 'ru', min(cyrillic_chars / total_chars * 1.5, 0.95)
        if arabic_chars > 0:
            return 'ar', min(arabic_chars / total_chars * 1.5, 0.95)
        if thai_chars > 0:
            return 'th', min(thai_chars / total_chars * 1.5, 0.95)
        if devanagari_chars > 0:
            return 'hi', min(devanagari_chars / total_chars * 1.5, 0.95)
        latin_words = len(re.findall(r'[a-zA-Z]{2,}', text))
        scores['en'] = min(alphabetic_chars / max(1, total_chars), 1.0)
        if ideographic_score < 0.05 and alphabetic_chars > 0:
            return 'en', min(alphabetic_chars / max(1, total_chars), 0.9)
        best_lang = max(scores, key=scores.get)
        best_score = scores[best_lang]
        if best_score < 0.1:
            return 'en', 0.3
        return best_lang, min(best_score, 0.95)

    def detect(self, text):
        with self.lock:
            if not text or not text.strip():
                return 'en', 0.5
            text_sample = text.strip()[:1000]
            if self.model:
                try:
                    predictions = self.model.predict(text_sample, k=3)
                    if predictions and len(predictions[0]) > 0:
                        lang = predictions[0][0].replace('__label__', '')
                        conf = float(predictions[1][0])
                        if lang in config.SUPPORTED_LANGUAGES:
                            return lang, conf
                        lang_map = {
                            'zh-cn': 'zh',
                            'zh-tw': 'zh',
                            'cmn': 'zh',
                            'spa': 'es',
                            'fra': 'fr',
                            'deu': 'de',
                            'jpn': 'ja',
                            'kor': 'ko',
                            'rus': 'ru',
                            'por': 'pt',
                            'ita': 'it',
                            'nld': 'nl',
                            'arb': 'ar',
                            'hin': 'hi',
                            'tha': 'th',
                            'vie': 'vi',
                            'ind': 'id',
                            'zsm': 'ms',
                            'tur': 'tr',
                            'pol': 'pl',
                            'swe': 'sv',
                            'dan': 'da',
                            'fin': 'fi',
                            'nob': 'no',
                            'ces': 'cs',
                            'ell': 'el',
                            'heb': 'he',
                        }
                        mapped = lang_map.get(lang, lang)
                        if mapped in config.SUPPORTED_LANGUAGES:
                            return mapped, conf
                except Exception:
                    pass
            return self._heuristic_detect(text_sample)

    def detect_language(self, text):
        lang, conf = self.detect(text)
        return lang
