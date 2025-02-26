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

"""Region Similarity Calculators for BoxLists.

Region Similarity Calculators compare a pairwise measure of similarity
between the boxes in two BoxLists.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from abc import ABCMeta
from abc import abstractmethod

import six
import tensorflow as tf

from wai.tfrecords.object_detection.core import box_list_ops
from wai.tfrecords.object_detection.core import standard_fields as fields


class RegionSimilarityCalculator(six.with_metaclass(ABCMeta, object)):
  """Abstract base class for region similarity calculator."""

  def compare(self, boxlist1, boxlist2, scope=None):
    """Computes matrix of pairwise similarity between BoxLists.

    This op (to be overridden) computes a measure of pairwise similarity between
    the boxes in the given BoxLists. Higher values indicate more similarity.

    Note that this method simply measures similarity and does not explicitly
    perform a matching.

    Args:
      boxlist1: BoxList holding N boxes.
      boxlist2: BoxList holding M boxes.
      scope: Op scope name. Defaults to 'Compare' if None.

    Returns:
      a (float32) tensor of shape [N, M] with pairwise similarity score.
    """
    with tf.name_scope(scope, 'Compare', [boxlist1, boxlist2]) as scope:
      return self._compare(boxlist1, boxlist2)

  @abstractmethod
  def _compare(self, boxlist1, boxlist2):
    pass


class IouSimilarity(RegionSimilarityCalculator):
  """Class to compute similarity based on Intersection over Union (IOU) metric.

  This class computes pairwise similarity between two BoxLists based on IOU.
  """

  def _compare(self, boxlist1, boxlist2):
    """Compute pairwise IOU similarity between the two BoxLists.

    Args:
      boxlist1: BoxList holding N boxes.
      boxlist2: BoxList holding M boxes.

    Returns:
      A tensor with shape [N, M] representing pairwise iou scores.
    """
    return box_list_ops.iou(boxlist1, boxlist2)


class NegSqDistSimilarity(RegionSimilarityCalculator):
  """Class to compute similarity based on the squared distance metric.

  This class computes pairwise similarity between two BoxLists based on the
  negative squared distance metric.
  """

  def _compare(self, boxlist1, boxlist2):
    """Compute matrix of (negated) sq distances.

    Args:
      boxlist1: BoxList holding N boxes.
      boxlist2: BoxList holding M boxes.

    Returns:
      A tensor with shape [N, M] representing negated pairwise squared distance.
    """
    return -1 * box_list_ops.sq_dist(boxlist1, boxlist2)


class IoaSimilarity(RegionSimilarityCalculator):
  """Class to compute similarity based on Intersection over Area (IOA) metric.

  This class computes pairwise similarity between two BoxLists based on their
  pairwise intersections divided by the areas of second BoxLists.
  """

  def _compare(self, boxlist1, boxlist2):
    """Compute pairwise IOA similarity between the two BoxLists.

    Args:
      boxlist1: BoxList holding N boxes.
      boxlist2: BoxList holding M boxes.

    Returns:
      A tensor with shape [N, M] representing pairwise IOA scores.
    """
    return box_list_ops.ioa(boxlist1, boxlist2)


class ThresholdedIouSimilarity(RegionSimilarityCalculator):
  """Class to compute similarity based on thresholded IOU and score.

  This class computes pairwise similarity between two BoxLists based on IOU and
  a 'score' present in boxlist1. If IOU > threshold, then the entry in the
  output pairwise tensor will contain `score`, otherwise 0.
  """

  def __init__(self, iou_threshold=0):
    """Initialize the ThresholdedIouSimilarity.

    Args:
      iou_threshold: For a given pair of boxes, if the IOU is > iou_threshold,
        then the comparison result will be the foreground probability of
        the first box, otherwise it will be zero.
    """
    super(ThresholdedIouSimilarity, self).__init__()
    self._iou_threshold = iou_threshold

  def _compare(self, boxlist1, boxlist2):
    """Compute pairwise IOU similarity between the two BoxLists and score.

    Args:
      boxlist1: BoxList holding N boxes. Must have a score field.
      boxlist2: BoxList holding M boxes.

    Returns:
      A tensor with shape [N, M] representing scores threholded by pairwise
      iou scores.
    """
    ious = box_list_ops.iou(boxlist1, boxlist2)
    scores = boxlist1.get_field(fields.BoxListFields.scores)
    scores = tf.expand_dims(scores, axis=1)
    row_replicated_scores = tf.tile(scores, [1, tf.shape(ious)[-1]])
    thresholded_ious = tf.where(ious > self._iou_threshold,
                                row_replicated_scores, tf.zeros_like(ious))

    return thresholded_ious
