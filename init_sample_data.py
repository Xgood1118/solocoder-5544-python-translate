import json
import os
import config


def init_sample_data():
    os.makedirs(config.DATA_DIR, exist_ok=True)
    term_base_file = config.TERM_BASE_FILE
    if not os.path.exists(term_base_file) or os.path.getsize(term_base_file) == 0:
        sample_terms = [
            {
                'id': 1,
                'source': 'AirPods Pro',
                'target': 'AirPods Pro',
                'source_lang': 'en',
                'target_lang': 'zh',
                'category': 'brand'
            },
            {
                'id': 2,
                'source': 'SKU-8845A12',
                'target': 'SKU-8845A12',
                'source_lang': 'auto',
                'target_lang': 'auto',
                'category': 'sku'
            },
            {
                'id': 3,
                'source': 'Bluetooth 5.3',
                'target': '蓝牙 5.3',
                'source_lang': 'en',
                'target_lang': 'zh',
                'category': 'spec'
            },
            {
                'id': 4,
                'source': 'USB-C',
                'target': 'USB-C',
                'source_lang': 'auto',
                'target_lang': 'auto',
                'category': 'spec'
            },
            {
                'id': 5,
                'source': '降噪耳机',
                'target': 'Noise Cancelling Headphones',
                'source_lang': 'zh',
                'target_lang': 'en',
                'category': 'product'
            },
            {
                'id': 6,
                'source': '跨境电商',
                'target': 'Cross-border E-commerce',
                'source_lang': 'zh',
                'target_lang': 'en',
                'category': 'general'
            }
        ]
        with open(term_base_file, 'w', encoding='utf-8') as f:
            json.dump({'terms': sample_terms}, f, ensure_ascii=False, indent=2)
        print(f'Initialized sample term base: {len(sample_terms)} terms')

    memory_file = config.TRANSLATION_MEMORY_FILE
    if not os.path.exists(memory_file) or os.path.getsize(memory_file) == 0:
        import time
        from datetime import datetime, timedelta
        sample_entries = [
            {
                'id': 1,
                'source': 'Thank you for your purchase.',
                'target': '感谢您的购买。',
                'norm_source': 'thankyouforyourpurchase',
                'source_lang': 'en',
                'target_lang': 'zh',
                'preferred': True,
                'created_at': datetime.now().timestamp(),
                'updated_at': datetime.now().timestamp(),
                'expires_at': (datetime.now() + timedelta(days=90)).timestamp(),
                'metadata': {'category': 'customer_service'}
            },
            {
                'id': 2,
                'source': 'Fast shipping worldwide.',
                'target': '全球快速配送。',
                'norm_source': 'fastshippingworldwide',
                'source_lang': 'en',
                'target_lang': 'zh',
                'preferred': False,
                'created_at': datetime.now().timestamp(),
                'updated_at': datetime.now().timestamp(),
                'metadata': {'category': 'marketing'}
            }
        ]
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump({'entries': sample_entries}, f, ensure_ascii=False, indent=2)
        print(f'Initialized sample translation memory: {len(sample_entries)} entries')


if __name__ == '__main__':
    init_sample_data()
    print('Sample data initialization complete.')
