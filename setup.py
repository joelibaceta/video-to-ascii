import setuptools

setuptools.setup(
    name="video_to_ascii",
    version="1.0.1",
    author="Joel Ibaceta",
    author_email="mail@joelibaceta.com",
    description="A simple tool to play a video using ascii characters",
    url="https://github.com/joelibaceta/video-to-terminal",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    scripts=['bin/video-to-ascii'],
)