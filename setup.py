from setuptools import setup, find_packages

setup(
    name="video_to_ascii",
    version="1.2.0",
    author="Joel Ibaceta",
    author_email="mail@joelibaceta.com",
    license='MIT',
    description="It is a simple python package to play videos in the terminal",
    long_description="A simple tool to play a video using ascii characters using colored characters as pixels or other usefull outputs",
    url="https://github.com/joelibaceta/video-to-ascii",
    project_urls={
        'Source': 'https://github.com/joelibaceta/video-to-ascii',
        'Tracker': 'https://github.com/joelibaceta/video-to-ascii/issues'
    },
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
          'opencv-python', 'xtermcolor'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    keywords='video ascii terminal opencv',
    scripts=['bin/video-to-ascii'],
)