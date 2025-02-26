# Copyright 2019 The TensorFlow Authors. All Rights Reserved.
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

"""Tests for tensorflow_models.object_detection.core.post_processing."""
import numpy as np
import tensorflow as tf
from wai.tfrecords.object_detection.core import post_processing
from wai.tfrecords.object_detection.core import standard_fields as fields
from wai.tfrecords.object_detection.utils import test_case


class MulticlassNonMaxSuppressionTest(test_case.TestCase):

  def test_multiclass_nms_select_with_shared_boxes(self):
    boxes = tf.constant([[[0, 0, 1, 1]],
                         [[0, 0.1, 1, 1.1]],
                         [[0, -0.1, 1, 0.9]],
                         [[0, 10, 1, 11]],
                         [[0, 10.1, 1, 11.1]],
                         [[0, 100, 1, 101]],
                         [[0, 1000, 1, 1002]],
                         [[0, 1000, 1, 1002.1]]], tf.float32)
    scores = tf.constant([[.9, 0.01], [.75, 0.05],
                          [.6, 0.01], [.95, 0],
                          [.5, 0.01], [.3, 0.01],
                          [.01, .85], [.01, .5]])
    score_thresh = 0.1
    iou_thresh = .5
    max_output_size = 4

    exp_nms_corners = [[0, 10, 1, 11],
                       [0, 0, 1, 1],
                       [0, 1000, 1, 1002],
                       [0, 100, 1, 101]]
    exp_nms_scores = [.95, .9, .85, .3]
    exp_nms_classes = [0, 0, 1, 0]

    nms, _ = post_processing.multiclass_non_max_suppression(
        boxes, scores, score_thresh, iou_thresh, max_output_size)
    with self.test_session() as sess:
      nms_corners_output, nms_scores_output, nms_classes_output = sess.run(
          [nms.get(), nms.get_field(fields.BoxListFields.scores),
           nms.get_field(fields.BoxListFields.classes)])
      self.assertAllClose(nms_corners_output, exp_nms_corners)
      self.assertAllClose(nms_scores_output, exp_nms_scores)
      self.assertAllClose(nms_classes_output, exp_nms_classes)

  def test_multiclass_nms_select_with_shared_boxes_pad_to_max_output_size(self):
    boxes = np.array([[[0, 0, 1, 1]],
                      [[0, 0.1, 1, 1.1]],
                      [[0, -0.1, 1, 0.9]],
                      [[0, 10, 1, 11]],
                      [[0, 10.1, 1, 11.1]],
                      [[0, 100, 1, 101]],
                      [[0, 1000, 1, 1002]],
                      [[0, 1000, 1, 1002.1]]], np.float32)
    scores = np.array([[.9, 0.01], [.75, 0.05],
                       [.6, 0.01], [.95, 0],
                       [.5, 0.01], [.3, 0.01],
                       [.01, .85], [.01, .5]], np.float32)
    score_thresh = 0.1
    iou_thresh = .5
    max_size_per_class = 4
    max_output_size = 5

    exp_nms_corners = [[0, 10, 1, 11],
                       [0, 0, 1, 1],
                       [0, 1000, 1, 1002],
                       [0, 100, 1, 101]]
    exp_nms_scores = [.95, .9, .85, .3]
    exp_nms_classes = [0, 0, 1, 0]

    def graph_fn(boxes, scores):
      nms, num_valid_nms_boxes = post_processing.multiclass_non_max_suppression(
          boxes,
          scores,
          score_thresh,
          iou_thresh,
          max_size_per_class,
          max_total_size=max_output_size,
          pad_to_max_output_size=True)
      return [nms.get(), nms.get_field(fields.BoxListFields.scores),
              nms.get_field(fields.BoxListFields.classes), num_valid_nms_boxes]

    [nms_corners_output, nms_scores_output, nms_classes_output,
     num_valid_nms_boxes] = self.execute(graph_fn, [boxes, scores])

    self.assertEqual(num_valid_nms_boxes, 4)
    self.assertAllClose(nms_corners_output[0:num_valid_nms_boxes],
                        exp_nms_corners)
    self.assertAllClose(nms_scores_output[0:num_valid_nms_boxes],
                        exp_nms_scores)
    self.assertAllClose(nms_classes_output[0:num_valid_nms_boxes],
                        exp_nms_classes)

  def test_multiclass_nms_select_with_shared_boxes_given_keypoints(self):
    boxes = tf.constant([[[0, 0, 1, 1]],
                         [[0, 0.1, 1, 1.1]],
                         [[0, -0.1, 1, 0.9]],
                         [[0, 10, 1, 11]],
                         [[0, 10.1, 1, 11.1]],
                         [[0, 100, 1, 101]],
                         [[0, 1000, 1, 1002]],
                         [[0, 1000, 1, 1002.1]]], tf.float32)
    scores = tf.constant([[.9, 0.01], [.75, 0.05],
                          [.6, 0.01], [.95, 0],
                          [.5, 0.01], [.3, 0.01],
                          [.01, .85], [.01, .5]])
    num_keypoints = 6
    keypoints = tf.tile(
        tf.reshape(tf.range(8), [8, 1, 1]),
        [1, num_keypoints, 2])
    score_thresh = 0.1
    iou_thresh = .5
    max_output_size = 4

    exp_nms_corners = [[0, 10, 1, 11],
                       [0, 0, 1, 1],
                       [0, 1000, 1, 1002],
                       [0, 100, 1, 101]]
    exp_nms_scores = [.95, .9, .85, .3]
    exp_nms_classes = [0, 0, 1, 0]
    exp_nms_keypoints_tensor = tf.tile(
        tf.reshape(tf.constant([3, 0, 6, 5], dtype=tf.float32), [4, 1, 1]),
        [1, num_keypoints, 2])

    nms, _ = post_processing.multiclass_non_max_suppression(
        boxes,
        scores,
        score_thresh,
        iou_thresh,
        max_output_size,
        additional_fields={fields.BoxListFields.keypoints: keypoints})

    with self.test_session() as sess:
      (nms_corners_output,
       nms_scores_output,
       nms_classes_output,
       nms_keypoints,
       exp_nms_keypoints) = sess.run([
           nms.get(),
           nms.get_field(fields.BoxListFields.scores),
           nms.get_field(fields.BoxListFields.classes),
           nms.get_field(fields.BoxListFields.keypoints),
           exp_nms_keypoints_tensor
       ])
      self.assertAllClose(nms_corners_output, exp_nms_corners)
      self.assertAllClose(nms_scores_output, exp_nms_scores)
      self.assertAllClose(nms_classes_output, exp_nms_classes)
      self.assertAllEqual(nms_keypoints, exp_nms_keypoints)

  def test_multiclass_nms_with_shared_boxes_given_keypoint_heatmaps(self):
    boxes = tf.constant([[[0, 0, 1, 1]],
                         [[0, 0.1, 1, 1.1]],
                         [[0, -0.1, 1, 0.9]],
                         [[0, 10, 1, 11]],
                         [[0, 10.1, 1, 11.1]],
                         [[0, 100, 1, 101]],
                         [[0, 1000, 1, 1002]],
                         [[0, 1000, 1, 1002.1]]], tf.float32)

    scores = tf.constant([[.9, 0.01], [.75, 0.05],
                          [.6, 0.01], [.95, 0],
                          [.5, 0.01], [.3, 0.01],
                          [.01, .85], [.01, .5]])

    num_boxes = tf.shape(boxes)[0]
    heatmap_height = 5
    heatmap_width = 5
    num_keypoints = 17
    keypoint_heatmaps = tf.ones(
        [num_boxes, heatmap_height, heatmap_width, num_keypoints],
        dtype=tf.float32)

    score_thresh = 0.1
    iou_thresh = .5
    max_output_size = 4
    exp_nms_corners = [[0, 10, 1, 11],
                       [0, 0, 1, 1],
                       [0, 1000, 1, 1002],
                       [0, 100, 1, 101]]

    exp_nms_scores = [.95, .9, .85, .3]
    exp_nms_classes = [0, 0, 1, 0]
    exp_nms_keypoint_heatmaps = np.ones(
        (4, heatmap_height, heatmap_width, num_keypoints), dtype=np.float32)

    nms, _ = post_processing.multiclass_non_max_suppression(
        boxes,
        scores,
        score_thresh,
        iou_thresh,
        max_output_size,
        additional_fields={
            fields.BoxListFields.keypoint_heatmaps: keypoint_heatmaps
        })

    with self.test_session() as sess:
      (nms_corners_output,
       nms_scores_output,
       nms_classes_output,
       nms_keypoint_heatmaps) = sess.run(
           [nms.get(),
            nms.get_field(fields.BoxListFields.scores),
            nms.get_field(fields.BoxListFields.classes),
            nms.get_field(fields.BoxListFields.keypoint_heatmaps)])

      self.assertAllClose(nms_corners_output, exp_nms_corners)
      self.assertAllClose(nms_scores_output, exp_nms_scores)
      self.assertAllClose(nms_classes_output, exp_nms_classes)
      self.assertAllEqual(nms_keypoint_heatmaps, exp_nms_keypoint_heatmaps)

  def test_multiclass_nms_with_additional_fields(self):
    boxes = tf.constant([[[0, 0, 1, 1]],
                         [[0, 0.1, 1, 1.1]],
                         [[0, -0.1, 1, 0.9]],
                         [[0, 10, 1, 11]],
                         [[0, 10.1, 1, 11.1]],
                         [[0, 100, 1, 101]],
                         [[0, 1000, 1, 1002]],
                         [[0, 1000, 1, 1002.1]]], tf.float32)

    scores = tf.constant([[.9, 0.01], [.75, 0.05],
                          [.6, 0.01], [.95, 0],
                          [.5, 0.01], [.3, 0.01],
                          [.01, .85], [.01, .5]])

    coarse_boxes_key = 'coarse_boxes'
    coarse_boxes = tf.constant([[0.1, 0.1, 1.1, 1.1],
                                [0.1, 0.2, 1.1, 1.2],
                                [0.1, -0.2, 1.1, 1.0],
                                [0.1, 10.1, 1.1, 11.1],
                                [0.1, 10.2, 1.1, 11.2],
                                [0.1, 100.1, 1.1, 101.1],
                                [0.1, 1000.1, 1.1, 1002.1],
                                [0.1, 1000.1, 1.1, 1002.2]], tf.float32)

    score_thresh = 0.1
    iou_thresh = .5
    max_output_size = 4

    exp_nms_corners = np.array([[0, 10, 1, 11],
                                [0, 0, 1, 1],
                                [0, 1000, 1, 1002],
                                [0, 100, 1, 101]], dtype=np.float32)

    exp_nms_coarse_corners = np.array([[0.1, 10.1, 1.1, 11.1],
                                       [0.1, 0.1, 1.1, 1.1],
                                       [0.1, 1000.1, 1.1, 1002.1],
                                       [0.1, 100.1, 1.1, 101.1]],
                                      dtype=np.float32)

    exp_nms_scores = [.95, .9, .85, .3]
    exp_nms_classes = [0, 0, 1, 0]

    nms, _ = post_processing.multiclass_non_max_suppression(
        boxes,
        scores,
        score_thresh,
        iou_thresh,
        max_output_size,
        additional_fields={coarse_boxes_key: coarse_boxes})

    with self.test_session() as sess:
      (nms_corners_output,
       nms_scores_output,
       nms_classes_output,
       nms_coarse_corners) = sess.run(
           [nms.get(),
            nms.get_field(fields.BoxListFields.scores),
            nms.get_field(fields.BoxListFields.classes),
            nms.get_field(coarse_boxes_key)])

      self.assertAllClose(nms_corners_output, exp_nms_corners)
      self.assertAllClose(nms_scores_output, exp_nms_scores)
      self.assertAllClose(nms_classes_output, exp_nms_classes)
      self.assertAllEqual(nms_coarse_corners, exp_nms_coarse_corners)

  def test_multiclass_nms_select_with_shared_boxes_given_masks(self):
    boxes = tf.constant([[[0, 0, 1, 1]],
                         [[0, 0.1, 1, 1.1]],
                         [[0, -0.1, 1, 0.9]],
                         [[0, 10, 1, 11]],
                         [[0, 10.1, 1, 11.1]],
                         [[0, 100, 1, 101]],
                         [[0, 1000, 1, 1002]],
                         [[0, 1000, 1, 1002.1]]], tf.float32)
    scores = tf.constant([[.9, 0.01], [.75, 0.05],
                          [.6, 0.01], [.95, 0],
                          [.5, 0.01], [.3, 0.01],
                          [.01, .85], [.01, .5]])
    num_classes = 2
    mask_height = 3
    mask_width = 3
    masks = tf.tile(
        tf.reshape(tf.range(8), [8, 1, 1, 1]),
        [1, num_classes, mask_height, mask_width])
    score_thresh = 0.1
    iou_thresh = .5
    max_output_size = 4

    exp_nms_corners = [[0, 10, 1, 11],
                       [0, 0, 1, 1],
                       [0, 1000, 1, 1002],
                       [0, 100, 1, 101]]
    exp_nms_scores = [.95, .9, .85, .3]
    exp_nms_classes = [0, 0, 1, 0]
    exp_nms_masks_tensor = tf.tile(
        tf.reshape(tf.constant([3, 0, 6, 5], dtype=tf.float32), [4, 1, 1]),
        [1, mask_height, mask_width])

    nms, _ = post_processing.multiclass_non_max_suppression(
        boxes, scores, score_thresh, iou_thresh, max_output_size, masks=masks)
    with self.test_session() as sess:
      (nms_corners_output,
       nms_scores_output,
       nms_classes_output,
       nms_masks,
       exp_nms_masks) = sess.run([nms.get(),
                                  nms.get_field(fields.BoxListFields.scores),
                                  nms.get_field(fields.BoxListFields.classes),
                                  nms.get_field(fields.BoxListFields.masks),
                                  exp_nms_masks_tensor])
      self.assertAllClose(nms_corners_output, exp_nms_corners)
      self.assertAllClose(nms_scores_output, exp_nms_scores)
      self.assertAllClose(nms_classes_output, exp_nms_classes)
      self.assertAllEqual(nms_masks, exp_nms_masks)

  def test_multiclass_nms_select_with_clip_window(self):
    boxes = tf.constant([[[0, 0, 10, 10]],
                         [[1, 1, 11, 11]]], tf.float32)
    scores = tf.constant([[.9], [.75]])
    clip_window = tf.constant([5, 4, 8, 7], tf.float32)
    score_thresh = 0.0
    iou_thresh = 0.5
    max_output_size = 100

    exp_nms_corners = [[5, 4, 8, 7]]
    exp_nms_scores = [.9]
    exp_nms_classes = [0]

    nms, _ = post_processing.multiclass_non_max_suppression(
        boxes,
        scores,
        score_thresh,
        iou_thresh,
        max_output_size,
        clip_window=clip_window)
    with self.test_session() as sess:
      nms_corners_output, nms_scores_output, nms_classes_output = sess.run(
          [nms.get(), nms.get_field(fields.BoxListFields.scores),
           nms.get_field(fields.BoxListFields.classes)])
      self.assertAllClose(nms_corners_output, exp_nms_corners)
      self.assertAllClose(nms_scores_output, exp_nms_scores)
      self.assertAllClose(nms_classes_output, exp_nms_classes)

  def test_multiclass_nms_select_with_clip_window_change_coordinate_frame(self):
    boxes = tf.constant([[[0, 0, 10, 10]],
                         [[1, 1, 11, 11]]], tf.float32)
    scores = tf.constant([[.9], [.75]])
    clip_window = tf.constant([5, 4, 8, 7], tf.float32)
    score_thresh = 0.0
    iou_thresh = 0.5
    max_output_size = 100

    exp_nms_corners = [[0, 0, 1, 1]]
    exp_nms_scores = [.9]
    exp_nms_classes = [0]

    nms, _ = post_processing.multiclass_non_max_suppression(
        boxes,
        scores,
        score_thresh,
        iou_thresh,
        max_output_size,
        clip_window=clip_window,
        change_coordinate_frame=True)
    with self.test_session() as sess:
      nms_corners_output, nms_scores_output, nms_classes_output = sess.run(
          [nms.get(), nms.get_field(fields.BoxListFields.scores),
           nms.get_field(fields.BoxListFields.classes)])
      self.assertAllClose(nms_corners_output, exp_nms_corners)
      self.assertAllClose(nms_scores_output, exp_nms_scores)
      self.assertAllClose(nms_classes_output, exp_nms_classes)

  def test_multiclass_nms_select_with_per_class_cap(self):
    boxes = tf.constant([[[0, 0, 1, 1]],
                         [[0, 0.1, 1, 1.1]],
                         [[0, -0.1, 1, 0.9]],
                         [[0, 10, 1, 11]],
                         [[0, 10.1, 1, 11.1]],
                         [[0, 100, 1, 101]],
                         [[0, 1000, 1, 1002]],
                         [[0, 1000, 1, 1002.1]]], tf.float32)
    scores = tf.constant([[.9, 0.01], [.75, 0.05],
                          [.6, 0.01], [.95, 0],
                          [.5, 0.01], [.3, 0.01],
                          [.01, .85], [.01, .5]])
    score_thresh = 0.1
    iou_thresh = .5
    max_size_per_class = 2

    exp_nms_corners = [[0, 10, 1, 11],
                       [0, 0, 1, 1],
                       [0, 1000, 1, 1002]]
    exp_nms_scores = [.95, .9, .85]
    exp_nms_classes = [0, 0, 1]

    nms, _ = post_processing.multiclass_non_max_suppression(
        boxes, scores, score_thresh, iou_thresh, max_size_per_class)
    with self.test_session() as sess:
      nms_corners_output, nms_scores_output, nms_classes_output = sess.run(
          [nms.get(), nms.get_field(fields.BoxListFields.scores),
           nms.get_field(fields.BoxListFields.classes)])
      self.assertAllClose(nms_corners_output, exp_nms_corners)
      self.assertAllClose(nms_scores_output, exp_nms_scores)
      self.assertAllClose(nms_classes_output, exp_nms_classes)

  def test_multiclass_nms_select_with_total_cap(self):
    boxes = tf.constant([[[0, 0, 1, 1]],
                         [[0, 0.1, 1, 1.1]],
                         [[0, -0.1, 1, 0.9]],
                         [[0, 10, 1, 11]],
                         [[0, 10.1, 1, 11.1]],
                         [[0, 100, 1, 101]],
                         [[0, 1000, 1, 1002]],
                         [[0, 1000, 1, 1002.1]]], tf.float32)
    scores = tf.constant([[.9, 0.01], [.75, 0.05],
                          [.6, 0.01], [.95, 0],
                          [.5, 0.01], [.3, 0.01],
                          [.01, .85], [.01, .5]])
    score_thresh = 0.1
    iou_thresh = .5
    max_size_per_class = 4
    max_total_size = 2

    exp_nms_corners = [[0, 10, 1, 11],
                       [0, 0, 1, 1]]
    exp_nms_scores = [.95, .9]
    exp_nms_classes = [0, 0]

    nms, _ = post_processing.multiclass_non_max_suppression(
        boxes, scores, score_thresh, iou_thresh, max_size_per_class,
        max_total_size)
    with self.test_session() as sess:
      nms_corners_output, nms_scores_output, nms_classes_output = sess.run(
          [nms.get(), nms.get_field(fields.BoxListFields.scores),
           nms.get_field(fields.BoxListFields.classes)])
      self.assertAllClose(nms_corners_output, exp_nms_corners)
      self.assertAllClose(nms_scores_output, exp_nms_scores)
      self.assertAllClose(nms_classes_output, exp_nms_classes)

  def test_multiclass_nms_threshold_then_select_with_shared_boxes(self):
    boxes = tf.constant([[[0, 0, 1, 1]],
                         [[0, 0.1, 1, 1.1]],
                         [[0, -0.1, 1, 0.9]],
                         [[0, 10, 1, 11]],
                         [[0, 10.1, 1, 11.1]],
                         [[0, 100, 1, 101]],
                         [[0, 1000, 1, 1002]],
                         [[0, 1000, 1, 1002.1]]], tf.float32)
    scores = tf.constant([[.9], [.75], [.6], [.95], [.5], [.3], [.01], [.01]])
    score_thresh = 0.1
    iou_thresh = .5
    max_output_size = 3

    exp_nms = [[0, 10, 1, 11],
               [0, 0, 1, 1],
               [0, 100, 1, 101]]
    nms, _ = post_processing.multiclass_non_max_suppression(
        boxes, scores, score_thresh, iou_thresh, max_output_size)
    with self.test_session() as sess:
      nms_output = sess.run(nms.get())
      self.assertAllClose(nms_output, exp_nms)

  def test_multiclass_nms_select_with_separate_boxes(self):
    boxes = tf.constant([[[0, 0, 1, 1], [0, 0, 4, 5]],
                         [[0, 0.1, 1, 1.1], [0, 0.1, 2, 1.1]],
                         [[0, -0.1, 1, 0.9], [0, -0.1, 1, 0.9]],
                         [[0, 10, 1, 11], [0, 10, 1, 11]],
                         [[0, 10.1, 1, 11.1], [0, 10.1, 1, 11.1]],
                         [[0, 100, 1, 101], [0, 100, 1, 101]],
                         [[0, 1000, 1, 1002], [0, 999, 2, 1004]],
                         [[0, 1000, 1, 1002.1], [0, 999, 2, 1002.7]]],
                        tf.float32)
    scores = tf.constant([[.9, 0.01], [.75, 0.05],
                          [.6, 0.01], [.95, 0],
                          [.5, 0.01], [.3, 0.01],
                          [.01, .85], [.01, .5]])
    score_thresh = 0.1
    iou_thresh = .5
    max_output_size = 4

    exp_nms_corners = [[0, 10, 1, 11],
                       [0, 0, 1, 1],
                       [0, 999, 2, 1004],
                       [0, 100, 1, 101]]
    exp_nms_scores = [.95, .9, .85, .3]
    exp_nms_classes = [0, 0, 1, 0]

    nms, _ = post_processing.multiclass_non_max_suppression(
        boxes, scores, score_thresh, iou_thresh, max_output_size)
    with self.test_session() as sess:
      nms_corners_output, nms_scores_output, nms_classes_output = sess.run(
          [nms.get(), nms.get_field(fields.BoxListFields.scores),
           nms.get_field(fields.BoxListFields.classes)])
      self.assertAllClose(nms_corners_output, exp_nms_corners)
      self.assertAllClose(nms_scores_output, exp_nms_scores)
      self.assertAllClose(nms_classes_output, exp_nms_classes)



if __name__ == '__main__':
  tf.test.main()
