import os
from typing import NoReturn
import cv2
import time
import typing
import logging
import datetime
import numpy as np
import pyrealsense2 as rs

from multiprocessing import Barrier, Pipe

from .BaseСamera import BaseCamera


class CameraRS(BaseCamera):
    
    __slots__ = ["__device_id", "__mode"]
    
    def __new__(cls, *args, **kwargs):
        
        # Создаем папку для хранения логов
        try:
            os.mkdir("./log")
        except FileExistsError:
            pass
        
        return super().__new__(cls)
  
    def __init__(self,
                 device_id: int,
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
        
        assert isinstance(device_id, int), f"The `device_id` parameter has the {type(device_id)}\ data type, the `int` data type is required for operation"
        
        # Создание базовой конфугурации логировния информации
        logging.basicConfig(level=logging.INFO, 
                            filename="./log/camera.log",
                            filemode="a",
                            format="%(asctime)s %(levelname)s %(message)s")
        
        camera_mode = ("stream", "video", "frame", "centring")
        if mode not in camera_mode:
            logging.warning(f"[RS] There is no '{mode}' mode of operation, 'stream' mode is selected by default")
            mode = "stream"
        
        contex = rs.context()
        devices = list(contex.query_devices())
        
        if  device_id > len(devices):
            logging.error("[RS] The transmitted id exceeds the number of connected devices")
            raise ValueError("[RS] The transmitted id exceeds the number of connected devices")
        if device_id < 0:
            logging.error("[RS] The transmitted id is less than 0 (id < 0)")
            raise ValueError("[RS] The transmitted id is less than 0 (id < 0)")
        
        self.__device = devices[device_id]
        self.__device_name = self.get_device_name()
        self.__device_serial_number = self.get_serial_number()
        
        self.__pipeline = rs.pipeline()
        self.__config = rs.config()
        self.__colorizer = rs.colorizer()
        
        self.__mode = mode.lower()
        self.__flag = True

        self.__color_frame = np.ndarray
        self.__depth_frame = np.ndarray
        
        self.__colorizer.set_option(rs.option.visual_preset, 0)

        logging.info(f"[RS] RealSense camera using {self.__device_name} #{self.__device_serial_number} camera id. Operating mode '{self.__mode}'")
          
    def __str__(self):
        return f"[RS] RealSense camera using {self.__device_name} #{self.__device_serial_number} camera id. Operating mode '{self.__mode}'"
    
    @property
    def device_id(self) -> int:
        """Получение текущего ID камеры

        Returns:
            `int`: ID камеры
        """
        return self.__device_id
    
    @device_id.setter
    def device_id(self, id: int) -> None:
        """Изминение ID потоковой камеры

        Args:
            `id (int)`: ID камеры
        """
        
        contex = rs.context()
        devices = list(contex.query_devices())
        
        if  id > len(devices):
            logging.error("[RS] The transmitted id exceeds the number of connected devices")
            raise ValueError("[RS] The transmitted id exceeds the number of connected devices")
        if id < 0:
            logging.error("[RS] The transmitted id is less than 0 (id < 0)")
            raise ValueError("[RS] The transmitted id is less than 0 (id < 0)")
        
        logging.info(f"[RS] A new device ID has been installed {id}")
        self.__device_id = id
        self.__device = devices[id]
        self.__device_name = self.get_device_name()
        self.__device_serial_number = self.get_serial_number()
    
    @property
    def mode(self) -> str:
        """Получение значения текущего режима работы камеры.
        `stream` - Потоковый вывод с камеры.
        `video` - Запись потокового вывода с камеры в видео файл
        `frame` - Запись кадров потокового вывода с камеры в файл
        `centring` - Центрирование кадра

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
        
        camera_mode = ("stream", "video", "frame", "centring")
        if mode not in camera_mode:
            logging.warning(f"[RS] There is no '{mode}' mode of operation, 'stream' mode is selected by default")
            mode = "stream"
        logging.info(f"[RS] A new camera mode has been installed {mode}")
        self.__mode = mode
    
    def getFrames(self) -> tuple:
        return self.__color_frame, self.__depth_frame

    @staticmethod
    def get_devices_str() -> list:
        
        """Получение информации о всех устройствам

        Returns:
            `list | str`: Возвращает список подключенных устройств
        """
        
        contex = rs.context()
        devs = list(contex.query_devices()) if len(list(contex.query_devices())) > 1 \
            else list(contex.query_devices())[0]
            
        return list(CameraRS.get_full_information(devs))
    
    @staticmethod
    def get_full_information(devive: typing.Union[list, rs.device]) -> list:
        
        """Получение информации о серийном номере устройства/устройств

        Args:
            `devive (list | rs.device)`: Список устройств или устройства `rs.device`
        Returns:
            `list`: Список серийных номеров
        """
            
        if isinstance(devive, list):
            dev_info = []
            
            for i, dev in enumerate(devive):
                dev_info.append(f"{i}. {dev.get_info(rs.camera_info.name)} #{dev.get_info(rs.camera_info.serial_number)}")
                
            return dev_info
        
        if isinstance(devive, rs.device):
            return [f"0. {devive.get_info(rs.camera_info.name)} #{devive.get_info(rs.camera_info.serial_number)}"]
    
    def _configuration_camera(self, color_profile: int, depth_profile:int) -> tuple:
        """Конфигурация камеры. Устновка формата работы камеры.

        Args:
            `color_profile (int)`: ID цветового профиля
            
            `depth_profile (int)`: ID профиля глубины

        Returns:
            `tuple`: Профиль глубины. Цветовой профидь
        """
        depth_prof = rs.video_stream_profile(self.__device.sensors[0].get_stream_profiles()[depth_profile])
        color_prof = rs.video_stream_profile(self.__device.sensors[1].get_stream_profiles()[color_profile])
        
        self.__config.enable_device(self.get_serial_number())
        self.__config.enable_stream(
            depth_prof.stream_type(),
            depth_prof.width(), 
            depth_prof.height(),
            depth_prof.format(),
            depth_prof.fps()
        )
        self.__config.enable_stream(
            color_prof.stream_type(),
            color_prof.width(), 
            color_prof.height(),
            color_prof.format(),
            color_prof.fps()
        )
        
        self.__pipeline.start(self.__config)
        
        return depth_prof, color_prof
    
    def _video_writer(self, path: str, d_prof, c_prof):
        """Обертка для cv2.VideoWriter с назначеним папки и текущего фпс

        Args:
            `path (str)`: Путь сохранения файла
            
            `fps (int)`: fps записи видео
            
            `d_prof (np.ndarray)`: Профиль глубины
            
            `c_prof (np.ndarray)`: Цветовой профиль

        Returns:
            `cv2.VideoWriter`: Объект для записи видео в файл
        """
        
        # device_product_line = str(self.device.get_info(rs.camera_info.product_line))
        # color_prof.fps() if device_product_line == "D400" else int(color_prof.fps() / 2)
            
        color_writer = cv2.VideoWriter(
            f"{path}/RS_Camera_{self.__device_name}_{self.__device_serial_number}_{self.__mode}/color_{self.__device_name}_{self.__device_serial_number}_{c_prof.width()}x{c_prof.height()}.avi",
            cv2.VideoWriter_fourcc(*"MJPG"), c_prof.fps(),
            (c_prof.width(), c_prof.height()), True)
        
        depth_writer = cv2.VideoWriter(
            f"{path}/RS_Camera_{self.__device_name}_{self.__device_serial_number}_{self.__mode}/depth_{self.__device_name}_{self.__device_serial_number}_{d_prof.width()}x{d_prof.height()}.avi",
            cv2.VideoWriter_fourcc(*"MJPG"), d_prof.fps(),
            (d_prof.width(), d_prof.height()), True)
        
        return depth_writer, color_writer
    
    def __centring(self, frame: np.ndarray) -> np.ndarray:
        h, w, _ = frame.shape

        frame = cv2.line(frame, (int(w/2), 0), (int(w/2), h), (0, 0, 255), 2)
        frame = cv2.line(frame, (0, int(h/2)), (w, int(h/2)), (0, 0, 255), 2)

        return frame

    def _save_frame(self, start_time: float, time_out: int, 
                    path: str, color_i: np.ndarray, 
                    depth_i: np.ndarray, depth_data_frame: np.ndarray, 
                    counter: int) -> tuple:
        """Обертка для сохранения кадра в папку

        Args:
            `start_time (float)`: _description_
            
            `time_out (int)`: Время с последнего кадра
            
            `path (str)`: Путь сохранения изображения
            
            `color_i (np.ndarray)`: Текущий цветной кадр
            
            `depth_i (np.ndarray)`: Текущий кадр с приминеним карты глубины
            
            `depth_data_frame (np.ndarray)`: Текущий кадр глубины 
            
            `counter (int)`: Колличество сохраненных кадров

        Returns:
            `tuple`: Текущий кадр с надписями о времени и колличестве сохраненных кадров.
            Колличество сохраненных кадров. Обновленное время с последнего кадра
        """
        
        current_time = time_out - (time.time() - start_time)
                    
        if current_time <= 0:
            cv2.imwrite(f"{path}/RS_Camera_{self.__device_name}_{self.__device_serial_number}_{self.__mode}/color/{counter}.png",
                        color_i)
            logging.info(f"[RS] Camera {self.__device_name} {self.__device_serial_number} color image {counter} saved successfully. Path = {path}/RS_Camera_{self.__device_name}_{self.__device_serial_number}_{self.__mode}/color/{counter}.png")
            
            cv2.imwrite(f"{path}/RS_Camera_{self.__device_name}_{self.__device_serial_number}_{self.__mode}/depth/{counter}.png",
                        depth_i)
            logging.info(f"[RS] Camera {self.__device_name} {self.__device_serial_number} depth image {counter} saved successfully. Path = {path}/RS_Camera_{self.__device_name}_{self.__device_serial_number}_{self.__mode}/depth/{counter}.png")
            
            np.save(f"{path}/RS_Camera_{self.__device_name}_{self.__device_serial_number}_{self.__mode}/depth_np/{counter}.npy",
                        depth_data_frame)
            logging.info(f"[RS] Camera {self.__device_name} {self.__device_serial_number} depth_np image {counter} saved successfully. Path = {path}/RS_Camera_{self.__device_name}_{self.__device_serial_number}_{self.__mode}/depth_np/{counter}.npy")

            start_time = time.time()
            counter += 1
        
        color_i = cv2.putText(color_i, f"Time: {int(current_time)}",
                    (20, 20), cv2.FONT_HERSHEY_COMPLEX_SMALL,
                    1, (0, 0, 0), 1)
        color_i = cv2.putText(color_i, f"Counter: {counter}",
                    (20, 40), cv2.FONT_HERSHEY_COMPLEX_SMALL,
                    1, (0, 0, 0), 1)
        
        return color_i, counter, start_time
    
    def get_serial_number(self) -> str:
        """Возвращает серийный номер устройства

        Returns:
            str: Серийный номер
        """
        return self.__device.get_info(rs.camera_info.serial_number)
    
    def get_profiles(self, sensor_id: int) -> list:
        """Получение профилей камеры по заданному сенсору

        Args:
            `sensor_id (int)`: ID сенсора. Можно получить воспользовавшись методом `CameraRS(device_id=0, mode="stream").get_sensors()`
            
        Returns:
            `list`: Список доступных профилей выбранного сенсора
        """
        assert isinstance(sensor_id, int)

        stream_profiles = []
        profiles = self.__device.sensors[sensor_id].get_stream_profiles()
        for i, profile in enumerate(profiles):
            video_profile = rs.video_stream_profile(profile)
            type_p = video_profile.stream_type()
            width, height = video_profile.width(), video_profile.height()
            fps = video_profile.fps()
            format_p = video_profile.format()

            stream_profiles.append(f"{i}. {type_p} {width}x{height} {format_p} {fps}")

        return stream_profiles
    
    def get_sensors(self) -> list:
        
        """Список сенсоров выбранного устройства

        Returns:
            `list`: Список сенсоров
        """
        
        sensors = []
        for i, sensor in enumerate(list(self.__device.query_sensors())):
            sensors.append(f"{i}. {sensor.get_info(rs.camera_info.name)}")

        return sensors
    
    def get_device_name(self) -> str:
        """Возвращает имя устройства

        Returns:
            str: Имя устройства
        """
        return self.__device.get_info(rs.camera_info.name)
    
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
            logging.error("[RS] The variable 'folder_name' and 'path' takes a string value")
            raise TypeError("[RS] The variable 'folder_name' and 'path' takes a string value")
        
        try:
            folder = f"{path}/{folder_name}"
            os.mkdir(folder)
            logging.info(f"[RS] Folder {folder.split('/')[-1]} created")
        except FileExistsError:
            logging.warning(f"[RS] It is not possible to create a folder '{folder_name}'. \
The folder has already been created")
    
    def release(self, writers=[]):
        """Обнуляем параметры камеры и уничтожаем имеющиеся окно предосмотра

        Args:
            show_gui (_type_): Имеется ли окно показа изображения.
            writers (list, optional): Список оберток cv2.VideoWriter. По умолчанию [].
        """
        
        cv2.destroyAllWindows()
        
        if self.__mode == "video":
            for writer in writers:
                writer.release()
            
        self.stop()
        logging.info(f"[CCTV] The camera with the index {self.__device_name} | {self.__device_serial_number} has shut down")
            
    def stop(self) -> None:
        """Вспомогательный метод для остановки потокового вещания камеры
        """
        self.__flag = False
        self.__pipeline.stop()
    
    def stream(self,
               color_profile: int, 
               depth_profile:int,
               img_count: int = 10,
               time_out: int = 5,
               path: str = "./",
               show_gui_color: bool = True,
               show_gui_depth: bool = True,
               barrier: Barrier = None,
               sender: Pipe = None):
        """Запуск потока видеозаписи видео/сохранения кадров/вывода

        Args:
            `color_profile (int)`: Цветовой профиль
            
            `depth_profile (int)`: Профиль глубины
            
            img_count (int, optional)`: Необходимое колличество изображений. Используется при режиме работы `frame`. По умолчанию `10`.
            
            `time_out (int, optional)`: Задержка перед сохранением кадра. Используется при режиме работы `frame`. По умолчанию `5`.
            
            `path (str, optional)`: Путь сохранения кадра или видео. Используется при режиме работы `frame` или `video`. По умолчанию `./`.
            
            `show_gui (bool, optional)`: Показ окна предварительного просмотра. По умолчанию `True`.
            
            `fps (int, optional)`: FPS записи для видеофайла. Используется при режиме работы `video`. По умолчанию `30`.
            
            `barier (Barrier)`: Барьер для синхронизации потоков. Используется в мультипроцесорности или многопоточности. По умолчанию None.
        """
        
        self.__flag = True
        
        # Конфигурирование камер
        depth_prof, color_prof = self._configuration_camera(color_profile=color_profile,
                                                             depth_profile=depth_profile)
        
        #  Создание папки для записи материалов
        if self.__mode == "video":
            self._create_folder(folder_name=f"RS_Camera_{self.__device_name}_{self.__device_serial_number}_{self.__mode}", 
                                path=path)
        elif self.__mode == "frame":
            self._create_folder(folder_name=f"RS_Camera_{self.__device_name}_{self.__device_serial_number}_{self.__mode}", 
                                path=path)
            self._create_folder(folder_name=f"RS_Camera_{self.__device_name}_{self.__device_serial_number}_{self.__mode}/color", 
                                path=path)
            self._create_folder(folder_name=f"RS_Camera_{self.__device_name}_{self.__device_serial_number}_{self.__mode}/depth", 
                                path=path)
            self._create_folder(folder_name=f"RS_Camera_{self.__device_name}_{self.__device_serial_number}_{self.__mode}/depth_np", 
                                path=path)
        
        # Настройка файлов записи видео материала
        depth_writer, color_writer = None, None
        if self.__mode == "video":
            depth_writer, color_writer = self._video_writer(path, depth_prof, color_prof)
        
        # Ожидание других потоков или процессов
        if barrier:
            barrier.wait()
        
        start_time = time.time()
        counter = 0
        logging.info(f"RS] The camera {self.__device_name} #{self.__device_serial_number} has started working in the '{self.__mode}' mode")
        
        while self.__flag:
            try:
                
                datetime_now = datetime.datetime.now()
                key = cv2.waitKey(1)
                
                # Предобработка кадров глубины и цвета
                frame = self.__pipeline.wait_for_frames()
                depth_f = frame.get_depth_frame()
                color_f = frame.get_color_frame()
                
                depth_data_frame = np.asanyarray(depth_f.get_data())
                # depth_i = cv2.applyColorMap(cv2.convertScaleAbs(depth_f, alpha=0.05), cv2.COLORMAP_JET)
                depth_i = np.asanyarray(self.__colorizer.colorize(depth_f).get_data())
                color_i = np.asanyarray(color_f.get_data())

                #  Сохранение кадра в файл
                if self.__mode == "frame":
                    color_i, counter, start_time = self._save_frame(start_time, time_out, 
                                                                    path, color_i, 
                                                                    depth_i, depth_data_frame, 
                                                                    counter)
                # Сохранение видео в файл
                elif self.__mode == "video":
                    color_i = cv2.putText(color_i, 
                                          f"{datetime_now.hour}:{datetime_now.minute}:{datetime_now.second}",
                                          (20, 20), cv2.FONT_HERSHEY_COMPLEX_SMALL,
                                          1, (0, 0, 255), 1)
                    
                    depth_writer.write(depth_i) 
                    color_writer.write(color_i)

                elif self.__mode == "centring":
                    color_i = self.__centring(color_i)
                
                self.__color_frame = color_i
                self.__depth_frame = depth_i

                if sender:
                    sender.send((color_i, depth_i))

                # Отображение окна предосмотра видео
                if show_gui_color:
                    cv2.imshow(f"{self.__device_name} | {self.__device_serial_number} color", color_i)
                    
                if show_gui_depth:
                    cv2.imshow(f"{self.__device_name} | {self.__device_serial_number} depth", depth_i)
                
                # Выход по нажатию клавиши Q или по вызову метода stop
                if key == ord('q') & 0xFF or not self.__flag:
                    logging.info("[RS] The recording was completed by pressing a key or calling the 'stop' method")
                    self.release(writers=[depth_writer, color_writer])
                
                # Выход при сохранении всех изображений
                if counter >= img_count:
                    logging.info("[RS] The recording has ended. All images have been successfully collected")
                    self.release(writers=[depth_writer, color_writer])
                
            except:
                logging.error(f"[RS] An unexpected error has occurred, the operation of the camera under the index {self.__device_name} #{self.__device_serial_number} is suspended")
                self.release(writers=[depth_writer, color_writer])