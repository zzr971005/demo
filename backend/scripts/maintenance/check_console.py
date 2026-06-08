from playwright.sync_api import sync_playwright
import sys

url = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:3003'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    console_messages = []
    page.on('console', lambda msg: console_messages.append({'type': msg.type, 'text': msg.text}))

    page_errors = []
    page.on('pageerror', lambda err: page_errors.append(str(err)))

    try:
        page.goto(url, timeout=15000)
        page.wait_for_timeout(8000)
    except Exception as e:
        print(f'页面加载异常: {e}')

    print('=== Console Errors & Warnings ===')
    error_count = 0
    for msg in console_messages:
        if msg['type'] in ['error', 'warning']:
            print(f'[{msg["type"]}] {msg["text"][:200]}')
            error_count += 1
            if error_count > 30:
                print('...(超过30条，显示前30条)')
                break

    print()
    print('=== Page Errors ===')
    for err in page_errors[:10]:
        print(f'ERROR: {err[:200]}')

    browser.close()