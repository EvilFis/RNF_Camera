import re
import os
import cv2
import time
import typing
import logging
import datetime
import numpy as np

from multiprocessing import Barrier, Pipe

from .BaseСamera import BaseCamera


class Camera(BaseCamera):

    # Размрешенные имена переменных
    __slots__ = ["__device_id", "__mode"]
    

    def __new__(cls, *args, **kwargs):
        
        # Создаем папку для хранения логов
        try:
            os.mkdir("./log")
        except FileExistsError:
            pass
        
        return super().__new__(cls)
    

    def __init__(self,
                 device_id: typing.Union[int, str],
                 mode: str = "stream"):
        """
        Args:
            `device_id (int | str)`: ID камеры
            
            `mode (str, optional)`: Режим работы камеры. По умолчанию `stream`.
            `stream` - Потоковый вывод с камеры.
            `video` - Запись потокового вывода с камеры в видео файл
            `frame` - Запись кадров потокового вывода с камеры в файл
            `centring` - Центрирование кадра
        """
        # Создание базовой конфугурации логировния информации
        logging.basicConfig(level=logging.INFO, 
                            filename="./log/camera.log",
                            filemode="a",
                            format="%(asctime)s %(levelname)s %(message)s")
        
        camera_mode = ("stream", "video", "frame", "centring")
        if mode not in camera_mode:
            logging.warning(f"[CCTV] There is no '{mode}' mode of operation, 'stream' mode is selected by default")
            mode = "stream"
        
        self.__device_id = device_id
        self.__id = self.__valid_id(device_id) if isinstance(device_id, str) else device_id
        self.__mode = mode.lower()
        self.__flag = True

        self.__frame = np.ndarray

        logging.info(f"[CCTV] Camera using {self.__device_id} camera id. Operating mode '{self.__mode}'")
    

    def __str__(self) -> str:
        return f"[CCTV] Camera using '{self.__device_id}' camera id.\nOperating mode '{self.__mode}'"
    

    def get_frame(self):
        return self.__frame


    @property
    def device_id(self) -> typing.Union[int, str]:
        """Получение текущего ID камеры

        Returns:
            `int | str`: ID камеры
        """
        return self.__device_id
    

    @device_id.setter
    def device_id(self, id: typing.Union[int, str]) -> None:
        """Изминение ID потоковой камеры

        Args:
            `id (typing.Union[int, str])`: ID камеры
        """
        
        logging.info(f"[CCTV] A new device ID has been installed {id}")
        self.__device_id = self.__valid_id(id) if isinstance(id, str) else id
    

    @property
    def mode(self) -> str:
        """Получение значения текущего режима работы камеры.
        `stream` - Потоковый вывод с камеры.
        `video` - Запись потокового вывода с камеры в видео файл
        `frame` - Запись кадров потокового вывода с камеры в файл

        Returns:
            `str`: Режим работы камеры
        """
        return self.__mode
    

    @mode.setter
    def mode(self, mode: str) -> None:
        """Изминения значения ржима работы камеры. Доступные режимы `stream`, `video`, `frame`
        `stream` - Потоковый вывод с камеры.
        `video` - Запись потокового вывода с камеры в видео файл
        `frame` - Запись кадров потокового вывода с камеры в файл
        
        Args:
            `str`: Режим работы камеры.

        """
        camera_mode = ("stream", "video", "frame")
        if mode not in camera_mode:
            logging.warning(f"[CCTV] There is no '{mode}' mode of operation, 'stream' mode is selected by default")
            mode = "stream"
        logging.info(f"[CCTV] A new camera mode has been installed {mode}")
        self.__mode = mode
    

    def _video_writer(self, path: str, fps: int, frame: np.ndarray):
        """Обертка для cv2.VideoWriter с назначеним папки и текущего фпс

        Args:
            `path (str)`: Путь сохранения файла
            
            `fps (int)`: fps записи видео
            
            `frame (np.ndarray)`: Текущий кадр
            
        Returns:
            `cv2.VideoWriter`: Объект для записи видео в файл
            
        """
        
        width = frame.shape[1]
        height = frame.shape[0]     
        writer = cv2.VideoWriter(
                f"{path}/Camera_{self.__id}_{self.__mode}/camera_{self.__id} {width}x{height}.avi",
                cv2.VideoWriter_fourcc(*"MJPG"),
                fps, (width, height), True
            )
        
        return writer


    def _save_frame(self, start_time: float, 
                    time_out: int, path: str, 
                    frame: np.ndarray, counter: int) -> tuple:
        """Обертка для сохранения кадра в папку

        Args:
            `start_time (float)`: Время с последнего кадра
            
            `time_out (int)`: Время задержки
            
            `path (str)`: Путь сохранения изображения
            
            `frame (np.ndarray)`: Текущий кадр
            
            `counter (int)`: Колличество сохраненных кадров

        Returns:
            `tuple`: Текущий кадр с надписями о времени и колличестве сохраненных кадров.
            Колличество сохраненных кадров. Обновленное время с последнего кадра
        """
        current_time = time_out - (time.time() - start_time)
                    
        if current_time <= 0:
            cv2.imwrite(f"{path}/Camera_{self.__id}_{self.__mode}/{counter}.png", frame)
            logging.info(f"[CCTV] Camera {self.__device_id}] image {counter} saved successfully. Path = {path}/Camera_{self.__id}_{self.__mode}/{counter}.png")
            start_time = time.time()
            counter += 1
            
        frame = cv2.putText(frame, f"Time: {int(current_time)}",
                    (20, 20), cv2.FONT_HERSHEY_COMPLEX_SMALL,
                    1, (0, 0, 0), 1)
        frame = cv2.putText(frame, f"Counter: {counter}",
                    (20, 40), cv2.FONT_HERSHEY_COMPLEX_SMALL,
                    1, (0, 0, 0), 1)
        
        return frame, counter, start_time
    

    def _create_folder(self, folder_name: str, path: str = "./") -> None:
        """Создает папку в необходимой директории

        Args:
            `folder_name (str)`: Название папки
            
            `path (str, optional)`: Путь создания папки. По умолчанию "./".

        Raises:
            `TypeError`: Возникает при передаче не строкового значения.
        """
        
        try:
            assert isinstance(folder_name, str)
            assert isinstance(path, str)
            
        except AssertionError:
            logging.error("[CCTV] The variable 'folder_name' and 'path' takes a string value")
            raise TypeError("[CCTV] The variable 'folder_name' and 'path' takes a string value")
        
        try:
            folder = f"{path}/{folder_name}"
            os.mkdir(folder)
            logging.info(f"[CCTV] Folder {folder.split('/')[-1]} created")
        except FileExistsError:
            logging.warning(f"[CCTV] It is not possible to create a folder '{folder_name}'. \
The folder has already been created")
    

    def __valid_id(self, device_id: str) -> typing.Union[str, int]:
        """Проверка типа полученного ID камеры.
        Если при инициализации класса ID устройства относиться к типу данных str
        Проверяем наличие IPv4 адреса. Если адрес имеется возвращаем ID в виде IPv4.
        Иначе проверяем строку на наличие числа. Если имеется число преобразуем строку в целое значение и возвращаем ID
        Иначе возвращаем изначально полученную строку

        Args:
            `device_id (str)`: ID камеры

        Returns:
            `str | int`: Валидное ID камеры
        """
        ipv4_extract_pattern = "(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
        ipv4 = re.findall(ipv4_extract_pattern, device_id)
        
        if len(ipv4) >=1:
            return ipv4[0].replace(".", "_")
        elif device_id.isdigit():
            return int(device_id)
        return device_id
            

    def __check_camera(self, capture: cv2.VideoCapture) -> tuple:
        """Проверка работы камеры

        Args:
            `capture (cv2.VideoCapture)`: Захваченная камера OpenCV

        Raises:
            `Exception`: Вызывается в случае не удачи захвата камеры 

        Returns:
            `tuple`: Статуст камеры. Полученный кадр с камеры 
        """
        
        ret, frame = capture.read()
        
        if not ret:
            logging.error(f"Failed to get information from camera {self.__device_id}")
            raise Exception(f"Failed to get information from camera {self.__device_id}")
        
        return ret, frame
    

    def __centring(self, frame: np.ndarray) -> np.ndarray:
        h, w, _ = frame.shape

        frame = cv2.line(frame, (int(w/2), 0), (int(w/2), h), (0, 0, 255), 2)
        frame = cv2.line(frame, (0, int(h/2)), (w, int(h/2)), (0, 0, 255), 2)

        return frame


    def release(self, capture: cv2.VideoCapture,
                show_gui: bool, 
                writer = None) -> None: 
        """Обнуляем параметры камеры и уничтожаем имеющиеся окно предосмотра

        Args:
            `capture (cv2.VideoCapture)`: Захваченное устройство
            `show_gui (bool)`: Имеется ли окно показа изображения.
            `writer (cv2.VideoWriter, optional)`: Обертка cv2.VideoWriter. По умолчанию `None`.
        """
        
        if show_gui:
            cv2.destroyAllWindows()
        
        if self.__mode == "video":
            writer.release()
            
        capture.release()
        self.stop()
        logging.info(f"[CCTV] The camera with the index {self.__device_id} has shut down")
    

    def stop(self) -> None:
        """Вспомогательный метод для остановки потокового вещания камеры
        """
        self.__flag = False
    

    def stream(self,
               size: tuple = (640, 480), 
               img_count: int = 10,
               time_out: int = 5,
               path: str = "./",
               show_gui: bool = True,
               fps: int = 30,
               barrier: Barrier = None,
               sender: Pipe = None) -> None:
        """Запуск потока видеозаписи видео/сохранения кадров/вывода

        Args:
            `img_count (int, optional)`: Необходимое колличество изображений. Используется при режиме работы `frame`. По умолчанию `10`.
            
            `time_out (int, optional)`: Задержка перед сохранением кадра. Используется при режиме работы `frame`. По умолчанию `5`.
            
            `path (str, optional)`: Путь сохранения кадра или видео. Используется при режиме работы `frame` или `video`. По умолчанию `./`.
            
            `show_gui (bool, optional)`: Показ окна предварительного просмотра. По умолчанию `True`.
            
            `fps (int, optional)`: FPS записи для видеофайла. Используется при режиме работы `video`. По умолчанию `30`.
            
            `barier (Barrier)`: Барьер для синхронизации потоков. Используется в мультипроцесорности или многопоточности. По умолчанию None.
        """
        
        self.__flag = True
        
        cap = cv2.VideoCapture(self.device_id, cv2.CAP_FFMPEG if isinstance(self.device_id, str) else None)
        _, frame = self.__check_camera(cap) # Проверка камеры на роботоспособность

        
        if self.__mode == "video" or self.__mode == "frame":
            self._create_folder(folder_name=f"Camera_{self.__id}_{self.__mode}", path=path)
        
        # Подготовка к записи видео
        writer = None
        if self.__mode == "video":
            writer = self._video_writer(path, fps, cv2.resize(frame, size))

        # Ожидание других потоков или процессов
        if barrier:
            barrier.wait()
        
        start_time = time.time()
        counter = 0
        logging.info(f"[CCTV] The camera with the index {self.__device_id} has started working in the '{self.__mode}' mode")
        
        while self.__flag:
            
            datetime_now = datetime.datetime.now()

            try:
                key = cv2.waitKey(1)
                _, frame = cap.read()

                frame = cv2.resize(frame, size)

                # Сохранение кадра в файл
                if (self.__mode == "frame"):
                    frame, counter, start_time = self._save_frame(start_time, time_out, path, frame, counter)
                
                # Сохранение видео в файл
                elif (self.__mode == "video"):
                    frame = cv2.putText(frame, f"{datetime_now.hour}:{datetime_now.minute}:{datetime_now.second}",
                    (20, 20), cv2.FONT_HERSHEY_COMPLEX_SMALL,
                    1, (0, 0, 255), 1)
                    writer.write(frame)

                elif self.__mode == "centring":
                    frame = self.__centring(frame)
                
                self.__frame = frame

                if sender:
                    sender.send((frame, ))

                # Отображение окна предосмотра видео
                if show_gui:
                    cv2.imshow(f"Camera {self.__device_id}", frame)
                
                # Выход по нажатию клавиши Q или по вызову метода stop
                if key == ord('q') & 0xFF or not self.__flag:
                    logging.info("[CCTV] The recording was completed by pressing a key or calling the 'stop' method")
                    self.release(capture=cap, show_gui=show_gui, writer=writer)
                
                # Выход при сохранении всех изображений
                if counter >= img_count:
                    logging.info(f"[CCTV] The recording has ended. All images have been successfully collected")
                    self.release(capture=cap, show_gui=show_gui, writer=writer)
                
            except:
                logging.error(f"[CCTV] An unexpected error has occurred, the operation of the camera under the index {self.__device_id} is suspended")
                self.release(capture=cap, show_gui=show_gui, writer=writer)