"""This module has an abstract class for render strategies"""

from abc import ABC, abstractmethod

class RenderStrategy(ABC):
    """An abstract class to guide about how to implement a render_strategy class"""

    @abstractmethod
    def render(self, vc):
        """
        This method must be implemented with the necessary instructions to process the video frames and generate the output
        """
        raise Exception("NotImplementedException")
        