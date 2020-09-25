import os
import sys
import base64
import pydicom
from pydicom.filebase import DicomBytesIO

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


def model_predict(img, model):
    img = img.resize((224, 224))

    # Preprocessing the image
    x = image.img_to_array(img)
    # x = np.true_divide(x, 255)
    x = np.expand_dims(x, axis=0)

    # Be careful how your trained model deals with the input
    # otherwise, it won't make correct prediction!
    x = preprocess_input(x, mode='tf')

    preds = model.predict(x)
    return preds

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

@app.route('/predict-test', methods=['POST'])
def predictTest():
    if request.method == 'POST':
        encoded_file = request.json['file'].partition(';base64,')[2]
        decoded_file = base64.b64decode(encoded_file)
        try:
            dicom = pydicom.dcmread(DicomBytesIO(decoded_file))
            result = Results(filename=request.json['title'], accession=dicom.PatientID, result="processing", tag=request.json['tag'])
        except Exception as e:
            result = Results(filename=request.json['title'], accession='n/a', result="not a dicom", tag=request.json['tag'])
        db.session.add(result)
        db.session.commit()
        return "success"
        #return render_template('index.html', results=results)
    return 'Error'

@app.route('/clear-table', methods=['POST'])
def clearTable():
    if request.method == 'POST':
        Results.query.delete()
        db.session.commit()
        return 'Success'
    return 'Error'


@app.route('/predict', methods=['GET', 'POST'])
def predict():
    if request.method == 'POST':
        print(request)
        # Get the image from post request
        img = base64_to_pil(request.json)

        # Save the image to ./uploads
        # img.save("./uploads/image.png")

        # # Make prediction
        # preds = model_predict(img, model)

        # # Process your result for human
        # pred_proba = "{:.3f}".format(np.amax(preds))    # Max probability
        # pred_class = decode_predictions(preds, top=1)   # ImageNet Decode

        # result = str(pred_class[0][0][1])               # Convert to string
        # result = result.replace('_', ' ').capitalize()
        
        # Serialize the result, you can add additional fields
        # return jsonify(result=result, probability=pred_proba)
        return jsonify(result="result", probability=0.5)

    return None


if __name__ == '__main__':
    # app.run(port=5002, threaded=False)

    # Serve the app with gevent
    http_server = WSGIServer(('0.0.0.0', 5000), app)
    http_server.serve_forever()
