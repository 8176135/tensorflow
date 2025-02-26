# Copyright 2017 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

"""Tests for object_detection.core.target_assigner."""
import numpy as np
import tensorflow as tf

from wai.tfrecords.object_detection.box_coders import keypoint_box_coder
from wai.tfrecords.object_detection.box_coders import mean_stddev_box_coder
from wai.tfrecords.object_detection.core import box_list
from wai.tfrecords.object_detection.core import region_similarity_calculator
from wai.tfrecords.object_detection.core import standard_fields as fields
from wai.tfrecords.object_detection.core import target_assigner as targetassigner
from wai.tfrecords.object_detection.matchers import argmax_matcher
from wai.tfrecords.object_detection.matchers import bipartite_matcher
from wai.tfrecords.object_detection.utils import test_case


class TargetAssignerTest(test_case.TestCase):

  def test_assign_agnostic(self):
    def graph_fn(anchor_means, groundtruth_box_corners):
      similarity_calc = region_similarity_calculator.IouSimilarity()
      matcher = argmax_matcher.ArgMaxMatcher(matched_threshold=0.5,
                                             unmatched_threshold=0.5)
      box_coder = mean_stddev_box_coder.MeanStddevBoxCoder(stddev=0.1)
      target_assigner = targetassigner.TargetAssigner(
          similarity_calc, matcher, box_coder)
      anchors_boxlist = box_list.BoxList(anchor_means)
      groundtruth_boxlist = box_list.BoxList(groundtruth_box_corners)
      result = target_assigner.assign(
          anchors_boxlist, groundtruth_boxlist, unmatched_class_label=None)
      (cls_targets, cls_weights, reg_targets, reg_weights, _) = result
      return (cls_targets, cls_weights, reg_targets, reg_weights)

    anchor_means = np.array([[0.0, 0.0, 0.5, 0.5],
                             [0.5, 0.5, 1.0, 0.8],
                             [0, 0.5, .5, 1.0]], dtype=np.float32)
    groundtruth_box_corners = np.array([[0.0, 0.0, 0.5, 0.5],
                                        [0.5, 0.5, 0.9, 0.9]],
                                       dtype=np.float32)
    exp_cls_targets = [[1], [1], [0]]
    exp_cls_weights = [[1], [1], [1]]
    exp_reg_targets = [[0, 0, 0, 0],
                       [0, 0, -1, 1],
                       [0, 0, 0, 0]]
    exp_reg_weights = [1, 1, 0]

    (cls_targets_out,
     cls_weights_out, reg_targets_out, reg_weights_out) = self.execute(
         graph_fn, [anchor_means, groundtruth_box_corners])
    self.assertAllClose(cls_targets_out, exp_cls_targets)
    self.assertAllClose(cls_weights_out, exp_cls_weights)
    self.assertAllClose(reg_targets_out, exp_reg_targets)
    self.assertAllClose(reg_weights_out, exp_reg_weights)
    self.assertEquals(cls_targets_out.dtype, np.float32)
    self.assertEquals(cls_weights_out.dtype, np.float32)
    self.assertEquals(reg_targets_out.dtype, np.float32)
    self.assertEquals(reg_weights_out.dtype, np.float32)

  def test_assign_class_agnostic_with_ignored_matches(self):
    # Note: test is very similar to above. The third box matched with an IOU
    # of 0.35, which is between the matched and unmatched threshold. This means
    # That like above the expected classification targets are [1, 1, 0].
    # Unlike above, the third target is ignored and therefore expected
    # classification weights are [1, 1, 0].
    def graph_fn(anchor_means, groundtruth_box_corners):
      similarity_calc = region_similarity_calculator.IouSimilarity()
      matcher = argmax_matcher.ArgMaxMatcher(matched_threshold=0.5,
                                             unmatched_threshold=0.3)
      box_coder = mean_stddev_box_coder.MeanStddevBoxCoder(stddev=0.1)
      target_assigner = targetassigner.TargetAssigner(
          similarity_calc, matcher, box_coder)
      anchors_boxlist = box_list.BoxList(anchor_means)
      groundtruth_boxlist = box_list.BoxList(groundtruth_box_corners)
      result = target_assigner.assign(
          anchors_boxlist, groundtruth_boxlist, unmatched_class_label=None)
      (cls_targets, cls_weights, reg_targets, reg_weights, _) = result
      return (cls_targets, cls_weights, reg_targets, reg_weights)

    anchor_means = np.array([[0.0, 0.0, 0.5, 0.5],
                             [0.5, 0.5, 1.0, 0.8],
                             [0.0, 0.5, .9, 1.0]], dtype=np.float32)
    groundtruth_box_corners = np.array([[0.0, 0.0, 0.5, 0.5],
                                        [0.5, 0.5, 0.9, 0.9]], dtype=np.float32)
    exp_cls_targets = [[1], [1], [0]]
    exp_cls_weights = [[1], [1], [0]]
    exp_reg_targets = [[0, 0, 0, 0],
                       [0, 0, -1, 1],
                       [0, 0, 0, 0]]
    exp_reg_weights = [1, 1, 0]
    (cls_targets_out,
     cls_weights_out, reg_targets_out, reg_weights_out) = self.execute(
         graph_fn, [anchor_means, groundtruth_box_corners])
    self.assertAllClose(cls_targets_out, exp_cls_targets)
    self.assertAllClose(cls_weights_out, exp_cls_weights)
    self.assertAllClose(reg_targets_out, exp_reg_targets)
    self.assertAllClose(reg_weights_out, exp_reg_weights)
    self.assertEquals(cls_targets_out.dtype, np.float32)
    self.assertEquals(cls_weights_out.dtype, np.float32)
    self.assertEquals(reg_targets_out.dtype, np.float32)
    self.assertEquals(reg_weights_out.dtype, np.float32)

  def test_assign_agnostic_with_keypoints(self):
    def graph_fn(anchor_means, groundtruth_box_corners,
                 groundtruth_keypoints):
      similarity_calc = region_similarity_calculator.IouSimilarity()
      matcher = argmax_matcher.ArgMaxMatcher(matched_threshold=0.5,
                                             unmatched_threshold=0.5)
      box_coder = keypoint_box_coder.KeypointBoxCoder(
          num_keypoints=6, scale_factors=[10.0, 10.0, 5.0, 5.0])
      target_assigner = targetassigner.TargetAssigner(
          similarity_calc, matcher, box_coder)
      anchors_boxlist = box_list.BoxList(anchor_means)
      groundtruth_boxlist = box_list.BoxList(groundtruth_box_corners)
      groundtruth_boxlist.add_field(fields.BoxListFields.keypoints,
                                    groundtruth_keypoints)
      result = target_assigner.assign(
          anchors_boxlist, groundtruth_boxlist, unmatched_class_label=None)
      (cls_targets, cls_weights, reg_targets, reg_weights, _) = result
      return (cls_targets, cls_weights, reg_targets, reg_weights)

    anchor_means = np.array([[0.0, 0.0, 0.5, 0.5],
                             [0.5, 0.5, 1.0, 1.0],
                             [0.0, 0.5, .9, 1.0]], dtype=np.float32)
    groundtruth_box_corners = np.array([[0.0, 0.0, 0.5, 0.5],
                                        [0.45, 0.45, 0.95, 0.95]],
                                       dtype=np.float32)
    groundtruth_keypoints = np.array(
        [[[0.1, 0.2], [0.1, 0.3], [0.2, 0.2], [0.2, 0.2], [0.1, 0.1], [0.9, 0]],
         [[0, 0.3], [0.2, 0.4], [0.5, 0.6], [0, 0.6], [0.8, 0.2], [0.2, 0.4]]],
        dtype=np.float32)
    exp_cls_targets = [[1], [1], [0]]
    exp_cls_weights = [[1], [1], [1]]
    exp_reg_targets = [[0, 0, 0, 0, -3, -1, -3, 1, -1, -1, -1, -1, -3, -3, 13,
                        -5],
                       [-1, -1, 0, 0, -15, -9, -11, -7, -5, -3, -15, -3, 1, -11,
                        -11, -7],
                       [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]
    exp_reg_weights = [1, 1, 0]
    (cls_targets_out, cls_weights_out, reg_targets_out,
     reg_weights_out) = self.execute(graph_fn, [anchor_means,
                                                groundtruth_box_corners,
                                                groundtruth_keypoints])
    self.assertAllClose(cls_targets_out, exp_cls_targets)
    self.assertAllClose(cls_weights_out, exp_cls_weights)
    self.assertAllClose(reg_targets_out, exp_reg_targets)
    self.assertAllClose(reg_weights_out, exp_reg_weights)
    self.assertEquals(cls_targets_out.dtype, np.float32)
    self.assertEquals(cls_weights_out.dtype, np.float32)
    self.assertEquals(reg_targets_out.dtype, np.float32)
    self.assertEquals(reg_weights_out.dtype, np.float32)

  def test_assign_class_agnostic_with_keypoints_and_ignored_matches(self):
    # Note: test is very similar to above. The third box matched with an IOU
    # of 0.35, which is between the matched and unmatched threshold. This means
    # That like above the expected classification targets are [1, 1, 0].
    # Unlike above, the third target is ignored and therefore expected
    # classification weights are [1, 1, 0].
    def graph_fn(anchor_means, groundtruth_box_corners,
                 groundtruth_keypoints):
      similarity_calc = region_similarity_calculator.IouSimilarity()
      matcher = argmax_matcher.ArgMaxMatcher(matched_threshold=0.5,
                                             unmatched_threshold=0.5)
      box_coder = keypoint_box_coder.KeypointBoxCoder(
          num_keypoints=6, scale_factors=[10.0, 10.0, 5.0, 5.0])
      target_assigner = targetassigner.TargetAssigner(
          similarity_calc, matcher, box_coder)
      anchors_boxlist = box_list.BoxList(anchor_means)
      groundtruth_boxlist = box_list.BoxList(groundtruth_box_corners)
      groundtruth_boxlist.add_field(fields.BoxListFields.keypoints,
                                    groundtruth_keypoints)
      result = target_assigner.assign(
          anchors_boxlist, groundtruth_boxlist, unmatched_class_label=None)
      (cls_targets, cls_weights, reg_targets, reg_weights, _) = result
      return (cls_targets, cls_weights, reg_targets, reg_weights)

    anchor_means = np.array([[0.0, 0.0, 0.5, 0.5],
                             [0.5, 0.5, 1.0, 1.0],
                             [0.0, 0.5, .9, 1.0]], dtype=np.float32)
    groundtruth_box_corners = np.array([[0.0, 0.0, 0.5, 0.5],
                                        [0.45, 0.45, 0.95, 0.95]],
                                       dtype=np.float32)
    groundtruth_keypoints = np.array(
        [[[0.1, 0.2], [0.1, 0.3], [0.2, 0.2], [0.2, 0.2], [0.1, 0.1], [0.9, 0]],
         [[0, 0.3], [0.2, 0.4], [0.5, 0.6], [0, 0.6], [0.8, 0.2], [0.2, 0.4]]],
        dtype=np.float32)
    exp_cls_targets = [[1], [1], [0]]
    exp_cls_weights = [[1], [1], [1]]
    exp_reg_targets = [[0, 0, 0, 0, -3, -1, -3, 1, -1, -1, -1, -1, -3, -3, 13,
                        -5],
                       [-1, -1, 0, 0, -15, -9, -11, -7, -5, -3, -15, -3, 1, -11,
                        -11, -7],
                       [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]
    exp_reg_weights = [1, 1, 0]
    (cls_targets_out, cls_weights_out, reg_targets_out,
     reg_weights_out) = self.execute(graph_fn, [anchor_means,
                                                groundtruth_box_corners,
                                                groundtruth_keypoints])
    self.assertAllClose(cls_targets_out, exp_cls_targets)
    self.assertAllClose(cls_weights_out, exp_cls_weights)
    self.assertAllClose(reg_targets_out, exp_reg_targets)
    self.assertAllClose(reg_weights_out, exp_reg_weights)
    self.assertEquals(cls_targets_out.dtype, np.float32)
    self.assertEquals(cls_weights_out.dtype, np.float32)
    self.assertEquals(reg_targets_out.dtype, np.float32)
    self.assertEquals(reg_weights_out.dtype, np.float32)

  def test_assign_multiclass(self):

    def graph_fn(anchor_means, groundtruth_box_corners, groundtruth_labels):
      similarity_calc = region_similarity_calculator.IouSimilarity()
      matcher = argmax_matcher.ArgMaxMatcher(matched_threshold=0.5,
                                             unmatched_threshold=0.5)
      box_coder = mean_stddev_box_coder.MeanStddevBoxCoder(stddev=0.1)
      unmatched_class_label = tf.constant([1, 0, 0, 0, 0, 0, 0], tf.float32)
      target_assigner = targetassigner.TargetAssigner(
          similarity_calc, matcher, box_coder)

      anchors_boxlist = box_list.BoxList(anchor_means)
      groundtruth_boxlist = box_list.BoxList(groundtruth_box_corners)
      result = target_assigner.assign(
          anchors_boxlist,
          groundtruth_boxlist,
          groundtruth_labels,
          unmatched_class_label=unmatched_class_label)
      (cls_targets, cls_weights, reg_targets, reg_weights, _) = result
      return (cls_targets, cls_weights, reg_targets, reg_weights)

    anchor_means = np.array([[0.0, 0.0, 0.5, 0.5],
                             [0.5, 0.5, 1.0, 0.8],
                             [0, 0.5, .5, 1.0],
                             [.75, 0, 1.0, .25]], dtype=np.float32)
    groundtruth_box_corners = np.array([[0.0, 0.0, 0.5, 0.5],
                                        [0.5, 0.5, 0.9, 0.9],
                                        [.75, 0, .95, .27]], dtype=np.float32)
    groundtruth_labels = np.array([[0, 1, 0, 0, 0, 0, 0],
                                   [0, 0, 0, 0, 0, 1, 0],
                                   [0, 0, 0, 1, 0, 0, 0]], dtype=np.float32)

    exp_cls_targets = [[0, 1, 0, 0, 0, 0, 0],
                       [0, 0, 0, 0, 0, 1, 0],
                       [1, 0, 0, 0, 0, 0, 0],
                       [0, 0, 0, 1, 0, 0, 0]]
    exp_cls_weights = [[1, 1, 1, 1, 1, 1, 1],
                       [1, 1, 1, 1, 1, 1, 1],
                       [1, 1, 1, 1, 1, 1, 1],
                       [1, 1, 1, 1, 1, 1, 1]]
    exp_reg_targets = [[0, 0, 0, 0],
                       [0, 0, -1, 1],
                       [0, 0, 0, 0],
                       [0, 0, -.5, .2]]
    exp_reg_weights = [1, 1, 0, 1]

    (cls_targets_out,
     cls_weights_out, reg_targets_out, reg_weights_out) = self.execute(
         graph_fn, [anchor_means, groundtruth_box_corners, groundtruth_labels])
    self.assertAllClose(cls_targets_out, exp_cls_targets)
    self.assertAllClose(cls_weights_out, exp_cls_weights)
    self.assertAllClose(reg_targets_out, exp_reg_targets)
    self.assertAllClose(reg_weights_out, exp_reg_weights)
    self.assertEquals(cls_targets_out.dtype, np.float32)
    self.assertEquals(cls_weights_out.dtype, np.float32)
    self.assertEquals(reg_targets_out.dtype, np.float32)
    self.assertEquals(reg_weights_out.dtype, np.float32)

  def test_assign_multiclass_with_groundtruth_weights(self):

    def graph_fn(anchor_means, groundtruth_box_corners, groundtruth_labels,
                 groundtruth_weights):
      similarity_calc = region_similarity_calculator.IouSimilarity()
      matcher = argmax_matcher.ArgMaxMatcher(matched_threshold=0.5,
                                             unmatched_threshold=0.5)
      box_coder = mean_stddev_box_coder.MeanStddevBoxCoder(stddev=0.1)
      unmatched_class_label = tf.constant([1, 0, 0, 0, 0, 0, 0], tf.float32)
      target_assigner = targetassigner.TargetAssigner(
          similarity_calc, matcher, box_coder)

      anchors_boxlist = box_list.BoxList(anchor_means)
      groundtruth_boxlist = box_list.BoxList(groundtruth_box_corners)
      result = target_assigner.assign(
          anchors_boxlist,
          groundtruth_boxlist,
          groundtruth_labels,
          unmatched_class_label=unmatched_class_label,
          groundtruth_weights=groundtruth_weights)
      (_, cls_weights, _, reg_weights, _) = result
      return (cls_weights, reg_weights)

    anchor_means = np.array([[0.0, 0.0, 0.5, 0.5],
                             [0.5, 0.5, 1.0, 0.8],
                             [0, 0.5, .5, 1.0],
                             [.75, 0, 1.0, .25]], dtype=np.float32)
    groundtruth_box_corners = np.array([[0.0, 0.0, 0.5, 0.5],
                                        [0.5, 0.5, 0.9, 0.9],
                                        [.75, 0, .95, .27]], dtype=np.float32)
    groundtruth_labels = np.array([[0, 1, 0, 0, 0, 0, 0],
                                   [0, 0, 0, 0, 0, 1, 0],
                                   [0, 0, 0, 1, 0, 0, 0]], dtype=np.float32)
    groundtruth_weights = np.array([0.3, 0., 0.5], dtype=np.float32)

    # background class gets weight of 1.
    exp_cls_weights = [[0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3],
                       [0, 0, 0, 0, 0, 0, 0],
                       [1, 1, 1, 1, 1, 1, 1],
                       [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]]
    exp_reg_weights = [0.3, 0., 0., 0.5]  # background class gets weight of 0.

    (cls_weights_out, reg_weights_out) = self.execute(graph_fn, [
        anchor_means, groundtruth_box_corners, groundtruth_labels,
        groundtruth_weights
    ])
    self.assertAllClose(cls_weights_out, exp_cls_weights)
    self.assertAllClose(reg_weights_out, exp_reg_weights)

  def test_assign_multidimensional_class_targets(self):

    def graph_fn(anchor_means, groundtruth_box_corners, groundtruth_labels):
      similarity_calc = region_similarity_calculator.IouSimilarity()
      matcher = argmax_matcher.ArgMaxMatcher(matched_threshold=0.5,
                                             unmatched_threshold=0.5)
      box_coder = mean_stddev_box_coder.MeanStddevBoxCoder(stddev=0.1)

      unmatched_class_label = tf.constant([[0, 0], [0, 0]], tf.float32)
      target_assigner = targetassigner.TargetAssigner(
          similarity_calc, matcher, box_coder)

      anchors_boxlist = box_list.BoxList(anchor_means)
      groundtruth_boxlist = box_list.BoxList(groundtruth_box_corners)
      result = target_assigner.assign(
          anchors_boxlist,
          groundtruth_boxlist,
          groundtruth_labels,
          unmatched_class_label=unmatched_class_label)
      (cls_targets, cls_weights, reg_targets, reg_weights, _) = result
      return (cls_targets, cls_weights, reg_targets, reg_weights)

    anchor_means = np.array([[0.0, 0.0, 0.5, 0.5],
                             [0.5, 0.5, 1.0, 0.8],
                             [0, 0.5, .5, 1.0],
                             [.75, 0, 1.0, .25]], dtype=np.float32)
    groundtruth_box_corners = np.array([[0.0, 0.0, 0.5, 0.5],
                                        [0.5, 0.5, 0.9, 0.9],
                                        [.75, 0, .95, .27]], dtype=np.float32)

    groundtruth_labels = np.array([[[0, 1], [1, 0]],
                                   [[1, 0], [0, 1]],
                                   [[0, 1], [1, .5]]], np.float32)

    exp_cls_targets = [[[0, 1], [1, 0]],
                       [[1, 0], [0, 1]],
                       [[0, 0], [0, 0]],
                       [[0, 1], [1, .5]]]
    exp_cls_weights = [[[1, 1], [1, 1]],
                       [[1, 1], [1, 1]],
                       [[1, 1], [1, 1]],
                       [[1, 1], [1, 1]]]
    exp_reg_targets = [[0, 0, 0, 0],
                       [0, 0, -1, 1],
                       [0, 0, 0, 0],
                       [0, 0, -.5, .2]]
    exp_reg_weights = [1, 1, 0, 1]
    (cls_targets_out,
     cls_weights_out, reg_targets_out, reg_weights_out) = self.execute(
         graph_fn, [anchor_means, groundtruth_box_corners, groundtruth_labels])
    self.assertAllClose(cls_targets_out, exp_cls_targets)
    self.assertAllClose(cls_weights_out, exp_cls_weights)
    self.assertAllClose(reg_targets_out, exp_reg_targets)
    self.assertAllClose(reg_weights_out, exp_reg_weights)
    self.assertEquals(cls_targets_out.dtype, np.float32)
    self.assertEquals(cls_weights_out.dtype, np.float32)
    self.assertEquals(reg_targets_out.dtype, np.float32)
    self.assertEquals(reg_weights_out.dtype, np.float32)

  def test_assign_empty_groundtruth(self):

    def graph_fn(anchor_means, groundtruth_box_corners, groundtruth_labels):
      similarity_calc = region_similarity_calculator.IouSimilarity()
      matcher = argmax_matcher.ArgMaxMatcher(matched_threshold=0.5,
                                             unmatched_threshold=0.5)
      box_coder = mean_stddev_box_coder.MeanStddevBoxCoder(stddev=0.1)
      unmatched_class_label = tf.constant([0, 0, 0], tf.float32)
      anchors_boxlist = box_list.BoxList(anchor_means)
      groundtruth_boxlist = box_list.BoxList(groundtruth_box_corners)
      target_assigner = targetassigner.TargetAssigner(
          similarity_calc, matcher, box_coder)
      result = target_assigner.assign(
          anchors_boxlist,
          groundtruth_boxlist,
          groundtruth_labels,
          unmatched_class_label=unmatched_class_label)
      (cls_targets, cls_weights, reg_targets, reg_weights, _) = result
      return (cls_targets, cls_weights, reg_targets, reg_weights)

    groundtruth_box_corners = np.zeros((0, 4), dtype=np.float32)
    groundtruth_labels = np.zeros((0, 3), dtype=np.float32)
    anchor_means = np.array([[0.0, 0.0, 0.5, 0.5],
                             [0.5, 0.5, 1.0, 0.8],
                             [0, 0.5, .5, 1.0],
                             [.75, 0, 1.0, .25]],
                            dtype=np.float32)
    exp_cls_targets = [[0, 0, 0],
                       [0, 0, 0],
                       [0, 0, 0],
                       [0, 0, 0]]
    exp_cls_weights = [[1, 1, 1],
                       [1, 1, 1],
                       [1, 1, 1],
                       [1, 1, 1]]
    exp_reg_targets = [[0, 0, 0, 0],
                       [0, 0, 0, 0],
                       [0, 0, 0, 0],
                       [0, 0, 0, 0]]
    exp_reg_weights = [0, 0, 0, 0]
    (cls_targets_out,
     cls_weights_out, reg_targets_out, reg_weights_out) = self.execute(
         graph_fn, [anchor_means, groundtruth_box_corners, groundtruth_labels])
    self.assertAllClose(cls_targets_out, exp_cls_targets)
    self.assertAllClose(cls_weights_out, exp_cls_weights)
    self.assertAllClose(reg_targets_out, exp_reg_targets)
    self.assertAllClose(reg_weights_out, exp_reg_weights)
    self.assertEquals(cls_targets_out.dtype, np.float32)
    self.assertEquals(cls_weights_out.dtype, np.float32)
    self.assertEquals(reg_targets_out.dtype, np.float32)
    self.assertEquals(reg_weights_out.dtype, np.float32)

  def test_raises_error_on_incompatible_groundtruth_boxes_and_labels(self):
    similarity_calc = region_similarity_calculator.NegSqDistSimilarity()
    matcher = bipartite_matcher.GreedyBipartiteMatcher()
    box_coder = mean_stddev_box_coder.MeanStddevBoxCoder()
    unmatched_class_label = tf.constant([1, 0, 0, 0, 0, 0, 0], tf.float32)
    target_assigner = targetassigner.TargetAssigner(
        similarity_calc, matcher, box_coder)

    prior_means = tf.constant([[0.0, 0.0, 0.5, 0.5],
                               [0.5, 0.5, 1.0, 0.8],
                               [0, 0.5, .5, 1.0],
                               [.75, 0, 1.0, .25]])
    priors = box_list.BoxList(prior_means)

    box_corners = [[0.0, 0.0, 0.5, 0.5],
                   [0.0, 0.0, 0.5, 0.8],
                   [0.5, 0.5, 0.9, 0.9],
                   [.75, 0, .95, .27]]
    boxes = box_list.BoxList(tf.constant(box_corners))

    groundtruth_labels = tf.constant([[0, 1, 0, 0, 0, 0, 0],
                                      [0, 0, 0, 0, 0, 1, 0],
                                      [0, 0, 0, 1, 0, 0, 0]], tf.float32)
    with self.assertRaisesRegexp(ValueError, 'Unequal shapes'):
      target_assigner.assign(
          priors,
          boxes,
          groundtruth_labels,
          unmatched_class_label=unmatched_class_label)

  def test_raises_error_on_invalid_groundtruth_labels(self):
    similarity_calc = region_similarity_calculator.NegSqDistSimilarity()
    matcher = bipartite_matcher.GreedyBipartiteMatcher()
    box_coder = mean_stddev_box_coder.MeanStddevBoxCoder(stddev=1.0)
    unmatched_class_label = tf.constant([[0, 0], [0, 0], [0, 0]], tf.float32)
    target_assigner = targetassigner.TargetAssigner(
        similarity_calc, matcher, box_coder)

    prior_means = tf.constant([[0.0, 0.0, 0.5, 0.5]])
    priors = box_list.BoxList(prior_means)

    box_corners = [[0.0, 0.0, 0.5, 0.5],
                   [0.5, 0.5, 0.9, 0.9],
                   [.75, 0, .95, .27]]
    boxes = box_list.BoxList(tf.constant(box_corners))
    groundtruth_labels = tf.constant([[[0, 1], [1, 0]]], tf.float32)

    with self.assertRaises(ValueError):
      target_assigner.assign(
          priors,
          boxes,
          groundtruth_labels,
          unmatched_class_label=unmatched_class_label)


class BatchTargetAssignerTest(test_case.TestCase):

  def _get_target_assigner(self):
    similarity_calc = region_similarity_calculator.IouSimilarity()
    matcher = argmax_matcher.ArgMaxMatcher(matched_threshold=0.5,
                                           unmatched_threshold=0.5)
    box_coder = mean_stddev_box_coder.MeanStddevBoxCoder(stddev=0.1)
    return targetassigner.TargetAssigner(similarity_calc, matcher, box_coder)

  def test_batch_assign_targets(self):

    def graph_fn(anchor_means, groundtruth_boxlist1, groundtruth_boxlist2):
      box_list1 = box_list.BoxList(groundtruth_boxlist1)
      box_list2 = box_list.BoxList(groundtruth_boxlist2)
      gt_box_batch = [box_list1, box_list2]
      gt_class_targets = [None, None]
      anchors_boxlist = box_list.BoxList(anchor_means)
      agnostic_target_assigner = self._get_target_assigner()
      (cls_targets, cls_weights, reg_targets, reg_weights,
       _) = targetassigner.batch_assign_targets(
           agnostic_target_assigner, anchors_boxlist, gt_box_batch,
           gt_class_targets)
      return (cls_targets, cls_weights, reg_targets, reg_weights)

    groundtruth_boxlist1 = np.array([[0., 0., 0.2, 0.2]], dtype=np.float32)
    groundtruth_boxlist2 = np.array([[0, 0.25123152, 1, 1],
                                     [0.015789, 0.0985, 0.55789, 0.3842]],
                                    dtype=np.float32)
    anchor_means = np.array([[0, 0, .25, .25],
                             [0, .25, 1, 1],
                             [0, .1, .5, .5],
                             [.75, .75, 1, 1]], dtype=np.float32)

    exp_cls_targets = [[[1], [0], [0], [0]],
                       [[0], [1], [1], [0]]]
    exp_cls_weights = [[[1], [1], [1], [1]],
                       [[1], [1], [1], [1]]]
    exp_reg_targets = [[[0, 0, -0.5, -0.5],
                        [0, 0, 0, 0],
                        [0, 0, 0, 0,],
                        [0, 0, 0, 0,],],
                       [[0, 0, 0, 0,],
                        [0, 0.01231521, 0, 0],
                        [0.15789001, -0.01500003, 0.57889998, -1.15799987],
                        [0, 0, 0, 0]]]
    exp_reg_weights = [[1, 0, 0, 0],
                       [0, 1, 1, 0]]

    (cls_targets_out,
     cls_weights_out, reg_targets_out, reg_weights_out) = self.execute(
         graph_fn, [anchor_means, groundtruth_boxlist1, groundtruth_boxlist2])
    self.assertAllClose(cls_targets_out, exp_cls_targets)
    self.assertAllClose(cls_weights_out, exp_cls_weights)
    self.assertAllClose(reg_targets_out, exp_reg_targets)
    self.assertAllClose(reg_weights_out, exp_reg_weights)

  def test_batch_assign_multiclass_targets(self):

    def graph_fn(anchor_means, groundtruth_boxlist1, groundtruth_boxlist2,
                 class_targets1, class_targets2):
      box_list1 = box_list.BoxList(groundtruth_boxlist1)
      box_list2 = box_list.BoxList(groundtruth_boxlist2)
      gt_box_batch = [box_list1, box_list2]
      gt_class_targets = [class_targets1, class_targets2]
      anchors_boxlist = box_list.BoxList(anchor_means)
      multiclass_target_assigner = self._get_target_assigner()
      num_classes = 3
      unmatched_class_label = tf.constant([1] + num_classes * [0], tf.float32)
      (cls_targets, cls_weights, reg_targets, reg_weights,
       _) = targetassigner.batch_assign_targets(
           multiclass_target_assigner, anchors_boxlist, gt_box_batch,
           gt_class_targets, unmatched_class_label)
      return (cls_targets, cls_weights, reg_targets, reg_weights)

    groundtruth_boxlist1 = np.array([[0., 0., 0.2, 0.2]], dtype=np.float32)
    groundtruth_boxlist2 = np.array([[0, 0.25123152, 1, 1],
                                     [0.015789, 0.0985, 0.55789, 0.3842]],
                                    dtype=np.float32)
    class_targets1 = np.array([[0, 1, 0, 0]], dtype=np.float32)
    class_targets2 = np.array([[0, 0, 0, 1],
                               [0, 0, 1, 0]], dtype=np.float32)

    anchor_means = np.array([[0, 0, .25, .25],
                             [0, .25, 1, 1],
                             [0, .1, .5, .5],
                             [.75, .75, 1, 1]], dtype=np.float32)
    exp_cls_targets = [[[0, 1, 0, 0],
                        [1, 0, 0, 0],
                        [1, 0, 0, 0],
                        [1, 0, 0, 0]],
                       [[1, 0, 0, 0],
                        [0, 0, 0, 1],
                        [0, 0, 1, 0],
                        [1, 0, 0, 0]]]
    exp_cls_weights = [[[1, 1, 1, 1],
                        [1, 1, 1, 1],
                        [1, 1, 1, 1],
                        [1, 1, 1, 1]],
                       [[1, 1, 1, 1],
                        [1, 1, 1, 1],
                        [1, 1, 1, 1],
                        [1, 1, 1, 1]]]
    exp_reg_targets = [[[0, 0, -0.5, -0.5],
                        [0, 0, 0, 0],
                        [0, 0, 0, 0,],
                        [0, 0, 0, 0,],],
                       [[0, 0, 0, 0,],
                        [0, 0.01231521, 0, 0],
                        [0.15789001, -0.01500003, 0.57889998, -1.15799987],
                        [0, 0, 0, 0]]]
    exp_reg_weights = [[1, 0, 0, 0],
                       [0, 1, 1, 0]]

    (cls_targets_out, cls_weights_out, reg_targets_out,
     reg_weights_out) = self.execute(graph_fn, [
         anchor_means, groundtruth_boxlist1, groundtruth_boxlist2,
         class_targets1, class_targets2
     ])
    self.assertAllClose(cls_targets_out, exp_cls_targets)
    self.assertAllClose(cls_weights_out, exp_cls_weights)
    self.assertAllClose(reg_targets_out, exp_reg_targets)
    self.assertAllClose(reg_weights_out, exp_reg_weights)

  def test_batch_assign_multiclass_targets_with_padded_groundtruth(self):

    def graph_fn(anchor_means, groundtruth_boxlist1, groundtruth_boxlist2,
                 class_targets1, class_targets2, groundtruth_weights1,
                 groundtruth_weights2):
      box_list1 = box_list.BoxList(groundtruth_boxlist1)
      box_list2 = box_list.BoxList(groundtruth_boxlist2)
      gt_box_batch = [box_list1, box_list2]
      gt_class_targets = [class_targets1, class_targets2]
      gt_weights = [groundtruth_weights1, groundtruth_weights2]
      anchors_boxlist = box_list.BoxList(anchor_means)
      multiclass_target_assigner = self._get_target_assigner()
      num_classes = 3
      unmatched_class_label = tf.constant([1] + num_classes * [0], tf.float32)
      (cls_targets, cls_weights, reg_targets, reg_weights,
       _) = targetassigner.batch_assign_targets(
           multiclass_target_assigner, anchors_boxlist, gt_box_batch,
           gt_class_targets, unmatched_class_label, gt_weights)
      return (cls_targets, cls_weights, reg_targets, reg_weights)

    groundtruth_boxlist1 = np.array([[0., 0., 0.2, 0.2],
                                     [0., 0., 0., 0.]], dtype=np.float32)
    groundtruth_weights1 = np.array([1, 0], dtype=np.float32)
    groundtruth_boxlist2 = np.array([[0, 0.25123152, 1, 1],
                                     [0.015789, 0.0985, 0.55789, 0.3842],
                                     [0, 0, 0, 0]],
                                    dtype=np.float32)
    groundtruth_weights2 = np.array([1, 1, 0], dtype=np.float32)
    class_targets1 = np.array([[0, 1, 0, 0], [0, 0, 0, 0]], dtype=np.float32)
    class_targets2 = np.array([[0, 0, 0, 1],
                               [0, 0, 1, 0],
                               [0, 0, 0, 0]], dtype=np.float32)

    anchor_means = np.array([[0, 0, .25, .25],
                             [0, .25, 1, 1],
                             [0, .1, .5, .5],
                             [.75, .75, 1, 1]], dtype=np.float32)

    exp_cls_targets = [[[0, 1, 0, 0],
                        [1, 0, 0, 0],
                        [1, 0, 0, 0],
                        [1, 0, 0, 0]],
                       [[1, 0, 0, 0],
                        [0, 0, 0, 1],
                        [0, 0, 1, 0],
                        [1, 0, 0, 0]]]
    exp_cls_weights = [[[1, 1, 1, 1],
                        [1, 1, 1, 1],
                        [1, 1, 1, 1],
                        [1, 1, 1, 1]],
                       [[1, 1, 1, 1],
                        [1, 1, 1, 1],
                        [1, 1, 1, 1],
                        [1, 1, 1, 1]]]
    exp_reg_targets = [[[0, 0, -0.5, -0.5],
                        [0, 0, 0, 0],
                        [0, 0, 0, 0,],
                        [0, 0, 0, 0,],],
                       [[0, 0, 0, 0,],
                        [0, 0.01231521, 0, 0],
                        [0.15789001, -0.01500003, 0.57889998, -1.15799987],
                        [0, 0, 0, 0]]]
    exp_reg_weights = [[1, 0, 0, 0],
                       [0, 1, 1, 0]]

    (cls_targets_out, cls_weights_out, reg_targets_out,
     reg_weights_out) = self.execute(graph_fn, [
         anchor_means, groundtruth_boxlist1, groundtruth_boxlist2,
         class_targets1, class_targets2, groundtruth_weights1,
         groundtruth_weights2
     ])
    self.assertAllClose(cls_targets_out, exp_cls_targets)
    self.assertAllClose(cls_weights_out, exp_cls_weights)
    self.assertAllClose(reg_targets_out, exp_reg_targets)
    self.assertAllClose(reg_weights_out, exp_reg_weights)

  def test_batch_assign_multidimensional_targets(self):

    def graph_fn(anchor_means, groundtruth_boxlist1, groundtruth_boxlist2,
                 class_targets1, class_targets2):
      box_list1 = box_list.BoxList(groundtruth_boxlist1)
      box_list2 = box_list.BoxList(groundtruth_boxlist2)
      gt_box_batch = [box_list1, box_list2]
      gt_class_targets = [class_targets1, class_targets2]
      anchors_boxlist = box_list.BoxList(anchor_means)
      multiclass_target_assigner = self._get_target_assigner()
      target_dimensions = (2, 3)
      unmatched_class_label = tf.constant(np.zeros(target_dimensions),
                                          tf.float32)
      (cls_targets, cls_weights, reg_targets, reg_weights,
       _) = targetassigner.batch_assign_targets(
           multiclass_target_assigner, anchors_boxlist, gt_box_batch,
           gt_class_targets, unmatched_class_label)
      return (cls_targets, cls_weights, reg_targets, reg_weights)

    groundtruth_boxlist1 = np.array([[0., 0., 0.2, 0.2]], dtype=np.float32)
    groundtruth_boxlist2 = np.array([[0, 0.25123152, 1, 1],
                                     [0.015789, 0.0985, 0.55789, 0.3842]],
                                    dtype=np.float32)
    class_targets1 = np.array([[[0, 1, 1],
                                [1, 1, 0]]], dtype=np.float32)
    class_targets2 = np.array([[[0, 1, 1],
                                [1, 1, 0]],
                               [[0, 0, 1],
                                [0, 0, 1]]], dtype=np.float32)

    anchor_means = np.array([[0, 0, .25, .25],
                             [0, .25, 1, 1],
                             [0, .1, .5, .5],
                             [.75, .75, 1, 1]], dtype=np.float32)

    exp_cls_targets = [[[[0., 1., 1.],
                         [1., 1., 0.]],
                        [[0., 0., 0.],
                         [0., 0., 0.]],
                        [[0., 0., 0.],
                         [0., 0., 0.]],
                        [[0., 0., 0.],
                         [0., 0., 0.]]],
                       [[[0., 0., 0.],
                         [0., 0., 0.]],
                        [[0., 1., 1.],
                         [1., 1., 0.]],
                        [[0., 0., 1.],
                         [0., 0., 1.]],
                        [[0., 0., 0.],
                         [0., 0., 0.]]]]
    exp_cls_weights = [[[[1., 1., 1.],
                         [1., 1., 1.]],
                        [[1., 1., 1.],
                         [1., 1., 1.]],
                        [[1., 1., 1.],
                         [1., 1., 1.]],
                        [[1., 1., 1.],
                         [1., 1., 1.]]],
                       [[[1., 1., 1.],
                         [1., 1., 1.]],
                        [[1., 1., 1.],
                         [1., 1., 1.]],
                        [[1., 1., 1.],
                         [1., 1., 1.]],
                        [[1., 1., 1.],
                         [1., 1., 1.]]]]
    exp_reg_targets = [[[0, 0, -0.5, -0.5],
                        [0, 0, 0, 0],
                        [0, 0, 0, 0,],
                        [0, 0, 0, 0,],],
                       [[0, 0, 0, 0,],
                        [0, 0.01231521, 0, 0],
                        [0.15789001, -0.01500003, 0.57889998, -1.15799987],
                        [0, 0, 0, 0]]]
    exp_reg_weights = [[1, 0, 0, 0],
                       [0, 1, 1, 0]]

    (cls_targets_out, cls_weights_out, reg_targets_out,
     reg_weights_out) = self.execute(graph_fn, [
         anchor_means, groundtruth_boxlist1, groundtruth_boxlist2,
         class_targets1, class_targets2
     ])
    self.assertAllClose(cls_targets_out, exp_cls_targets)
    self.assertAllClose(cls_weights_out, exp_cls_weights)
    self.assertAllClose(reg_targets_out, exp_reg_targets)
    self.assertAllClose(reg_weights_out, exp_reg_weights)

  def test_batch_assign_empty_groundtruth(self):

    def graph_fn(anchor_means, groundtruth_box_corners, gt_class_targets):
      groundtruth_boxlist = box_list.BoxList(groundtruth_box_corners)
      gt_box_batch = [groundtruth_boxlist]
      gt_class_targets_batch = [gt_class_targets]
      anchors_boxlist = box_list.BoxList(anchor_means)

      multiclass_target_assigner = self._get_target_assigner()
      num_classes = 3
      unmatched_class_label = tf.constant([1] + num_classes * [0], tf.float32)
      (cls_targets, cls_weights, reg_targets, reg_weights,
       _) = targetassigner.batch_assign_targets(
           multiclass_target_assigner, anchors_boxlist,
           gt_box_batch, gt_class_targets_batch, unmatched_class_label)
      return (cls_targets, cls_weights, reg_targets, reg_weights)

    groundtruth_box_corners = np.zeros((0, 4), dtype=np.float32)
    anchor_means = np.array([[0, 0, .25, .25],
                             [0, .25, 1, 1]], dtype=np.float32)
    exp_cls_targets = [[[1, 0, 0, 0],
                        [1, 0, 0, 0]]]
    exp_cls_weights = [[[1, 1, 1, 1],
                        [1, 1, 1, 1]]]
    exp_reg_targets = [[[0, 0, 0, 0],
                        [0, 0, 0, 0]]]
    exp_reg_weights = [[0, 0]]
    num_classes = 3
    pad = 1
    gt_class_targets = np.zeros((0, num_classes + pad), dtype=np.float32)

    (cls_targets_out,
     cls_weights_out, reg_targets_out, reg_weights_out) = self.execute(
         graph_fn, [anchor_means, groundtruth_box_corners, gt_class_targets])
    self.assertAllClose(cls_targets_out, exp_cls_targets)
    self.assertAllClose(cls_weights_out, exp_cls_weights)
    self.assertAllClose(reg_targets_out, exp_reg_targets)
    self.assertAllClose(reg_weights_out, exp_reg_weights)


class BatchGetTargetsTest(test_case.TestCase):

  def test_scalar_targets(self):
    batch_match = np.array([[1, 0, 1],
                            [-2, -1, 1]], dtype=np.int32)
    groundtruth_tensors_list = np.array([[11, 12], [13, 14]], dtype=np.int32)
    groundtruth_weights_list = np.array([[1.0, 1.0], [1.0, 0.5]],
                                        dtype=np.float32)
    unmatched_value = np.array(99, dtype=np.int32)
    unmatched_weight = np.array(0.0, dtype=np.float32)

    def graph_fn(batch_match, groundtruth_tensors_list,
                 groundtruth_weights_list, unmatched_value, unmatched_weight):
      targets, weights = targetassigner.batch_get_targets(
          batch_match, tf.unstack(groundtruth_tensors_list),
          tf.unstack(groundtruth_weights_list),
          unmatched_value, unmatched_weight)
      return (targets, weights)

    (targets_np, weights_np) = self.execute(graph_fn, [
        batch_match, groundtruth_tensors_list, groundtruth_weights_list,
        unmatched_value, unmatched_weight
    ])
    self.assertAllEqual([[12, 11, 12],
                         [99, 99, 14]], targets_np)
    self.assertAllClose([[1.0, 1.0, 1.0],
                         [0.0, 0.0, 0.5]], weights_np)

  def test_1d_targets(self):
    batch_match = np.array([[1, 0, 1],
                            [-2, -1, 1]], dtype=np.int32)
    groundtruth_tensors_list = np.array([[[11, 12], [12, 13]],
                                         [[13, 14], [14, 15]]],
                                        dtype=np.float32)
    groundtruth_weights_list = np.array([[1.0, 1.0], [1.0, 0.5]],
                                        dtype=np.float32)
    unmatched_value = np.array([99, 99], dtype=np.float32)
    unmatched_weight = np.array(0.0, dtype=np.float32)

    def graph_fn(batch_match, groundtruth_tensors_list,
                 groundtruth_weights_list, unmatched_value, unmatched_weight):
      targets, weights = targetassigner.batch_get_targets(
          batch_match, tf.unstack(groundtruth_tensors_list),
          tf.unstack(groundtruth_weights_list),
          unmatched_value, unmatched_weight)
      return (targets, weights)

    (targets_np, weights_np) = self.execute(graph_fn, [
        batch_match, groundtruth_tensors_list, groundtruth_weights_list,
        unmatched_value, unmatched_weight
    ])
    self.assertAllClose([[[12, 13], [11, 12], [12, 13]],
                         [[99, 99], [99, 99], [14, 15]]], targets_np)
    self.assertAllClose([[1.0, 1.0, 1.0],
                         [0.0, 0.0, 0.5]], weights_np)


class BatchTargetAssignConfidencesTest(test_case.TestCase):

  def _get_target_assigner(self):
    similarity_calc = region_similarity_calculator.IouSimilarity()
    matcher = argmax_matcher.ArgMaxMatcher(matched_threshold=0.5,
                                           unmatched_threshold=0.5)
    box_coder = mean_stddev_box_coder.MeanStddevBoxCoder(stddev=0.1)
    return targetassigner.TargetAssigner(similarity_calc, matcher, box_coder)

  def test_batch_assign_empty_groundtruth(self):

    def graph_fn(anchor_means, groundtruth_box_corners, gt_class_confidences):
      groundtruth_boxlist = box_list.BoxList(groundtruth_box_corners)
      gt_box_batch = [groundtruth_boxlist]
      gt_class_confidences_batch = [gt_class_confidences]
      anchors_boxlist = box_list.BoxList(anchor_means)

      num_classes = 3
      implicit_class_weight = 0.5
      unmatched_class_label = tf.constant([1] + num_classes * [0], tf.float32)
      multiclass_target_assigner = self._get_target_assigner()
      (cls_targets, cls_weights, reg_targets, reg_weights,
       _) = targetassigner.batch_assign_confidences(
           multiclass_target_assigner,
           anchors_boxlist,
           gt_box_batch,
           gt_class_confidences_batch,
           unmatched_class_label=unmatched_class_label,
           include_background_class=True,
           implicit_class_weight=implicit_class_weight)
      return (cls_targets, cls_weights, reg_targets, reg_weights)

    groundtruth_box_corners = np.zeros((0, 4), dtype=np.float32)
    anchor_means = np.array([[0, 0, .25, .25],
                             [0, .25, 1, 1]], dtype=np.float32)
    num_classes = 3
    pad = 1
    gt_class_confidences = np.zeros((0, num_classes + pad), dtype=np.float32)

    exp_cls_targets = [[[1, 0, 0, 0],
                        [1, 0, 0, 0]]]
    exp_cls_weights = [[[0.5, 0.5, 0.5, 0.5],
                        [0.5, 0.5, 0.5, 0.5]]]
    exp_reg_targets = [[[0, 0, 0, 0],
                        [0, 0, 0, 0]]]
    exp_reg_weights = [[0, 0]]

    (cls_targets_out,
     cls_weights_out, reg_targets_out, reg_weights_out) = self.execute(
         graph_fn,
         [anchor_means, groundtruth_box_corners, gt_class_confidences])
    self.assertAllClose(cls_targets_out, exp_cls_targets)
    self.assertAllClose(cls_weights_out, exp_cls_weights)
    self.assertAllClose(reg_targets_out, exp_reg_targets)
    self.assertAllClose(reg_weights_out, exp_reg_weights)

  def test_batch_assign_confidences_agnostic(self):

    def graph_fn(anchor_means, groundtruth_boxlist1, groundtruth_boxlist2):
      box_list1 = box_list.BoxList(groundtruth_boxlist1)
      box_list2 = box_list.BoxList(groundtruth_boxlist2)
      gt_box_batch = [box_list1, box_list2]
      gt_class_confidences_batch = [None, None]
      anchors_boxlist = box_list.BoxList(anchor_means)
      agnostic_target_assigner = self._get_target_assigner()
      implicit_class_weight = 0.5
      (cls_targets, cls_weights, reg_targets, reg_weights,
       _) = targetassigner.batch_assign_confidences(
           agnostic_target_assigner,
           anchors_boxlist,
           gt_box_batch,
           gt_class_confidences_batch,
           include_background_class=False,
           implicit_class_weight=implicit_class_weight)
      return (cls_targets, cls_weights, reg_targets, reg_weights)

    groundtruth_boxlist1 = np.array([[0., 0., 0.2, 0.2]], dtype=np.float32)
    groundtruth_boxlist2 = np.array([[0, 0.25123152, 1, 1],
                                     [0.015789, 0.0985, 0.55789, 0.3842]],
                                    dtype=np.float32)
    anchor_means = np.array([[0, 0, .25, .25],
                             [0, .25, 1, 1],
                             [0, .1, .5, .5],
                             [.75, .75, 1, 1]], dtype=np.float32)

    exp_cls_targets = [[[1], [0], [0], [0]],
                       [[0], [1], [1], [0]]]
    exp_cls_weights = [[[1], [0.5], [0.5], [0.5]],
                       [[0.5], [1], [1], [0.5]]]
    exp_reg_targets = [[[0, 0, -0.5, -0.5],
                        [0, 0, 0, 0],
                        [0, 0, 0, 0,],
                        [0, 0, 0, 0,],],
                       [[0, 0, 0, 0,],
                        [0, 0.01231521, 0, 0],
                        [0.15789001, -0.01500003, 0.57889998, -1.15799987],
                        [0, 0, 0, 0]]]
    exp_reg_weights = [[1, 0, 0, 0],
                       [0, 1, 1, 0]]

    (cls_targets_out,
     cls_weights_out, reg_targets_out, reg_weights_out) = self.execute(
         graph_fn, [anchor_means, groundtruth_boxlist1, groundtruth_boxlist2])
    self.assertAllClose(cls_targets_out, exp_cls_targets)
    self.assertAllClose(cls_weights_out, exp_cls_weights)
    self.assertAllClose(reg_targets_out, exp_reg_targets)
    self.assertAllClose(reg_weights_out, exp_reg_weights)

  def test_batch_assign_confidences_multiclass(self):

    def graph_fn(anchor_means, groundtruth_boxlist1, groundtruth_boxlist2,
                 class_targets1, class_targets2):
      box_list1 = box_list.BoxList(groundtruth_boxlist1)
      box_list2 = box_list.BoxList(groundtruth_boxlist2)
      gt_box_batch = [box_list1, box_list2]
      gt_class_confidences_batch = [class_targets1, class_targets2]
      anchors_boxlist = box_list.BoxList(anchor_means)
      multiclass_target_assigner = self._get_target_assigner()
      num_classes = 3
      implicit_class_weight = 0.5
      unmatched_class_label = tf.constant([1] + num_classes * [0], tf.float32)
      (cls_targets, cls_weights, reg_targets, reg_weights,
       _) = targetassigner.batch_assign_confidences(
           multiclass_target_assigner,
           anchors_boxlist,
           gt_box_batch,
           gt_class_confidences_batch,
           unmatched_class_label=unmatched_class_label,
           include_background_class=True,
           implicit_class_weight=implicit_class_weight)
      return (cls_targets, cls_weights, reg_targets, reg_weights)

    groundtruth_boxlist1 = np.array([[0., 0., 0.2, 0.2]], dtype=np.float32)
    groundtruth_boxlist2 = np.array([[0, 0.25123152, 1, 1],
                                     [0.015789, 0.0985, 0.55789, 0.3842]],
                                    dtype=np.float32)
    class_targets1 = np.array([[0, 1, 0, 0]], dtype=np.float32)
    class_targets2 = np.array([[0, 0, 0, 1],
                               [0, 0, -1, 0]], dtype=np.float32)

    anchor_means = np.array([[0, 0, .25, .25],
                             [0, .25, 1, 1],
                             [0, .1, .5, .5],
                             [.75, .75, 1, 1]], dtype=np.float32)
    exp_cls_targets = [[[0, 1, 0, 0],
                        [1, 0, 0, 0],
                        [1, 0, 0, 0],
                        [1, 0, 0, 0]],
                       [[1, 0, 0, 0],
                        [0, 0, 0, 1],
                        [1, 0, 0, 0],
                        [1, 0, 0, 0]]]
    exp_cls_weights = [[[1, 1, 0.5, 0.5],
                        [0.5, 0.5, 0.5, 0.5],
                        [0.5, 0.5, 0.5, 0.5],
                        [0.5, 0.5, 0.5, 0.5]],
                       [[0.5, 0.5, 0.5, 0.5],
                        [1, 0.5, 0.5, 1],
                        [0.5, 0.5, 1, 0.5],
                        [0.5, 0.5, 0.5, 0.5]]]
    exp_reg_targets = [[[0, 0, -0.5, -0.5],
                        [0, 0, 0, 0],
                        [0, 0, 0, 0,],
                        [0, 0, 0, 0,],],
                       [[0, 0, 0, 0,],
                        [0, 0.01231521, 0, 0],
                        [0, 0, 0, 0],
                        [0, 0, 0, 0]]]
    exp_reg_weights = [[1, 0, 0, 0],
                       [0, 1, 0, 0]]

    (cls_targets_out, cls_weights_out, reg_targets_out,
     reg_weights_out) = self.execute(graph_fn, [
         anchor_means, groundtruth_boxlist1, groundtruth_boxlist2,
         class_targets1, class_targets2
     ])
    self.assertAllClose(cls_targets_out, exp_cls_targets)
    self.assertAllClose(cls_weights_out, exp_cls_weights)
    self.assertAllClose(reg_targets_out, exp_reg_targets)
    self.assertAllClose(reg_weights_out, exp_reg_weights)

  def test_batch_assign_confidences_multiclass_with_padded_groundtruth(self):

    def graph_fn(anchor_means, groundtruth_boxlist1, groundtruth_boxlist2,
                 class_targets1, class_targets2, groundtruth_weights1,
                 groundtruth_weights2):
      box_list1 = box_list.BoxList(groundtruth_boxlist1)
      box_list2 = box_list.BoxList(groundtruth_boxlist2)
      gt_box_batch = [box_list1, box_list2]
      gt_class_confidences_batch = [class_targets1, class_targets2]
      gt_weights = [groundtruth_weights1, groundtruth_weights2]
      anchors_boxlist = box_list.BoxList(anchor_means)
      multiclass_target_assigner = self._get_target_assigner()
      num_classes = 3
      unmatched_class_label = tf.constant([1] + num_classes * [0], tf.float32)
      implicit_class_weight = 0.5
      (cls_targets, cls_weights, reg_targets, reg_weights,
       _) = targetassigner.batch_assign_confidences(
           multiclass_target_assigner,
           anchors_boxlist,
           gt_box_batch,
           gt_class_confidences_batch,
           gt_weights,
           unmatched_class_label=unmatched_class_label,
           include_background_class=True,
           implicit_class_weight=implicit_class_weight)

      return (cls_targets, cls_weights, reg_targets, reg_weights)

    groundtruth_boxlist1 = np.array([[0., 0., 0.2, 0.2],
                                     [0., 0., 0., 0.]], dtype=np.float32)
    groundtruth_weights1 = np.array([1, 0], dtype=np.float32)
    groundtruth_boxlist2 = np.array([[0, 0.25123152, 1, 1],
                                     [0.015789, 0.0985, 0.55789, 0.3842],
                                     [0, 0, 0, 0]],
                                    dtype=np.float32)
    groundtruth_weights2 = np.array([1, 1, 0], dtype=np.float32)
    class_targets1 = np.array([[0, 1, 0, 0], [0, 0, 0, 0]], dtype=np.float32)
    class_targets2 = np.array([[0, 0, 0, 1],
                               [0, 0, -1, 0],
                               [0, 0, 0, 0]], dtype=np.float32)
    anchor_means = np.array([[0, 0, .25, .25],
                             [0, .25, 1, 1],
                             [0, .1, .5, .5],
                             [.75, .75, 1, 1]], dtype=np.float32)

    exp_cls_targets = [[[0, 1, 0, 0],
                        [1, 0, 0, 0],
                        [1, 0, 0, 0],
                        [1, 0, 0, 0]],
                       [[1, 0, 0, 0],
                        [0, 0, 0, 1],
                        [1, 0, 0, 0],
                        [1, 0, 0, 0]]]
    exp_cls_weights = [[[1, 1, 0.5, 0.5],
                        [0.5, 0.5, 0.5, 0.5],
                        [0.5, 0.5, 0.5, 0.5],
                        [0.5, 0.5, 0.5, 0.5]],
                       [[0.5, 0.5, 0.5, 0.5],
                        [1, 0.5, 0.5, 1],
                        [0.5, 0.5, 1, 0.5],
                        [0.5, 0.5, 0.5, 0.5]]]
    exp_reg_targets = [[[0, 0, -0.5, -0.5],
                        [0, 0, 0, 0],
                        [0, 0, 0, 0,],
                        [0, 0, 0, 0,],],
                       [[0, 0, 0, 0,],
                        [0, 0.01231521, 0, 0],
                        [0, 0, 0, 0],
                        [0, 0, 0, 0]]]
    exp_reg_weights = [[1, 0, 0, 0],
                       [0, 1, 0, 0]]

    (cls_targets_out, cls_weights_out, reg_targets_out,
     reg_weights_out) = self.execute(graph_fn, [
         anchor_means, groundtruth_boxlist1, groundtruth_boxlist2,
         class_targets1, class_targets2, groundtruth_weights1,
         groundtruth_weights2
     ])
    self.assertAllClose(cls_targets_out, exp_cls_targets)
    self.assertAllClose(cls_weights_out, exp_cls_weights)
    self.assertAllClose(reg_targets_out, exp_reg_targets)
    self.assertAllClose(reg_weights_out, exp_reg_weights)

  def test_batch_assign_confidences_multidimensional(self):

    def graph_fn(anchor_means, groundtruth_boxlist1, groundtruth_boxlist2,
                 class_targets1, class_targets2):
      box_list1 = box_list.BoxList(groundtruth_boxlist1)
      box_list2 = box_list.BoxList(groundtruth_boxlist2)
      gt_box_batch = [box_list1, box_list2]
      gt_class_confidences_batch = [class_targets1, class_targets2]
      anchors_boxlist = box_list.BoxList(anchor_means)
      multiclass_target_assigner = self._get_target_assigner()
      target_dimensions = (2, 3)
      unmatched_class_label = tf.constant(np.zeros(target_dimensions),
                                          tf.float32)
      implicit_class_weight = 0.5
      (cls_targets, cls_weights, reg_targets, reg_weights,
       _) = targetassigner.batch_assign_confidences(
           multiclass_target_assigner,
           anchors_boxlist,
           gt_box_batch,
           gt_class_confidences_batch,
           unmatched_class_label=unmatched_class_label,
           include_background_class=True,
           implicit_class_weight=implicit_class_weight)
      return (cls_targets, cls_weights, reg_targets, reg_weights)

    groundtruth_boxlist1 = np.array([[0., 0., 0.2, 0.2]], dtype=np.float32)
    groundtruth_boxlist2 = np.array([[0, 0.25123152, 1, 1],
                                     [0.015789, 0.0985, 0.55789, 0.3842]],
                                    dtype=np.float32)
    class_targets1 = np.array([[0, 1, 0, 0]], dtype=np.float32)
    class_targets2 = np.array([[0, 0, 0, 1],
                               [0, 0, 1, 0]], dtype=np.float32)
    class_targets1 = np.array([[[0, 1, 1],
                                [1, 1, 0]]], dtype=np.float32)
    class_targets2 = np.array([[[0, 1, 1],
                                [1, 1, 0]],
                               [[0, 0, 1],
                                [0, 0, 1]]], dtype=np.float32)

    anchor_means = np.array([[0, 0, .25, .25],
                             [0, .25, 1, 1],
                             [0, .1, .5, .5],
                             [.75, .75, 1, 1]], dtype=np.float32)

    with self.assertRaises(ValueError):
      _, _, _, _ = self.execute(graph_fn, [
          anchor_means, groundtruth_boxlist1, groundtruth_boxlist2,
          class_targets1, class_targets2
      ])


class CreateTargetAssignerTest(tf.test.TestCase):

  def test_create_target_assigner(self):
    """Tests that named constructor gives working target assigners.

    TODO(rathodv): Make this test more general.
    """
    corners = [[0.0, 0.0, 1.0, 1.0]]
    groundtruth = box_list.BoxList(tf.constant(corners))

    priors = box_list.BoxList(tf.constant(corners))
    multibox_ta = (targetassigner
                   .create_target_assigner('Multibox', stage='proposal'))
    multibox_ta.assign(priors, groundtruth)
    # No tests on output, as that may vary arbitrarily as new target assigners
    # are added. As long as it is constructed correctly and runs without errors,
    # tests on the individual assigners cover correctness of the assignments.

    anchors = box_list.BoxList(tf.constant(corners))
    faster_rcnn_proposals_ta = (targetassigner
                                .create_target_assigner('FasterRCNN',
                                                        stage='proposal'))
    faster_rcnn_proposals_ta.assign(anchors, groundtruth)

    fast_rcnn_ta = (targetassigner
                    .create_target_assigner('FastRCNN'))
    fast_rcnn_ta.assign(anchors, groundtruth)

    faster_rcnn_detection_ta = (targetassigner
                                .create_target_assigner('FasterRCNN',
                                                        stage='detection'))
    faster_rcnn_detection_ta.assign(anchors, groundtruth)

    with self.assertRaises(ValueError):
      targetassigner.create_target_assigner('InvalidDetector',
                                            stage='invalid_stage')


if __name__ == '__main__':
  tf.test.main()
