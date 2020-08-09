import os
from models.schema import *
from models.form import *
from datetime import date, datetime
from flask_bootstrap import Bootstrap
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from werkzeug.security import check_password_hash, generate_password_hash
from index import get_tech_words, get_cities_from_techwords, get_points_from_city
from flask import Flask, render_template, redirect, url_for, make_response, request, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

global event_url 

app = Flask(__name__)
Bootstrap(app)
app.secret_key = 'my-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
login_manager = LoginManager(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

@app.before_first_request
def create_tables():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        if current_user.is_authenticated and (current_user.username == 'saikiran' or current_user.username == 'saikirannalla' or current_user.username == 'mmblack'):
            return True
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login', next=request.url))


class MyModelView(ModelView):
    def is_accessible(self):
        if current_user.is_authenticated and (current_user.username == 'saikiran' or current_user.username == 'saikirannalla' or current_user.username == 'mmblack'):
            return True

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login', next=request.url))


class UserView(MyModelView):
    column_list = ('id','username','first_name','last_name','email')

class UserRoleView(MyModelView):
    column_list = ('role', 'user.username')

class TeamLearnedView(MyModelView):
    column_list = ('event_id', 'member_id', 'topic', 'points', 'points_created_by', 'reason' , 'time', 'validation', 'team.team_name')


admin = Admin(app, index_view=MyAdminIndexView())
admin.add_view(UserView(User, db.session))
admin.add_view(UserRoleView(UserRole, db.session))
admin.add_view(TeamLearnedView(EventTeamLearned, db.session))


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST', 'GET'])
def login():
    form = LoginForm()
    error = None
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user, remember=form.remember.data)
                last = LoginHistory.query.filter(LoginHistory.user_id == user.id, LoginHistory.lastday < date.today()).first()
                if last:
                    s0, s1 = last.yesterday_point, last.today_point
                    point = Points.query.filter_by(user_id=last.user_id).first()
                    point.points += last.today_point
                    last.today_point+=s0
                    last.yesterday_point=s1
                    last.lastday=date.today()
                    db.session.commit()
                return redirect('/app')
        error = 'Invalid User. Username doesn\'t exists.'
    return render_template('login.html', form=form, error=error)

@app.route('/signup')
def signupget():
    form = RegisterForm()
    return render_template('signup.html', form=form)
    
@app.route('/signup', methods=['POST','GET'])
def signup():
    error = None
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first() is None:
            if User.query.filter_by(email=form.email.data).first() is None:
                new_user = User(username=form.username.data, email=form.email.data, first_name=form.first_name.data, last_name=form.last_name.data ,password='')
                hashed_password = generate_password_hash(form.password.data, method='sha256')
                new_user.password = hashed_password
                d_point = Points(user=new_user)
                db.session.add(new_user)
                db.session.add(d_point)
                db.session.commit()
                new_histroy = LoginHistory(yesterday_point=0, today_point=1,lastday=date.today(),user_id=new_user.id)
                permission = UserRole(user_id=new_user.id, role=4)
                db.session.add(new_histroy)
                db.session.add(permission)
                db.session.commit()
                return redirect(url_for('login'))
            else:
                error = "email already exists"
        else:
            error = "username already exists"

    return render_template('signup.html', form=form, error = error)
    

@app.route('/app', methods=['POST', 'GET'])
@login_required
def app_home():
    form = TechKeyForm()
    error = None
    q_user = User.query.filter_by(username=current_user.username).first()
    print(q_user.id)
    q_points = Points.query.filter_by(user=q_user).first()
    q_city = Cities.query.filter_by(user=q_user).first()
    if form.validate_on_submit():
        content = form.techword.data
        words = get_tech_words(content.split())
        cities = get_cities_from_techwords(words)
        if 'no tech keys' in words:
            error = 'No Tech Keys Found'
        d = dict(zip(words, cities))
        if q_city is None:
            for k, v in d.items():
                tmp = Cities(cities=v, words=k, user=q_user)
                db.session.add(tmp)
            d_points = get_points_from_city(cities)
            q_points.points += d_points
            db.session.commit()
        if q_city is not None:
            _cities = Cities.query.filter_by(user_id=q_user.id).all()
            g_cities = [city.cities for city in _cities]
            g_words = [city.words for city in _cities]
            r_cities = cities - set(g_cities)
            r_words = words - set(g_words)
            d = dict(zip(r_words, r_cities))
            for k, v in d.items():
                tmp = Cities(cities=v, words=k, user=q_user)
                db.session.add(tmp)
            d_points = get_points_from_city(r_cities)
            q_points.points += d_points
            db.session.commit()
    user_role = UserRole.query.filter_by(user_id=q_user.id).first()        
    if user_role.role == 1:
        return render_template('app.html', form=form, points=q_points.points, error=error, username=q_user.username,admin='admin',validater='validater')
    elif user_role.role == 2:
        return render_template('app.html', form=form, points=q_points.points, error=error, username=q_user.username,validater='validater')
    return render_template('app.html', form=form, points=q_points.points, error=error, username=q_user.username)

