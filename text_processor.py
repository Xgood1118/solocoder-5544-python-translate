import re
import jieba
try:
    from bs4 import BeautifulSoup, NavigableString, Tag
    _bs4_available = True
except ImportError:
    _bs4_available = False
import config


class TextProcessor:
    def __init__(self):
        self.sentence_endings = r'[。！？!?\.\n]+'
        self.chinese_sentence_endings = r'[。！？]+'
        self.western_sentence_endings = r'[.!?]+'

    def is_html(self, text):
        if not text:
            return False
        html_pattern = r'<\s*[a-zA-Z][^>]*>'
        return bool(re.search(html_pattern, text.strip()[:500]))

    def is_empty_or_numeric(self, text):
        if not text:
            return True
        stripped = text.strip()
        if not stripped:
            return True
        return bool(re.fullmatch(r'[\d\s\.\,\-\+\(\)\%]+', stripped))

    def split_sentences(self, text):
        if not text:
            return [], []
        sentences = []
        positions = []
        paragraphs = text.split('\n')
        current_pos = 0
        for para_idx, paragraph in enumerate(paragraphs):
            if para_idx > 0:
                current_pos += 1
            if not paragraph.strip():
                sentences.append('\n')
                positions.append((current_pos, current_pos + 1))
                current_pos += len(paragraph) + (1 if para_idx < len(paragraphs) - 1 else 0)
                continue
            para_sentences = self._split_single_paragraph(paragraph)
            para_start = current_pos
            for s in para_sentences:
                s_stripped = s
                sentences.append(s_stripped)
                positions.append((para_start, para_start + len(s_stripped)))
                para_start += len(s_stripped)
            current_pos += len(paragraph) + (1 if para_idx < len(paragraphs) - 1 else 0)
        return sentences, positions

    def _split_single_paragraph(self, text):
        if not text:
            return []
        sentences = []
        current = ''
        i = 0
        while i < len(text):
            char = text[i]
            current += char
            if char in '.!?。！？':
                closing_chars = "\"')]"
                if i + 1 < len(text) and text[i + 1] in closing_chars:
                    current += text[i + 1]
                    i += 1
                if char in '.!?':
                    if i + 1 < len(text) and text[i + 1].isupper():
                        sentences.append(current)
                        current = ''
                    elif i + 1 < len(text) and text[i + 1] == ' ' and i + 2 < len(text) and text[i + 2].isupper():
                        sentences.append(current)
                        current = ''
                    elif i == len(text) - 1:
                        sentences.append(current)
                        current = ''
                else:
                    sentences.append(current)
                    current = ''
            i += 1
        if current:
            sentences.append(current)
        if len(sentences) == 0:
            sentences = [text]
        return sentences

    def reconstruct_text(self, translated_sentences, original_sentences):
        if not translated_sentences:
            return ''
        result = []
        for orig, trans in zip(original_sentences, translated_sentences):
            if orig == '\n':
                result.append('\n')
            else:
                result.append(trans if trans else orig)
        return ''.join(result)

    def process_html(self, html_text, translate_func):
        if not _bs4_available:
            return translate_func(html_text)
        if not html_text:
            return html_text
        soup = BeautifulSoup(html_text, 'lxml')
        self._translate_soup(soup, translate_func)
        return str(soup)

    def _translate_soup(self, element, translate_func):
        if isinstance(element, NavigableString):
            text = str(element)
            if text.strip():
                translated = translate_func(text)
                element.replace_with(translated)
        elif isinstance(element, Tag):
            for child in list(element.children):
                self._translate_soup(child, translate_func)

    def translate_long_text(self, text, translate_single_func, source_lang, target_lang):
        if not text:
            return ''
        if self.is_empty_or_numeric(text):
            return text
        if self.is_html(text):
            def html_translate(t):
                return self._translate_plain_text(t, translate_single_func, source_lang, target_lang)
            return self.process_html(text, html_translate)
        return self._translate_plain_text(text, translate_single_func, source_lang, target_lang)

    def _translate_plain_text(self, text, translate_single_func, source_lang, target_lang):
        sentences, positions = self.split_sentences(text)
        if len(sentences) == 0:
            return text
        translated = []
        for s in sentences:
            if s == '\n':
                translated.append('\n')
            elif self.is_empty_or_numeric(s):
                translated.append(s)
            else:
                try:
                    t = translate_single_func(s, source_lang, target_lang)
                    translated.append(t if t else s)
                except Exception:
                    translated.append(s)
        return self.reconstruct_text(translated, sentences)

    def estimate_tokens(self, text):
        if not text:
            return 0
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        other_words = len(re.findall(r'[a-zA-Z0-9_]+', text))
        return chinese_chars + other_words * 2

    def needs_async(self, text):
        return self.estimate_tokens(text) > config.MAX_SYNC_TOKENS
