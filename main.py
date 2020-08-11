import os, json
from flask import Flask, request, jsonify, make_response
from flask_restful import Resource, Api
import firebase_admin
from firebase_admin import credentials, firestore, initialize_app
from google.cloud import secretmanager
from schema import Schema, And, Use, Optional

#Authenticating into GCP, and choosing project
client = secretmanager.SecretManagerServiceClient()
project_id = os.environ["GOOGLE_CLOUD_PROJECT"]

#Retrieving latest version of Firebase json key file named 'firebase-key' from GCP Secret Manager
name = client.secret_version_path(project_id, "firestore-key", "latest")
response = client.access_secret_version(name)
key = response.payload.data.decode("UTF-8") #storing file contents in key variable

# Initializing Firebase App with the key retrieved from Secret Manager
cred = credentials.Certificate(json.loads(key))
default_app = initialize_app(cred)

#Accessing Firestore and getting reference to persons document
db = firestore.client()
persons_ref = db.collection('persons')

#Flask App initialization
app = Flask(__name__)

#Flask API Handler initialization
api = Api(app)

#Person Schema definition using schema lib from https://github.com/keleshev/schema
schema = Schema({'nationalId': And(str, len),
                   Optional('name'): And(str, len),
                   Optional('lastName'): And(str, len),
                   Optional('age'):  And(Use(int), lambda n: 1 <= n <= 99),
                   Optional('originPlanet'): And(str, len),
                   Optional('pictureUrl'): And(str, len)
                })

#Resource class to handle GET, PUT and DELETE calls passing nationalId
class Person(Resource):
    #This method retrieves a single Person document from the collection
    def get(self,id):
        person = persons_ref.document(id).get()
        if person.to_dict() :
            #ID is found, retrieve object and return HTTP 200
            return make_response(jsonify(person.to_dict()), 200)
        else:
            #ID is not found, return HTTP 404
            return make_response("", 404)
    
    #This method updates an existing Person document in the collection
    def put(self,id):
        if request.headers["Content-Type"] == "application/json" :
            #Enters if the content of the request is markd as JSON in the headers
            #First, force the nationalId to be in the incoming JSON payload, as it is not optional in the schema definition
            data = request.get_json()
            data["nationalId"] = id
            if schema.is_valid(data):
                #Enters when JSON payload sent is correct
                content = schema.validate(data)
                person = persons_ref.document(id).get()
                if person.to_dict() :
                    #NationalId already exists, so update it and return HTTP 200
                    persons_ref.document(id).update(content)
                    return make_response(content, 200)
                else:
                    #NationalId is not in the collection, return HTTP 404
                    return make_response("", 404)
            else:
                #Schema validation error
                return make_response("", 400)
        else:
            #Header validation error
            return make_response("", 400)
    
    def delete(self,id):
    #This method deletes an existing Person document from the collection
        person = persons_ref.document(id).get()
        if person.to_dict() :
            #ID is found, delete object and return HTTP 200
            persons_ref.document(id).delete()
            return make_response("", 200)
        else:
            #ID is not found, return HTTP 404
            return make_response("", 404)

#Resource class to handle GET and POST calls, without providing nationalId
class PersonList(Resource):
    def get(self):
    #Just list all items in persons collection
        persons = [doc.to_dict() for doc in persons_ref.stream()]
        return make_response(jsonify(persons), 200)
    
    def post(self):
    #Upon receiving a JSON Payload, this method will create a new document with the person information
        if request.headers["Content-Type"] == "application/json" and schema.is_valid(request.get_json()):
            #Enters when header is correct AND JSON payload sent is correct
            content = schema.validate(request.get_json())
            id = content["nationalId"]
            person = persons_ref.document(id).get()
            if person.to_dict() :
                #NationalId already exists the collection, return HTTP 500
                return make_response("", 500)
            else:
                #NationalId is not in the collection, so create it and return HTTP 201
                persons_ref.document(id).set(content)
                return make_response(content, 201)
        else:
            #JSON Schema Validation error
            return make_response("", 400)

#Registering routes into the API handler    
api.add_resource(Person,'/people/<id>')
api.add_resource(PersonList,'/people')


if __name__ == '__main__':
    app.run(debug=True)