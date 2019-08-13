#########################################################
#
# Precision-recall framework for evaluating cell detection
#  algorithm accuracy
#
# Author: Noah Apthorpe
#
# Description: calculates precision, recall, and F1 score
#   for multiple sets of predicted and ground-truth ROIs
#
# Usage: 
#    1) from test import Score
#    2) s = Score(None, None, ground_truth_rois, predicted_rois)
#         where *_rois has type [index, numpy.array(roi #, width px, height px)]
#    3) str(s) pretty-formats results
#
################################################################


import numpy as np
from itertools import chain
import random
import os
from collections import defaultdict
import os.path
import load
from preprocess import is_labeled, add_pathsep
import ConfigParser


class Score:
    """Class to calculate and store score.
    
    Constructor takes a prediction function that takes a list of image stacks and 
    returns a list of 3D 0-1 ROI arrays with dimensions (stack, roi index, w, h).
    
    self.predictions      = list of predicted ROIs (stack, ROI index, w, h)
    self.actual           = list of ground-truth ROIs (stack, ROI index, w, h)
    self.categorized      = list of predicted ROIs divided into FPs, FNs, and TPs matched with true ROIs
                             pred ROIs with <0.5 overlap to any true ROI are false positives
                             true ROIs with <0.5 overlap to any pred ROI are false negatives
                             true positive pairs are made by maximizing overlap between pairs
                             e.g. self.categorized[0]["fps"][n] = nth false positive ROI from the 0th image stack
                             e.g. self.categorized[0]["tps"][n] = nth (pred ROI, true ROI) pair from 0th image stack
    self.total_f1_score   = F1 score with all image stacks merged
    self.f1_scores        = list of F1 scores per stack
    self.total_precision  = total precision with all image stacks merged
    self.precisions       = list of precisions per stack
    self.total_recall     = total recall with all stacks merged
    self.recalls          = list of recalls per stack
    self.total_overlap_bq = dict of pixel-wise precisions and recalls for all paired TP predicted ROIs and true ROIs
                            keys = ["mean precision", "std precision", "mean recall", "std recall"]
                             e.g. self.total_overlap_bq["mean precision"] = 
                               mean (pixels in both pred_roi and true_roi) / (pixels in pred_roi)
    self.overlap_bqs      = list of dicts as in self.total_overlap_bq with one dict per image stack                   
    """
    def __init__(self, actual_labels, predicted_labels):
        self.predictions = predicted_labels
        self.actual = actual_labels
        # assert that predicted and true ROI stacks are the same shape
        assert(all([self.predictions[i].shape[1] == self.actual[i].shape[1] 
                    for i in range(len(self.actual))]))
        # assert that predicted ROI stacks are 0-1 arrays
        assert(all([np.all(np.logical_or(self.predictions[i] == 1, self.predictions[i] == 0)) 
                    for i in range(len(self.predictions))]))
        self.categorized = categorize(self.predictions, self.actual)
        self.precisions, self.total_precision, self.recalls, self.total_recall = calc_precision_recall(self.categorized)
        self.f1_scores = map(calc_f1_score, zip(self.precisions, self.recalls))
        #print self.f1_scores
        self.total_f1_score = np.mean(self.f1_scores) 
        #print self.total_f1_score
        self.overlap_bqs, self.total_overlap_bq = overlap_boundary_quality(self.categorized)
       
    def __str__(self):
        """Convert Score to readable output"""
        string =  "Total F1 Score      = {}\n".format(self.total_f1_score)
        string += "F1 Score per stack  = {!s}\n".format(self.f1_scores)
        string += "Total Precision     = {}\n".format(self.total_precision)
        string += "Precision per stack = {!s}\n".format(self.precisions)
        string += "Total Recall        = {}\n".format(self.total_recall)
        string += "Recall per stack    = {!s}\n".format(self.recalls)
        string += "Overlap Boundary Quality, all stacks = {!s}\n".format(self.total_overlap_bq)
        string += "Overlap Boundary Quality, per stack  = {!s}\n\n".format(self.overlap_bqs)
        return string
    
        
def categorize(predictions, labels):
    "Divide predictions and labels into FPs, FNs, and TPs"
    categorized = []
    for i in range(len(predictions)):
        categorized.append({"fps":[], "fns":[], "tps":[]})
        rois_pred, rois_true = list(predictions[i].copy()), list(labels[i].copy())
        for roi_pred in rois_pred:
            overlaps = map(lambda roi_true: calc_overlap(roi_pred, roi_true)[0], rois_true)
            best_overlap, best_index = np.max(overlaps), np.argmax(overlaps)
            if best_overlap > 0.5:
                categorized[i]["tps"].append((roi_pred, rois_true[best_index]))
                del rois_true[best_index]
            else:
                categorized[i]["fps"].append(roi_pred)
        for roi_true in rois_true:
            categorized[i]["fns"].append(roi_true)
    return categorized

