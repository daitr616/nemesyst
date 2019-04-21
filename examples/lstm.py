#!/usr/bin/env python3

# @Author: George Onoufriou <archer>
# @Date:   2018-09-27
# @Filename: lstm.py
# @Last modified by:   archer
# @Last modified time: 2019-03-07
# @License: Please see LICENSE file in project root

"""
Module handler for LSTM networks
"""

import copy
import datetime
import json
import os
import pickle
import pprint
import sys

import numpy as np
import pandas as pd
from keras.layers import (LSTM, Activation, BatchNormalization, Dense, Flatten,
                          LeakyReLU, Reshape)
from keras.models import Sequential

fileName = "lstm.py"
prePend = "[ " + fileName + " ] "
# this is calling system wide nemesyst src.arg so if you are working on a branch
# dont forget this will be the main branch version of args


def main(args, db, log):
    """
    Module entry point

    This entry point deals with the proper invocation of Lstm().
    """

    # deep copy args to maintain them throught the rest of the program
    args = copy.deepcopy(args)
    log(prePend + "\n\tArg dict of length: " + str(len(args))
        + "\n\tDatabase obj: " + str(db) + "\n\tLogger object: " + str(log), 0)
    db.connect()
    lstm = Lstm(args=args, db=db, log=log)
    lstm.debug()

    if(args["toTrain"]):
        lstm.train()

    if(args["toTest"]):
        lstm.test()

    if(args["toPredict"]):
        lstm.predict()