#BROKEN CODE 
@app.route('/event')
@login_required
def event():  
    events = Event.query.all()
    q_user = User.query.filter_by(username=current_user.username).first()
    if UserRole.query.filter(UserRole.user_id==q_user.id,UserRole.role==1).first():
        return render_template('event.html', admin='admin', username=current_user.username,validater='validater', events=events)
    elif UserRole.query.filter(UserRole.user_id==q_user.id,UserRole.role==2).first():
        return render_template('event.html', validater='validater',  username=current_user.username,events=events)
    return render_template("event.html", username=current_user.username, events=events)

@app.route('/event_register/<id>', methods=['POST', 'GET'])
@login_required
def event_register(id):
    error = None
    form = TeamForm()  
    teams = db.session.query(Team).join(TeamMembers).filter(Team.tid==TeamMembers.team_id,TeamMembers.member_id==current_user.id)
    form.team_name.choices = [(team.team_name, team.team_name) for team in teams]
    # check user have team
    if teams.first() is None:
        error = "Create a team first!!"
    else:
        team = teams.first()
        # check user team is reagister for event
        if EventTeam.query.filter_by(team_id=(teams.first()).tid,event_id=id).first():
            if EventTeam.query.filter(EventTeam.event_id==id,EventTeam.team_id==team.tid).first() and Event.query.filter(Event.eid==id,Event.start_date<=date.today(),Event.end_date>=date.today()).first():
                return redirect('/event_id/'+str(id)+'/team_id/'+str((teams.first()).tid))
        if form.validate_on_submit():
            if EventTeam.query.filter(EventTeam.team_id==team.tid,EventTeam.event_id==id).first() is None:
                event_team = EventTeam(event_id=id,team_id=team.tid)
                db.session.add(event_team)
                # temp_team_point = EventTeamLearned(event_id=id,event_team_id=team.tid,member_id=current_user.id,points=0,validation=1,time=date.today())
                # db.session.add(temp_team_point)
                db.session.commit()
            if EventTeam.query.filter(EventTeam.event_id==id,EventTeam.team_id==team.tid).first() and Event.query.filter(Event.eid==id,Event.start_date<=date.today(),Event.end_date>=date.today()).first():
                return redirect('/event_id/{}/team_id/{}'.format(id,team.tid))
            else:
                error = 'Event not available'
    user_role = UserRole.query.filter_by(user_id=current_user.id).first()        
    if user_role.role == 1:
        return render_template('event_register.html', form=form, username=current_user.username, error=error, eventid=id , admin='admin',validater='validater')
    elif user_role.role == 2:
        return render_template('event_register.html', form=form, username=current_user.username, error=error, eventid=id ,validater='validater')
    return render_template('event_register.html', form=form, username=current_user.username, error=error, eventid=id)

@app.route('/event_id/<eid>/team_id/<tid>', methods=['POST', 'GET'])
@login_required
def event_learn(eid,tid):
    form = TechKeyForm()
    error = None
    topic = EventTeamLearned.query.filter_by(event_id=eid,event_team_id=tid)
    team = Team.query.filter_by(tid=tid).first()
    points= db.session.query(func.sum(EventTeamLearned.points).label("total")).filter(EventTeamLearned.event_id==eid,EventTeamLearned.event_team_id==tid).one()
    print(points[0])
    points = points[0]
    if form.validate_on_submit():
        content = form.techword.data
        team_lear = EventTeamLearned(event_id=int(eid),event_team_id=int(tid),topic=content,points=0,points_created_by=1,time=date.today(),member_id=current_user.id)
        db.session.add(team_lear)
        db.session.commit()

    user_role = UserRole.query.filter_by(user_id=current_user.id).first()        
    if user_role.role == 1:
        return render_template('event_learned.html', form=form, username=current_user.username, points=points, error=error, topics=topic, team_name=team.team_name,admin='admin',validater='validater',eid=eid,tid=tid)
    elif user_role.role == 2:
        return render_template('event_learned.html', form=form, username=current_user.username, points=points, error=error, topics=topic, team_name=team.team_name,validater='validater',eid=eid,tid=tid)
    return render_template('event_learned.html', form=form, username=current_user.username, points=points, error=error, topics=topic, team_name=team.team_name,eid=eid,tid=tid)

