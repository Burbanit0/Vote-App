from flask import Flask, request, jsonify
import psycopg
from flask_cors import CORS
from psycopg import sql

app = Flask(__name__)

CORS(app)

# Database connection parameters
db_params = {
    'dbname': 'mydatabase',
    'user': 'myuser',
    'password': 'mypassword',
    'host': '127.0.0.1',
    'port': '4000'
}

def get_db_connection():
    return psycopg.connect(**db_params)

# Candidate Endpoints

@app.route('/candidates', methods=['GET'])
def get_candidates():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Candidate')
    candidates = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([{'id': c[0], 'first_name': c[1], 'last_name': c[2]} for c in candidates])

@app.route('/candidates/<int:candidate_id>', methods=['GET'])
def get_candidate(candidate_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Candidate WHERE id = %s', (candidate_id,))
    candidate = cursor.fetchone()
    cursor.close()
    conn.close()
    if candidate:
        return jsonify({'id': candidate[0], 'first_name': candidate[1], 'last_name': candidate[2]})
    return jsonify({'error': 'Candidate not found'}), 404

@app.route('/candidates', methods=['POST'])
def create_candidate():
    data = request.get_json()
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO Candidate (first_name, last_name) VALUES (%s, %s) RETURNING id', (first_name, last_name))
    candidate_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'id': candidate_id, 'first_name': first_name, 'last_name': last_name}), 201

@app.route('/candidates/<int:candidate_id>', methods=['PUT'])
def update_candidate(candidate_id):
    data = request.get_json()
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE Candidate SET first_name = %s, last_name = %s WHERE id = %s', (first_name, last_name, candidate_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'id': candidate_id, 'first_name': first_name, 'last_name': last_name})

@app.route('/candidates/<int:candidate_id>', methods=['DELETE'])
def delete_candidate(candidate_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM Candidate WHERE id = %s', (candidate_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'result': True})


# Voter Endpoints

# for a voter we want the informations: 
# first name, last name, first choice, multiple choice

@app.route('/voters', methods=['GET'])
def get_voters():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Voter')
    voters = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([{'id': v[0], 'first_name': v[1], 'last_name': v[2], 'choice': v[3]} for v in voters])

@app.route('/voters/<int:voter_id>', methods=['GET'])
def get_voter(voter_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Voter WHERE id = %s', (voter_id,))
    voter = cursor.fetchone()
    cursor.close()
    conn.close()
    if voter:
        return jsonify({'id': voter[0], 'first_name': voter[1], 'last_name': voter[2], 'choice': voter[3]})
    return jsonify({'error': 'Voter not found'}), 404

@app.route('/voters', methods=['POST'])
def create_voter():
    data = request.get_json()
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    choice = data.get('choice')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO Voter (first_name, last_name, choice) VALUES (%s, %s, %s) RETURNING id', (first_name, last_name, choice))
    voter_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'id': voter_id, 'first_name': first_name, 'last_name': last_name, 'choice': choice}), 201

@app.route('/voters/<int:voter_id>', methods=['PUT'])
def update_voter(voter_id):
    data = request.get_json()
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    choice = data.get('choice')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE Voter SET first_name = %s, last_name = %s, choice = %s WHERE id = %s', (first_name, last_name, choice, voter_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'id': voter_id, 'first_name': first_name, 'last_name': last_name, 'choice': choice})

@app.route('/voters/<int:voter_id>', methods=['DELETE'])
def delete_voter(voter_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM Voter WHERE id = %s', (voter_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'result': True})

if __name__ == '__main__':
    app.run(debug=True)