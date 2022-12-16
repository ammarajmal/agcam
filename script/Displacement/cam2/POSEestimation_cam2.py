'''
Sample Usage:-
python3 POSEestimation_cam2.py --K_Matrix calibration_matrix.npy --D_Coeff distortion_coefficients.npy --type DICT_5X5_100
'''
marker_size = 0.053 # in meters
distance_from_marker = 0.88 # in meters

import sys
import math
import time
import argparse
import numpy as np
import pandas as pd
import openpyxl
import cv2.aruco as aruco
import cv2
import mvsdk
import xlrd
from utils import ARUCO_DICT, aruco_dimensions


# Checks if a matrix is a valid rotation matrix.
def isRotationMatrix(R) :
    Rt = np.transpose(R)
    shouldBeIdentity = np.dot(Rt, R)
    I = np.identity(3, dtype = R.dtype)
    n = np.linalg.norm(I - shouldBeIdentity)
    return n < 1e-6

# Calculates rotation matrix to euler angles
# The result is the same as MATLAB except the order
# of the euler angles ( x and z are swapped ).
def rotationMatrixToEulerAngles(R):
    assert(isRotationMatrix(R))
    sy = math.sqrt(R[0,0] * R[0,0] +  R[1,0] * R[1,0])
    singular = sy < 1e-6
    if  not singular:
        x = math.atan2(R[2,1] , R[2,2])
        y = math.atan2(-R[2,0], sy)
        z = math.atan2(R[1,0], R[0,0])
    else :
        x = math.atan2(-R[1,2], R[1,1])
        y = math.atan2(-R[2,0], sy)
        z = 0
    return np.array([x, y, z])


