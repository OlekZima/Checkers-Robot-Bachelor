import customtkinter as ctk
from tkinter import messagebox as tk_messagebox
from serial.tools import list_ports
import cv2
from PIL import Image
from serial.tools.list_ports_linux import SysFS
from src.computer_vision.gameplay_recognition import (
    list_camera_ports as list_camera_ports,
)

ctk.set_appearance_mode("system")


class CheckersGUI(ctk.CTk):
    """Main application window for the Checkers Robot Dobot Magician V2 GUI."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Checkers Robot")
        self.geometry("500x500")
        self.minsize(300, 300)

        self.frames = {}

        for FrameClass in (ColorSelectPage, PortSelectionPage, ConfigureCVColors):
            frame = FrameClass(self)
            self.frames[FrameClass] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.show_frame(ColorSelectPage)

    def show_frame(self, cont) -> None:
        """Bring the specified frame to the front."""
        frame = self.frames[cont]
        frame.tkraise()

    def set_robot_port(self, port) -> None:
        """Set selected robot port."""
        self.selected_robot_port = port

    def set_camera_port(self, port: int) -> None:
        """Set selected camera port."""
        self.selected_camera_port = port


class ColorSelectPage(ctk.CTkFrame):
    """Application page for selecting color of the player and robot"""

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.parent = parent

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure((0, 1), weight=1)

        self.create_widgets()

    def create_widgets(self) -> None:
        orange_button_image = ctk.CTkImage(
            Image.open("img/orange.png"), size=(100, 100)
        )
        blue_button_image = ctk.CTkImage(Image.open("img/blue.png"), size=(100, 100))

        instruction_label = ctk.CTkLabel(master=self, text="Select a robot color")
        instruction_label.grid(row=0, column=0, columnspan=2, pady=10)

        orange_button = ctk.CTkButton(
            master=self,
            image=orange_button_image,
            text="",
            command=self.select_orange_color,
        )
        orange_button.grid(row=1, column=0, sticky="")

        blue_button = ctk.CTkButton(
            master=self,
            image=blue_button_image,
            text="",
            command=self.select_blue_color,
        )
        blue_button.grid(row=1, column=1, sticky="")

        self.selected_color_label = ctk.CTkLabel(
            master=self, text="Selected Color for robot: None"
        )
        self.selected_color_label.grid(row=2, column=0, columnspan=2, pady=10)

        next_button = ctk.CTkButton(self, text="Next", command=self.select_next_page)
        next_button.grid(row=4, column=0, pady=(50, 5), sticky="s", columnspan=2)

    def select_next_page(self):
        if self.selected_color is None:
            tk_messagebox.showerror(
                title="Error!", message="You must select color before moving forward."
            )
        else:
            self.parent.show_frame(PortSelectionPage)

    def select_orange_color(self) -> None:
        self.selected_color = "Orange"
        self.update_selected_color_label()

    def select_blue_color(self) -> None:
        self.selected_color = "Blue"
        self.update_selected_color_label()

    def update_selected_color_label(self) -> None:
        """Updates the label with the selected color"""
        self.selected_color_label.configure(
            text=f"Selected Color: {self.selected_color}"
        )


class PortSelectionPage(ctk.CTkFrame):
    """Initial page for robot's configuration."""

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.parent = parent

        self.grid_rowconfigure((0, 1, 2, 3, 4), weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.create_widgets()

    def create_widgets(self) -> None:
        """Create and place ComboBox widgets on the initial page."""

        robot_label = ctk.CTkLabel(self, text="Select Robot's port")
        robot_label.grid(row=0, column=0, padx=20, pady=(20, 0))

        self.robot_ports_list: list[SysFS] = list_ports.comports()
        robot_port_options: list[str] = [port.device for port in self.robot_ports_list]

        robot_ports_combo = ctk.CTkComboBox(
            self, values=robot_port_options, command=self.robot_port_selected
        )
        robot_ports_combo.grid(row=1, column=0, padx=20, pady=10)

        camera_label = ctk.CTkLabel(self, text="Select camera's port")
        camera_label.grid(row=2, column=0, padx=20, pady=(20, 0))

        _, self.camera_ports_list = list_camera_ports()
        self.camera_port_options = [str(port) for port in self.camera_ports_list]

        camera_ports = ctk.CTkComboBox(
            self, values=self.camera_port_options, command=self.camera_port_selected
        )
        camera_ports.grid(row=3, column=0, padx=20, pady=10)

        next_button = ctk.CTkButton(
            self, text="Next", command=lambda: self.parent.show_frame(ConfigureCVColors)
        )
        next_button.grid(row=4, column=0, padx=20, pady=(50, 5))

    def camera_port_selected(self, choice) -> None:
        self.parent.set_camera_port(int(choice))
        print(f"Selected camera's port: {choice}")

    def robot_port_selected(self, choice) -> None:
        self.parent.set_robot_port(choice)
        print(f"Selected robot's port: {choice}")


class ConfigureCVColors(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.parent.geometry("800x600")
        self.parent.resizable(False, False)

        self.grid_rowconfigure((0, 1, 2, 3, 4), weight=1)
        self.grid_columnconfigure((0, 1), weight=1)

        self.steps = ["Select Orange", "Select Blue", "Select Dark", "Select White"]
        self.current_step = 0
        self.rgb_values = {}

        self.create_widgets()

        self.cap = cv2.VideoCapture(self.parent.selected_camera_port)
        self.current_frame = None

        self.update_video_frame()

    def create_widgets(self):
        self.video_label = ctk.CTkLabel(self, text="")
        self.video_label.pack()
        self.video_label.grid(row=0, column=0, padx=20, pady=(20, 0))

        self.step_label = ctk.CTkLabel(
            self, text=f"Current step: {self.steps[self.current_step]}"
        )
        self.step_label.grid(row=0, column=1, padx=20, pady=5, sticky="w")

        self.next_button = ctk.CTkButton(self, text="Next Step", command=self.next_step)
        self.next_button.grid(row=1, column=1, padx=20, pady=5)

        self.video_label.bind("<ButtonPress-1>", self.get_rgb_values_from_pixel)

    def update_video_frame(self):
        ret, frame = self.cap.read()
        if ret:
            self.current_frame = frame
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            imgCTk = ctk.CTkImage(
                light_image=Image.fromarray(frame),
                size=(int(self.cap.get(3)), int(self.cap.get(4))),
            )

            self.video_label.imgtk = imgCTk  # type: ignore
            self.video_label.configure(image=imgCTk)

        self.after(10, func=self.update_video_frame)

    def get_rgb_values_from_pixel(self, event):
        if self.current_frame is None:
            print("No current frame")
            return

        width: int = self.video_label.winfo_width()
        height = self.video_label.winfo_height()
        original_height, original_width, _ = self.current_frame.shape

        scale_x = original_width / width
        scale_y = original_height / height

        x = int(event.x * scale_x)
        y = int(event.y * scale_y)

        b, g, r = self.current_frame[y, x]
        self.rgb_values[self.steps[self.current_step]] = (r, g, b)
        print(
            f"Clicked pixel RGB values for {self.steps[self.current_step]}: ({r}, {g}, {b})"
        )

    def next_step(self):
        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self.step_label.configure(
                text=f"Current step\n{self.steps[self.current_step]}"
            )
        else:
            print("All steps completed!")
            print("Collected RGB values:", self.rgb_values)

        if len(self.rgb_values) == 4:
            print("All steps completed!")

    def on_closing(self):
        self.cap.release()


if __name__ == "__main__":
    app = CheckersGUI()
    app.mainloop()
