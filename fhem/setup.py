from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(name='fhem',
      version='0.5.4',
      description='Python API for FHEM home automation server',
      long_description=long_description,
      classifiers=[
          'Development Status :: 4 - Beta',
          'License :: OSI Approved :: MIT License',
      ],
      keywords='fhem home automation',
      url='http://github.com/domschl/python-fhem',
      author='Dominik Schloesser',
      author_email='dsc@dosc.net',
      license='MIT',
      packages=['fhem'],
      zip_safe=False)
