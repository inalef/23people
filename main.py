import os, json
from flask import Flask, request, jsonify, make_response, abort
from flask_restful import Resource, Api
import firebase_admin
from firebase_admin import credentials, firestore, initialize_app
from google.cloud import secretmanager
from schema import Schema, And, Use, Optional

#Authenticating into GCP, and choosing project
project_id = os.environ["GOOGLE_CLOUD_PROJECT"]
client = secretmanager.SecretManagerServiceClient()

#Retrieving Firebase json key file stored in GCP Secret Manager
name = client.secret_version_path(project_id, "firestore-key", "latest")
response = client.access_secret_version(name)
key = response.payload.data.decode("UTF-8")

# Initializing Firestore DB with the key retrieved from Secret Manager
cred = credentials.Certificate(json.loads(key))
default_app = initialize_app(cred)
db = firestore.client()
persons_ref = db.collection('persons')

#Flask App initialization
app = Flask(__name__)

#API Handler initialization
api = Api(app)

#Person Schema definition using schema lib from https://github.com/keleshev/schema
schema = Schema({'nationalId': And(str, len),
                   Optional('name'): And(str, len),
                   Optional('lastName'): And(str, len),
                   Optional('age'):  And(Use(int), lambda n: 1 <= n <= 99),
                   Optional('originPlanet'): And(str, len),
                   Optional('pictureUrl'): And(str, len)
                })

#Resource class to handle calls passing national_id
class Person(Resource):
    def get(self,id):
        person = persons_ref.document(id).get()
        if person.to_dict() :
            return make_response(jsonify(person.to_dict()), 200)
        else:
            return make_response("", 404)
    
    def put(self,id):
        #First, force the nationalId to be in the incoming JSON payload, as it is not optional in the schema definition
        data = request.get_json()
        data["nationalId"] = id
        if request.headers["Content-Type"] == "application/json" and schema.is_valid(data):
            #Enters when header is correct AND JSON payload sent is correct
            content = schema.validate(data)
            person = persons_ref.document(id).get()
            if person.to_dict() :
                #NationalId already exists in DB, so update it and return HTTP 201
                persons_ref.document(id).update(content)
                response = make_response(content, 200)
            else:
                #NationalId is not in DB, return HTTP 404
                response = make_response("", 404)
        else:
            #Header validation error
            response = make_response("", 400)
        return response

#Resource class to handle calls not passing GET arguments, such as an empty GET and POST
class PersonList(Resource):
    def get(self):
        persons = [doc.to_dict() for doc in persons_ref.stream()]
        return make_response(jsonify(persons), 200)
    
    def post(self):
        if request.headers["Content-Type"] == "application/json" and schema.is_valid(request.get_json()):
            #Enters when header is correct AND JSON payload sent is correct
            content = schema.validate(request.get_json())
            id = content["nationalId"]
            person = persons_ref.document(id).get()
            if person.to_dict() :
                #NationalId already exists in DB, return HTTP 500
                response = make_response("", 500)
            else:
                #NationalId is not in DB, so create it and return HTTP 201
                persons_ref.document(id).set(content)
                response = make_response(content, 201)
        else:
            #JSON Schema Validation error
            response = make_response("", 400)
        return response

#Registering routes into the API handler    
api.add_resource(Person,'/people/<id>')
api.add_resource(PersonList,'/people')


if __name__ == '__main__':
    app.run(debug=True)