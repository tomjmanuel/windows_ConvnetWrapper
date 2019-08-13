##########################################################################
#
# GUI allowing inspection and manual thresholding of Convnet ROIs
# based on average probability (from Convnet output) inside each ROI
#
# Author: Noah Apthorpe (revised by Tom Manuel)
#
# Usage: python visualize.py <configuration filepath> <path to image with associated rois

# python visualizeTom.py ..\data\Try3\main_config.cfg data31_postprocessed\data31.tif
#
###########################################################################


import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure
import sys
import os
import os.path
from Tkinter import *
from collections import defaultdict
import numpy as np
import ConfigParser
from preprocess import add_pathsep, is_labeled
from load import load_stack, load_rois
from skimage import io


class App:
    '''Tkinter GUI application'''
    
    def __init__(self, root, fname, img_width, img_height):
        self.fname = fname
        self.root = root
        self.rname = self.fname[0:-4]+ 'dF.npz'
        self.img_width, self.img_height = img_width, img_height
        self.manual_thresh = StringVar()
        self.just_set_thresh = False
        self.manual_thresh.trace("w", self.manual_thresh_change)
        self.image = self.getIm()
        #self.image = load_stack(self.fname)
        self.convnet_rois = np.load(self.rname)['rois']
        self.convnet_roi_probs = np.load(self.rname)['roi_probabilities']
        self.roi_index = self.convnet_rois.shape[0]
        self.indexed_roi_probs = sorted([(v,i) for i,v in enumerate(self.convnet_roi_probs)], reverse=True)
        self.image_index = 10
        self.make_widgets(root, img_width, img_height)
        self.draw_canvas()
        
    def getIm(self):
        im = io.imread(self.fname)
        im = np.divide(im,np.mean(im))
        return im

    def make_widgets(self, root, img_width, img_height):
        # enclosing frame
        frame = Frame(root)
        frame.grid(padx=10, pady=10)

        # canvas
        self.f = Figure(figsize=(img_width/100.0, img_height/100.0), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.f, master=frame)
        self.canvas.show()
        self.canvas.get_tk_widget().grid(column=0, row=1, rowspan=5)

        # other widgets
        self.filename_label = Label(frame, text="Filename")
        self.filename_label.grid(column=0, row=0)
        self.roi_slider = Scale(frame, from_=self.convnet_rois.shape[0]-1, to=0, orient=VERTICAL, length=400, command=self.roi_slider_change)
        self.roi_slider.grid(column=1, row=1, rowspan=4, padx=25)        
        self.image_slider = Scale(frame, from_=0, to=self.image.shape[0]-1, orient=HORIZONTAL, length=400, command=self.image_slider_change)
        self.image_slider.grid(column=0, row=6)
        self.save_button = Button(frame, text="Save Displayed ROIs", command=self.save_button_press)
        self.save_button.grid(column=2, columnspan=2, row=3)
        prev_next_frame = Frame(frame)
        prev_next_frame.grid(column=2, columnspan=2, row=4)




    def draw_canvas(self):
        '''draw current image and selected ROIs'''
        self.f.clf()
        frame = Frame(self.root)
        frame.grid(padx=10, pady=10)
        self.image_slider = Scale(frame, from_=0, to=self.image.shape[0]-1, orient=HORIZONTAL, length=400, command=self.image_slider_change)
        overlay = np.zeros((self.image.shape[1], self.image.shape[2], 3))
        overlay[:,:,0] = self.image[self.image_index,:,:]
        overlay[:,:,1] = self.image[self.image_index,:,:]
        overlay[:,:,2] = self.image[self.image_index,:,:]

        current_roi_indices = [i for (v,i) in self.indexed_roi_probs[0:self.roi_index]]
        if len(current_roi_indices) > 0:
            print(self.roi_index-1)
            cutoff = self.indexed_roi_probs[self.roi_index-1][0]
            current_rois_mask = self.convnet_rois[current_roi_indices].max(axis=0)
            overlay[:,:,2][current_rois_mask == 1] = 1    
        else:
            cutoff = self.indexed_roi_probs[0][0]
       
        self.f.figimage(overlay)
        self.canvas.draw()

            
    def roi_slider_change(self, value):
        '''callback for threshold value slider''' 
        self.roi_index = int(value)
        if self.manual_thresh.get() != "" and not self.just_set_thresh:
            self.manual_thresh.set("")
        self.just_set_thresh = False
        self.draw_canvas()

        
    def image_slider_change(self, value):
        '''callback for image sequence slider'''
        self.image_index = int(value)
        self.draw_canvas()
        
        
    def save_button_press(self):
        '''callback to save currently selected ROIs'''
        current_roi_indices = [i for (v,i) in self.indexed_roi_probs[0:self.roi_index]]
        current_rois = self.convnet_rois[current_roi_indices]
        new_file = self.fname[0:-4] + "_ROIsManual.csv"
        self.saveROIsAsCSV(current_rois, new_file)
        #np.savez_compressed(new_file, rois=current_rois)
        print "saved as " + new_file
        
    def saveROIsAsCSV(self,rois,fname):
        dim = rois.shape
        outArr = np.zeros([dim[0],4]) #minX, minY, maxX, maxY
        for x in range(dim[0]):
            #make a 1d array that sums elements across the first dim
            temp1 = np.sum(rois[x,:,:], axis=0) #dim 1
            temp2 = np.sum(rois[x,:,:], axis=1) #dim 2

            #now find the first and last nonzero elements in these 1ds
            temp1nz = np.nonzero(temp1)
            temp2nz = np.nonzero(temp2)

            outArr[x,:] = [temp1nz[0][0],temp2nz[0][0],temp1nz[-1][-1],temp2nz[-1][-1]]
        np.savetxt(fname,outArr,delimiter=',',fmt='%i')
        
    def manual_thresh_change(self, *args):
        '''callback for manual thresholsd entry'''
        if self.manual_thresh.get().strip() != "":
            new_index = self.convnet_rois.shape[0]
            for j,(p,ind) in enumerate(self.indexed_roi_probs):
                if p < float(self.manual_thresh.get()):
                    new_index = j
                    break
            self.roi_index = new_index
            self.just_set_thresh = True
            self.roi_slider.set(new_index)
            self.draw_canvas(root)    
                            
                                        
def main(main_config_fpath, fnameshort):
    '''use configuration file to find all image and
    ROI paths then start GUI application'''
    cfg_parser = ConfigParser.SafeConfigParser()
    cfg_parser.readfp(open(main_config_fpath,'r'))
    
    img_width = cfg_parser.getint('general','img_width')
    img_height = cfg_parser.getint('general', 'img_height')
                       
    root = Tk()
    root.wm_title("ConvnetCellDetection")
    app = App(root, fnameshort, img_width, img_height)
    root.mainloop()

    
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print "Usage python " + sys.argv[0] + "config_file_path" + " filenameshort"
        sys.exit()
    main_config_fpath = sys.argv[1]
    fnameshort = sys.argv[2]
    main(main_config_fpath, fnameshort)
    
