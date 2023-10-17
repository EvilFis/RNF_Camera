from typing import NoReturn, Union
from abc import ABCMeta, abstractmethod


class BaseCamera(metaclass=ABCMeta):

    @abstractmethod
    def _create_folder(self) -> NoReturn:
        pass

    @abstractmethod
    def _video_writer(self):
        pass

    @abstractmethod
    def _save_frame(self):
        pass

    @abstractmethod
    def release(self) -> NoReturn:
        pass

    @abstractmethod
    def stop(self) -> NoReturn:
        pass

    @abstractmethod
    def stream(self) -> NoReturn:
        pass

    @property
    @abstractmethod
    def device_id(self) -> Union[int, str]:
        pass

    @property
    @abstractmethod
    def mode(self) -> str:
        pass