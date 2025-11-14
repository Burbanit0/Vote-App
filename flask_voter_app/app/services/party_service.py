# app/services/party_service.py
from app import db
from app.models import Party, User


class PartyService:
    @staticmethod
    def get_all_parties():
        parties = Party.query.all()
        return [
            {"id": party.id, "name": party.name, "description": party.description}
            for party in parties
        ]

    @staticmethod
    def create_party(name, description):
        if not name:
            return {"message": "Name is required"}, 400

        if Party.query.filter_by(name=name).first():
            return {"message": "Party with this name already exists"}, 400

        party = Party(name=name, description=description)
        db.session.add(party)
        db.session.commit()

        return {"id": party.id, "name": party.name, "description": party.description}

    @staticmethod
    def get_party(party_id):
        party = Party.query.get_or_404(party_id)
        return {"id": party.id, "name": party.name, "description": party.description}

    @staticmethod
    def update_party(party_id, name, description):
        party = Party.query.get_or_404(party_id)

        if name:
            if name != party.name and Party.query.filter_by(name=name).first():
                return {"message": "Party with this name already exists"}, 400
            party.name = name

        if description is not None:
            party.description = description

        db.session.commit()

        return {"id": party.id, "name": party.name, "description": party.description}

    @staticmethod
    def assign_user_to_party(user_id, party_id):
        user = User.query.get_or_404(user_id)
        party = Party.query.get_or_404(party_id)

        user.party_id = party_id
        db.session.commit()

        return {
            "message": "User assigned to party successfully",
            "user_id": user.id,
            "party_id": party.id,
        }

    @staticmethod
    def remove_user_from_party(user_id):
        user = User.query.get_or_404(user_id)
        user.party_id = None
        db.session.commit()

        return {"message": "User removed from party successfully", "user_id": user.id}

    @staticmethod
    def get_party_users(party_id):
        party = Party.query.get_or_404(party_id)
        users = party.members

        return [
            {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
            for user in users
        ]
