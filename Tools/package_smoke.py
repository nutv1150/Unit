"""Opt-in packaged GUI self-test using only a temporary workspace (no network)."""
import json
import os
from pathlib import Path
import tempfile
import time


# หน้าที่: ทดสอบ packaged app ด้วย workspace/profile ชั่วคราวและคืน environment เมื่อเสร็จ
# ที่มา: entry point ของ CLI/launcher; รับข้อมูลจาก command line หรือระบบ
# Input: ไม่มีพารามิเตอร์ที่ส่งเข้ามาโดยตรง
# อ่านภายใน: resource files ของ bundle (Path) และ environment (Mapping[str, str]); ใช้ profile ชั่วคราว
# อ่านภายใน: inspection.result_boxes[str(source)].textbox.get() — ค่าจาก widget/Tk variable (str หรือชนิดของ Variable)
def main():
    previous_cwd = Path.cwd()
    previous_data = os.environ.get('UNIT_DATA_HOME')
    with tempfile.TemporaryDirectory(prefix='unit-package-test-') as folder:
        work = Path(folder)
        os.environ['UNIT_DATA_HOME'] = str(work / 'profile')
        os.chdir(work)
        root = None
        try:
            # These imports must follow the profile override, before GUI creation.
            from app import UNITApp
            from Tools.regex_runner import find_match_spans
            from Tools.solve_history import export_html
            from Pipeline.config_store import write_json, saved_pipelines
            from Tools.app_paths import writable_path
            from Tools.stream_capture import run_capture
            root = UNITApp()
            errors = []
            root.report_callback_exception = lambda *args: errors.append(str(args))
            root.withdraw()
            assert root.TkdndVersion
            assert len(root._unit_icons) == 3
            assert all(icon.width() > 0 for icon in root._unit_icons)
            for name in root.pages:
                root.switch_page(name)
                root.update()
            assert find_match_spans(r'flag\{[^}]+\}', 'ไทย FLAG{ok}') == [[4, 12]]
            try:
                find_match_spans('(a+)+$', 'a'*32+'!', timeout=.5)
            except ValueError as error:
                assert 'exceeded' in str(error)
            else:
                raise AssertionError('Regex timeout did not stop worker')
            page = root.pages['Data Hashing']
            page.set_mode('Decode')
            page.algo_menu.set('Base64')
            page.input_box.insert('1.0', 'SGVsbG8=')
            page.process_data()
            assert page.output_bytes == b'Hello'
            inspection = root.pages['File Inspection']
            source = work / 'ตัวอย่าง.txt'
            source.write_text('flag{package_test}', encoding='utf-8')
            inspection.tool_menu.set('Strings')
            inspection.regex_var.set(r'flag\{[^}]+\}')
            inspection.load_files([str(source)])
            deadline = time.monotonic()+10
            while inspection.btn_analyze.cget('state') == 'disabled':
                root.update()
                if time.monotonic() > deadline:
                    raise AssertionError('Inspection did not finish')
                time.sleep(.01)
            assert 'flag{package_test}' in inspection.result_boxes[str(source)].textbox.get('1.0','end')
            assert 'ERROR' not in inspection.warning_label.cget('text')
            result = root.pages['Pipeline'].engine.run_text_tool('base64_decode', b'SGVsbG8=', detailed=True)
            assert result.succeeded and result.stdout == b'Hello', result.stderr
            event = root.history_store.begin('Pipeline', 'package smoke')
            root.history_store.finish(event, 'Success', output_data=result.stdout)
            export_html(work/'history.html', root.history_store.iter_events())
            assert 'package smoke' in (work/'history.html').read_text()
            assert root.history_store.path.is_relative_to(work)
            assert root.dashboard_store.state_path.is_relative_to(work)
            target = writable_path('Pipeline/saved_pipelines.json')
            write_json(target, {'saved_pipelines':[{'pipeline_name':'test', 'steps':[{'name':'strings'}]}]})
            assert saved_pipelines(target)['saved_pipelines'][0]['pipeline_name'] == 'test'
            assert not errors, errors
            for callback in root.tk.call('after', 'info'):
                root.tk.call('after', 'cancel', callback)
            root.on_close()
            root = None
            print(json.dumps({'result':'PASS', 'checks':['8 GUI pages', 'application icon loaded', 'TkDnD loaded', 'regex unicode and timeout',
                'codec bytes', 'inspection strings/regex', 'external pipeline', 'isolated history/export',
                'saved pipeline persistence', 'clean close']}, ensure_ascii=False))
            return 0
        finally:
            if root is not None:
                root.destroy()
            os.chdir(previous_cwd)
            if previous_data is None:
                os.environ.pop('UNIT_DATA_HOME', None)
            else:
                os.environ['UNIT_DATA_HOME'] = previous_data
