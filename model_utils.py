import tensorflow as tf
import numpy as np

vgg_weights = np.load('./pretrained_weights/vgg16_weights.npz')


def conv_layer(parent, kernel, bias, name):
    """
    This simple utility function create a convolution layer
    and applied relu activation.

    :param parent:
    :param kernel: Kernel weight tensor
    :param bias: Bias tensor
    :param name: Name of this layer
    :return: Convolution layer created according to the given parameters.
    """
    with tf.variable_scope(name) as scope:
        init = tf.constant_initializer(value=kernel, dtype=tf.float32)
        kernel = tf.get_variable(name="weights", initializer=init, shape=kernel.shape)
        conv = tf.nn.conv2d(parent, kernel, [1, 1, 1, 1], padding='SAME')

        init = tf.constant_initializer(value=bias, dtype=tf.float32)
        biases = tf.get_variable(name="biases", initializer=init, shape=bias.shape)

        conv_with_bias = tf.nn.bias_add(conv, biases)
        conv_with_relu = tf.nn.relu(conv_with_bias, name=scope.name)
    return conv_with_relu


def max_pool_layer(parent, kernel, stride, name, padding='SAME'):
    max_pool = tf.nn.max_pool(parent, ksize=kernel, strides=stride, padding=padding, name=name)
    return max_pool


def fully_collected_layer(parent, name, num_classes=2):
    with tf.variable_scope(name) as scope:
        if name == 'fc_1':
            kernel = _reshape_fc_weights('fc6_W', [7, 7, 512, 4096])
            conv = tf.nn.conv2d(parent, kernel, [1, 1, 1, 1], padding='SAME')
            bias = _get_bias('fc6_b')
            output = tf.nn.bias_add(conv, bias)
            return tf.nn.relu(output, name=scope.name)

        if name == 'fc_2':
            kernel = _reshape_fc_weights('fc7_W', [1, 1, 4096, 4096])
            conv = tf.nn.conv2d(parent, kernel, [1, 1, 1, 1], padding='SAME')
            bias = _get_bias('fc7_b')
            output = tf.nn.bias_add(conv, bias)
            return tf.nn.relu(output, name=scope.name)

        if name == 'fc_3':
            initial = tf.truncated_normal([1, 1, 4096, num_classes], stddev=0.01)
            kernel = tf.get_variable('kernel', initializer=initial)
            conv = tf.nn.conv2d(parent, kernel, [1, 1, 1, 1], padding='SAME')
            initial = tf.constant(0.0, shape=[num_classes])
            bias = tf.get_variable('bias', initializer=initial)
            output = tf.nn.bias_add(conv, bias)
            return output

        raise RuntimeError('{} is not supported as a fully connected name'.format(name))


def upsample_layer(bottom, shape, n_channels, name, upscale_factor, num_classes=2):
    kernel_size = 2 * upscale_factor - upscale_factor % 2
    stride = upscale_factor
    strides = [1, stride, stride, 1]
    with tf.variable_scope(name):
        output_shape = [shape[0], shape[1], shape[2], num_classes]
        filter_shape = [kernel_size, kernel_size, n_channels, n_channels]
        weights = _get_bilinear_filter(filter_shape, upscale_factor)
        deconv = tf.nn.conv2d_transpose(bottom, weights, output_shape,
                                        strides=strides, padding='SAME')
    return deconv


def _reshape_fc_weights(name, new_shape):
    w = vgg_weights[name]
    w = w.reshape(new_shape)
    init = tf.constant_initializer(value=w,
                                   dtype=tf.float32)
    var = tf.get_variable(name="weights", initializer=init, shape=new_shape)
    return var


def _get_bias(name):
    bias_weights = vgg_weights[name]
    shape = bias_weights.shape
    init = tf.constant_initializer(value=bias_weights, dtype=tf.float32)
    bias = tf.get_variable(name='bias', initializer=init, shape=shape)
    return bias


def _get_bilinear_filter(filter_shape, upscale_factor):
    kernel_size = filter_shape[1]
    if kernel_size % 2 == 1:
        centre_location = upscale_factor - 1
    else:
        centre_location = upscale_factor - 0.5

    bilinear = np.zeros([filter_shape[0], filter_shape[1]])
    for x in range(filter_shape[0]):
        for y in range(filter_shape[1]):
            value = (1 - abs((x - centre_location) / upscale_factor)) * (
                1 - abs((y - centre_location) / upscale_factor))
            bilinear[x, y] = value
    weights = np.zeros(filter_shape)
    for i in range(filter_shape[2]):
        weights[:, :, i, i] = bilinear
    init = tf.constant_initializer(value=weights,
                                   dtype=tf.float32)

    bilinear_weights = tf.get_variable(name="decon_bilinear_filter", initializer=init,
                                       shape=weights.shape)
    return bilinear_weights
