import os
import threading
import time
import config


class TranslationEngine:
    def __init__(self):
        self.lock = threading.RLock()
        self.pipelines = {}
        self.model_cache_dir = config.MODEL_CACHE_DIR
        os.environ['TRANSFORMERS_CACHE'] = self.model_cache_dir
        os.environ['HF_HOME'] = self.model_cache_dir
        os.environ.setdefault('HF_HUB_DOWNLOAD_TIMEOUT', '15')
        os.environ.setdefault('HUGGINGFACE_HUB_CACHE', self.model_cache_dir)
        self._transformers_available = False
        self._torch_available = False
        self._loading_pipelines = {}
        self._check_dependencies()

    def _check_dependencies(self):
        try:
            import transformers
            self._transformers_available = True
        except ImportError:
            self._transformers_available = False
            print('Warning: transformers not installed. Translation will use mock mode.')
        try:
            import torch
            self._torch_available = True
        except ImportError:
            self._torch_available = False
            print('Warning: torch not installed. Translation will use mock mode.')

    def _get_model_name(self, source_lang, target_lang):
        if source_lang == target_lang:
            return None
        lang_pairs = [
            (source_lang, target_lang),
            (target_lang, source_lang),
        ]
        for s, t in lang_pairs:
            model_name = f'Helsinki-NLP/opus-mt-{s}-{t}'
            if self._model_exists(model_name):
                return model_name
        return f'Helsinki-NLP/opus-mt-{source_lang}-{target_lang}'

    def _model_exists(self, model_name):
        safe_name = model_name.replace('/', '--')
        model_path = os.path.join(self.model_cache_dir, f'models--{safe_name}')
        return os.path.exists(model_path)

    def _load_pipeline_with_timeout(self, model_name, timeout=60):
        result = {'pipe': None, 'error': None}

        def worker():
            try:
                from transformers import MarianMTModel, MarianTokenizer, pipeline
                import torch
                tokenizer = MarianTokenizer.from_pretrained(
                    model_name,
                    cache_dir=self.model_cache_dir,
                    local_files_only=self._model_exists(model_name)
                )
                model = MarianMTModel.from_pretrained(
                    model_name,
                    cache_dir=self.model_cache_dir,
                    local_files_only=self._model_exists(model_name)
                )
                device = 0 if torch.cuda.is_available() else -1
                pipe = pipeline(
                    'translation',
                    model=model,
                    tokenizer=tokenizer,
                    device=device
                )
                result['pipe'] = pipe
            except Exception as e:
                result['error'] = str(e)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        if thread.is_alive():
            print(f'Model loading timeout ({timeout}s) for {model_name}, using mock translation.')
            return None
        if result['error']:
            print(f'Failed to load model {model_name}: {result["error"]}')
            return None
        return result['pipe']

    def _load_pipeline(self, model_name):
        if not self._transformers_available or not self._torch_available:
            return None
        if not self._model_exists(model_name):
            print(f'Model {model_name} not cached. Will try to download (timeout 60s)...')
        pipe = self._load_pipeline_with_timeout(model_name, timeout=60)
        if pipe is not None:
            return pipe
        fallback_models = [
            'Helsinki-NLP/opus-mt-en-mul',
            'Helsinki-NLP/opus-mt-mul-en'
        ]
        for fb_model in fallback_models:
            if self._model_exists(fb_model):
                print(f'Trying fallback model: {fb_model}')
                fb_pipe = self._load_pipeline_with_timeout(fb_model, timeout=30)
                if fb_pipe is not None:
                    return fb_pipe
        return None

    def get_pipeline(self, source_lang, target_lang):
        with self.lock:
            if source_lang == target_lang:
                return None
            key = f'{source_lang}-{target_lang}'
            if key in self.pipelines:
                return self.pipelines[key]
            reverse_key = f'{target_lang}-{source_lang}'
            model_name = self._get_model_name(source_lang, target_lang)
            if not model_name:
                self.pipelines[key] = None
                return None
            print(f'Loading translation model: {model_name} ...')
            pipe = self._load_pipeline(model_name)
            self.pipelines[key] = pipe
            if pipe is None and reverse_key in self.pipelines:
                print(f'Note: Using reverse pipeline as fallback')
            return pipe

    def preload_common_pairs(self):
        print('Preloading common language pairs...')
        for src, tgt in config.PRELOAD_LANG_PAIRS:
            try:
                self.get_pipeline(src, tgt)
                print(f'  Preloaded: {src} -> {tgt}')
            except Exception as e:
                print(f'  Failed to preload {src} -> {tgt}: {e}')

    def translate_single(self, text, source_lang, target_lang, max_length=512):
        if source_lang == target_lang:
            return text
        pipe = self.get_pipeline(source_lang, target_lang)
        if pipe is None:
            return self._mock_translate(text, source_lang, target_lang)
        try:
            result = pipe(text, max_length=max_length, truncation=True)
            if result and len(result) > 0:
                return result[0]['translation_text']
            return text
        except Exception as e:
            print(f'Translation error: {e}')
            return self._mock_translate(text, source_lang, target_lang)

    def translate_batch(self, texts, source_lang, target_lang, max_length=512, batch_size=8):
        if source_lang == target_lang:
            return list(texts)
        pipe = self.get_pipeline(source_lang, target_lang)
        if pipe is None:
            return [self._mock_translate(t, source_lang, target_lang) for t in texts]
        results = []
        try:
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batch_results = pipe(batch, max_length=max_length, truncation=True)
                for r in batch_results:
                    results.append(r['translation_text'] if r else '')
            return results
        except Exception as e:
            print(f'Batch translation error: {e}')
            return [self._mock_translate(t, source_lang, target_lang) for t in texts]

    def _mock_translate(self, text, source_lang, target_lang):
        if not text:
            return text
        return f'[{source_lang}->{target_lang}]{text}'

    def is_available(self):
        return self._transformers_available and self._torch_available
