"""
Make an autoencoder using NEF-like (PES-like) batch learning
"""

import collections
import os
import gzip
import cPickle as pickle
import urllib

import numpy as np
import matplotlib.pyplot as plt
plt.ion()

import plotting

import nengo
# from nengo.utils.distributions import UniformHypersphere
from nengo.utils.numpy import norm, rms

def create_mask(n_hid, im_shape, rf_shape, rng=np.random):
    M, N = im_shape
    m, n = rf_shape

    # find random positions for top-left corner of each RF
    i = rng.randint(low=0, high=M-m+1, size=n_hid)
    j = rng.randint(low=0, high=N-n+1, size=n_hid)

    mask = np.zeros((n_hid, M, N), dtype='bool')
    for k in xrange(n_hid):
        mask[k, i[k]:i[k]+m, j[k]:j[k]+n] = True

    mask = mask.reshape(n_hid, n_vis)
    return mask

# --- load the data
filename = 'mnist.pkl.gz'

if not os.path.exists(filename):
    url = 'http://deeplearning.net/data/mnist/mnist.pkl.gz'
    urllib.urlretrieve(url, filename=filename)

with gzip.open(filename, 'rb') as f:
    train, valid, test = pickle.load(f)

train_images, _ = train
test_images, _ = train
for images in [train_images, test_images]:
    images[:] = 2 * images - 1  # normalize to -1 to 1

# --- set up network parameters
n_vis = train_images.shape[1]
n_hid = 500
rng = np.random

if 1:
    rf_shape = (9, 9)
    mask = create_mask(n_hid, (28, 28), rf_shape)
    encoders = rng.normal(size=(n_hid, n_vis)) * mask

encoders = encoders.T
mask = mask.T
encoders /= norm(encoders, axis=0, keepdims=True)

neurons = nengo.LIF()
gain, bias = neurons.gain_bias(200, -0.5)

def encode(x):
    return neurons.rates(np.dot(x, encoders), gain, bias)

# --- train the network
n_epochs = 1
batch_size = 10

batches = train_images.reshape(-1, batch_size, train_images.shape[1])

# determine initial decoders
x = train_images[:1000]
decoders, _ = nengo.decoders.LstsqL2()(encode(x), x)

rate = 0.001

for i in range(n_epochs):
    for x in batches:

        a = encode(x)
        xhat = np.dot(a, decoders)
        x_err = xhat - x

        # update encoders
        a_err = np.dot(x_err, encoders)
        d_encoders = (rate / batch_size) * np.dot(x.T, a_err)
        encoders += d_encoders

        # update decoders
        # d_decoders = (rate / batch_size) * np.dot(a.T, x_err)
        # decoders += d_decoders

        x = train_images[:1000]
        decoders, _ = nengo.decoders.LstsqL2()(encode(x), x)

        # test error
        x = test_images[:200]
        a = encode(x)
        xhat = np.dot(a, decoders)

        plt.figure(99)
        plt.clf()

        plotting.compare(
            [x.reshape(-1, 28, 28), xhat.reshape(-1, 28, 28)],
            rows=5, cols=20, vlims=(-1, 1))
        plt.draw()

        print "error", rms(xhat - x, axis=1).mean()

        # raw_input("key?")
