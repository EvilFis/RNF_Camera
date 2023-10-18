import cv2
import random
from multiprocessing import Process, Barrier, Pipe

from Calibration.utils import find_calibration_template


def preview_cameras(barrier: Barrier, *args) -> None:
    """Предпросмотр кадров с камер. Функция используется при мультипроцесрной работе камер

    Args:
        `barrier` (Barrier): Ожидание других потоковых операций
        
        `*args` (Pipe): Информация с других камер типа `Pipe`
    """

    barrier.wait()

    while True:
        key = cv2.waitKey(1)

        for i, reciver in enumerate(args):
            frame = reciver.recv()
            frame_c = frame[0]

            cv2.imshow(f"Camera color {i}", frame_c)

            if len(frame) == 2:
                cv2.imshow(f"Camera depth {i}", frame[1])
        
        if key == ord('q') & 0xFF:
            cv2.destroyAllWindows()
            break
        

def preview_cameras_template_calibration(barrier: Barrier, reciver: Pipe, type: str, size: tuple, name_window: str) -> None:

    if not name_window:
        name_window = random.random()

    barrier.wait()

    while True:
        key = cv2.waitKey(1)
            
        frame = reciver.recv()

        frame_chessboard = find_calibration_template(frame[0], type=type, size=size)

        cv2.imshow(name_window, frame_chessboard)

        if key == ord('q') & 0xFF:
            cv2.destroyAllWindows()
            break