# flask_voter_app/app/services/election_service.py
from app import db
from app.models import Election, User, ElectionRole, user_election_roles


class ElectionService:
    @staticmethod
    def get_all_elections(page, per_page, search, status, sort_by, sort_dir):
        # Base query with join
        query = db.session.query(Election, User.first_name, User.last_name).join(
            User, Election.created_by == User.id
        )

        # Apply filters and sorting (copy logic from routes/elections.py)
        if search:
            query = query.filter(
                (Election.name.ilike(f"%{search}%"))
                | (Election.description.ilike(f"%{search}%"))
            )

        if status != "all":
            query = query.filter(Election.status.ilike(f"%{status}"))

        if sort_by == "name":
            query = query.order_by(
                Election.name.desc() if sort_dir == "desc" else Election.name.asc()
            )
        elif sort_by == "date":
            query = query.order_by(
                Election.start_date.desc()
                if sort_dir == "desc"
                else Election.start_date.asc()
            )

        paginated_elections = query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        # Format results
        formatted_elections = [
            {
                "id": election.id,
                "name": election.name,
                "description": election.description,
                "status": election.status,
                "start_date": (
                    election.start_date.isoformat() if election.start_date else None
                ),
                "end_date": (
                    election.end_date.isoformat() if election.end_date else None
                ),
                "created_at": election.created_at,
                "created_by": {
                    "id": election.created_by,
                    "first_name": first_name,
                    "last_name": last_name,
                },
            }
            for election, first_name, last_name in paginated_elections.items
        ]

        return {
            "elections": formatted_elections,
            "total": paginated_elections.total,
            "pages": paginated_elections.pages,
            "current_page": paginated_elections.page,
            "per_page": paginated_elections.per_page,
        }

    @staticmethod
    def create_election(name, description, start_date, end_date, created_by):
        election = Election(
            name=name,
            description=description,
            start_date=start_date,
            end_date=end_date,
            created_by=created_by,
        )
        db.session.add(election)
        db.session.commit()

        # Add the creator as an organizer
        db.session.execute(
            user_election_roles.insert().values(
                user_id=created_by, election_id=election.id, role=ElectionRole.ORGANIZER
            )
        )
        db.session.commit()

        return {
            "id": election.id,
            "name": election.name,
            "description": election.description,
            "start_date": (
                election.start_date.isoformat() if election.start_date else None
            ),
            "end_date": election.end_date.isoformat() if election.end_date else None,
            "created_at": (
                election.created_at.isoformat() if election.created_at else None
            ),
            "created_by": election.created_by,
        }
