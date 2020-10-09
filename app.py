import os
import pydicom
import shutil
from pathlib import Path
import BreatHeatDocker.Infer as infer

# Flask
from flask import Flask, request, render_template, jsonify, abort
from gevent.pywsgi import WSGIServer

# SQL
from flask_sqlalchemy import SQLAlchemy

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

print('Model loaded. Check http://127.0.0.1:5000/')

table_header = [
    'filename',
    'accession',
    'tag',
    'result'
]

data_base = "/app/data/"
temp_base = "/app/data/tmp/"
raw_base = "/app/data/raw/"
pprocessed_base = "/app/data/pprocessed/"


def make_subdirectories(directory):
    Path(directory).mkdir(parents=True, exist_ok=True)


def delete_folder_contents(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))


def get_chunk_name(uploaded_filename, chunk_number):
    return uploaded_filename + "_part_%03d" % chunk_number


def get_chunk_name_finished(uploaded_filename, chunk_number):
    return uploaded_filename + "_part_%03d.finished" % chunk_number


@app.route('/', methods=['GET'])
def index():
    # Main page
    results = Results.query.all()
    return render_template('index.html', results=results)


@app.route("/resumable", methods=['GET'])
def resumable():
    resumableIdentfier = request.args.get('resumableIdentifier', type=str)
    resumableFilename = request.args.get('resumableFilename', type=str)
    resumableChunkNumber = request.args.get('resumableChunkNumber', type=int)
    print(resumableIdentfier, resumableFilename, resumableChunkNumber)

    if not resumableIdentfier or not resumableFilename or not resumableChunkNumber:
        # Parameters are missing or invalid
        abort(500, 'Parameter error')

    # chunk folder path based on the parameters
    temp_dir = os.path.join(temp_base, resumableIdentfier)

    # chunk path based on the parameters
    chunk_file = os.path.join(temp_dir, get_chunk_name(
        resumableFilename, resumableChunkNumber))
    app.logger.debug('Getting chunk: %s', chunk_file)

    if os.path.isfile(chunk_file):
        # Let resumable.js know this chunk already exists
        return 'OK'
    else:
        # Let resumable.js know this chunk does not exists and needs to be uploaded
        abort(404, 'Not found')


# if it didn't already upload, resumable.js sends the file here
@app.route("/resumable", methods=['POST'])
def resumable_post():
    resumableTotalChunks = request.form.get('resumableTotalChunks', type=int)
    resumableChunkNumber = request.form.get(
        'resumableChunkNumber', default=1, type=int)
    resumableFilename = request.form.get(
        'resumableFilename', default='error', type=str)
    resumableIdentfier = request.form.get(
        'resumableIdentifier', default='error', type=str)
    tag_text = request.form.get('tag', default='', type=str)

    # get the chunk data
    chunk_data = request.files['file']

    # make our temp directory
    temp_dir = os.path.join(temp_base, resumableIdentfier)
    make_subdirectories(temp_dir)

    # save the chunk data
    chunk_name = get_chunk_name(resumableFilename, resumableChunkNumber)
    chunk_file = os.path.join(temp_dir, chunk_name)
    chunk_data.save(chunk_file)
    chunk_name_finished = get_chunk_name_finished(
        resumableFilename, resumableChunkNumber)
    # TODO: Clean up the chunk finished code
    chunk_finished_file = os.path.join(temp_dir, chunk_name_finished)
    f = open(chunk_finished_file, 'w')
    f.write("\n")
    f.close()

    app.logger.debug('Saved chunk: %s', chunk_file)

    # check if the upload is complete
    chunk_paths = [os.path.join(temp_dir, get_chunk_name(
        resumableFilename, x)) for x in range(1, resumableTotalChunks + 1)]
    chunk_paths_finished = [os.path.join(temp_dir, get_chunk_name_finished(
        resumableFilename, x)) for x in range(1, resumableTotalChunks + 1)]
    upload_complete = all([os.path.exists(p) for p in chunk_paths])
    upload_finished_complete = all(
        [os.path.exists(p) for p in chunk_paths_finished])

    # combine all the chunks to create the final file
    if upload_finished_complete:
        target_file_name = os.path.join(temp_base, resumableFilename)
        make_subdirectories(temp_base)
        with open(target_file_name, "ab") as target_file:
            for p in chunk_paths:
                stored_chunk_file_name = p
                stored_chunk_file = open(stored_chunk_file_name, 'rb')
                target_file.write(stored_chunk_file.read())
                stored_chunk_file.close()
        target_file.close()
        shutil.rmtree(temp_dir)
        app.logger.debug('File saved to: %s', target_file_name)
        make_subdirectories(raw_base)
        try:
            dicom = pydicom.dcmread(target_file_name)
            result = Results(filename=resumableFilename, accession=dicom.PatientID,
                             result="ready to process", tag=tag_text)
            shutil.move(target_file_name, f"{raw_base}{resumableFilename}")
        except Exception as e:
            print(e)
            result = Results(filename=resumableFilename,
                             accession='n/a', result="not a dicom", tag=tag_text)
            print("this is not a dicom")
        db.session.add(result)
        db.session.commit()
    return 'OK'


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
        make_subdirectories(pprocessed_base)
        results = infer.run_pipeline()
        for result_set in results:
            for idx in result_set:
                file = os.path.split(result_set[idx]['File'])[1]
                score = result_set[idx]['Cancer Score']
                res = Results.query.filter_by(filename=file).first()
                print(file, score, res)
                res.result = str(score)
                db.session.commit()
        return "Success"
    return 'Error'


@app.route('/clear-table', methods=['POST'])
def clearTable():
    if request.method == 'POST':
        delete_folder_contents(data_base)
        Results.query.delete()
        db.session.commit()
        return 'Success'
    return 'Error'


if __name__ == '__main__':
    # app.run(port=5002, threaded=False)

    # Serve the app with gevent
    http_server = WSGIServer(('0.0.0.0', 5000), app)
    http_server.serve_forever()
