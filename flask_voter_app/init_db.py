from app import create_app, db  # Adjust the import according to your project structure
from app.models import User, Voter, Candidate
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

def create_initial_data():
    app = create_app()  # Create the Flask app instance

    with app.app_context():
        # Create an admin user
        db.create_all()

        admin_user = User(
            username='admin',
            role='Admin'
        )
        admin_user.set_password('admin_password')
        db.session.add(admin_user)

        # Create voter users and their profiles
        voter_users = [
            {'username': 'voter1', 'password': 'voter1_password', 'first_name': 'John', 'last_name': 'Doe'},
            {'username': 'voter2', 'password': 'voter2_password', 'first_name': 'Jane', 'last_name': 'Smith'},
            {'username': 'voter3', 'password': 'voter3_password', 'first_name': 'Alice', 'last_name': 'Johnson'},
            {'username': 'voter4', 'password': 'voter4_password', 'first_name': 'Bob', 'last_name': 'Brown'}
        ]

        for voter_data in voter_users:
            voter_user = User(
                username=voter_data['username'],
                role='Voter'
            )
            voter_user.set_password(voter_data['password'])
            db.session.add(voter_user)
            db.session.flush()  # Flush to get the user ID

            voter_profile = Voter(
                user_id=voter_user.id,
                first_name=voter_data['first_name'],
                last_name=voter_data['last_name']
            )
            db.session.add(voter_profile)

        # Create candidates
        candidates = [
            {'first_name': 'Candidate', 'last_name': 'One'},
            {'first_name': 'Candidate', 'last_name': 'Two'},
            {'first_name': 'Candidate', 'last_name': 'Three'}
        ]

        for candidate_data in candidates:
            candidate = Candidate(
                first_name=candidate_data['first_name'],
                last_name=candidate_data['last_name']
            )
            db.session.add(candidate)

        # Commit all changes to the database
        db.session.commit()

# Call the function to create initial data
if __name__ == '__main__':
    create_initial_data()
