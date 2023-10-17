from multiprocessing import Process, Barrier, Pipe

from .RealSenseCamera import CameraRS

class RealSenseMultiProc(Process):

    def __init__(self, 
                 device_id: int, 
                 mode: str, 
                 color_profile: int, 
                 depth_profile: int,
                 img_count: int = 10,
                 time_out: int = 5,
                 path: str = "./",
                 show_gui_color: bool = True,
                 show_gui_depth: bool = True, 
                 barrier: Barrier = None,
                 sender: Pipe = None):
        
        super(RealSenseMultiProc, self).__init__()

        self.device_id = device_id
        self.mode = mode
        self.color_profile = color_profile
        self.depth_profile = depth_profile
        self.img_count = img_count
        self.time_out = time_out
        self.path = path
        self.show_gui_color = show_gui_color
        self.show_gui_depth = show_gui_depth
        self.barrier = barrier
        self.sender = sender

    def run(self):

        rs = CameraRS(self.device_id, self.mode)
        rs.stream(color_profile=self.color_profile, 
                  depth_profile=self.depth_profile,
                  img_count = self.img_count,
                  time_out = self.time_out,
                  path = self.path,
                  show_gui_color = self.show_gui_color,
                  show_gui_depth  = self.show_gui_depth,
                  barrier=self.barrier,
                  sender=self.sender)