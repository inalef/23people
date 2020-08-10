import os, json
from flask import Flask, request, jsonify, make_response, abort
from flask_restful import Resource, Api
import firebase_admin
from firebase_admin import credentials, firestore, initialize_app
from google.cloud import secretmanager
from schema import Schema, And, Use, Optional

#Authenticating into GCP, and choosing project
project_id = os.environ["PROJECT_ID"]
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

#Schema definition using schema lib from https://github.com/keleshev/schema
schema = Schema({'nationalId': And(str, len),
                  'name': And(str, len),
                  'lastName': And(str, len),
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

#Resource class to handle calls not passing GET arguments, such as an empty GET and POST
class PersonList(Resource):
    def get(self):
        persons = [doc.to_dict() for doc in persons_ref.stream()]
        return make_response(jsonify(persons), 200)
    
    def post(self):
        response = make_response("", 400)
        if request.headers["Content-Type"] == "application/json":
            try:
                content = schema.validate(request.get_json())
                response = make_response(content, 200)
            except Exception as e:
                #Validation error
                print(e)
                response = make_response("", 400)
        else:
            #Wrong header
            response = make_response("", 400)
        return response

#Registering routes into the API handler    
api.add_resource(Person,'/people/<id>')
api.add_resource(PersonList,'/people')


if __name__ == '__main__':
    app.run(debug=True)