@app.route('/create_team', methods=['POST', 'GET'])
@login_required
def create_team():
    form = TeamMake()
    error = None
    if Team.query.filter_by(team_lead_id=current_user.id).first() is None: 
        if form.validate_on_submit():

            if Team.query.filter_by(team_name=form.team_name.data).first() is None:

                new_team = Team(team_name=form.team_name.data,team_lead_id=current_user.id)
                db.session.add(new_team)
                db.session.commit()
                team_member = TeamMembers(team_id=new_team.tid,member_id=current_user.id,join_date=date.today())
                db.session.add(team_member)
                db.session.commit()
                return redirect('/event')
            error = 'Team name alreay exists'
    else:
        error = "You already have team"

    user_role = UserRole.query.filter_by(user_id=current_user.id).first()        
    if user_role.role == 1:
        return render_template('team_register.html', form=form, error=error, username=current_user.username, eventid=id , admin='admin',validater='validater')
    elif user_role.role == 2:
        return render_template('team_register.html', form=form, error=error, username=current_user.username, eventid=id ,validater='validater')
    return render_template('team_register.html', form=form, error=error, username=current_user.username, eventid=id)
    #return render_template('team_register.html', form = form, error = error)


@app.route('/team')
@login_required
def team():
    user_role = UserRole.query.filter_by(user_id=current_user.id).first()        
    if user_role.role == 1:
        return render_template('team_home.html', admin='admin', username=current_user.username,validater='validater')
    elif user_role.role == 2:
        return render_template('team_home.html', username=current_user.username, validater='validater')
    return render_template('team_home.html')

@app.route('/team_manage')
@login_required
def team_manage():
    teams = db.session.query(Team).join(TeamMembers).filter(TeamMembers.member_id==current_user.id)
    user_role = UserRole.query.filter_by(user_id=current_user.id).first()        
    if user_role.role == 1:
       return render_template('team_manage.html', username=current_user.username, admin='admin',validater='validater', teams=teams)
    elif user_role.role == 2:
        return render_template('team_manage.html', username=current_user.username, validater='validater', teams=teams)
    return render_template('team_manage.html',  username=current_user.username,teams=teams)

@app.route('/team_edit/<id>')
@login_required
def team_edit(id):
    members = db.session.query(TeamMembers).join(User).filter(TeamMembers.team_id==id)
    table_name = Team.query.filter_by(tid=id).first()
    user_role = UserRole.query.filter_by(user_id=current_user.id).first()        
    if user_role.role == 1:
        return render_template('team_table.html',teamid=id, teamname=table_name.team_name, username=current_user.username, members=members,admin='admin',validater='validater')
    elif user_role.role == 2:
        return render_template('team_table.html',teamid=id, teamname=table_name.team_name, username=current_user.username, members=members,validater='validater')
    return render_template('team_table.html',teamid=id, teamname=table_name.team_name, username=current_user.username, members=members)

@app.route('/change/team_name/<tid>/<name>', methods=['GET','POST'])
@login_required
def team_name_change(tid,name):
    error = None
    if Team.query.filter_by(team_name=name).first() is None:
        if Team.query.filter(Team.tid==tid,Team.team_lead_id==current_user.id).first():
            team = Team.query.filter_by(tid=tid).first()
            team.team_name = name
            db.session.add(team)
            db.session.commit()
        else:
            error = "Team lead only can change team name"
    else:
        error = "Team name already exists"
    members = db.session.query(TeamMembers).join(User).filter(TeamMembers.team_id==tid)
    table_name = Team.query.filter_by(tid=tid).first()
    user_role = UserRole.query.filter_by(user_id=current_user.id).first()        
    if user_role.role == 1:
        return render_template('team_table.html',teamid=tid, error=error, teamname=table_name.team_name, username=current_user.username, members=members,admin='admin',validater='validater')
    elif user_role.role == 2:
        return render_template('team_table.html',teamid=tid,error=error, teamname=table_name.team_name, username=current_user.username, members=members,validater='validater')
    return render_template('team_table.html',teamid=tid,error=error, teamname=table_name.team_name, username=current_user.username, members=members)
    
    
    

