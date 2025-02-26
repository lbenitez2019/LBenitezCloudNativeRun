"""
############################
# 1st phase - all in 1 app #
############################
1. flask hello world

2. add other flask endpoints

3. hard code responses

4. look up how to accept only POST (GET is default)

5. return html for GET /
<form method="post" enctype="multipart/form-data" action="/upload" method="post">
  <div>
    <label for="file">Choose file to upload</label>
    <input type="file" id="file" name="form_file" accept="image/jpeg"/>
  </div>
  <div>
    <button>Submit</button>
  </div>
</form>

6. in GET /files return a hardcoded list for initial testing
files = ['file1.jpeg', 'file2.jpeg', 'file3.jpeg']

7. in GET / call the function for GET /files and loop through the list to add to the HTML
GET /
    ...
    for file in list_files():
        index_html += "<li><a href=\"/files/" + file + "\">" + file + "</a></li>"

    return index_html

8. in POST /upload - lookup how to extract uploaded file and save locally to ./files
def upload():
    file = request.files['form_file']  # item name must match name in HTML form
    file.save(os.path.join("./files", file.filename))

    return redirect("/")
#https://flask.palletsprojects.com/en/2.2.x/patterns/fileuploads/

9. in GET /files - look up how to list files in a directory

    files = os.listdir("./files")
    #TODO: filter jpeg only
    return files

10. filter only .jpeg
@app.route('/files')
def list_files():
    files = os.listdir("./files")
    for file in files:
        if not file.endswith(".jpeg"):
            files.remove(file)
    return files
"""
import os
from flask import Flask, redirect, request, send_file, Response
from google.cloud import storage  # Added for GCS
import tempfile

os.makedirs('files', exist_ok = True)

def create_bucket_class_location(bucket_name):
    """
    Create a new bucket in the US region with the coldline storage
    class
    """
    # bucket_name = "fluted-union-449221-g4_cloudbuild"

    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)
    bucket.storage_class = "COLDLINE"
    new_bucket = storage_client.create_bucket(bucket, location="us")

    print(
        "Created bucket {} in {} with storage class {}".format(
            new_bucket.name, new_bucket.location, new_bucket.storage_class
        )
    )
    return new_bucket

# Added for GCS
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/lukebro321123/Project/fluted-union-449221-g4-3806dbff18ba.json"  # Replace with your service account key path
storage_client = storage.Client()
bucket_name = "fluted-union-449221-g4_cloudbuild"  # Replace with your GCS bucket name
bucket = storage_client.bucket(bucket_name)

app = Flask(__name__)

@app.route('/')
def index():
    index_html="""
<form method="post" enctype="multipart/form-data" action="/upload" method="post">
  <div>
    <label for="file">Choose file to upload</label>
    <input type="file" id="file" name="form_file" accept="image/jpeg"/>
  </div>
  <div>
    <button>Submit</button>
  </div>
</form>
<ul>
"""    

    for file in list_files():
        index_html += "<li><a href=\"/files/" + file + "\">" + file + "</a></li>"
    index_html += "</ul>"

    return index_html

@app.route('/upload', methods=["POST"])
def upload():
    file = request.files['form_file']  # item name must match name in HTML form
    # Use a temporary file instead of saving directly to a specific location
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
      file.save(temp_file.name)
      temp_file_name = temp_file.name
    
    # Added for GCS: Upload the file to the bucket from temp file
    blob = bucket.blob(file.filename)
    blob.upload_from_filename(temp_file_name)
    
    os.remove(temp_file_name) #clean up the temp file

    return redirect("/")

@app.route('/files')
def list_files():
    # Modified for GCS: List files in the bucket
    blobs = bucket.list_blobs()
    jpegs = []
    for blob in blobs:
        if blob.name.lower().endswith(".jpeg") or blob.name.lower().endswith(".jpg"):
            jpegs.append(blob.name)
    
    return jpegs

@app.route('/files/<filename>')
def get_file(filename):
    # Modified for GCS: Download the file from the bucket and serve it
    blob = bucket.blob(filename)
    
    # Use a temporary file for downloading
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
        blob.download_to_filename(temp_file.name)
        temp_file_name = temp_file.name

        # Determine the correct mimetype
        if filename.lower().endswith(('.jpg', '.jpeg')):
            mimetype = 'image/jpeg'
        else:
            mimetype = 'application/octet-stream'

        with open(temp_file_name, 'rb') as f:
          file_data = f.read()

        os.remove(temp_file_name)

    return Response(file_data, mimetype=mimetype)

if __name__ == '__main__':
    app.run(debug=True)
