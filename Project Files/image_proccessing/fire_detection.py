from PIL import Image
import numpy as np
#from skimage.future import graph
from skimage import io
from skimage.color import rgb2lab, deltaE_cie76, rgb2grey, label2rgb
#rom skimage.exposure import histogram
from skimage.measure import label, regionprops
#from skimage.morphology import binary_dilation, binary_opening, skeletonize, binary_erosion, binary_closing, disk, remove_small_objects

import time

# Helper function
def load_image_into_numpy_array(image):
    (im_width, im_height) = image.size
    return np.array(image.getdata()).reshape((im_height, im_width, 3)).astype(np.uint8)

''' Hamish's Image Processing Code :) '''

def run_fire_detection (image_np,print_output = False,console_print = False):

    '''

    This function works by taking the given input image and converting it from rgb to a more uniformly based colour system (deltaE_cie76) lab - cie
    Given the designated pixel value 'fire_pink' all values outside the 'threshold_fire' range of the color will be thresholded white.
    This thresholded image will then be segmented, all segments will be will be iterated over and total area, largest area and other metrics will calculated.
    All values will be returned, unless there are no valide detections, in which can null and zero values are returned.

    '''


    fire_values = {
        'exists': False,
        'ratio': 0.0,
        'region': None,
        'label_image': None,
        'labels': None,
        'combined_area': 0

    }

    ''' Fire Prediction Values'''

    low_thresh = 800 # If image segmentations are under this, they are not considered substantial enough
    high_thresh = 15000 # Total area is divided by this to give a ratio of fire presence

    # Array of rgb colors
    rgb = load_image_into_numpy_array(image_np)

    img = rgb

    lab = rgb2lab(rgb)

    # Color and threshold values
    fire_pink = [250,190,230]#[212,86,219]

    threshold_fire = 51

    #replace_colour = [[[0,0,0]]]
    replace_colour = [[[255,255,255]]]

    # Fire thresholding

    bobber_3d = np.uint8(np.asarray([[fire_pink]]))

    dE_bobber = deltaE_cie76(rgb2lab(bobber_3d), lab)

    rgb[dE_bobber > threshold_fire] = replace_colour

    # grey version
    grey = rgb2grey(rgb)

    # only black parts
    thres_img = np.empty_like(grey)
    thres_img[grey == 1] = 0
    thres_img[grey < 1] = 1

    # label parts
    label_image = label(thres_img,connectivity = 2,background = 0)

    image_label_overlay = label2rgb(label_image, image=img)


    # Region
    big_region = {"area" : 0, "bbox" : (0,0,0,0), "center" : (0,0)}
    combined_area = 0

    # Region/Label analysis
    for region in regionprops(label_image):
        # If not above low_thresh, don't count it (too insignificant)
        if region.area >= low_thresh:

            # region bounding box
            minr, minc, maxr, maxc = region.bbox
            bbox_ = [minc,minr,maxc,maxr]

            # center
            center = region.centroid

            # add to combined_area
            combined_area += region.area

            # get biggest area region
            if region.area > big_region["area"]:
                big_region["area"] = region.area
                big_region["bbox"] = bbox_
                big_region["center"] = center

    # --

    # Found Fire
    if big_region["area"] > 0:
        if console_print:
            print("-- Found Fire --")
        center = big_region["center"]
        if print_output:
            io.imsave("fd_output.jpg",image_label_overlay)# Visual representation of label regions
        fire_values['exists'] = True
        fire_values['region'] = big_region
        fire_values['labels'] = label_image
        fire_values['label_image'] = image_label_overlay
        fire_values['combined_area'] = combined_area

        # Calculate approx fire ratio
        fire_amount = combined_area#big_region["area"]
        fire_amount = fire_amount / high_thresh
        # Cap at 1.0
        if fire_amount > 1.0:
            fire_amount = 1.0
        fire_values['ratio'] = fire_amount

    # If no fire
    else:
        if console_print:
            print("-- No Fire --")
        fire_values['exists'] = False
    return fire_values
# --
