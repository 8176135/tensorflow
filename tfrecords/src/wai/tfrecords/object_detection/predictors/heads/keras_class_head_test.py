# Copyright 2018 The TensorFlow Authors. All Rights Reserved.
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

"""Tests for object_detection.predictors.heads.class_head."""
import tensorflow as tf

from google.protobuf import text_format
from wai.tfrecords.object_detection.builders import hyperparams_builder
from wai.tfrecords.object_detection.predictors.heads import keras_class_head
from wai.tfrecords.object_detection.protos import hyperparams_pb2
from wai.tfrecords.object_detection.utils import test_case


class ConvolutionalKerasClassPredictorTest(test_case.TestCase):

  def _build_conv_hyperparams(self):
    conv_hyperparams = hyperparams_pb2.Hyperparams()
    conv_hyperparams_text_proto = """
    activation: NONE
      regularizer {
        l2_regularizer {
        }
      }
      initializer {
        truncated_normal_initializer {
        }
      }
    """
    text_format.Merge(conv_hyperparams_text_proto, conv_hyperparams)
    return hyperparams_builder.KerasLayerHyperparams(conv_hyperparams)

  def test_prediction_size_depthwise_false(self):
    conv_hyperparams = self._build_conv_hyperparams()
    class_prediction_head = keras_class_head.ConvolutionalClassHead(
        is_training=True,
        num_class_slots=20,
        use_dropout=True,
        dropout_keep_prob=0.5,
        kernel_size=3,
        conv_hyperparams=conv_hyperparams,
        freeze_batchnorm=False,
        num_predictions_per_location=1,
        use_depthwise=False)
    image_feature = tf.random_uniform(
        [64, 17, 19, 1024], minval=-10.0, maxval=10.0, dtype=tf.float32)
    class_predictions = class_prediction_head(image_feature,)
    self.assertAllEqual([64, 323, 20],
                        class_predictions.get_shape().as_list())

  def test_prediction_size_depthwise_true(self):
    conv_hyperparams = self._build_conv_hyperparams()
    class_prediction_head = keras_class_head.ConvolutionalClassHead(
        is_training=True,
        num_class_slots=20,
        use_dropout=True,
        dropout_keep_prob=0.5,
        kernel_size=3,
        conv_hyperparams=conv_hyperparams,
        freeze_batchnorm=False,
        num_predictions_per_location=1,
        use_depthwise=True)
    image_feature = tf.random_uniform(
        [64, 17, 19, 1024], minval=-10.0, maxval=10.0, dtype=tf.float32)
    class_predictions = class_prediction_head(image_feature,)
    self.assertAllEqual([64, 323, 20],
                        class_predictions.get_shape().as_list())


class MaskRCNNClassHeadTest(test_case.TestCase):

  def _build_fc_hyperparams(self,
                            op_type=hyperparams_pb2.Hyperparams.FC):
    hyperparams = hyperparams_pb2.Hyperparams()
    hyperparams_text_proto = """
      activation: NONE
      regularizer {
        l2_regularizer {
        }
      }
      initializer {
        truncated_normal_initializer {
        }
      }
    """
    text_format.Merge(hyperparams_text_proto, hyperparams)
    hyperparams.op = op_type
    return hyperparams_builder.KerasLayerHyperparams(hyperparams)

  def test_prediction_size(self):
    class_prediction_head = keras_class_head.MaskRCNNClassHead(
        is_training=False,
        num_class_slots=20,
        fc_hyperparams=self._build_fc_hyperparams(),
        freeze_batchnorm=False,
        use_dropout=True,
        dropout_keep_prob=0.5)
    roi_pooled_features = tf.random_uniform(
        [64, 7, 7, 1024], minval=-10.0, maxval=10.0, dtype=tf.float32)
    prediction = class_prediction_head(roi_pooled_features)
    self.assertAllEqual([64, 1, 20], prediction.get_shape().as_list())


class WeightSharedConvolutionalKerasClassPredictorTest(test_case.TestCase):

  def _build_conv_hyperparams(self):
    conv_hyperparams = hyperparams_pb2.Hyperparams()
    conv_hyperparams_text_proto = """
    activation: NONE
      regularizer {
        l2_regularizer {
        }
      }
      initializer {
        truncated_normal_initializer {
        }
      }
    """
    text_format.Merge(conv_hyperparams_text_proto, conv_hyperparams)
    return hyperparams_builder.KerasLayerHyperparams(conv_hyperparams)

  def test_prediction_size_depthwise_false(self):
    conv_hyperparams = self._build_conv_hyperparams()
    class_prediction_head = keras_class_head.WeightSharedConvolutionalClassHead(
        num_class_slots=20,
        conv_hyperparams=conv_hyperparams,
        num_predictions_per_location=1,
        use_depthwise=False)
    image_feature = tf.random_uniform(
        [64, 17, 19, 1024], minval=-10.0, maxval=10.0, dtype=tf.float32)
    class_predictions = class_prediction_head(image_feature)
    self.assertAllEqual([64, 323, 20], class_predictions.get_shape().as_list())

  def test_prediction_size_depthwise_true(self):
    conv_hyperparams = self._build_conv_hyperparams()
    class_prediction_head = keras_class_head.WeightSharedConvolutionalClassHead(
        num_class_slots=20,
        conv_hyperparams=conv_hyperparams,
        num_predictions_per_location=1,
        use_depthwise=True)
    image_feature = tf.random_uniform(
        [64, 17, 19, 1024], minval=-10.0, maxval=10.0, dtype=tf.float32)
    class_predictions = class_prediction_head(image_feature)
    self.assertAllEqual([64, 323, 20], class_predictions.get_shape().as_list())

  def test_variable_count_depth_wise_true(self):
    g = tf.Graph()
    with g.as_default():
      conv_hyperparams = self._build_conv_hyperparams()
      class_prediction_head = (
          keras_class_head.WeightSharedConvolutionalClassHead(
              num_class_slots=20,
              conv_hyperparams=conv_hyperparams,
              num_predictions_per_location=1,
              use_depthwise=True))
      image_feature = tf.random_uniform(
          [64, 17, 19, 1024], minval=-10.0, maxval=10.0, dtype=tf.float32)
      _ = class_prediction_head(image_feature)
      variables = g.get_collection(tf.GraphKeys.GLOBAL_VARIABLES)
    self.assertEqual(len(variables), 3)

  def test_variable_count_depth_wise_False(self):
    g = tf.Graph()
    with g.as_default():
      conv_hyperparams = self._build_conv_hyperparams()
      class_prediction_head = (
          keras_class_head.WeightSharedConvolutionalClassHead(
              num_class_slots=20,
              conv_hyperparams=conv_hyperparams,
              num_predictions_per_location=1,
              use_depthwise=False))
      image_feature = tf.random_uniform(
          [64, 17, 19, 1024], minval=-10.0, maxval=10.0, dtype=tf.float32)
      _ = class_prediction_head(image_feature)
      variables = g.get_collection(tf.GraphKeys.GLOBAL_VARIABLES)
    self.assertEqual(len(variables), 2)


if __name__ == '__main__':
  tf.test.main()
