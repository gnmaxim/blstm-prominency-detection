from keras.models import Sequential
from keras.layers.core import Dense, Activation, Dropout, RepeatVector, Merge, Masking, Reshape
from keras.layers.wrappers import TimeDistributed, Bidirectional
from keras.layers.recurrent import LSTM
from keras.layers.embeddings import Embedding
from keras.preprocessing import sequence
from keras import backend as K

import pandas
import numpy
import sys


# Path per i relativi dataset
PATHS = ['../corpus/train.csv',
            '../corpus/validation.csv',
            '../corpus/test.csv']

# Da rivedere l'ordine delle colonne
COLUMNS = ['nucleus-duration',
            'spectral-emphasis',
            'pitch-movements',
            'overall-intensity',
            'syllable-duration',
            'prominent-syllable']


dataset = []
max_utterance_length = 0

for path in PATHS:
    total_rows = len(pandas.read_csv(path, skip_blank_lines = False)) + 1
    reader = pandas.read_csv(path, delim_whitespace = True,
                                header = None,
                                names = COLUMNS,
                                skip_blank_lines = False,
                                chunksize = 1)
    print ("Extracting", path)

    x_utterance = []
    y_utterance = []
    x = []
    y = []
    chunks = 0

    for chunk in reader:
        # Estrazione del vettore delle features di ogni sillaba
        x_syllable = chunk.loc[:, 'nucleus-duration':'syllable-duration'].values[0]
        chunks += 1

        # Se il vettore contiene NaN allora la frase è finita
        if not(numpy.isnan(x_syllable[0])) and chunks < total_rows:
            x_utterance.append(x_syllable)
            if chunk.loc[:, 'prominent-syllable'].values[0] == 0:
                y_syllable = [1, 0, 0]
            else:
                y_syllable = [0, 1, 0]
            #y_syllable = chunk.loc[:, 'prominent-syllable'].values[0]
            y_utterance.append(y_syllable)
            #y_utterance.append(numpy.full(1, y_syllable))
        else:
            # Appendi le features e le prominenze della frase al dataset
            if path == PATHS[-1]:
                x_utterance[-1] = numpy.full(5, 0)
            x.append(x_utterance)
            y.append(y_utterance)
            if max_utterance_length < len(x_utterance):
                max_utterance_length = len(x_utterance)

            # print ("Features estratte: ", x_utterance)
            # print ("Sillabe prominenti:", y_utterance, "\n")

            x_utterance = []
            y_utterance = []

    dataset.append([x, y])
    print ("... extracted ", len(x), "utterances.")

print ("\nLongest expression with", max_utterance_length, "syllables.",
        "Filling shorter expressions with zeroes...")

for i in range(len(dataset)):
    for j in range(len(dataset[i])):
        if j == 0:
            dataset[i][j] = sequence.pad_sequences(dataset[i][j],
                                                maxlen = max_utterance_length,
                                                dtype = 'float', padding = 'post',
                                                truncating = 'post', value = 0.)
        else:
            dataset[i][j] = sequence.pad_sequences(dataset[i][j],
                                                maxlen = max_utterance_length,
                                                dtype = 'float', padding = 'post',
                                                truncating = 'post', value = [0., 0., 1.])

# print (dataset[2][0][0])
# print (dataset[2][1][0])

dataset = numpy.asarray(dataset)

'''
epochs      100     200     300     500
Accuracy:   90.74   91.13   90.93   91.13
F1:         86.07   86.68   86.39   86.68
Precision:  86.26   86.75   86.54   86.75
'''
model = Sequential()
model.add(Bidirectional(LSTM(17, return_sequences = True),
                        input_shape = (max_utterance_length, len(COLUMNS) - 1)))
model.add(Dropout(0.5))
model.add(TimeDistributed(Dense(len(dataset[0][1][0][0]), activation = 'softmax')))


model.compile(loss = 'binary_crossentropy', optimizer = 'adam',
                metrics = ['accuracy', 'fmeasure', 'precision'])
print (model.summary())


model.fit(dataset[0][0], dataset[0][1],
            validation_data = (dataset[1][0], dataset[1][1]),
            nb_epoch = 100, batch_size = 5)


scores = model.evaluate(dataset[2][0], dataset[2][1], verbose = 1)
print ("Accuracy: %.2f%%" % (scores[1]*100))
print ("F1: %.2f%%" % (scores[2]*100))
print ("Precision: %.2f%%" % (scores[3]*100))

''' Codice per vedere risultati di layer intermedi '''
# get_3rd_layer_output = K.function([model.layers[0].input, K.learning_phase()],
#                                     [model.layers[2].output])
# layer_output = get_3rd_layer_output([dataset[2][0], 0])[0]
# numpy.set_printoptions(threshold = sys.maxsize)
# print (layer_output.shape)
# print (layer_output[3])
# print (dataset[2][0][3])
# print (dataset[2][1][3])
