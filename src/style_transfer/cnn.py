import tensorflow as tf
import numpy as np
import datetime
from tensorflow.contrib.layers.python.layers import xavier_initializer, batch_norm
from os.path import dirname, exists
import os

from DataLoader import TrainValSetLoader
from display import show_comparison

# Read username from user.txt. This file will not be synchronized
with open('../../user.txt') as settings_file:
    user = settings_file.readline()[:-1]
    computer = settings_file.readline()[:-1]

print('Current user is ' + user)
print('Running on ' + computer)

if user == 'zijinshi':
    # If is running on server, save instead of showing results on server
    on_server = True  #(computer == 'server')                                          ######edited by Mike

    # Sizes of training and validation sets
    train_set_size = 3000
    val_set_size = 450
    assert train_set_size + val_set_size <= 3498 # Only 3498 in total

    # Dataset Parameters
    batch_size = 50 #if on_server else 10                                                ######edited by Mike
    print('batch_size = %d' % batch_size)
    load_size = 160 # size of the images on disk
    fine_size = 160 # size of the images after disposition (flip, translation, ...)
    target_size = 40 # size of output images
    original_font = 'Baoli' # transfer style from this font
    target_font = 'Hannotate' # transfer style to this font

    # Training Parameters
    learning_rate = 0.001 # Initial learning rate for Adam optimizer
    dropout = 0.5 # Dropout, probability to -keep- units
    training_iters = 10000
    do_training = True
    do_validation = False
    # Interval to test loss on training and validation set, and display(save) comparison
    step_display = 100 #if on_server else 1                                                   ######edited by Mike
    step_save = 2000
    save_path = '../../saved_train_data/cnn_deep/style_transfer_zijin'                        ######edited by Mike
    start_from = ''
    #start_from = save_path + '-2000' # Saved data file

    variation_loss_scale = 0.0001*0 # Scale of variation loss in total loss function

else:
    train_set_size = 3400
    val_set_size = 98
    assert train_set_size + val_set_size <= 3498

    # Graph selection
    NN = False  ## True means we use only fully connected layer
    l2_loss = True  ## True means we use l2_loss function   
    BN = False     #### batch normalisation for neural network training 
    pool1 = False    ## whether to pool for layer n
    pool2 = True    ## set the second layer to be true
    pool3 = False  
    pool4 = True 
    pool5 = False 
    pool6 = False 
    pool7 = True
    pool8 = False
    pool9 = False
    pool10 = True 
    pool11 = False
    pool12 = False
    pool13 = True   # ## set the final layer to do max pool
    

    # Dataset Parameters
    batch_size = 50
    load_size = 160
    fine_size = 160
    target_size = 40
    original_font = 'Baoli'
    target_font = 'Hannotate'

    # Training Parameters
    learning_rate = 0.001
    dropout = 0.1  ### changed to tf.layers.dropout, probability to drop
    training_iters = 10000
    do_training = True
    do_validation = False
    # do_comparison = True
    on_server = True   ### if set to false, will show pictures
    step_display = 100
    step_save = 2000
    save_path = '../../saved_train_data/cnn_l1/style_transfer_mike'
    start_from = ''
    #start_from = save_path + '-final'

    variation_loss_importance = 0.000025 * 0

# mean values of images for each font (currently not in use)
mean_map = {
    'Cao': 0.8508965474736796,
    'Hannotate': 0.74494465944527832,
    'Xingkai': 0.76178657894442514,
    'simkai': 0.8331927743152947,
    'STHeiti': 0.68690325752875914,
    'Songti': 0.63991741282015269,
    'Hanzipen': 0.79626192713369814,
    'Baoli': 0.76018856022486725,
    'WeibeiSC': 0.78538279635254127,
    'Yuanti': 0.5077452970321058
}

# Construct dataloader
opt_data = {
    'data_root': '../../img/',
    'original_font': original_font,
    'target_font': target_font,
    'train_set_size': train_set_size,
    'val_set_size': val_set_size,
    'load_size': load_size,
    'fine_size': fine_size,
    'target_size': target_size,
    # 'original_mean': mean_map[original_font],
    # 'target_mean': mean_map[target_font],
    'randomize': False,
    'user': user
}