def calc_precision_recall(categorized):
    """Calculate precision and recall from categorized predictions and labels"""
    num_fps = [len(categorized[i]["fps"]) for i in range(len(categorized))]
    num_fns = [len(categorized[i]["fns"]) for i in range(len(categorized))]
    num_pairs = [len(categorized[i]["tps"]) for i in range(len(categorized))]
    precisions = [num_pairs[i] / float(num_pairs[i] + num_fps[i]) if num_pairs[i] + num_fps[i] != 0 else 0 for i in range(len(categorized))]
    recalls = [num_pairs[i] / float(num_pairs[i] + num_fns[i]) if num_pairs[i] + num_fns[i] != 0 else 0 for i in range(len(categorized))]
    total_precision = np.mean(precisions) 
    total_recall = np.mean(recalls) 
    return precisions, total_precision, recalls, total_recall
    
def calc_overlap(roi_pred, roi_true):
    """For a given (2D array, 2D array) pair of predicted and true ROIs,
    overlap   = (# pixel intersection / (# pixel union)
    precision = (# pixel intersection) / (# pixels in true ROI)
    recall    = (# pixel interection) / (# pixels in pred ROI)
    """
    intersection = float(np.dot(roi_pred.flat, roi_true.flat))
    
    if intersection == 0: 
        return 0, 0, 0
    
    pred = np.sum(roi_pred)
    true = np.sum(roi_true)
    union = pred + true - intersection
    
    precision = intersection / pred
    recall = intersection / true
    overlap = intersection / union
    return overlap, precision, recall

def calc_f1_score((precision, recall)):
    """F1 score is harmonic mean of precision and recall"""
    if recall == 0:
        return 0 
    else:
        return (2 * precision * recall) / (precision + recall)
    
def overlap_boundary_quality(categorized):
    """Calculates pixel-based mean and std of precision and recall 
    of TP (pred roi, true roi) pairs
    """
    qualities = []
    precisions = []
    recalls = []
    for i in range(len(categorized)):
        precisions.append([])
        recalls.append([])
        for roi_pred, roi_true in categorized[i]["tps"]:
            _, precision, recall = calc_overlap(roi_pred, roi_true)
            precisions[i].append(precision)
            recalls[i].append(recall)
        qualities.append({"mean precision": np.mean(precisions[i]), "std precision": np.std(precisions[i]),
                          "mean recall": np.mean(recalls[i]), "std recall": np.std(recalls[i])})
    overall = {"mean precision": np.mean(list(chain.from_iterable(precisions))),
               "std precision": np.std(list(chain.from_iterable(precisions))),
               "mean recall": np.mean(list(chain.from_iterable(recalls))),
               "std recall": np.std(list(chain.from_iterable(recalls)))}
    return qualities, overall   

    
def score_labeled_data(postprocess_dir, data_dir, img_width, img_height):
    categories = ["training/", "validation/", "test/"]
    for c in categories:
        ground_truth_rois, filenames = load.load_data(data_dir + c, img_width, img_height, rois_only=True)
        rois = defaultdict(lambda: [None, None])
        for i,r in enumerate(ground_truth_rois):
            rois[filenames[i]][0] = r
        for f in os.listdir(postprocess_dir + c):
            filename = os.path.splitext(os.path.basename(f))[0]
            if f.endswith('.npz'):
                rois[filename][1] = np.load(postprocess_dir + c + f)['rois']
        files_to_remove = []
        for f in rois:
            if rois[f][0] is None:
                print "Unable to score " + f + " : missing ground truth data"
                files_to_remove.append(f)
            elif rois[f][1] is None:
                print "Unable to score " + f + " : missing convnet data"
                files_to_remove.append(f)
        for f in files_to_remove:
            rois.pop(f)
        ground_truth_rois, convnet_rois = zip(*rois.values())
        score = Score(ground_truth_rois, convnet_rois)
        with open(postprocess_dir + c + "score.txt", 'w') as score_file:
            score_file.write(str(score))
            

def main(main_config_fpath='../data/example/main_config.cfg'):
    cfg_parser = ConfigParser.SafeConfigParser()
    cfg_parser.readfp(open(main_config_fpath,'r'))
    
    # read parameters
    data_dir = add_pathsep(cfg_parser.get('general', 'data_dir'))
    postprocess_dir = data_dir[0:-1] + "_postprocessed" + os.sep
    img_width = cfg_parser.getint('general', 'img_width')
    img_height = cfg_parser.getint('general', 'img_height')
    # if not is_labeled(data_dir) or not is_labeled(postprocess_dir): #we haven't been putting test/train/val into a "labeled" folder #Let's discuss if we should. -AR 09/13/16

    if not is_labeled(data_dir):
        print "original data_dir was not called 'labeled'. Aborting scoring."
        return
    else:
        print "Scoring labeled data"
        if postprocess_dir[-1] != os.path.sep:
            postprocess_dir += os.path.sep
        if data_dir[-1] != os.path.sep:
            data_dir += os.path.sep
        score_labeled_data(postprocess_dir, data_dir, img_width, img_height)

if __name__ == "__main__":
    main()