def pose_esitmation(frame, aruco_dict_type, matrix_coefficients, distortion_coefficients):

    '''
    frame - Frame from the video stream
    matrix_coefficients - Intrinsic matrix of the calibrated camera
    distortion_coefficients - Distortion coefficients associated with your camera

    return:-
    frame - The frame with the axis drawn on it
    '''

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    cv2.aruco_dict = cv2.aruco.Dictionary_get(aruco_dict_type)
    parameters = cv2.aruco.DetectorParameters_create()


    corners, ids, rejected_img_points = cv2.aruco.detectMarkers(gray, cv2.aruco_dict,parameters=parameters,
        cameraMatrix=matrix_coefficients,
        distCoeff=distortion_coefficients)
    # detected_markers = aruco_display(corners, ids, rejected, frame)

        # If markers are detected
    if len(corners) > 0:
        for i in range(0, len(ids)):
            # Estimate pose of marker and show the pose of the marker along with the distance from the camera
            rvec_list, tvec_list, markerPoints = cv2.aruco.estimatePoseSingleMarkers(corners[i], 0.053, matrix_coefficients, distortion_coefficients)
            cv2.putText(frame, f"Distance: {tvec_list[0][0][2]:.2f}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            rvec = rvec_list[0][0]
            tvec = tvec_list[0][0]
            # print("rvec_list: ", rvec)
            # print("tvec_list: ", tvec)
            
            aruco.drawAxis(frame, matrix_coefficients, distortion_coefficients, rvec, tvec, 0.05)
            
            rvec_flipped = rvec * -1
            tvec_flipped = tvec * -1
            
            rotation_matrix, jacobian = cv2.Rodrigues(rvec_flipped)
            realworld_tvec = np.dot(rotation_matrix, tvec_flipped)
            
            pitch, roll, yaw = rotationMatrixToEulerAngles(rotation_matrix)
            
            return True, frame, realworld_tvec, pitch, roll, yaw
    return False, frame, None, None, None, None
# def write_to_excel(tvec_str, rvec_str):
#                 # function to write tvec and rvec to excel file
                
#                 # Create a Pandas dataframe from the data.
#                 # write tvec_str to excel file
#                 # write rvec_str to excel file
#                 df_tvec = pd.DataFrame({'X': [realworld_tvec[0]], 'Y': [realworld_tvec[1]], 'Z': [realworld_tvec[2]], 'roll': [math.degrees(roll)], 'pitch': [math.degrees(pitch)], 'yaw': [math.degrees(yaw)]})
#                 df_rvec = pd.DataFrame({'roll': [math.degrees(roll)], 'pitch': [math.degrees(pitch)], 'yaw': [math.degrees(yaw)]})
                
                                
#                 # Create a Pandas Excel writer using XlsxWriter as the engine.
#                 writer = pd.ExcelWriter('Pose_Cam3.xlsx', engine='xlsxwriter')
                
#                 # Convert the dataframe to an XlsxWriter Excel object.
#                 df_tvec.to_excel(writer, sheet_name='Sheet1', index=False)
#                 df_rvec.to_excel(writer, sheet_name='Sheet2', index=False)
                
#                 # Close the Pandas Excel writer and output the Excel file.
#                 writer.save()
            
if __name__ == '__main__':

    ap = argparse.ArgumentParser()
    ap.add_argument("-k", "--K_Matrix", required=True, help="Path to calibration matrix (numpy file)")
    ap.add_argument("-d", "--D_Coeff", required=True, help="Path to distortion coefficients (numpy file)")
    ap.add_argument("-t", "--type", type=str, default="DICT_ARUCO_ORIGINAL", help="Type of ArUCo tag to detect")
    args = vars(ap.parse_args())

    
    if ARUCO_DICT.get(args["type"], None) is None:
        print(f"ArUCo tag type '{args['type']}' is not supported")
        sys.exit(0)

    aruco_dict_type = ARUCO_DICT[args["type"]]
    calibration_matrix_path = args["K_Matrix"]
    distortion_coefficients_path = args["D_Coeff"]
    
    k = np.load(calibration_matrix_path)
    d = np.load(distortion_coefficients_path)

    video = cv2.VideoCapture(0)
    time.sleep(2.0)
    DevList = mvsdk.CameraEnumerateDevice()
    nDev = len(DevList)
    cal_image_count = 0
    if nDev < 1:
        print("No camera was found!")
    for i, DevInfo in enumerate(DevList):
        print("{}: {} {}".format(i, DevInfo.GetFriendlyName(), DevInfo.GetPortType()))
    i = 0 if nDev == 1 else int(input("Select camera: "))
    DevInfo = DevList[i]
    print(DevInfo)
    
    # Turn on the camera
    hCamera = 0
    try:
        hCamera = mvsdk.CameraInit(DevInfo, -1, -1)
    except mvsdk.CameraException as myexcept:
        print("CameraInit Failed({}): {}".format(myexcept.error_code, myexcept.message) )
    # Get camera feature description
    cap = mvsdk.CameraGetCapability(hCamera)
    
    # Determine whether it is a black and white camera or a color camera
    monoCamera = (cap.sIspCapacity.bMonoSensor != 0)

    # Monochrome camera allows ISP to directly output MONO data 
    # instead of expanding to 24-bit grayscale with R=G=B
    if monoCamera:
        mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_MONO8)
    else:
        mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_BGR8)

    # Camera mode switched to continuous acquisition
    mvsdk.CameraSetTriggerMode(hCamera, 0)

    # Manual exposure, exposure time 30ms
    mvsdk.CameraSetAeState(hCamera, 0)
    mvsdk.CameraSetExposureTime(hCamera, 7 * 1000)

    # Let the SDK internal image fetching thread start to work
    mvsdk.CameraPlay(hCamera)

    # Calculate the required size of the RGB buffer, 
    # which is directly allocated according to the maximum resolution of the camera
    FrameBufferSize = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * (1 if monoCamera else 3)

	# Allocate RGB buffer to store the image output by ISP
	
 	# Remarks: RAW data is transmitted from the camera to the PC, 
 	# which is converted to RGB data by the software ISP on the PC 
	# (if it is a black and white camera, there is no need to convert the format,
	# but the ISP has other processing, so this buffer also needs to be allocated)
    pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)
    pTime = time.time()
    while True:
        try:
            pRawData, FrameHead = mvsdk.CameraGetImageBuffer(hCamera, 200)
            mvsdk.CameraImageProcess(hCamera, pRawData, pFrameBuffer, FrameHead)
            mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)
        
            # Convert the data to OpenCV format
            frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(pFrameBuffer)
            frame = np.frombuffer(frame_data, dtype=np.uint8)
            frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth, 1 if monoCamera else 3))
            frame = cv2.resize(frame, (1280,720), interpolation = cv2.INTER_LINEAR)
            realworld_tvec, roll, pitch, yaw = 0, 0, 0, 0
            
            
            flag, output, realworld_tvec, roll, pitch, yaw = pose_esitmation(frame, aruco_dict_type, k, d)
            if flag:
                    tvec_str = f"X: {realworld_tvec[0]:.2f}, Y: {realworld_tvec[1]:.2f}, Z: {realworld_tvec[2]:.2f}"
                    rvec_str = f"roll: {math.degrees(roll):.2f}, pitch: {math.degrees(pitch):.2f}, yaw: {math.degrees(yaw):.2f}"
                    # write_to_excel(tvec_str, rvec_str)
                    tvec_text = f"{realworld_tvec[0]:.2f},{realworld_tvec[1]:.2f},{realworld_tvec[2]:.2f}"
                    with open('PoseCam2.txt', 'a+') as f:
                        f.write(tvec_text)
                        f.write('\n')
                            
                    cv2.putText(frame, tvec_str, (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                    cv2.putText(frame, rvec_str, (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                        
            
            cTime = time.time()
            fps = 1/(cTime-pTime)
            pTime = cTime
            
            cv2.putText(output, f'FPS: {int(fps)}', (20, 50), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)
            cv2.imshow("Cam2 Pose", output)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
        except mvsdk.CameraException as e:
            print("CameraGetImageBuffer failed({}): {}".format(e.error_code, e.message))
            break
    mvsdk.CameraUnInit(hCamera)
    mvsdk.CameraAlignFree(pFrameBuffer)
        

        
    
