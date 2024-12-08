from setuptools import setup

APP = ['main.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': True,
    'plist': {
        'LSUIElement': True,
        'CFBundleName': 'Timebox',
        'CFBundleDisplayName': 'Timebox',
        'CFBundleIdentifier': 'com.walteh.timebox',
        'CFBundleVersion': '0.6.2'
    },
    'packages': ['rumps', 'things', 'watchdog'],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={},
    setup_requires=[],
)
