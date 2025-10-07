from setuptools import setup

setup(
    entry_points={
        'console_scripts': [
            'chatmgr=chatmgr:main',
        ],
    },
)
