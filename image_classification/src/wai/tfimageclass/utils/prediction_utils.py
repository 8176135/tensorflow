# Copyright 2015 The TensorFlow Authors. All Rights Reserved.
# Copyright 2019 University of Waikato, Hamilton, NZ.
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

import numpy as np
import tensorflow as tf


def load_graph(model_file):
    """
    Loads the model from disk.

    :param model_file: the model to load
    :type model_file: str
    :return: the graph
    :rtype: tf.Graph
    """

    graph = tf.Graph()
    graph_def = tf.compat.v1.GraphDef()

    with open(model_file, "rb") as f:
        graph_def.ParseFromString(f.read())
    with graph.as_default():
        tf.import_graph_def(graph_def)

    return graph


def read_tensor_from_image_file(file_name,
                                input_height,
                                input_width,
                                input_mean=0,
                                input_std=255,
                                sess=None):
    """
    Reads the tensor from the image file.

    :param file_name: the image to load
    :type file_name: str
    :param input_height: the image height
    :type input_height: int
    :param input_width: the image width
    :type input_width: int
    :param input_mean: the mean to use
    :type input_mean: int
    :param input_std: the standard deviation to use
    :type input_std: int
    :return: the tensor
    :param sess: the tensorflow session to use
    :type sess: tf.Session
    """

    input_name = "file_reader"
    file_reader = tf.io.read_file(file_name, input_name)
    if file_name.lower().endswith(".png"):
        image_reader = tf.image.decode_png(file_reader, channels=3, name="png_reader")
    elif file_name.lower().endswith(".gif"):
        image_reader = tf.squeeze(tf.image.decode_gif(file_reader, name="gif_reader"))
    elif file_name.lower().endswith(".bmp"):
        image_reader = tf.image.decode_bmp(file_reader, name="bmp_reader")
    else:
        image_reader = tf.image.decode_jpeg(file_reader, channels=3, name="jpeg_reader")
    float_caster = tf.cast(image_reader, tf.float32)
    dims_expander = tf.expand_dims(float_caster, 0)
    resized = tf.compat.v1.image.resize_bilinear(dims_expander, [input_height, input_width])
    normalized = tf.divide(tf.subtract(resized, [input_mean]), [input_std])
    if sess is None:
        sess = tf.compat.v1.Session()
    result = sess.run(normalized)

    return result


def load_labels(label_file):
    """
    Loads the labels from the specified text file.

    :param label_file: the text file with the labels
    :type label_file: str
    :return: the list of labels
    :rtype: list
    """

    label = []
    proto_as_ascii_lines = tf.io.gfile.GFile(label_file).readlines()
    for l in proto_as_ascii_lines:
        label.append(l.rstrip())
    return label


def tensor_to_probs(graph, input_layer, output_layer, tensor, sess=None):
    """
    Turns the image tensor into probabilities.

    :param graph: the underlying graph
    :type graph: tf.Graph
    :param input_layer: the input layer name
    :type input_layer: str
    :param output_layer:  the output layer name
    :type output_layer: str
    :param tensor: the image tensor
    :return: the probabilities
    :rtype: ndarray
    :param sess: the tensorflow session to use
    :type sess: tf.Session
    """
    input_operation = graph.get_operation_by_name("import/" + input_layer)
    output_operation = graph.get_operation_by_name("import/" + output_layer)

    if sess is None:
        with tf.compat.v1.Session(graph=graph) as sess:
            results = sess.run(output_operation.outputs[0], {
                input_operation.outputs[0]: tensor
            })
    else:
        results = sess.run(output_operation.outputs[0], {
            input_operation.outputs[0]: tensor
        })

    return np.squeeze(results)


def top_k_probs(probs, k):
    """
    Returns the top K probabilities.

    :param probs: the ndarray with the probabilities
    :type probs: ndarray
    :param k: the number of top probabilities to return, use -1 for all
    :type k: int
    :return: the
    """

    if k > 0:
        return probs.argsort()[-k:][::-1]
    else:
        return probs.argsort()[:][::-1]
