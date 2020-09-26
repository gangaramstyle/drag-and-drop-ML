import os
import sys
import base64
import pydicom
from pydicom.filebase import DicomBytesIO
sys.path.append('/BreatHeatDocker')
print(os.listdir('/BreatHeatDocker/'))
import Infer
from Infer import pre_process

# Flask
from flask import Flask, redirect, url_for, request, render_template, Response, jsonify, redirect
from werkzeug.utils import secure_filename
from gevent.pywsgi import WSGIServer

# SQL
from flask_sqlalchemy import SQLAlchemy

# TensorFlow and tf.keras
import tensorflow as tf
from tensorflow import keras

from tensorflow.keras.applications.imagenet_utils import preprocess_input, decode_predictions
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image

# Some utilites
import numpy as np
from util import base64_to_pil
import json

# Declare a flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)

class Results(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    accession = db.Column(db.String(200), nullable=False)
    result = db.Column(db.String(200), nullable=False)
    tag = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return '<Result %r>' % self.filename

db.create_all()

# You can use pretrained model from Keras
# Check https://keras.io/applications/
# or https://www.tensorflow.org/api_docs/python/tf/keras/applications

#from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2
#model = MobileNetV2(weights='imagenet')

print('Model loaded. Check http://127.0.0.1:5000/')


# Model saved with Keras model.save()
MODEL_PATH = 'models/your_model.h5'

# Load your own trained model
# model = load_model(MODEL_PATH)
# model._make_predict_function()          # Necessary
# print('Model loaded. Start serving...')

table_header = [
    'filename',
    'accession',
    'tag',
    'result'
]

@app.route('/', methods=['GET'])
def index():
    # Main page
    results = Results.query.all()
    return render_template('index.html', results=results)

@app.route('/inference-status', methods=['GET'])
def inferenceStatus():
    if request.method == 'GET':
        results = Results.query.all()
        print(results)
        table_body = []
        for result in results:
            row = []
            for key in table_header:
                row.append(getattr(result, key))
            table_body.append(row[:])

        return jsonify({'header': table_header, 'body': table_body})

@app.route('/run-model', methods=['POST'])
def runModel():
    if request.method == 'POST':
        #RUN MODEL
        #SAVE MODEL

        return "Success"
    return 'Error'

@app.route('/upload', methods=['POST'])
def uploadFile():
    if request.method == 'POST':
        encoded_file = request.json['file'].partition(';base64,')[2]
        decoded_file = base64.b64decode(encoded_file)
        try:
            dicom = pydicom.dcmread(DicomBytesIO(decoded_file))
            with open(f"/app/data/{request.json['title']}", "wb") as fh:
                fh.write(decoded_file)
            print(os.listdir('/app/data/'))
            #TODO: Save dicom file
            result = Results(filename=request.json['title'], accession=dicom.PatientID, result="ready to process", tag=request.json['tag'])
        except Exception as e:
            result = Results(filename=request.json['title'], accession='n/a', result="not a dicom", tag=request.json['tag'])
        db.session.add(result)
        db.session.commit()
        return "Success"
    return 'Error'

@app.route('/clear-table', methods=['POST'])
def clearTable():
    if request.method == 'POST':
        #TODO: Delete data folder
        Results.query.delete()
        db.session.commit()
        return 'Success'
    return 'Error'

if __name__ == '__main__':
    # app.run(port=5002, threaded=False)

    # Serve the app with gevent
    http_server = WSGIServer(('0.0.0.0', 5000), app)
    http_server.serve_forever()
