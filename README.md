# Ultrasound Data Preprocessing
Simple GUI for the pre-processing of ultrasound images acquired using
[Ultrasound Data Capture](https://github.com/rorybennett/Ultrasound-Data-Capture). As such, many assumptions
are made regarding the stored data format.

## Basic functions
The list of functions below are what the program is capable of. Sample dimensions are given for known
image cut sizes. This list is roughly the order in which a recording should be processed. The white box
at the bottom of the program shows any extra information related to the processing.

1. Select a recording: Browse for the folder containing frames of a recording (as .png files) with a data.txt file of IMU and
supplementary data. After the folder is selected, the frames will be loaded.
2. Vertical flip: If a perineal scan is loaded it will need to be flipped for consistency with transabdominal
depth measurements.
3. Show plot: Show a plot to help choose pixel limits (common limits are shown below in Clip Dimension Samples).
4. Clip ROI: Clip the region of interest based on pixel limits. Will also update data.txt file.
5. Duplicate check: Check for duplicates. If reduced ROI is selected only the area within the red lines will
be used to check for duplicate (this is fine if the frames of not been clipped).
6. Show duplicates: Show a list of the duplicates.
7. Remove duplicates: Remove the duplicate frame files and update the data.txt file.

## Clip Dimension Samples
The list below contains pixel dimensions that can be used for specific scan width and depths for either
transverse or sagittal scans. Order of pixel limits is [top, bottom, left, right].

### Transabdominal Scans

1. 110x170: 242, 878, 461, 1442
2. 130x190: 234, 878, 470, 1409
3. 140x210: 231, 878, 450, 1419
4. 150x220: 228, 878, 476, 1428
5. 160x200: 226, 878, 540, 1354
6. 170x240: 224, 878, 481, 1404
7. 180x200: 222, 878, 645, 1376 
8. 190x200: 220, 878, 658, 1350
9. 200x250: 218, 878, 569, 1393

### Perineal Scans

1. 110x170: 257, 893, 461, 1442
2. 120x170: 253, 893, 492, 1398
3. 130x190: 249, 893, 470, 1409
4. 170x240: 239, 893, 481, 1404