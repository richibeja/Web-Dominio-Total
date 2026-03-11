import pathlib, sys

root = pathlib.Path(r"C:\\Users\\ALP\\Documents\\modelos  ia para monitizar")
errors = []
for py_file in root.rglob('*.py'):
    try:
        compile(py_file.read_text(encoding='utf-8'), str(py_file), 'exec')
    except Exception as e:
        errors.append((py_file, e))

if errors:
    for f, e in errors:
        print(f'Error in {f}: {e}')
    sys.exit(1)
else:
    print('All .py files compiled successfully.')
