from setuptools import setup

setup(name='hcheck',
      version='1.8',
      description='Health Check Package for Flask App',
      author='Sayed Raianul Kabir',
      author_email='raianul.berlin@gmail.com',
      license='MIT',
      packages=['hcheck'],
      install_requires=[
          'Werkzeug>=0.9.6',
          'requests>=2.8.1',
      ],
      zip_safe=False)
