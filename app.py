import os
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS
import config
from translation_service import TranslationService
from task_manager import TaskManager


app = Flask(__name__)
CORS(app)

translation_service = TranslationService()
task_manager = TaskManager(translation_service)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'service': 'local-translation-service',
        'version': '1.0.0'
    })


@app.route('/api/status', methods=['GET'])
def get_status():
    status = translation_service.get_status()
    return jsonify(status)


@app.route('/api/languages', methods=['GET'])
def list_languages():
    return jsonify({
        'languages': config.SUPPORTED_LANGUAGES,
        'count': len(config.SUPPORTED_LANGUAGES)
    })


@app.route('/api/detect', methods=['POST'])
def detect_language():
    data = request.get_json(force=True, silent=True) or {}
    text = data.get('text', '')
    if not text:
        return jsonify({'error': 'text is required'}), 400
    result = translation_service.detect_language(text)
    return jsonify(result)


@app.route('/api/translate', methods=['POST'])
def translate():
    data = request.get_json(force=True, silent=True) or {}
    text = data.get('text', '')
    source_lang = data.get('source_lang', 'auto')
    target_lang = data.get('target_lang', 'en')
    use_term_base = data.get('use_term_base', True)
    use_memory = data.get('use_memory', True)
    save_to_memory = data.get('save_to_memory', True)
    mark_preferred = data.get('mark_preferred', False)
    if text is None:
        return jsonify({'error': 'text is required'}), 400
    needs_async = translation_service.text_processor.needs_async(text)
    if needs_async:
        task_id, task = task_manager.create_task('translate', {
            'text': text,
            'source_lang': source_lang,
            'target_lang': target_lang,
            'use_term_base': use_term_base,
            'use_memory': use_memory,
            'save_to_memory': save_to_memory,
            'mark_preferred': mark_preferred
        })
        return jsonify({
            'async': True,
            'task_id': task_id,
            'message': 'Text too long, use async task API',
            'task_status': f'/api/tasks/{task_id}'
        }), 202
    result = translation_service.translate(
        text=text,
        source_lang=source_lang,
        target_lang=target_lang,
        use_term_base=use_term_base,
        use_memory=use_memory,
        save_to_memory=save_to_memory,
        mark_preferred=mark_preferred
    )
    return jsonify(result)


@app.route('/api/translate/batch', methods=['POST'])
def translate_batch():
    data = request.get_json(force=True, silent=True) or {}
    items = data.get('items', [])
    source_lang = data.get('source_lang', 'auto')
    target_lang = data.get('target_lang', 'en')
    use_term_base = data.get('use_term_base', True)
    use_memory = data.get('use_memory', True)
    save_to_memory = data.get('save_to_memory', True)
    mark_preferred = data.get('mark_preferred', False)
    if not items or len(items) == 0:
        return jsonify({'error': 'items is required and must be non-empty'}), 400
    total_tokens = sum(translation_service.text_processor.estimate_tokens(item.get('text', '')) for item in items)
    if total_tokens > config.MAX_SYNC_TOKENS * 3 or len(items) > 20:
        task_id, task = task_manager.create_task('batch_translate', {
            'items': items,
            'source_lang': source_lang,
            'target_lang': target_lang,
            'use_term_base': use_term_base,
            'use_memory': use_memory,
            'save_to_memory': save_to_memory,
            'mark_preferred': mark_preferred
        })
        return jsonify({
            'async': True,
            'task_id': task_id,
            'message': 'Batch too large, use async task API',
            'task_status': f'/api/tasks/{task_id}'
        }), 202
    results = translation_service.translate_batch(
        items=items,
        source_lang=source_lang,
        target_lang=target_lang,
        use_term_base=use_term_base,
        use_memory=use_memory,
        save_to_memory=save_to_memory,
        mark_preferred=mark_preferred
    )
    return jsonify({'results': results})


@app.route('/api/tasks', methods=['GET'])
def list_tasks():
    status = request.args.get('status')
    limit = int(request.args.get('limit', 50))
    tasks = task_manager.list_tasks(status=status, limit=limit)
    return jsonify({'tasks': tasks, 'count': len(tasks)})