def batch_norm_layer(x, train_phase, scope_bn):
    """
    Apply a batch norm layer on input x.
    :param x: input tensor
    :param train_phase: whether need to train parameters
    :param scope_bn: variable scope
    :return: output tensor after batch normalization
    """
    return batch_norm(x, decay=0.9, center=True, scale=True,
                      updates_collections=None,
                      is_training=train_phase,
                      reuse=None,
                      trainable=True,
                      scope=scope_bn)


class CharacterTransform:
    def __init__(self):
        """Initialize the cnn and prepare data. """
        self.graph = tf.Graph()

        if user == 'zijinshi':
            self.build_graph_better()
        else:
            self.l2_loss = l2_loss
            self.NN = NN
            self.build_graph_best()

        self.loader = TrainValSetLoader(**opt_data)

        # self.session = tf.Session(graph=self.graph)
        # self.session.run(tf.global_variables_initializer())
        # print('finished')

    def build_graph_better(self):
        """Build the cnn graph. """

        print('Building graph')
        with self.graph.as_default():
            # Input data
            self.images = tf.placeholder(tf.float32, shape=(None, fine_size, fine_size, 1))
            self.labels = tf.placeholder(tf.float32, shape=(None, target_size, target_size, 1))
            self.training = tf.placeholder(tf.bool)
            self.keep_dropout = tf.placeholder(tf.float32)

            global_step = tf.Variable(0,trainable=False)

            # 160 -> 80
            conv1 = tf.layers.conv2d(self.images, filters=16, kernel_size=21, strides=2, padding='same',
                                     kernel_initializer = xavier_initializer(uniform=False))
            conv1 = batch_norm_layer(conv1, self.training, 'bn1')
            conv1 = tf.nn.relu(conv1)
            print('conv1 shape = %s' % conv1.shape)
            pool1 = tf.layers.max_pooling2d(conv1, pool_size=3, strides=2, padding='same')
            print('pool1 shape = %s' % pool1.shape)

            # 80 -> 40
            conv12 = tf.layers.conv2d(conv1, filters=64, kernel_size=11, strides=2, padding='same',
                                     kernel_initializer = xavier_initializer(uniform=False))
            conv12 = batch_norm_layer(conv12, self.training, 'bn12')
            conv12 = tf.nn.relu(conv12)
            print('conv12 shape = %s' % conv12.shape)

            # 40 -> 20
            conv2 = tf.layers.conv2d(conv12, filters=256, kernel_size=5, strides=2, padding='same',
                                     kernel_initializer = xavier_initializer(uniform=False))
            conv2 = batch_norm_layer(conv2, self.training, 'bn2')
            conv2 = tf.nn.relu(conv2)
            print('conv2 shape = %s' % conv2.shape)
            # pool2 = tf.layers.max_pooling2d(conv2, pool_size=3, strides=2, padding='same')
            # print('pool2 shape = %s' % pool2.shape)

            # 20 -> 10
            conv3 = tf.layers.conv2d(conv2, filters=256, kernel_size=5, strides=2, padding='same',
                                     kernel_initializer = xavier_initializer(uniform=False))
            conv3 = batch_norm_layer(conv3, self.training, 'bn3')
            conv3 = tf.nn.relu(conv3)
            print('conv3 shape = %s' % conv3.shape)

            # 10 -> 10
            conv4 = tf.layers.conv2d(conv3, filters=256, kernel_size=3, strides=1, padding='same',
                                     kernel_initializer = xavier_initializer(uniform=False))
            conv4 = batch_norm_layer(conv4, self.training, 'bn4')
            conv4 = tf.nn.relu(conv4)
            print('conv4 shape = %s' % conv4.shape)

            # 10 -> 10
            conv42 = tf.layers.conv2d(conv4, filters=256, kernel_size=3, strides=1, padding='same',
                                     kernel_initializer = xavier_initializer(uniform=False))
            conv42 = batch_norm_layer(conv42, self.training, 'bn42')
            conv42 = tf.nn.relu(conv42)
            print('conv42 shape = %s' % conv42.shape)

            # 10 -> 10
            conv43 = tf.layers.conv2d(conv42, filters=256, kernel_size=3, strides=1, padding='same',
                                     kernel_initializer = xavier_initializer(uniform=False))
            conv43 = batch_norm_layer(conv43, self.training, 'bn43')
            conv43 = tf.nn.relu(conv43)
            print('conv43 shape = %s' % conv43.shape)

            fc5 = tf.reshape(conv43, [-1, 256 * 10 * 10])
            print('fc5 input shape = %s' % fc5.shape)
            fc5 = tf.contrib.layers.fully_connected(fc5, 5000, tf.nn.relu,
                                                    weights_initializer=xavier_initializer(uniform=False))
            fc5 = batch_norm_layer(fc5, self.training, 'bn5')
            fc5 = tf.nn.dropout(fc5, self.keep_dropout)
            print('fc5 output shape = %s' % fc5.shape)


            fc6 = tf.contrib.layers.fully_connected(fc5, 5000, tf.nn.relu,
                                                    weights_initializer=xavier_initializer(uniform=False))
            print('fc6 input shape = %s' % fc6.shape)
            fc6 = batch_norm_layer(fc6, self.training, 'bn6')
            fc6 = tf.nn.dropout(fc6, self.keep_dropout)

            # Output layer. Sigmoid function is used to gain result between 0 and 1
            out = tf.contrib.layers.fully_connected(fc6, target_size * target_size, tf.nn.sigmoid,
                                                    weights_initializer=xavier_initializer(uniform=False))
            # out = tf.multiply(tf.add(tf.sign(tf.subtract(out, tf.constant(0.5))), tf.constant(1.)), 0.5)

            # Reshape the output to a 2d image
            self.result = tf.reshape(out, [-1, target_size, target_size, 1])

            l1_loss = tf.losses.absolute_difference(self.labels, self.result)
            variation_loss = tf.image.total_variation(self.result)

            # Loss is a combination of L1 norm loss and total variation loss
            self.loss = tf.reduce_mean(l1_loss + variation_loss * variation_loss_scale)

            update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
            with tf.control_dependencies(update_ops):
                #self.optimizer = tf.train.GradientDescentOptimizer(LEARNING_RATE).minimize(self.loss)
                self.optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate).minimize(self.loss)

            self.saver = tf.train.Saver() #### define the saving part

        print('Graph building finished')

    def build_graph_best(self):
        print('Building graph')

        with self.graph.as_default():
            # Input data
            self.images = tf.placeholder(tf.float32, shape=(None, fine_size, fine_size, 1))
            self.labels = tf.placeholder(tf.float32, shape=(None, target_size, target_size, 1))
            self.training = tf.placeholder(tf.bool)
            self.keep_dropout = tf.placeholder(tf.float32)

            global_step = tf.Variable(0,trainable=False)

            # 80 -> 40 -> 20
            if self.NN:

                fc1 = tf.contrib.layers.fully_connected(tf.reshape(self.images, [-1, fine_size * fine_size]), 3000, tf.nn.relu,
                                                    weights_initializer=xavier_initializer(uniform=False))
                fc1 = batch_norm_layer(fc1, self.training, 'bn1')
                fc1 = tf.nn.dropout(fc1, self.keep_dropout)


                fc2 = tf.contrib.layers.fully_connected(fc1, 3000, tf.nn.relu,
                                                    weights_initializer=xavier_initializer(uniform=False))
                fc2 = batch_norm_layer(fc2, self.training, 'bn2')
                fc2 = tf.nn.dropout(fc2, self.keep_dropout)

                fc3 = tf.contrib.layers.fully_connected(fc2, 3000, tf.nn.relu,
                                                    weights_initializer=xavier_initializer(uniform=False))
                fc3 = batch_norm_layer(fc3, self.training, 'bn3')
                fc3 = tf.nn.dropout(fc3, self.keep_dropout)

                fc4 = tf.contrib.layers.fully_connected(fc3, 3000, tf.nn.relu,
                                                    weights_initializer=xavier_initializer(uniform=False))
                fc4 = batch_norm_layer(fc4, self.training, 'bn4')
                fc4 = tf.nn.dropout(fc4, self.keep_dropout)

                fc5 = tf.contrib.layers.fully_connected(fc4, 3000, tf.nn.relu,
                                                    weights_initializer=xavier_initializer(uniform=False))
                fc5 = batch_norm_layer(fc5, self.training, 'bn5')
                fc5 = tf.nn.dropout(fc5, self.keep_dropout)

                fc6 = tf.contrib.layers.fully_connected(fc5, 3000, tf.nn.relu,
                                                    weights_initializer=xavier_initializer(uniform=False))
                fc6 = batch_norm_layer(fc6, self.training, 'bn6')
                fc6 = tf.nn.dropout(fc6, self.keep_dropout)

                fc7 = tf.contrib.layers.fully_connected(fc6, 3000, tf.nn.relu,
                                                    weights_initializer=xavier_initializer(uniform=False))
                fc7 = batch_norm_layer(fc7, self.training, 'bn7')
                train_out = tf.nn.dropout(fc7, self.keep_dropout)

            else:
                conv1_1 = tf.layers.conv2d(inputs=self.images, filters=64, kernel_size=3, strides=1, padding="same", activation=tf.nn.relu)
                if pool1:
                    conv1_1 = tf.layers.max_pooling2d(inputs=conv1_1, pool_size=2, strides=2)
                if BN: 
                    conv1_1 = tf.layers.batch_normalization(inputs=conv1_1, axis=3)
                print('conv1 shape = %s' % conv1_1.shape)

                conv1_2 = tf.layers.conv2d(inputs=conv1_1, filters=64, kernel_size=3, strides=1, padding="same", activation=tf.nn.relu)
                if pool2:
                    conv1_2 = tf.layers.max_pooling2d(inputs=conv1_2, pool_size=2, strides=2)
                if BN: 
                    conv1_2 = tf.layers.batch_normalization(inputs=conv1_2, axis=3)
                print('conv2 shape = %s' % conv1_2.shape)

                conv2_1 = tf.layers.conv2d(inputs=conv1_2, filters=128, kernel_size=3, strides=1, padding="same", activation=tf.nn.relu)
                if pool3:
                    conv2_1 = tf.layers.max_pooling2d(inputs=conv2_1, pool_size=2, strides=2)
                if BN: 
                    conv2_1 = tf.layers.batch_normalization(inputs=conv2_1, axis=3)

                conv2_2 = tf.layers.conv2d(inputs=conv2_1, filters=128, kernel_size=3, strides=1, padding="same", activation=tf.nn.relu)
                if pool4:
                    conv2_2 = tf.layers.max_pooling2d(inputs=conv2_2, pool_size=2, strides=2)
                if BN: 
                    conv2_2 = tf.layers.batch_normalization(inputs=conv2_2, axis=3)
                print('conv2_2 shape = %s' % conv2_2.shape)
                conv3_1 = tf.layers.conv2d(inputs=conv2_2, filters=256, kernel_size=3, strides=1, padding="same", activation=tf.nn.relu)
                if pool5:
                    conv3_1 = tf.layers.max_pooling2d(inputs=conv3_1, pool_size=2, strides=2)
                if BN: 
                    conv3_1 = tf.layers.batch_normalization(inputs=conv3_1, axis=3)
                
                conv3_2 = tf.layers.conv2d(inputs=conv3_1, filters=256, kernel_size=3, strides=1, padding="same", activation=tf.nn.relu)
                if pool6:
                    conv3_2 = tf.layers.max_pooling2d(inputs=conv3_2, pool_size=2, strides=2)
                if BN: 
                    conv3_2 = tf.layers.batch_normalization(inputs=conv3_2, axis=3)
                
                conv3_3 = tf.layers.conv2d(inputs=conv3_2, filters=256, kernel_size=3, strides=1, padding="same", activation=tf.nn.relu)
                if pool7:
                    conv3_3 = tf.layers.max_pooling2d(inputs=conv3_3, pool_size=2, strides=2)
                if BN: 
                    conv3_3 = tf.layers.batch_normalization(inputs=conv3_3, axis=3)
                print('conv3_3 shape = %s' % conv3_3.shape)
                conv4_1 = tf.layers.conv2d(inputs=conv3_3, filters=512, kernel_size=3, strides=1, padding="same", activation=tf.nn.relu)
                if pool8:
                    conv4_1 = tf.layers.max_pooling2d(inputs=conv4_1, pool_size=2, strides=2)
                if BN: 
                    conv4_1 = tf.layers.batch_normalization(inputs=conv4_1, axis=3)

                conv4_2 = tf.layers.conv2d(inputs=conv4_1, filters=512, kernel_size=3, strides=1, padding="same", activation=tf.nn.relu)
                if pool9:
                    conv4_2 = tf.layers.max_pooling2d(inputs=conv4_2, pool_size=2, strides=2)
                if BN: 
                    conv4_2 = tf.layers.batch_normalization(inputs=conv4_2, axis=3)
                
                conv4_3 = tf.layers.conv2d(inputs=conv4_2, filters=512, kernel_size=3, strides=1, padding="same", activation=tf.nn.relu)
                if pool10:
                    conv4_3 = tf.layers.max_pooling2d(inputs=conv4_3, pool_size=2, strides=2)
                if BN: 
                    conv4_3 = tf.layers.batch_normalization(inputs=conv4_3, axis=3)
                print('conv4_3 shape = %s' % conv4_3.shape)
                conv5_1 = tf.layers.conv2d(inputs=conv4_3, filters=512, kernel_size=3, strides=1, padding="same", activation=tf.nn.relu)
                if pool11:
                    conv5_1 = tf.layers.max_pooling2d(inputs=conv5_1, pool_size=2, strides=2)
                if BN: 
                    conv5_1 = tf.layers.batch_normalization(inputs=conv5_1, axis=3)

                conv5_2 = tf.layers.conv2d(inputs=conv5_1, filters=512, kernel_size=3, strides=1, padding="same", activation=tf.nn.relu)
                if pool12:
                    conv5_2 = tf.layers.max_pooling2d(inputs=conv5_2, pool_size=2, strides=2)
                if BN: 
                    conv5_2 = tf.layers.batch_normalization(inputs=conv5_2, axis=3)
                
                conv5_3 = tf.layers.conv2d(inputs=conv5_2, filters=512, kernel_size=3, strides=1, padding="same", activation=tf.nn.relu)
                if pool13:
                    conv5_3 = tf.layers.max_pooling2d(inputs=conv5_3, pool_size=2, strides=2)
                if BN: 
                    conv5_3 = tf.layers.batch_normalization(inputs=conv5_3, axis=3)
                print('conv5_3 shape = %s' % conv5_3.shape)
                #conv1 = tf.layers.conv2d(self.images, filters=64, kernel_size=3, strides=1, padding='same',
                #                     kernel_initializer = xavier_initializer(uniform=False))
                #conv1 = batch_norm_layer(conv1, self.training, 'bn1')
                #conv1 = tf.nn.relu(conv1)
                #print('conv1 shape = %s' % conv1.shape)
                #pool1 = tf.layers.max_pooling2d(conv1, pool_size=3, strides=2, padding='same')
                #print('pool1 shape = %s' % pool1.shape)

                flat = tf.contrib.layers.flatten(inputs=conv5_3)
                flat = tf.layers.dropout(inputs=flat, rate=dropout, training=self.training)
                print('flat shape = %s' % flat.shape)
                #fc5 = tf.reshape(conv5_3, [-1, 4096])
                #print('flat shape = %s' % fc5.shape)
                fc1 = tf.contrib.layers.fully_connected(flat, 4096, tf.nn.relu,
                                                    weights_initializer=xavier_initializer(uniform=False))
                fc2 = batch_norm_layer(fc1, self.training, 'bn5')


                fc3 = tf.contrib.layers.fully_connected(fc2, 4096, tf.nn.relu,
                                                    weights_initializer=xavier_initializer(uniform=False))
                fc3 = batch_norm_layer(fc2, self.training, 'bn7')
                
                fc4 = tf.contrib.layers.fully_connected(fc3, target_size*target_size, tf.nn.relu,
                                                    weights_initializer=xavier_initializer(uniform=False))
                fc4 = batch_norm_layer(fc3, self.training, 'bn8')


                train_out = tf.nn.dropout(fc2, self.keep_dropout)   ##tra

            out = tf.contrib.layers.fully_connected(train_out, target_size * target_size, tf.nn.sigmoid,
                                                    weights_initializer=xavier_initializer(uniform=False))
            # out = tf.multiply(tf.add(tf.sign(tf.subtract(out, tf.constant(0.5))), tf.constant(1.)), 0.5)

            self.result = tf.reshape(out, [-1, target_size, target_size, 1])

            if self.l2_loss:
                l2_loss = tf.reduce_mean(tf.losses.mean_squared_error(self.result,self.labels))
                variation_loss = tf.image.total_variation(self.result)
                self.loss = tf.reduce_mean(l2_loss + variation_loss * variation_loss_importance)
            else:
                l1_loss = tf.losses.absolute_difference(self.labels, self.result)  ######  loss function need to be changed to l2
                variation_loss = tf.image.total_variation(self.result)
                self.loss = tf.reduce_mean(l1_loss + variation_loss * variation_loss_importance)

            update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
            with tf.control_dependencies(update_ops):
                #self.optimizer = tf.train.GradientDescentOptimizer(LEARNING_RATE).minimize(self.loss)
                self.optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate).minimize(self.loss)

            self.saver = tf.train.Saver() #### define the saving part

        print('Graph building finished')

    def train_model(self):
        """
        Train the model.
        Display comparison for every step_display steps and save parameters for every step_save steps
        """

        with tf.Session(graph=self.graph) as self.session:
            # If a saved file is specified, restore from that file. Otherwise initialize
            if len(start_from) > 1:
                if not exists(start_from + '.meta'):
                    raise RuntimeError('File %s specified by start_from does not exist' % start_from)
                self.saver.restore(self.session, start_from)
                print('Restored from last time: %s' % start_from)
            else:
                self.session.run(tf.global_variables_initializer())
                print('Initialized model')

            # Start training
            for step in range(training_iters):
                # Data to feed into the placeholder variables in the tensorflow graph
                images_batch, labels_batch = self.loader.next_batch_train(batch_size)

                # Calculate loss and do comparison for every step_display steps
                if step % step_display == 0:
                    print('[%s]:' % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

                    # Calculate batch loss on training set
                    loss, result_batch = self.session.run([self.loss, self.result],
                                feed_dict={self.images: images_batch, self.labels: labels_batch,
                                           self.keep_dropout: 1., self.training: False})
                    print("-Iter " + str(step) + ", Training Loss= " + "{:.6f}".format(loss))
                    show_comparison(images_batch, labels_batch, result_batch,
                                    save=on_server, mode='display_train', iter=step)

                    # Calculate batch loss on validation set
                    images_batch_val, labels_batch_val = self.loader.next_batch_val(batch_size)
                    loss, result_batch = self.session.run([self.loss, self.result],
                                feed_dict={self.images: images_batch_val, self.labels: labels_batch_val,
                                           self.keep_dropout: 1., self.training: False})
                    print("-Iter " + str(step) + ", Validation Loss= " + "{:.6f}".format(loss))
                    show_comparison(images_batch_val, labels_batch_val, result_batch,
                                    save=on_server, mode='display_val', iter=step)

                # Run optimization op (backprop)
                self.session.run(self.optimizer, feed_dict={self.images: images_batch, self.labels: labels_batch,
                                                            self.keep_dropout: dropout, self.training: True})
                # Save model for every step_save steps
                if step != 0 and step % step_save == 0:
                    if not exists(dirname(save_path)):
                        print('Warning: %s not exist' % dirname(save_path))
                        os.makedirs(dirname(save_path))
                    self.saver.save(self.session, save_path, global_step=step)
                    print('Model saved in file: %s at Iter-%d' % (save_path, step))

            # Save model after the whole training process
            self.saver.save(self.session, save_path + '-final')
            print('Model saved in file: %s-final after the whole training process' % save_path)

    def validate(self):
        """Run the model on the whole validation set and show average loss. """
        print('Begin evaluating on the whole validation set...')

        num_batch = self.loader.size_val()//batch_size
        loss_total = 0.
        self.loader.reset_val()
        for i in range(num_batch):
            images_batch_val, labels_batch_val = self.loader.next_batch_val(batch_size)
            loss, result_batch = self.session.run([self.loss, self.result],
                            feed_dict={self.images: images_batch_val, self.labels: labels_batch_val,
                                       self.keep_dropout: 1., self.training: False})
            loss_total += loss
            print("Validation Loss = " + "{:.6f}".format(loss))
            show_comparison(images_batch_val, labels_batch_val, result_batch,
                            save=on_server, mode='validate', iter=i)

        loss_total /= num_batch
        print("Evaluation Finished! Loss = " + "{:.6f}".format(loss_total))

    def prediction(self, image_batch):
        """
        Run the model on one image batch
        :param image_batch: input images
        :return: output images after font transfer
        """
        raise RuntimeError('Not implemented!')

    def run(self):
        """Run the model and do training or validation according to settings. """
        if do_training:
            self.train_model()
        if do_validation:
            self.validate()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.session.close()


if __name__ == '__main__':
    #a = CharacterTransform()
    with CharacterTransform() as conv_net:
        conv_net.run()
