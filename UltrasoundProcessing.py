"""
User-interface for the pre-processing of ultrasound images. Contains all pre-processing functionality.

Any work done to images is done to the images stored on the disk, and not the images stored in memory. The
memory images are worked on, but permanent alterations are done to the disk images.
"""
import os
from datetime import timedelta
from pathlib import Path
import cv2
import numpy as np
from matplotlib import pyplot as plt
from natsort import natsorted
import PySimpleGUI as Psg
from skimage.metrics import structural_similarity

# Graph dimensions for display.
DISPLAY_DIMENSIONS = (800, 450)
# Default clipping to have a roi for scan depth 150mm, width 220mm, transverse-transabdominal.
CLIP_PIXELS = [228, 878, 476, 1428]


class UltrasoundProcessing:
    def __init__(self):
        """
        Initialise the user interface.
        """
        self.cwd = Path.cwd()
        self.recording_path = ''
        self.names = []
        self.frames = []
        self.data = []
        self.index = 0
        self.duplicates = []

        self.enable_operations = False
        self.temp_files = []

        layout = [
            [Psg.T('Select a recording')],
            [Psg.In(k='-INP-FILE-PATH-', expand_x=True, change_submits=True, disabled=True),
             Psg.FolderBrowse(initial_folder=str(self.cwd.parent.absolute()) + '/Generated/Videos')],
            [Psg.T(k='-TXT-DETAILS-', expand_x=True),
             Psg.T(k='-TXT-INDEX-', size=10, justification='r')],
            [Psg.HSep()],
            [Psg.G(k='-GRAPH-FRAME-', canvas_size=DISPLAY_DIMENSIONS, background_color='#000000',
                   pad=(0, 10), graph_bottom_left=(0, 0), graph_top_right=DISPLAY_DIMENSIONS,
                   enable_events=True)],
            [Psg.Col(element_justification='c', expand_y=True, layout=[
                [Psg.CB(k='-CB-REDUCED-ROI-', text='Reduced ROI', default=False, disabled=True)],
                [Psg.B(k='-BTN-DUPLICATE-CHECK-', size=18, button_text='Duplicate Check', expand_x=True)],
                [Psg.B(k='-BTN-SHOW-DUPLICATES-', button_text='Show Duplicates', disabled=True, expand_x=True)],
                [Psg.B(k='-BTN-REMOVE-DUPLICATES-', button_text='Remove Duplicates', disabled=True, expand_x=True)],
                [Psg.T(k='-TXT-DUPLICATE-COUNT-', text='Possible Duplicates: ___')],
                [Psg.T(k='-TXT-SCAN-STATUS-', justification='c', expand_x=True)]
            ]),
             Psg.Col(element_justification='c', expand_y=True, layout=[
                 [Psg.B(k='-BTN-FLIP-', size=18, button_text='Vertical Flip', expand_x=True)],
                 [Psg.Text(k='-TXT-ROTATED-', expand_x=True, justification='c')]
             ]),
             Psg.Col(element_justification='c', expand_y=True, layout=[
                 [Psg.B(k='-BTN-PLOT-', size=18, button_text='Show Plot', expand_x=True)],
                 [Psg.Col(element_justification='l', layout=[
                     [Psg.T(text='Top Px:')],
                     [Psg.T(text='Bottom Px:')],
                     [Psg.T(text='Left Px:')],
                     [Psg.T(text='Right Px:')]]),
                  Psg.Col(element_justification='r', layout=[
                      [Psg.I(k='-INP-TOP-', size=7, default_text=CLIP_PIXELS[0])],
                      [Psg.I(k='-INP-BOTTOM-', size=7, default_text=CLIP_PIXELS[1])],
                      [Psg.I(k='-INP-LEFT-', size=7, default_text=CLIP_PIXELS[2])],
                      [Psg.I(k='-INP-RIGHT-', size=7, default_text=CLIP_PIXELS[3])]])]
             ]),
             Psg.Col(element_justification='c', expand_y=True, layout=[
                 [Psg.B(k='-BTN-CLIP-', button_text='Clip ROI', expand_x=True)],
                 [Psg.CB(k='-CB-ENABLE-ROI-', text='Enable ROI', enable_events=True, default=True)]
             ]),
             Psg.Col(element_justification='c', expand_y=True, layout=[
                 [Psg.B(k='-BTN-DATA-', size=18, button_text='Update Data', expand_x=True)],
                 [Psg.Col(element_justification='l', layout=[
                     [Psg.T(text='Height mm:')],
                     [Psg.T(text='Width mm:')]
                 ]),
                  Psg.Col(element_justification='r', layout=[
                      [Psg.I(k='-INP-HEIGHT-', size=7, default_text=150)],
                      [Psg.I(k='-INP-WIDTH-', size=7, default_text=150)]
                  ])]
             ])],
            [Psg.Multiline(k='-TXT-INFO-', size=(0, 10), expand_x=True, disabled=True, autoscroll=True,
                           enable_events=False)]
        ]

        self.window = Psg.Window('Ultrasound Pre-Processing', layout=layout, location=(10, 10), finalize=True)
        self.window.bind('<Up>', '-NAV-UP-')
        self.window.bind('<Down>', '-NAV-DOWN-')
        self.window['-INP-TOP-'].bind('<Return>', '_Enter')
        self.window['-INP-BOTTOM-'].bind('<Return>', '_Enter')
        self.window['-INP-LEFT-'].bind('<Return>', '_Enter')
        self.window['-INP-RIGHT-'].bind('<Return>', '_Enter')

        while True:
            event, values = self.window.read()

            if event in (Psg.WIN_CLOSED, 'Exit'):
                break

            if event == '-INP-FILE-PATH-' and values[event]:
                self.load_frames(values[event])

            if event in ('-NAV-UP-', '-NAV-DOWN-') and self.enable_operations:
                self.navigate(event)

            if event == '-BTN-SHOW-DUPLICATES-' and len(self.duplicates) > 0 and self.enable_operations:
                self.show_duplicates()

            if event == '-BTN-DUPLICATE-CHECK-' and self.enable_operations:
                self.check_for_duplicates()

            if event == '-BTN-REMOVE-DUPLICATES-' and len(self.duplicates) > 0 and self.enable_operations:
                self.remove_duplicates()

            if event == '-BTN-FLIP-' and self.enable_operations:
                self.flip()

            if event == '-BTN-PLOT-' and self.enable_operations:
                self.show_plot()

            if event in ('-INP-TOP-' + '_Enter', '-INP-BOTTOM-' + '_Enter', '-INP-LEFT-' + '_Enter',
                         '-INP-RIGHT-' + '_Enter') and self.enable_operations:
                self.update_graph()

            if event == '-BTN-DATA-' and self.enable_operations:
                self.update_data_file()

            if event == '-BTN-CLIP-' and self.enable_operations:
                self.clip_frames()

            if event == '-CB-ENABLE-ROI-' and self.enable_operations:
                self.update_graph()

        self.window.close()

    def update_data_file(self):
        """
        Update the data.txt file with correct values (dimensions and depths).
        """
        self.window['-TXT-INFO-'].update(
            f"{self.window['-TXT-INFO-'].get()}\n"
            f'-----------------------------------------------------------------------------\n'
            f'                         Updating data.txt file\n'
            f'-----------------------------------------------------------------------------\n'
            f'    Dimensions: ({self.frames[0].shape[1]}, {self.frames[0].shape[0]}).\n'
            f"    Scan height: {self.window['-INP-HEIGHT-'].get()} mm, "
            f"Scan width: {self.window['-INP-WIDTH-'].get()} mm.")
        self.window.refresh()

        with open(self.recording_path + '/data.txt', 'r') as file:
            self.data = file.readlines()

        data_temp = []

        for row in self.data:
            values = row.split(',')
            values[11] = str(self.frames[0].shape[1])
            values[12] = str(self.frames[0].shape[0])
            values[13] = ']depths['
            values[14] = self.window['-INP-HEIGHT-'].get()
            values[15] = self.window['-INP-WIDTH-'].get()
            try:
                values[16] = ']'
            except IndexError:
                values.append(']')

            data_temp.append(values)

        self.data = data_temp

        with open(str(self.recording_path) + '/data.txt', 'w') as file:
            for row in self.data:
                file.write(f"{','.join(row)}\n")

        self.window['-TXT-INFO-'].update(
            f"{self.window['-TXT-INFO-'].get()}\n"
            f"    data.txt file updated.")

    def clip_frames(self):
        """
        Cut out the region of interest on all frames.
        """
        self.enable_operations = False
        if len(self.frames) > 0 and self.recording_path:
            self.window['-TXT-INFO-'].update(
                f"{self.window['-TXT-INFO-'].get()}\n"
                f'-----------------------------------------------------------------------------\n'
                f'                         Clipping {len(self.frames)} frames...\n'
                f'-----------------------------------------------------------------------------\n')
            self.window.refresh()

            try:
                top = int(self.window['-INP-TOP-'].get())
                bottom = int(self.window['-INP-BOTTOM-'].get())
                left = int(self.window['-INP-LEFT-'].get())
                right = int(self.window['-INP-RIGHT-'].get())

                self.window['-TXT-INFO-'].update(
                    f"{self.window['-TXT-INFO-'].get()}\n"
                    f"    Final shape will be: ({bottom - top}, {right - left})")
                self.window.refresh()

                # Clip the frames on disk.
                for index, frame in enumerate(self.names):
                    img = cv2.imread(self.recording_path + '/' + frame, cv2.IMREAD_UNCHANGED)

                    clipped_frame = img[top:bottom, left:right]

                    cv2.imwrite(self.recording_path + '/' + frame, clipped_frame)

                self.window['-TXT-INFO-'].update(
                    f"{self.window['-TXT-INFO-'].get()}\n"
                    f'    Finished clipping {len(self.names)} frames to ({bottom - top}, {right - left}).')
                self.window.refresh()

                self.load_frames(self.recording_path)

                self.update_data_file()
            except (Exception,):
                self.window['-TXT-INFO-'].update(
                    f"{self.window['-TXT-INFO-'].get()}\nAn error occurred, ensure 'ints' are entered.")

        self.enable_operations = True

    def draw_roi_lines(self, frame):
        """
        Draw region of interest lines onto frame in memory.
        """
        top = self.window['-INP-TOP-'].get()
        bottom = self.window['-INP-BOTTOM-'].get()
        left = self.window['-INP-LEFT-'].get()
        right = self.window['-INP-RIGHT-'].get()

        try:
            top = int(top)
            cv2.line(frame, (0, top), (frame.shape[1], top), color=(0, 0, 255), thickness=1)
        except (Exception,):
            self.window['-TXT-INFO-'].update(f"{self.window['-TXT-INFO-'].get()}\nTop is not an 'int'")

        try:
            bottom = int(bottom)
            cv2.line(frame, (0, bottom), (frame.shape[1], bottom), color=(0, 0, 255), thickness=1)
        except (Exception,):
            self.window['-TXT-INFO-'].update(f"{self.window['-TXT-INFO-'].get()}\nBottom is not an 'int'")

        try:
            left = int(left)
            cv2.line(frame, (left, 0), (left, frame.shape[0]), color=(0, 0, 255), thickness=1)
        except (Exception,):
            self.window['-TXT-INFO-'].update(f"{self.window['-TXT-INFO-'].get()}\nTop is not an 'int'")

        try:
            right = int(right)
            cv2.line(frame, (right, 0), (right, frame.shape[0]), color=(0, 0, 255), thickness=1)
        except (Exception,):
            self.window['-TXT-INFO-'].update(f"{self.window['-TXT-INFO-'].get()}\nTop is not an 'int'")

    def show_plot(self):
        """
        Show the current frame in a plot window. Used to find cut dimensions.
        """
        fig, ax = plt.subplots(figsize=(16, 9), dpi=80)
        display_frame = self.frames[self.index].copy()
        self.draw_roi_lines(display_frame)
        ax.imshow(display_frame)
        plt.show()

    def flip(self):
        """
        Flip all frames vertically.
        """
        self.enable_operations = False
        if len(self.names) > 0:
            self.window['-TXT-ROTATED-'].update(f'Flipping {len(self.names)} frames\n')
            self.window.refresh()

            for index, name in enumerate(self.names):
                img = cv2.imread(self.recording_path + '/' + name, cv2.IMREAD_UNCHANGED)

                flipped_frame = cv2.flip(img, 0)

                cv2.imwrite(self.recording_path + '/' + name, flipped_frame)

            self.window['-TXT-ROTATED-'].update(f'Flipped {len(self.names)} frames.')
            self.window.refresh()

            self.load_frames(self.recording_path)
        else:
            self.window['-TXT-INFO-'].update(
                f"{self.window['-TXT-INFO-'].get()}\n"
                f'    No frames to flip.')

        self.enable_operations = True

    def remove_duplicates(self):
        """
        Remove duplicate frames.
        """
        self.enable_operations = False
        self.window['-TXT-SCAN-STATUS-'].update('Removing Duplicates...')
        self.window['-BTN-REMOVE-DUPLICATES-'].update(disabled=True)
        self.window['-TXT-INFO-'].update(
            f"{self.window['-TXT-INFO-'].get()}\n"
            f'-----------------------------------------------------------------------------\n'
            f'                           Deleting Duplicates\n'
            f'-----------------------------------------------------------------------------\n')
        self.window.refresh()

        # Remove duplicate .png and IMU data.
        if len(self.duplicates) > 0:
            for duplicate in self.duplicates:
                remove_path = Path(self.recording_path, duplicate[1])

                for row in self.data:
                    if row.split(',', 1)[0] == duplicate[1].split('.', 1)[0]:
                        self.window['-TXT-INFO-'].update(f"{self.window['-TXT-INFO-'].get()}\n"
                                                         f'    Deleting: {remove_path.name}')
                        self.window.refresh()

                        # Delete .png frame.
                        os.remove(remove_path)
                        # Delete corresponding row.
                        self.data.remove(row)
                        break
            # Rename files for consistency.
            self.names = [x for x in natsorted(os.listdir(self.recording_path)) if x.split('.')[-1] == 'png']
            i = 1
            for name in self.names:
                new_name = f"{i}-{name.split('-', 1)[1]}"
                os.rename(Path(self.recording_path, name), Path(self.recording_path, new_name))
                i += 1
            with open(str(self.recording_path) + '/data.txt', 'w') as file:
                i = 1
                for row in self.data:
                    file.write(f"{i}-{row.split('-', 1)[1]}")
                    i += 1

        self.window['-TXT-SCAN-STATUS-'].update('Duplicates Removed.')
        self.enable_operations = True
        self.load_frames(self.recording_path)

    def show_duplicates(self):
        """
        Show duplicates.
        """
        self.window['-TXT-INFO-'].update(
            f"{self.window['-TXT-INFO-'].get()}\n"
            f'-----------------------------------------------------------------------------\n'
            f'                            Duplicate Frames\n'
            f'-----------------------------------------------------------------------------\n')
        for line in self.duplicates:
            self.window['-TXT-INFO-'].update(f"{self.window['-TXT-INFO-'].get()}\n"
                                             f"    {line[0]}  ->  {line[1]}\n")

    def check_for_duplicates(self, window=2):
        """
        Compares each frame with the next 'window' frames. If reduced ROI is selected, only the ROI is used in the comparison of images. This should increase
        comparison speed substantially as a lost of the image is not of interest.
        """
        self.enable_operations = False

        top = int(self.window['-INP-TOP-'].get())
        bottom = int(self.window['-INP-BOTTOM-'].get())
        left = int(self.window['-INP-LEFT-'].get())
        right = int(self.window['-INP-RIGHT-'].get())

        self.window['-TXT-INFO-'].update(
            f"{self.window['-TXT-INFO-'].get()}\n"
            f'-----------------------------------------------------------------------------\n'
            f'                         Starting Duplicate Scan\n'
            f'-----------------------------------------------------------------------------\n')
        self.window['-TXT-DUPLICATE-COUNT-'].update(f'Possible Duplicates: ___')

        with open(self.recording_path + '/data.txt', 'r') as file:
            self.data = file.readlines()

        total_files = len([x for x in os.listdir(self.recording_path)])

        self.window['-TXT-INFO-'].update(f"{self.window['-TXT-INFO-'].get()}\n"
                                         f'    Total files in directory: {total_files}.\n'
                                         f'    Total .png frames in directory: {len(self.frames)}.\n')

        self.duplicates = []  # Reset duplicates.

        for i in range(0, len(self.frames) - 1):
            img1 = cv2.cvtColor(self.frames[i], cv2.COLOR_BGR2GRAY)  # First image
            if self.window['-CB-REDUCED-ROI-'].get():
                img1 = img1[top:bottom, left:right]
            for j in range(i + 1, i + window + 1):
                if j < len(self.names):
                    img2 = cv2.cvtColor(self.frames[j], cv2.COLOR_BGR2GRAY)  # Second image
                    if self.window['-CB-REDUCED-ROI-'].get():
                        img2 = img2[top:bottom, left:right]

                    self.window['-TXT-SCAN-STATUS-'].update(f"Comparing {self.names[i].split('-', 1)[0]} "
                                                            f"to {self.names[j].split('-', 1)[0]}")

                    score = structural_similarity(img1, img2)  # Compare images
                    if score == 1:  # 100% match.
                        self.duplicates.append([self.names[i], self.names[j]])

                        self.window['-TXT-DUPLICATE-COUNT-'].update(
                            f'Possible Duplicates: {len(np.unique(np.array(self.duplicates)[:, 0]))}')
                        # Once a duplicate is found, we can move on to the next set of images.
                        break

                self.window.refresh()

        if len(self.duplicates) > 0:
            self.window['-BTN-REMOVE-DUPLICATES-'].update(disabled=False)
            self.window['-BTN-SHOW-DUPLICATES-'].update(disabled=False)
        else:
            self.window['-BTN-REMOVE-DUPLICATES-'].update(disabled=True)
            self.window['-BTN-SHOW-DUPLICATES-'].update(disabled=True)
            self.window['-TXT-DUPLICATE-COUNT-'].update(f'Possible Duplicates: 0')

        self.window['-TXT-SCAN-STATUS-'].update(f'Scan Complete ({len(self.frames)}/{len(self.frames)})')

        self.window['-TXT-INFO-'].update(f"{self.window['-TXT-INFO-'].get()}\n"
                                         f"    Total duplicates detected: {len(self.duplicates)}.\n")

        self.enable_operations = True

    def load_frames(self, path):
        """
        Load all frames in path folder into memory.
        """
        self.window['-TXT-INFO-'].update(
            f"{self.window['-TXT-INFO-'].get()}\n"
            f'-----------------------------------------------------------------------------\n'
            f'                         Loading Frames\n'
            f'-----------------------------------------------------------------------------\n')
        self.window.refresh()

        self.recording_path = path
        self.names = [x for x in natsorted(os.listdir(self.recording_path)) if x.split('.')[-1] == 'png']
        self.frames = []
        self.data = []
        self.index = 0
        self.duplicates = []

        for name in self.names:
            frame = cv2.imread(path + '/' + name, cv2.IMREAD_UNCHANGED)
            cf = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
            self.frames.append(cf)

        duration = int(self.names[-1].split('.', 1)[0].split('-', 1)[1]) - int(
            self.names[0].split('.', 1)[0].split('-', 1)[1])

        self.window['-TXT-DETAILS-'].update(
            f"Total Frames: {len(self.frames)}\t\t"
            f"Duration: {str(timedelta(milliseconds=duration)).split('.', 1)[0]}s\t\t"
            f"FPS: {int(len(self.frames) * 1000 / duration)}\t\t"
            f"Shape: {cv2.imread(self.recording_path + '/' + self.names[0], cv2.IMREAD_UNCHANGED).shape}")
        self.window['-BTN-REMOVE-DUPLICATES-'].update(disabled=True)
        self.window['-BTN-SHOW-DUPLICATES-'].update(disabled=True)
        self.window['-CB-REDUCED-ROI-'].update(disabled=False)

        self.window['-TXT-INFO-'].update(
            f"{self.window['-TXT-INFO-'].get()}\n"
            f'                         Frames Loaded\n'
            f'-----------------------------------------------------------------------------\n')

        self.enable_operations = True
        self.update_graph()

    def navigate(self, command: str):
        """
        Navigate frames one at a time.
        """
        if command == '-NAV-DOWN-':
            self.index -= 1
        elif command == '-NAV-UP-':
            self.index += 1
        # Loop round if limits reached
        if self.index < 0:
            self.index = len(self.frames) + self.index
        elif self.index > len(self.frames) - 1:
            self.index = self.index - len(self.frames)

        self.update_graph()

    def update_graph(self):
        """
        Update Graph element.
        """
        self.window['-GRAPH-FRAME-'].erase()  # Prevents a memory leak

        display_frame = self.frames[self.index].copy()

        if self.window['-CB-ENABLE-ROI-'].get():
            self.draw_roi_lines(display_frame)

        display_frame = cv2.resize(display_frame, DISPLAY_DIMENSIONS, interpolation=cv2.INTER_AREA)
        self.window['-GRAPH-FRAME-'].draw_image(data=cv2.imencode(".png", display_frame)[1].tobytes(),
                                                location=(0, DISPLAY_DIMENSIONS[1]))

        self.window['-TXT-INDEX-'].update(f'{self.index + 1}/{len(self.frames)}')
        self.window.refresh()


if __name__ == '__main__':
    UltrasoundProcessing()
