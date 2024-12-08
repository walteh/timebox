from setuptools import setup

APP = ['main.py']
DATA_FILES = ['header.png']
OPTIONS = {
    'argv_emulation': True,
    'plist': {
        'LSUIElement': True,
        'CFBundleName': 'Timebox',
        'CFBundleDisplayName': 'Timebox',
        'CFBundleIdentifier': 'com.timebox.app',
        'CFBundleVersion': '0.6.0',
        'CFBundleShortVersionString': '0.6.0'
    },
    'packages': ['rumps'],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
