import customtkinter as ctk
from customtkinter import CTkImage
from serial.tools import list_ports
import cv2
from PIL import Image, ImageTk

from computer_vision.gameplay_recognition import list_ports as list_camera_ports

ctk.set_appearance_mode("system")


class CheckersGUI(ctk.CTk):
    """Main application window for the Checkers Robot Dobot Magician V2 GUI."""

    def __init__(self):
        super().__init__()
        self.title("Checkers Robot")
        self.geometry("500x500")
        self.minsize(300, 300)

        self.selected_camera_port = 0
        self.selected_robot_port = None

        self.frames: dict = {}

        for FrameClass in (PortSelectionPage, ConfigureCVColors):
            frame = FrameClass(self)
            self.frames[FrameClass] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.show_frame(PortSelectionPage)

    def show_frame(self, cont):
        """Bring the specified frame to the front."""
        frame = self.frames[cont]
        frame.tkraise()

    def set_robot_port(self, port):
        """Set selected robot port."""
        self.selected_robot_port = port

    def set_camera_port(self, port):
        """Set selected camera port."""
        self.selected_camera_port = port


class PortSelectionPage(ctk.CTkFrame):
    """Initial page for robot's configuration."""

    def __init__(self, parent, fg_color=None):
        super().__init__(parent)
        self.parent = parent

        self.grid_rowconfigure((0, 1, 2, 3, 4), weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.create_widgets()

    def create_widgets(self):
        """Create and place ComboBox widgets on the initial page."""

        robot_label = ctk.CTkLabel(self, text="Select Robot's port")
        robot_label.grid(row=0, column=0, padx=20, pady=(20, 0))

        self.robot_ports_list = list_ports.comports()
        robot_port_options = [port.device for port in self.robot_ports_list]

        robot_ports_combo = ctk.CTkComboBox(self, values=robot_port_options, command=self.robot_port_selected)
        robot_ports_combo.grid(row=1, column=0, padx=20, pady=10)

        camera_label = ctk.CTkLabel(self, text="Select camera's port")
        camera_label.grid(row=2, column=0, padx=20, pady=(20, 0))

        _, self.camera_ports_list = list_camera_ports()
        self.camera_port_options = [str(port) for port in self.camera_ports_list]

        camera_ports = ctk.CTkComboBox(self, values=self.camera_port_options, command=self.camera_port_selected)
        camera_ports.grid(row=3, column=0, padx=20, pady=10)

        next_button = ctk.CTkButton(self, text="Next", command=lambda: self.parent.show_frame(ConfigureCVColors))
        next_button.grid(row=4, column=0, padx=20, pady=(50, 5))

    def camera_port_selected(self, choice):
        """Pass the selected camera port to the main window."""
        self.parent.set_camera_port(int(choice))
        print(f"Selected camera's port: {choice}")

    def robot_port_selected(self, choice):
        """Pass the selected robot port to the main window."""
        self.parent.set_robot_port(choice)
        print(f"Selected robot's port: {choice}")


class ConfigureCVColors(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.parent.geometry("800x600")
        self.parent.resizable(False, False)

        self.grid_rowconfigure((0, 1, 2, 3, 4), weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.create_widgets()

        self.cap = cv2.VideoCapture(self.parent.selected_camera_port)
        self.current_frame = None

        self.update_video_frame()

    def create_widgets(self):
        self.video_label = ctk.CTkLabel(self, text="")
        self.video_label.grid(row=0, column=0, padx=20, pady=(20, 0))

        step_label = ctk.CTkLabel(self, text="Current step")
        step_label.grid(row=0, column=1, padx=20, pady=5, sticky="w")

        self.video_label.bind("<ButtonPress-1>", self.get_rgb_values_from_pixel)

    def update_video_frame(self):
        ret, frame = self.cap.read()
        if ret:
            self.current_frame = frame
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            imgCTk: CTkImage = ctk.CTkImage(light_image=Image.fromarray(frame), size=(self.cap.get(3), self.cap.get(4)))

            self.video_label.imgtk = imgCTk
            self.video_label.configure(image=imgCTk)

        self.after(10, func=self.update_video_frame)

    def get_rgb_values_from_pixel(self, event):
        if self.current_frame is not None:
            width = self.video_label.winfo_width()
            height = self.video_label.winfo_height()
            original_height, original_width, _ = self.current_frame.shape

            scale_x = original_width / width
            scale_y = original_height / height

            x = int(event.x * scale_x)
            y = int(event.y * scale_y)

            b, g, r = self.current_frame[y, x]
            print(f"Clicked pixel RGB values: ({r}, {g}, {b})")

    def on_closing(self):
        self.cap.release()

if __name__ == "__main__":
    app = CheckersGUI()
    app.mainloop()
