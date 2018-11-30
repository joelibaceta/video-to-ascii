import setuptools

setuptools.setup(
    name="video_to_ascii",
    version="1.1.3",
    author="Joel Ibaceta",
    author_email="mail@joelibaceta.com",
    description="A simple tool to play a video using ascii characters",
    url="https://github.com/joelibaceta/video-to-ascii",
    packages=setuptools.find_packages(),
    install_requires=[
          'opencv-python', 'colorize'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    scripts=['bin/video-to-ascii'],
)