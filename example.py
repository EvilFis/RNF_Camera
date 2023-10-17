import multiprocessing

from RTSPCamera import Camera
from RealSenseCamera import CameraRS
from RealSenseMultiProc import RealSenseMultiProc

rtsp = Camera("rtsp://grant:QWERTYUIOP{}@192.168.18.25:554/cam/realmonitor?channel=1&subtype=1", "video")
rs = CameraRS(0, "centring")
rsL515 = CameraRS(1, "centring")


if __name__ == "__main__":
    barrier = multiprocessing.Barrier(3)

    print(CameraRS.get_devices_str())


    print(rsL515.get_device_name())
    print(rsL515.get_sensors())
    print()

    for profile_rgb in rsL515.get_profiles(1):
        print(profile_rgb)

    print()

    for profile_d in rsL515.get_profiles(0):
        print(profile_d)

    # rs.stream(97, 226)
    # rsL515.stream(89, 7)

    rtsp_proc = multiprocessing.Process(target=rtsp.stream, kwargs={
        "barrier": barrier
    }, name="RTSP")

    rs_proc = RealSenseMultiProc(
                                device_id=0, mode="video",
                                color_profile=97, depth_profile=226,
                                barrier=barrier
                                )
    
    rsl515_proc = RealSenseMultiProc(
                                    device_id=1, mode="video",
                                    color_profile=89, depth_profile=7,
                                    barrier=barrier 
                                    )
    

    rtsp_proc.start()
    rs_proc.start()
    rsl515_proc.start()