@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    task = task_manager.get_task_status(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify(task)


@app.route('/api/tasks/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    task = task_manager.cancel_task(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify({'message': 'Task cancelled', 'task': task})


@app.route('/api/terms', methods=['GET'])
def list_terms():
    category = request.args.get('category')
    terms = translation_service.term_base.list_terms(category=category)
    return jsonify({'terms': terms, 'count': len(terms)})


@app.route('/api/terms', methods=['POST'])
def add_term():
    data = request.get_json(force=True, silent=True) or {}
    source = data.get('source')
    target = data.get('target')
    source_lang = data.get('source_lang', 'auto')
    target_lang = data.get('target_lang', 'auto')
    category = data.get('category', 'general')
    if not source or not target:
        return jsonify({'error': 'source and target are required'}), 400
    term = translation_service.term_base.add_term(
        source=source,
        target=target,
        source_lang=source_lang,
        target_lang=target_lang,
        category=category
    )
    return jsonify({'term': term}), 201


@app.route('/api/terms/<int:term_id>', methods=['DELETE'])
def remove_term(term_id):
    translation_service.term_base.remove_term(term_id)
    return jsonify({'message': 'Term removed'})


@app.route('/api/memory', methods=['GET'])
def list_memory():
    source_lang = request.args.get('source_lang')
    target_lang = request.args.get('target_lang')
    preferred_only = request.args.get('preferred_only', 'false').lower() == 'true'
    entries = translation_service.translation_memory.list_entries(
        source_lang=source_lang,
        target_lang=target_lang,
        preferred_only=preferred_only
    )
    return jsonify({'entries': entries, 'count': len(entries)})


@app.route('/api/memory', methods=['POST'])
def add_memory_entry():
    data = request.get_json(force=True, silent=True) or {}
    source = data.get('source')
    target = data.get('target')
    source_lang = data.get('source_lang')
    target_lang = data.get('target_lang')
    preferred = data.get('preferred', False)
    metadata = data.get('metadata')
    if not source or not target or not source_lang or not target_lang:
        return jsonify({'error': 'source, target, source_lang, target_lang are required'}), 400
    entry = translation_service.translation_memory.add_entry(
        source=source,
        target=target,
        source_lang=source_lang,
        target_lang=target_lang,
        preferred=preferred,
        metadata=metadata
    )
    return jsonify({'entry': entry}), 201


@app.route('/api/memory/<int:entry_id>/prefer', methods=['POST'])
def mark_preferred(entry_id):
    entry = translation_service.translation_memory.mark_preferred(entry_id)
    if not entry:
        return jsonify({'error': 'Entry not found'}), 404
    return jsonify({'entry': entry})


@app.route('/api/memory/search', methods=['POST'])
def search_memory():
    data = request.get_json(force=True, silent=True) or {}
    text = data.get('text', '')
    source_lang = data.get('source_lang')
    target_lang = data.get('target_lang')
    threshold = data.get('threshold')
    if not text or not source_lang or not target_lang:
        return jsonify({'error': 'text, source_lang, target_lang are required'}), 400
    exact = translation_service.translation_memory.lookup(text, source_lang, target_lang)
    similar = translation_service.translation_memory.find_similar(
        text, source_lang, target_lang, threshold=threshold
    )
    return jsonify({
        'exact_match': exact,
        'similar_matches': similar
    })


@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


def start_preload():
    def preload_thread():
        try:
            translation_service.preload()
        except Exception as e:
            print(f'Preload error (non-fatal): {e}')
    t = threading.Thread(target=preload_thread, daemon=True)
    t.start()


if __name__ == '__main__':
    print(f'Starting Local Translation Service on port {config.PORT}...')
    print(f'Data directory: {config.DATA_DIR}')
    print(f'Supported languages: {len(config.SUPPORTED_LANGUAGES)}')
    start_preload()
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG, threaded=True)
