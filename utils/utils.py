import cv2
from multiprocessing import Process, Barrier, Pipe


def preview_cameras(barrier: Barrier, *args):
    print(args)

    barrier.wait()

    while True:
        key = cv2.waitKey(1)

        for i, reciver in enumerate(args):
            frame = reciver.recv()

            cv2.imshow(f"Camera color {i}", frame[0])

            if len(frame) == 2:
                cv2.imshow(f"Camera depth {i}", frame[1])

        
        if key == ord('q') & 0xFF:
                cv2.destroyAllWindows()
                break