@app.route('/member_add/<id>/team_id/<tid>')
@login_required
def member_add(id,tid):
    temp = TeamMembers(team_id=tid,member_id=id,join_date=date.today())
    db.session.add(temp)
    db.session.commit()
    return redirect('/admin_team_edit/'+str(tid))

@app.route('/validater')
@login_required
def validater():
    events = db.session.query(Event)
    if UserRole.query.filter(UserRole.user_id==current_user.id,UserRole.role==1).first():
        return render_template('validater_home.html', admin='admin', username=current_user.username,validater='validater',events=events)
    elif UserRole.query.filter(UserRole.user_id==current_user.id,UserRole.role==2).first():
        return render_template('validater_home.html',validater='validater',username=current_user.username,events=events)
    
    return redirect('/app')

@app.route('/event_team_show/<eid>')
@login_required
def event_team_show(eid):
    teams = db.session.query(Team).join(EventTeam).filter(EventTeam.team_id==Team.tid,EventTeam.event_id==eid)
    if UserRole.query.filter(UserRole.user_id==current_user.id,UserRole.role==1).first():
        return render_template('validater_team_show.html', admin='admin', username=current_user.username,validater='validater',teams=teams, event_id=eid)
    elif UserRole.query.filter(UserRole.user_id==current_user.id,UserRole.role==2).first():
        return render_template('validater_team_show.html',validater='validater', username=current_user.username,teams=teams, event_id=eid)

@app.route('/validaterion/event_id/<eid>/team_id/<tid>')
@login_required
def validaterion(tid,eid):
    #team = EventTeamLearned.query.filter_by(validation=False,event_team_id=tid,event_id=eid).all()
    team = db.session.query(User,EventTeamLearned).join(EventTeamLearned,EventTeamLearned.member_id==User.id).filter(EventTeamLearned.event_team_id==tid,EventTeamLearned.event_id==eid,EventTeamLearned.validation==False)
    if UserRole.query.filter(UserRole.user_id==current_user.id,UserRole.role==1).first():
        return render_template('validater_point.html', admin='admin',validater='validater', username=current_user.username,team_info=team, team_id=tid, event_id=eid)
    elif UserRole.query.filter(UserRole.user_id==current_user.id,UserRole.role==2).first():
        return render_template('validater_point.html',validater='validater',team_info=team, username=current_user.username, team_id=tid, event_id=eid)

@app.route('/save/event_id/<eid>/team_id/<tid>', methods=['POST', 'GET'])
@login_required
def save(tid,eid):
    temp = EventTeamLearned.query.filter_by(etlid=int(request.form['etlidid'])).first()
    temp.validation=1
    temp.points = request.form['points']
    temp.reason = request.form['reason']
    temp.points_created_by = 2
    db.session.add(temp)
    db.session.commit()
    return redirect('/validaterion/event_id/{}/team_id/{}'.format(eid,tid))


@app.route('/appadmin')
@login_required
def appadmin():
    if UserRole.query.filter(UserRole.user_id==current_user.id,UserRole.role==1).first():
        return render_template('admin.html', admin='admin', username=current_user.username,validater='validater')
    
    return redirect('/app')

