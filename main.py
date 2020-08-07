from flask import Flask, request, jsonify, make_response
from flask_restful import Resource, Api
import firebase_admin
from firebase_admin import credentials, firestore, initialize_app

# Firestore DB initialization
cred = credentials.Certificate("people-ae72e-firebase-adminsdk-pksjb-b9f891908b.json")
default_app = initialize_app(cred)
db = firestore.client()
persons_ref = db.collection('persons')

#Flask App initialization
app = Flask(__name__)

#API Handler initialization
api = Api(app)

#Resource class to handle calls passing national_id
class Person(Resource):
    def get(self,id):
        person = persons_ref.document(id).get()
        return make_response(jsonify(person.to_dict()), 200)

#Resource class to handle calls not passing GET arguments, such as PUT, POST and get all      
class PersonList(Resource):
    def get(self):
        persons = [doc.to_dict() for doc in persons_ref.stream()]
        return make_response(jsonify(persons), 200)

#Registering routes into the API handler    
api.add_resource(Person,'/people/<id>')
api.add_resource(PersonList,'/people')


if __name__ == '__main__':
    app.run(debug=True)