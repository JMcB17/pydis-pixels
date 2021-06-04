import tkinter
import threading
import queue
import PIL.Image
import PIL.ImageTk


class GUICanvasDisplay:
    def __init__(self, canvas_size: dict, image_queue: queue.Queue, startup_barrier: threading.Barrier):
        self.image_queue = image_queue
        self.canvas_size = canvas_size
        w = self.canvas_size['width']
        h = self.canvas_size['height']

        self.root = tkinter.Tk()
        self.root.title('pydis-pixels')
        self.root.resizable(width=False, height=False)
        self.root.geometry(f'{w}x{h}')
        self.canvas = tkinter.Canvas(self.root, bg='#ffffff', width=w, height=h)
        self.canvas.pack()

        self.pil_tk_photo_image = PIL.ImageTk.PhotoImage('RGB', (w, h))
        self.canvas_image_id = self.canvas.create_image(
            (w/2, h/2), image=self.pil_tk_photo_image, state='normal'
        )

        self.root.bind('<<ImageUpdated>>', lambda event: self.process_image(event, self.image_queue.get()))

        startup_barrier.wait()

    # noinspection PyUnusedLocal
    def process_image(self, event: tkinter.Event, image_bytes: bytes):
        pil_image = PIL.Image.frombytes('RGB', (self.canvas_size['height'], self.canvas_size['height']), image_bytes)
        self.pil_tk_photo_image = PIL.ImageTk.PhotoImage(pil_image)
