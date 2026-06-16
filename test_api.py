"""
Local Translation Service - API Usage Examples
Run this after starting the server to test all endpoints.
"""
import requests
import json
import time

BASE_URL = 'http://localhost:8330'


def print_response(label, resp):
    print(f'\n=== {label} ===')
    print(f'Status: {resp.status_code}')
    try:
        data = resp.json()
        print(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception:
        print(resp.text)
    return resp


def test_health():
    resp = requests.get(f'{BASE_URL}/health')
    return print_response('Health Check', resp)


def test_status():
    resp = requests.get(f'{BASE_URL}/api/status')
    return print_response('Service Status', resp)


def test_languages():
    resp = requests.get(f'{BASE_URL}/api/languages')
    return print_response('Supported Languages', resp)


def test_detect():
    payload = {'text': 'Hello world, this is a test message.'}
    resp = requests.post(f'{BASE_URL}/api/detect', json=payload)
    print_response('Detect English', resp)

    payload = {'text': '你好世界，这是一条测试消息。'}
    resp = requests.post(f'{BASE_URL}/api/detect', json=payload)
    print_response('Detect Chinese', resp)


def test_translate_single():
    payload = {
        'text': 'Thank you for your purchase.',
        'source_lang': 'en',
        'target_lang': 'zh'
    }
    resp = requests.post(f'{BASE_URL}/api/translate', json=payload)
    return print_response('Translate Single (en->zh)', resp)


def test_translate_auto_detect():
    payload = {
        'text': '跨境电商是未来的发展趋势。',
        'source_lang': 'auto',
        'target_lang': 'en'
    }
    resp = requests.post(f'{BASE_URL}/api/translate', json=payload)
    return print_response('Translate with Auto Detect (zh->en)', resp)


def test_translate_with_terms():
    payload = {
        'text': 'This AirPods Pro with Bluetooth 5.3 and USB-C port is amazing.',
        'source_lang': 'en',
        'target_lang': 'zh',
        'use_term_base': True
    }
    resp = requests.post(f'{BASE_URL}/api/translate', json=payload)
    return print_response('Translate with Term Base', resp)


def test_translate_batch():
    payload = {
        'items': [
            {'id': 1, 'text': 'Hello world.'},
            {'id': 2, 'text': 'Good morning.'},
            {'id': 3, 'text': '12345'},
            {'id': 4, 'text': ''}
        ],
        'source_lang': 'en',
        'target_lang': 'zh'
    }
    resp = requests.post(f'{BASE_URL}/api/translate/batch', json=payload)
    return print_response('Batch Translate', resp)


def test_html_translate():
    html = '''
    <div class="product">
        <h1>Product Description</h1>
        <p>This is a <strong>great</strong> product with Bluetooth 5.3.</p>
        <ul>
            <li>Feature 1: High quality</li>
            <li>Feature 2: Fast shipping</li>
        </ul>
        <a href="/buy" title="Buy now">Purchase</a>
    </div>
    '''
    payload = {
        'text': html,
        'source_lang': 'en',
        'target_lang': 'zh'
    }
    resp = requests.post(f'{BASE_URL}/api/translate', json=payload)
    return print_response('HTML Translation', resp)


def test_terms_crud():
    print('\n=== Terms CRUD ===')
    print('\n-- List Terms --')
    resp = requests.get(f'{BASE_URL}/api/terms')
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))

    print('\n-- Add Term --')
    payload = {
        'source': 'Wireless Charging',
        'target': '无线充电',
        'source_lang': 'en',
        'target_lang': 'zh',
        'category': 'spec'
    }
    resp = requests.post(f'{BASE_URL}/api/terms', json=payload)
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))
    term_id = resp.json()['term']['id']

    print('\n-- List Terms Again --')
    resp = requests.get(f'{BASE_URL}/api/terms')
    data = resp.json()
    print(f'Total terms: {data["count"]}')

    print(f'\n-- Delete Term {term_id} --')
    resp = requests.delete(f'{BASE_URL}/api/terms/{term_id}')
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))


def test_memory_crud():
    print('\n=== Translation Memory CRUD ===')
    print('\n-- List Memory --')
    resp = requests.get(f'{BASE_URL}/api/memory')
    data = resp.json()
    print(f'Total entries: {data["count"]}')

    print('\n-- Add Memory Entry --')
    payload = {
        'source': 'We offer a 30-day money-back guarantee.',
        'target': '我们提供30天退款保证。',
        'source_lang': 'en',
        'target_lang': 'zh',
        'preferred': True
    }
    resp = requests.post(f'{BASE_URL}/api/memory', json=payload)
    data = resp.json()
    print(json.dumps(data, ensure_ascii=False, indent=2))
    entry_id = data['entry']['id']

    print('\n-- Mark Preferred --')
    resp = requests.post(f'{BASE_URL}/api/memory/{entry_id}/prefer')
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))

    print('\n-- Search Memory --')
    payload = {
        'text': 'We offer a 30-day money-back guarantee!',
        'source_lang': 'en',
        'target_lang': 'zh',
        'threshold': 0.8
    }
    resp = requests.post(f'{BASE_URL}/api/memory/search', json=payload)
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))


def test_async_task():
    print('\n=== Async Task Test ===')
    long_text = ' '.join(['This is a test sentence for translation.'] * 300)
    payload = {
        'text': long_text,
        'source_lang': 'en',
        'target_lang': 'zh'
    }
    resp = requests.post(f'{BASE_URL}/api/translate', json=payload)
    data = resp.json()
    print(json.dumps(data, ensure_ascii=False, indent=2))

    if data.get('async'):
        task_id = data['task_id']
        print(f'\nPolling task {task_id}...')
        for i in range(10):
            time.sleep(1)
            resp = requests.get(f'{BASE_URL}/api/tasks/{task_id}')
            status = resp.json()
            print(f'  [{i+1}] status={status["status"]} progress={status.get("progress",0)}/{status.get("total",0)}')
            if status['status'] in ('completed', 'failed', 'cancelled'):
                print(f'Final result: {json.dumps(status, ensure_ascii=False, indent=2)[:500]}...')
                break


if __name__ == '__main__':
    print(f'Testing Local Translation Service at {BASE_URL}')
    print('=' * 60)

    try:
        test_health()
        test_status()
        test_languages()
        test_detect()
        test_translate_single()
        test_translate_auto_detect()
        test_translate_with_terms()
        test_translate_batch()
        test_html_translate()
        test_terms_crud()
        test_memory_crud()
        test_async_task()

        print('\n' + '=' * 60)
        print('All tests completed!')
    except requests.ConnectionError:
        print(f'\nERROR: Cannot connect to {BASE_URL}')
        print('Please start the server first: run start.bat or python app.py')
    except Exception as e:
        print(f'\nERROR: {e}')
        import traceback
        traceback.print_exc()
