import json
import os
import uuid
import time
import threading
import queue
from datetime import datetime
import config


class TaskManager:
    def __init__(self, translation_service):
        self.lock = threading.RLock()
        self.tasks = {}
        self.translation_service = translation_service
        self.task_queue = queue.Queue()
        self._worker_threads = []
        self._start_workers(num_workers=3)
        self._load_persisted_tasks()

    def _start_workers(self, num_workers=3):
        for i in range(num_workers):
            t = threading.Thread(target=self._worker_loop, daemon=True, name=f'TaskWorker-{i}')
            t.start()
            self._worker_threads.append(t)

    def _worker_loop(self):
        while True:
            try:
                task_id = self.task_queue.get(timeout=1)
                self._execute_task(task_id)
                self.task_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f'Task worker error: {e}')

    def _task_file_path(self, task_id):
        return os.path.join(config.ASYNC_TASKS_DIR, f'{task_id}.json')

    def _load_persisted_tasks(self):
        if not os.path.exists(config.ASYNC_TASKS_DIR):
            return
        for fname in os.listdir(config.ASYNC_TASKS_DIR):
            if not fname.endswith('.json'):
                continue
            task_id = fname[:-5]
            fpath = self._task_file_path(task_id)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    task = json.load(f)
                    if task['status'] in ('pending', 'running'):
                        task['status'] = 'cancelled'
                        task['message'] = 'Service restarted'
                        with open(fpath, 'w', encoding='utf-8') as fw:
                            json.dump(task, fw, ensure_ascii=False, indent=2)
                    self.tasks[task_id] = task
            except Exception:
                pass

    def _save_task(self, task_id):
        task = self.tasks.get(task_id)
        if task:
            fpath = self._task_file_path(task_id)
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(task, f, ensure_ascii=False, indent=2)

    def create_task(self, task_type, params):
        with self.lock:
            task_id = str(uuid.uuid4())
            task = {
                'id': task_id,
                'type': task_type,
                'params': params,
                'status': 'pending',
                'progress': 0,
                'total': 0,
                'result': None,
                'error': None,
                'message': '',
                'created_at': datetime.now().timestamp(),
                'started_at': None,
                'completed_at': None,
            }
            self.tasks[task_id] = task
            self._save_task(task_id)
            self.task_queue.put(task_id)
            return task_id, task

    def _execute_task(self, task_id):
        with self.lock:
            task = self.tasks.get(task_id)
            if not task or task['status'] != 'pending':
                return
            task['status'] = 'running'
            task['started_at'] = datetime.now().timestamp()
            self._save_task(task_id)
        try:
            task_type = task['type']
            params = task['params']
            if task_type == 'translate':
                self._run_translate_task(task_id, params)
            elif task_type == 'batch_translate':
                self._run_batch_translate_task(task_id, params)
            else:
                raise ValueError(f'Unknown task type: {task_type}')
            with self.lock:
                task['status'] = 'completed'
                task['progress'] = task.get('total', 1)
                task['completed_at'] = datetime.now().timestamp()
                self._save_task(task_id)
        except Exception as e:
            with self.lock:
                task['status'] = 'failed'
                task['error'] = str(e)
                task['message'] = f'Task failed: {e}'
                task['completed_at'] = datetime.now().timestamp()
                self._save_task(task_id)

    def _update_progress(self, task_id, current, total, message=''):
        with self.lock:
            task = self.tasks.get(task_id)
            if task:
                task['progress'] = current
                task['total'] = total
                if message:
                    task['message'] = message
                self._save_task(task_id)

    def _run_translate_task(self, task_id, params):
        text = params.get('text', '')
        source_lang = params.get('source_lang', 'auto')
        target_lang = params.get('target_lang', 'en')
        use_term_base = params.get('use_term_base', True)
        use_memory = params.get('use_memory', True)
        sentences, _ = self.translation_service.text_processor.split_sentences(text)
        total = max(len([s for s in sentences if s.strip() and s != '\n']), 1)
        self._update_progress(task_id, 0, total, 'Starting translation...')
        result = self.translation_service.translate(
            text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            use_term_base=use_term_base,
            use_memory=use_memory,
            progress_callback=lambda cur, tot, msg: self._update_progress(task_id, cur, tot, msg)
        )
        with self.lock:
            task = self.tasks.get(task_id)
            if task:
                task['result'] = result
                self._save_task(task_id)

    def _run_batch_translate_task(self, task_id, params):
        items = params.get('items', [])
        source_lang = params.get('source_lang', 'auto')
        target_lang = params.get('target_lang', 'en')
        use_term_base = params.get('use_term_base', True)
        use_memory = params.get('use_memory', True)
        total = len(items)
        self._update_progress(task_id, 0, total, 'Starting batch translation...')
        results = []
        for idx, item in enumerate(items):
            try:
                text = item.get('text', '')
                result = self.translation_service.translate(
                    text=text,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    use_term_base=use_term_base,
                    use_memory=use_memory
                )
                results.append({
                    'id': item.get('id'),
                    'text': text,
                    'translation': result.get('translation'),
                    'detected_lang': result.get('detected_lang'),
                    'error': None
                })
            except Exception as e:
                results.append({
                    'id': item.get('id'),
                    'text': item.get('text', ''),
                    'translation': None,
                    'error': str(e)
                })
            self._update_progress(task_id, idx + 1, total, f'Processed {idx + 1}/{total}')
        with self.lock:
            task = self.tasks.get(task_id)
            if task:
                task['result'] = {'items': results}
                self._save_task(task_id)

    def get_task_status(self, task_id):
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return None
            task_copy = dict(task)
            return task_copy

    def cancel_task(self, task_id):
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return None
            if task['status'] in ('pending', 'running'):
                task['status'] = 'cancelled'
                task['message'] = 'Cancelled by user'
                task['completed_at'] = datetime.now().timestamp()
                self._save_task(task_id)
            return task

    def list_tasks(self, status=None, limit=50):
        with self.lock:
            tasks = list(self.tasks.values())
            if status:
                tasks = [t for t in tasks if t['status'] == status]
            tasks.sort(key=lambda t: t['created_at'], reverse=True)
            return tasks[:limit]

    def cleanup_old_tasks(self, max_age_seconds=86400 * 7):
        with self.lock:
            now = datetime.now().timestamp()
            to_remove = []
            for task_id, task in self.tasks.items():
                if task['status'] in ('completed', 'failed', 'cancelled'):
                    completed = task.get('completed_at') or task.get('created_at')
                    if now - completed > max_age_seconds:
                        to_remove.append(task_id)
            for task_id in to_remove:
                del self.tasks[task_id]
                fpath = self._task_file_path(task_id)
                if os.path.exists(fpath):
                    os.remove(fpath)
            return len(to_remove)