class Lstm():
    """
    Gate RNN based sequence neural network abstraction

    This class deals with all abstractions that fascilitate training deep
    neural networks from a MongoDb database object.
    """

    # import protected inside class so that it does not share instances
    from src.data import Data

    def __init__(self, args, db, log):
        self.db = db
        self.log = log
        self.epochs = 0
        self.args = args
        self.model_dict = None
        self.model_cursor = None
        self.prePend = "[ lstm.py -> Lstm ] "
        # this is a dictionary that should be referanced every time something
        # defaults or needs to check what is expected
        self.expected = {
            "type": "lstm",
            "shape": (self.args["batchSize"], self.args["timeSteps"], self.args["dimensionality"]),
        }
        tempArgs = copy.deepcopy(args)
        tempArgs["dimensionality"] = tempArgs["dimensionality"] - 1
        self.data = self.Data(args=tempArgs, db=db, log=log)
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = str(args["tfLogMin"])

    def debug(self):
        """
        Debug func for displaying class state
        """
        self.log(self.prePend, 3)

    def train(self):
        """
        Func responsible for training certain neural networks

        This func will handle the neccessary clean up and sorting out of
        values and call the correct functions to fully train this network.
        """
        # branch depending if model is to continue training or create new model
        if(self.args["toReTrain"] == True):
            # DONT FORGET IF YOU ARE RETRAINING TO CONCATENATE EXISTING STUFF LIKE EPOCHS
            modelPipe = self.getPipe(self.args["modelPipe"])
            self.model_dict = self.getModel(modelPipe)
            # check that the imported model is a lstm
            # model is already overwritten when loading from database so self.model != None now
        else:
            self.args["type"] = self.expected["type"]
            self.model_dict = self.createModel()
        # show dict to user
        model_json = json.dumps(self.model_dict, indent=4,
                                sort_keys=True, default=str)
        self.log(model_json, 3)

        self.trainer(self.model_dict["lstm"])

    def trainer(self, model):
        """
        Responsible for retrieving batches of data and subsequentley training

        This func will be able to handle training a given model with requested
        data batches.
        """
        counter_samples = 0
        loss_sum = 0
        # for loop that cant step backwards that will iterate the difference
        # between the current epoch of the model and the desired amount
        for epoch in range(self.model_dict["epochs"], self.args["epochs"], 1):
            counter_batch = 0
            # loops through database data by returning batches
            for data in self.data:
                documents = pd.DataFrame(data)
                # flattening list
                flat_l = [item for sublist in documents["data"]
                          for item in sublist]
                x = pd.DataFrame(flat_l)
                # duplicating target to be the same length as input
                y = np.repeat(
                    documents["target"], 1)
                x = np.reshape(
                    x.values, (self.args["batchSize"], self.args["timeSteps"], self.args["dimensionality"] - 1))

                # TRAINING HERE
                loss = model.train_on_batch(x, y)
                loss_sum = loss_sum + loss

                self.log("epoch: " + str(epoch) + ", batch: " + str(counter_batch) +
                    ", length: " + str(len(data)) + ", type: " +
                    str(type(data)) +
                    ", loss: " + str(loss)
                         , 0)
                counter_batch += 1
            counter_samples = counter_samples + counter_batch

        if(loss_sum != 0):
            loss_avg = loss_sum / counter_samples
            self.log("loss_avg: " + str(loss_avg))
        else:
            self.log("there was no data trained, check data exists \ndata: "
                     + str(self.data.getSample()), 1)

    def createLstm(self):

        model = Sequential()
        bInShape = (self.args["batchSize"], self.args["timeSteps"],
                    self.args["dimensionality"] - 1)

        self.log(
            self.prePend + "\n" +
            "\t" + "type:\t\t"         + str(self.args["type"])            + "\n" +
            "\t" + "layers:\t\t"       + str(self.args["layers"])          + "\n" +
            "\t" + "timesteps:\t"      + str(self.args["timeSteps"])       + "\n" +
            "\t" + "dimensionality:\t" + str(self.args["dimensionality" ])  + "\n" +
            "\t" + "batchSize:\t"      + str(self.args["batchSize"])       + "\n" +
            "\t" + "batchInShape:\t"   + str(bInShape)                     + "\n" +
            "\t" + "epochs:\t\t"       + str(self.args["epochs"])          + "\n" +
            "\t" + "epochs_chunk:\t"   + str(self.args["epochs_chunk"])    + "\n" +
            "\t" + "activation:\t" +
            str(self.args["activation" ])      + "\n",
            0
        )

        # gen layers
        for unused in range(self.args["layers"] - 1):
            model.add(LSTM(self.args["intLayerDim"], activation=self.args["activation"],
                           return_sequences=True, batch_input_shape=bInShape))
        model.add(LSTM(
            self.args["intLayerDim"], activation=self.args["activation"], batch_input_shape=bInShape))
        model.add(Dense(1, name="main_output"))
        self.log(self.prePend + "LSTM created", -1)
        return model

    def test(self, collection=None):
        """
        Func responsible for testing certain neural networks

        This func will attempt retrieval if neural network is not already in
        memory, prior to testing, and will comply to user specified metrics.
        """
        # uses its own collection variable to allow it to be reused if testColl != coll
        collection = collection if collection is not None else self.args["coll"]
        # branch depending if model is already in memory to save request to database
        if(self.model_dict != None):
            None
        else:
            self.model_dict = self.getModel(
                self.getPipe(self.args["modelPipe"]))
        # now model should exist now use it to test
        self.tester(self.model_dict["lstm"])

    def tester(self, model):
        tempArgs = copy.deepcopy(self.args)
        tempArgs["coll"] = tempArgs["testColl"]
        tempArgs["dimensionality"] = tempArgs["dimensionality"] - 1
        database = self.Data(args=tempArgs, db=self.db, log=self.log)

        batch = 0
        sum_loss = 0
        for data in database:
            documents = pd.DataFrame(data)
            # flattening list
            flat_l = [item for sublist in documents["data"]
                      for item in sublist]
            x = pd.DataFrame(flat_l)
            # duplicating target to be the same length as input
            y = np.repeat(
                documents["target"], 1)
            x = np.reshape(
                x.values, (self.args["batchSize"], self.args["timeSteps"], self.args["dimensionality"] - 1))
            loss = model.evaluate(x, y)
            sum_loss = sum_loss + loss
            self.log("batch: " + str(batch) + " loss_test: " + str(loss), 0)
            batch = batch + 1

        self.log("avg_loss: " + str(sum_loss / batch))

    def predict(self):
        """
        Func responsible for producing predictions for certain neural networks
        """
        # branch depending if model is already in memory to save request to database
        if(self.model_dict != None):
            None
        else:
            self.model_dict = self.getModel(
                self.getPipe(self.args["modelPipe"]))
        # assigning model to variable to aid readability
        model = self.model_dict["lstm"]

        tempArgs = copy.deepcopy(self.args)
        tempArgs["coll"] = tempArgs["testColl"]
        tempArgs["dimensionality"] = tempArgs["dimensionality"] - 1
        database = self.Data(args=tempArgs, db=self.db, log=self.log)

        batch = 0

        predictions = []
        truths = []
        for data in database:
            documents = pd.DataFrame(data)
            # flattening list
            flat_l = [item for sublist in documents["data"]
                      for item in sublist]
            x = pd.DataFrame(flat_l)
            # duplicating target to be the same length as input
            y = np.repeat(
                documents["target"], 1)
            x = np.reshape(
                x.values, (self.args["batchSize"], self.args["timeSteps"], self.args["dimensionality"] - 1))
            prediction = model.predict(x)
            predictions = predictions + list(prediction.flatten())
            truths = truths + list(y)
            batch = batch + 1
        df = pd.DataFrame(predictions, columns=["predictions"])
        df["truths"] = truths
        df.to_csv("predictions.csv", index=False)
        print(df)

    def save(self):
        """
        Func responsible for saving the resulting models/ states of models
        """
        None

    # function responsible for creating whatever type of model is desired by the
    # user in this case LSTMs
    def createModel(self):
        """

        Func which creates an LSTM model in a dict
        Currentley this is hard coded to be of a specific architecture but this
        can be easily modified and will propogate through should it be
        neccessary.
        """

        lstm = self.createLstm()

        lstm.summary()
        lstm.compile(loss=self.args["lossMetric"],
                     optimizer=self.args["optimizer"])

        model_dict = {
            "utc": datetime.datetime.utcnow(),
            "loss": None,
            "epochs": 0,
            "lstm": lstm,
        }
        return model_dict


    def getModel(self, model_pipe=None):
        """
        Func which retrieved neural network model from a MongoDb document
        """

        # modify keras witrh get and set funcs to be able to unserialise the data
        self.make_keras_picklable()
        query = model_pipe if model_pipe is not None else {}
        self.log(self.prePend + "db query: " + str(query), 0)
        # get model cursor to most recent match with query
        self.model_cursor = self.db.getMostRecent(
            query=query, collName=self.args["modelColl"])
        # get a dictionary of key:value pairs of this document from query
        model_dict = (
            pd.DataFrame(list(self.model_cursor))
        ).to_dict('records')[0]
        # self.model = pickle.loads(self.model_dict["model_bin"])
        # self.compile()
        if(model_dict["type"] != self.expected["type"]):
            raise RuntimeWarning(
                "The model retrieved using query: " + str(model_pipe)
                + " gives: " + str(model_dict["type"])
                + ", which != expected: " +  self.expected["type"])
        return model_dict

    def getPipe(self, pipePath):
        """
        Short func to retrieve pipelines from config files
        """

        with open(pipePath) as f:
            return json.load(f)

    def make_keras_picklable(self):
        """
        Function which fascilitates serialising keras objects to store as json

        This provides keras with __getstate__ and __setstate__ to be picklable.
        """
        import tempfile
        import keras.models
        import h5py

        def __getstate__(self):
            model_str = ""
            with tempfile.NamedTemporaryFile(suffix='.hdf5', delete=True) as fd:
                keras.models.save_model(self, fd.name, overwrite=True)
                model_str = fd.read()
                d = {'model_str': model_str}
                return d

        def __setstate__(self, state):
            with tempfile.NamedTemporaryFile(suffix='.hdf5', delete=True) as fd:
                fd.write(state['model_str'])
                fd.flush()
                model = keras.models.load_model(fd.name)
                self.__dict__ = model.__dict__

        cls = keras.models.Model
        cls.__getstate__ = __getstate__
        cls.__setstate__ = __setstate__