@app.route('/event_info/<eid>',methods=['POST','GET'])
@login_required
def event_info(eid):
    user_role = UserRole.query.filter_by(user_id=current_user.id).first() 
    try:
        date = request.form['date']
        if date: 
            top_performer = db.session.query(User.username, func.sum(EventTeamLearned.points), func.count(EventTeamLearned.points)).join(User,User.id==EventTeamLearned.member_id).filter(EventTeamLearned.event_id==eid,EventTeamLearned.time==date).group_by(User.username).order_by(func.sum(EventTeamLearned.points).desc())
            top_team = db.session.query(Team.team_name,func.sum(EventTeamLearned.points), func.count(EventTeamLearned.points)).join(Team,Team.tid==EventTeamLearned.event_team_id).filter(EventTeamLearned.event_id==eid,EventTeamLearned.time==date).group_by(Team.team_name).order_by(func.sum(EventTeamLearned.points).desc())
        else:
            top_performer = db.session.query(User.username, func.sum(EventTeamLearned.points), func.count(EventTeamLearned.points)).join(User,User.id==EventTeamLearned.member_id).filter(EventTeamLearned.event_id==eid).group_by(User.username).order_by(func.sum(EventTeamLearned.points).desc())
            top_team = db.session.query(Team.team_name,func.sum(EventTeamLearned.points), func.count(EventTeamLearned.points)).join(Team,Team.tid==EventTeamLearned.event_team_id).filter(EventTeamLearned.event_id==eid).group_by(Team.team_name).order_by(func.sum(EventTeamLearned.points).desc())
    except:
        top_performer = db.session.query(User.username, func.sum(EventTeamLearned.points), func.count(EventTeamLearned.points)).join(User,User.id==EventTeamLearned.member_id).filter(EventTeamLearned.event_id==eid).group_by(User.username).order_by(func.sum(EventTeamLearned.points).desc())
        top_team = db.session.query(Team.team_name,func.sum(EventTeamLearned.points), func.count(EventTeamLearned.points)).join(Team,Team.tid==EventTeamLearned.event_team_id).filter(EventTeamLearned.event_id==eid).group_by(Team.team_name).order_by(func.sum(EventTeamLearned.points).desc())
    if user_role.role == 1:
        return render_template('validater_event_info.html',top_performer=top_performer, event_id=eid, top_team=top_team, username=current_user.username,admin='admin',validater='validater')
    elif user_role.role == 2:
        return render_template('validater_event_info.html',top_performer=top_performer, event_id=eid, top_team=top_team, username=current_user.username,validater='validater')
    return render_template('validater_event_info.html',username=current_user.username)

@app.route('/admin_team_manage')
@login_required
def admin_team_manage():
    teams = Team.query.all()
    user_role = UserRole.query.filter_by(user_id=current_user.id).first()        
    if user_role.role == 1:
        return render_template('admin_team.html', teams=teams, username=current_user.username, admin='admin', validater='validater')
    elif user_role.role == 2:
        return render_template('admin_team.html', teams=teams, username=current_user.username, validater='validater')
    return render_template('admin_team.html', username=current_user.username, teams=teams)

@app.route('/admin_team_edit/<id>')
@login_required
def admin_team_edit(id):
     
    members = db.session.query(TeamMembers).join(User).filter(TeamMembers.team_id==id)
    table_name = Team.query.filter_by(tid=id).first()
    abl_user = db.session.query(User).outerjoin(TeamMembers,TeamMembers.member_id==User.id).filter(TeamMembers.join_date==None)
    user_role = UserRole.query.filter_by(user_id=current_user.id).first()        
    if user_role.role == 1:
        return render_template('admin_team_table.html',abl_user=abl_user, username=current_user.username, team_id=table_name.tid, teamname=table_name.team_name, members=members, admin='admin', validater='validater')
    elif user_role.role == 2:
        return render_template('admin_team_table.html',abl_user=abl_user, username=current_user.username, team_id=table_name.tid, teamname=table_name.team_name, members=members,validater='validater')
    return render_template('admin_team_table.html',abl_user=abl_user, username=current_user.username, team_id=table_name.tid, teamname=table_name.team_name, members=members)

@app.route('/member_remove/<id>/team_id/<tid>')
@login_required
def member_remove(id,tid):
    temp_member = TeamMembers.query.filter_by(team_id=tid,member_id=id).first()
    db.session.delete(temp_member)
    db.session.commit()
    return redirect('/admin_team_edit/'+str(tid))

@app.route('/creat_event', methods=['POST','GET'])
@login_required
def creat_event():
    form = EventForm()
    error = None
    if form.validate_on_submit():
        if Event.query.filter_by(event_name=form.event_name.data).first() is None:
            print(form.start_date.data)
            new_team = Event(event_name=form.event_name.data,start_date=datetime.strptime(form.start_date.data,"%d/%m/%Y").date(),end_date=datetime.strptime(form.end_date.data,"%d/%m/%Y").date())
            db.session.add(new_team)
            db.session.commit()
            return redirect('/event')
        error = 'Event name alreay exists'
    user_role = UserRole.query.filter_by(user_id=current_user.id).first()        
    if user_role.role == 1:
        return render_template('creat_event.html', form=form, error=error, username=current_user.username, eventid=id , admin='admin',validater='validater')
    elif user_role.role == 2:
        return render_template('creat_event.html', form=form, error=error, username=current_user.username, eventid=id ,validater='validater')
    return render_template('creat_event.html', form=form, error=error, username=current_user.username, eventid=id)



@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


if __name__ == "__main__":
    from db import db
    db.init_app(app)
    app.run(debug=True)