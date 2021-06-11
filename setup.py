from setuptools import find_packages
from setuptools import setup

setup(name='olcommon',
      version='1.0.dev1',
      classifiers=['Programming Language :: Python', 'Framework :: Pyramid'],
      author='Olive Link Pty Ltd',
      author_email='software@olivelink.net',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
        'setuptools',

        'plone.testing',
        'requests',

        'pyramid',
        'pyramid_chameleon',
        'pyramid_exclog',
        'pyramid_tm',
        'pyramid_mailer',
        'pyramid_redis_sessions',

        'sqlalchemy',
        'sqlalchemy-utils',
        'zope.sqlalchemy',

        'redis',

        'jsonschema',
        'pyjwt',
        'bcrypt',

        'ctq',
        'ctq-sqlalchemy',

        'psycopg2-binary',
      ])
