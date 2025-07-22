from flask import Flask, request, jsonify, render_template, redirect
from datetime import datetime
from models import db, RepairTicket, TicketUpdate, Tag


from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, RepairTicket, User

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Jun0Th3D3str0y3r'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)  # Initialize the app context with db

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect("/")
        return "Invalid credentials", 401
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")

@app.route("/admin/add_user", methods=["GET", "POST"])
@login_required
def add_user():
    if current_user.username != "michael":
        return "Access denied", 403

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if User.query.filter_by(username=username).first():
            return "User already exists", 400
        new_user = User(
            username=username,
            password=generate_password_hash(password)
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect("/admin/add_user")

    return render_template("add_user.html")


@app.route("/")
@login_required
def index():
    query = request.args.get("q", "").strip().lower()
    status = request.args.get("status", "all")
    selected_tag = request.args.get("tags", "")
    created_by_me = request.args.get("created_by_me", "false").lower() == "true"

    base_query = RepairTicket.query

    if query:
        base_query = base_query.filter(
            (RepairTicket.facility.ilike(f"%{query}%")) |
            (RepairTicket.user.ilike(f"%{query}%")) |
            (RepairTicket.device_type.ilike(f"%{query}%")) |
            (RepairTicket.issue.ilike(f"%{query}%")) |
            (RepairTicket.progress.ilike(f"%{query}%"))
        )

    if created_by_me:
        base_query = base_query.filter(RepairTicket.created_by == current_user.username)

    if selected_tag:
        base_query = base_query.join(RepairTicket.tags).filter(Tag.name == selected_tag)

    if status == "returned":
        base_query = base_query.filter(RepairTicket.date_returned.isnot(None))
    elif status == "in_progress":
        base_query = base_query.filter(RepairTicket.date_returned.is_(None))

    tickets = base_query.order_by(RepairTicket.id.desc()).all()

    # Stats
    total_count = RepairTicket.query.count()
    returned_count = RepairTicket.query.filter(RepairTicket.date_returned.isnot(None)).count()
    in_progress_count = RepairTicket.query.filter(RepairTicket.date_returned.is_(None)).count()

    # Get all tags for dropdown
    all_tags = Tag.query.order_by(Tag.name).all()

    return render_template(
        "index.html",
        tickets=tickets,
        query=query,
        status=status,
        selected_tag=selected_tag,
        created_by_me=created_by_me,
        all_tags=all_tags,
        total_count=total_count,
        returned_count=returned_count,
        in_progress_count=in_progress_count
    )


@app.route("/tickets/create", methods=["POST"])
@login_required
def create_ticket_form():
    data = request.form

    # Parse and prepare tags
    tag_input = data.get("tags", "")
    tag_names = [name.strip().lower() for name in tag_input.split(",") if name.strip()]
    tags = []

    for name in tag_names:
        tag = Tag.query.filter_by(name=name).first()
        if not tag:
            tag = Tag(name=name)
            db.session.add(tag)
        tags.append(tag)

    # Create the repair ticket with tags
    ticket = RepairTicket(
        facility=data["facility"],
        user=data["user"],
        device_type=data["device_type"],
        date_picked_up=datetime.strptime(data["date_picked_up"], "%Y-%m-%d"),
        issue=data["issue"],
        estimated_return_date=datetime.strptime(data["estimated_return_date"], "%Y-%m-%d"),
        created_by=current_user.username,
        updated_by=current_user.username,
        tags=tags
    )

    db.session.add(ticket)
    db.session.commit()
    return redirect("/")


@app.route("/tickets/<int:ticket_id>/update", methods=["POST"])
@login_required
def update_ticket_form(ticket_id):
    ticket = RepairTicket.query.get_or_404(ticket_id)
    data = request.form

    progress = data.get("progress", "").strip()
    if progress:
        update = TicketUpdate(
            ticket_id=ticket.id,
            content=progress,
            updated_by=current_user.username
        )
        db.session.add(update)

    ticket.estimated_return_date = datetime.strptime(data["estimated_return_date"], "%Y-%m-%d")
    ticket.updated_by = current_user.username

    db.session.commit()
    return redirect("/")

@app.route("/tickets/<int:ticket_id>/complete", methods=["POST"])
@login_required
def complete_ticket_form(ticket_id):
    ticket = RepairTicket.query.get_or_404(ticket_id)
    data = request.form
    ticket.date_returned = datetime.strptime(data["date_returned"], "%Y-%m-%d")
    ticket.updated_by = current_user.username
    db.session.commit()
    return redirect("/")

# --- JSON API routes ---
@app.route("/tickets", methods=["POST"])
def create_ticket():
    data = request.get_json()
    ticket = RepairTicket(
        facility=data["facility"],
        user=data["user"],
        device_type=data["device_type"],
        date_picked_up=datetime.strptime(data["date_picked_up"], "%Y-%m-%d"),
        issue=data["issue"],
        estimated_return_date=datetime.strptime(data["estimated_return_date"], "%Y-%m-%d")
    )
    db.session.add(ticket)
    db.session.commit()
    return jsonify(ticket.serialize()), 201

@app.route("/tickets", methods=["GET"])
def get_all_tickets():
    tickets = RepairTicket.query.all()
    return jsonify([ticket.serialize() for ticket in tickets])

@app.route("/tickets/<int:ticket_id>/delete", methods=["POST"])
@login_required
def delete_ticket(ticket_id):
    ticket = RepairTicket.query.get_or_404(ticket_id)

    # Optional: restrict to only creator or admin
    if current_user.username != "michael" and ticket.created_by != current_user.username:
        return "Unauthorized", 403

    db.session.delete(ticket)
    db.session.commit()
    return redirect("/")


@app.route("/tickets/<int:ticket_id>", methods=["PUT"])
def update_ticket(ticket_id):
    ticket = RepairTicket.query.get_or_404(ticket_id)
    data = request.get_json()
    ticket.progress = data.get("progress", ticket.progress)
    ticket.estimated_return_date = datetime.strptime(data["estimated_return_date"], "%Y-%m-%d")
    ticket.updated_by = current_user.username
    db.session.commit()
    return jsonify(ticket.serialize())

@app.route("/tickets/<int:ticket_id>/complete", methods=["POST"])
def complete_ticket(ticket_id):
    ticket = RepairTicket.query.get_or_404(ticket_id)
    data = request.get_json()
    ticket.date_returned = datetime.strptime(data["date_returned"], "%Y-%m-%d")
    db.session.commit()
    return jsonify(ticket.serialize())

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0")
