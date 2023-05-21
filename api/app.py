import json
from pymongo import MongoClient
import certifi

from flask import Flask
from flask_cors import CORS
import requests
import googlemaps
import time
import geocoder
import random
import datetime


from datetime import date

app = Flask(__name__)
CORS(app)

client = MongoClient(
    'mongodb+srv://125group:QF6ATvGuz2raHmlF@cluster0.z7no1h6.mongodb.net/?retryWrites=true&w=majority',
    tlsCAFile=certifi.where())
db = client.userInfo
info = db.info

muscle_groups = [['abdominals', 'lower_back', 'middle_back', 'chest'],
                 ['biceps', 'forearms', 'triceps', 'traps'],
                 ['calves', 'glutes', 'hamstrings', 'quadriceps']]

weight_loss = ['abdominals', 'cardio', 'biceps', 'cardio', 'chest', 'cardio', 'lower_back', 'cardio', 'quadriceps',
               'cardio']


@app.route('/api/')
def hello_world():  # put application's code here
    return json.dumps({'message': 'Hello world!'})


@app.route('/api/setgoal/<username>/<goal>')
def setGoal(username, goal):  # goal can be either strength or weightloss, default is strength
    info.update_one({"name": username}, {"$set": {"goal": goal}})
    return ""


@app.route('/api/newuser/<username>')
def new_user(username):
    user = {
        "name": username,
        "gym_access": True,
        "proficiency": None,
        "previous_weights": dict(),
        "previous_reps": dict(),
        "exercise_difficulty": dict(),
        "workouts": dict(),  # key is day and value is workouts
        "exercise_scores": dict(),
        "goal": "strength",
        "total_weight": 0,
        "total_reps": 0,
        "total_days": 0,
        "onboarded": False
    }
    info.insert_one(user)
    return ""


@app.route('/api/getstats/<username>')
def getStats(username):
    data = info.find_one({"name": username})
    total_weight = data['total_weight']
    total_reps = data['total_reps']
    total_days = data['total_days']
    d = dict()
    d['total_weight'] = total_weight
    d['total_reps'] = total_reps
    d['total_days'] = total_days
    return json.dumps(d)


@app.route('/api/hasonboarded/<username>')
def hasOnboarded(username):
    data = info.find_one({"name": username})
    # print(data)
    if data is None:
        return json.dumps({'onboarded': "false"})
    else:
        return json.dumps({'onboarded': "true"})


@app.route("/api/rateexercise/<username>/<exercise>/<difficulty>")  # sets workout weight and difficulty
def rateExercise(exercise, username, difficulty):
    current_vals = info.find_one({"name": username})
    exercise_difficulty = current_vals['exercise_difficulty']
    exercise_difficulty[exercise] = difficulty

    info.update_one({"name": username}, {"$set": {"exercise_difficulty": exercise_difficulty}})
    return ""


@app.route('/api/setgymaccess/<username>/<hasaccess>')
def setGym(username, hasaccess):  # sets whether or not the user has access to gyms, hasaccess is either true or false
    if hasaccess == 'false':
        info.update_one({"name": username}, {"$set": {"gym_access": False, "onboarded": True}})

    elif hasaccess == 'true':
        info.update_one({"name": username}, {"$set": {"gym_access": True}})
    return ""


@app.route('/api/setproficiency/<username>/<proficiency>')
def setProficiency(username, proficiency):  # can be beginner, intermediate, or expert
    info.update_one({"name": username}, {"$set": {"proficiency": proficiency}})
    return ""


@app.route('/api/getworkouthistory/<username>')
def workoutHistory(username):
    data = info.find_one({"name": username})
    return json.dumps(data['workouts'])


@app.route('/api/setworkoutrating/<username>/<exercise>/<rating>')  # rating is either 0 or 1, 0 being bad 1 being good
def setWorkoutRating(username, exercise, rating):
    data = info.find_one({"name": username})
    exercise_ratings = data['exercise_scores']
    if exercise not in exercise_ratings:
        exercise_ratings[exercise] = 1
    if rating == '0':
        exercise_ratings[exercise] = 0.8 * exercise_ratings[exercise]
    else:
        exercise_ratings[exercise] = 1.2 * exercise_ratings[exercise]

    info.update_one({"name": username}, {"$set": {"exercise_scores": exercise_ratings}})

    return ""


@app.route('/api/recommend/<username>/<numexercises>')
def recommend(username, numexercises):  # pass in num_exercises as param
    api_url = 'https://api.api-ninjas.com/v1/exercises?'
    data = info.find_one({"name": username})

    numexercises = int(numexercises)

    # if the user already has a workout for the day then return it
    today = date.today()
    workouts = data['workouts']
    #today='2023-03-16'
    if str(today) in workouts:
        return workouts[str(today)]

    gym_access = data['gym_access']
    proficiency = data['proficiency']
    exercise_scores = data['exercise_scores']
    goal = data['goal']
    previous_weights = data['previous_weights']
    previous_reps = data['previous_reps']
    exercise_difficulty = data['exercise_difficulty']
    total_weight = data['total_weight']
    total_reps = data['total_reps']
    total_days = data['total_days']

    if not gym_access:
        api_url += "equipment=body_only"
    if proficiency != None:
        if api_url[-1] != '?':
            api_url += '&'
        api_url += "difficulty=" + proficiency

    if api_url[-1] != '?':
        api_url += '&'
    # set muscle group based on day
    day = int(str(date.today())[8:10])
    cardio = False
    exercises = []
    if goal == 'strength':
        muscle_group = muscle_groups[day % len(muscle_groups)]
        # api_url+="muscle="+muscle+"&"
        # api_url += "offset="
        # page = 0
        exercise_categories = []
        for i in range(4):
            muscle = muscle_group[i]

            page = 0
            e = []
            while len(e) < numexercises * 3:
                temp_url = api_url + "muscle=" + muscle + "&offset=" + str(page * 10)
                response = requests.get(temp_url,
                                        headers={'X-Api-Key': 'NurcILhyzDs3UAbN0EykdA==86JfdPcpA2ndS7dN'})
                page += 1
                if response.status_code == requests.codes.ok:
                    js = json.loads(response.text)
                    if len(js) == 0:
                        break
                    e.extend(js)
                else:
                    print("Error:", response.status_code, response.text)
            exercise_categories.append(e)
        i = 0
        while len(exercises) < numexercises * 10:
            if len(exercise_categories[i]) == 0:
                continue
            exercises.append(exercise_categories[i][0])
            exercise_categories[i].pop(0)
            i += 1
            i %= 4

    else:
        workout = weight_loss[day % len(weight_loss)]
        if workout == 'cardio':
            api_url += "type=cardio&"
            cardio=True
        else:
            api_url += "muscle=" + workout + "&"
        api_url += "offset="
        page = 0
        while len(exercises) < numexercises * 10:
            response = requests.get(api_url + str(page * 10),
                                    headers={'X-Api-Key': 'NurcILhyzDs3UAbN0EykdA==86JfdPcpA2ndS7dN'})
            page += 1
            if response.status_code == requests.codes.ok:
                js = json.loads(response.text)
                if len(js) == 0:
                    break
                exercises.extend(js)
            else:
                print("Error:", response.status_code, response.text)
    scores = dict()
    name_to_muscle = dict()
    body_only = set()
    for exercise in exercises:
        score = 1
        if exercise['equipment']=='body_only':
            body_only.add(exercise['name'])
        if not gym_access:
            if exercise['equipment'] == 'body_only':
                score *= 1.2
            else:
                score *= 0.8
        if "".join(exercise['name'].split(" ")) in exercise_scores:
            score *= exercise_scores["".join(exercise['name'].split(" "))]
        else:
            score *= 1.2
        scores[exercise['name']] = score
        name_to_muscle[exercise['name']] = exercise['muscle']
    final_exercises = []
    for exercise, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        ex = dict()
        if len(final_exercises) < numexercises:
            ex['name'] = exercise
            ex['muscle'] = name_to_muscle[exercise]
            remove_spaces = "".join(exercise.split(" "))
            if remove_spaces in previous_weights:
                weight = previous_weights[remove_spaces]
                reps = previous_reps[remove_spaces]
                if remove_spaces in exercise_difficulty:
                    if exercise_difficulty[remove_spaces] == 'easy':
                        ex['weight'] = int(weight * 1.2)
                        previous_weights[remove_spaces] = int(weight * 1.2)
                        ex['reps'] = int(reps * 1.2)
                        previous_reps[remove_spaces] = int(reps * 1.2)
                    elif exercise_difficulty[remove_spaces] == 'medium':
                        ex['weight'] = int(weight * 1.2)
                        previous_weights[remove_spaces] = int(weight * 1.2)
                        ex['reps'] = reps
                    else:
                        ex['weight'] = int(weight * 0.8)
                        previous_weights[remove_spaces] = int(weight * 0.8)
                        ex['reps'] = int(reps * 0.8)
                        previous_reps[remove_spaces] = int(reps * 0.8)
                else:
                    ex['weight'] = int(weight * 1.2)
                    ex['reps'] = int(reps)
                    previous_weights[remove_spaces] = int(weight * 1.2)
            else:
                # recommend weight of 10lb
                previous_weights[remove_spaces] = 10
                ex['weight'] = 10
                previous_reps[remove_spaces] = 15
                ex['reps'] = 15
            if exercise in body_only:
                ex['weight'] = 0
            if cardio:
                ex['weight'] = 0
                ex['reps'] = 0
            total_weight+=ex['weight']
            total_reps+=ex['reps']
            final_exercises.append(ex)
        else:
            break

    d = {"exercises": final_exercises[:min(len(final_exercises), numexercises)]}
    temp = json.dumps(d)
    workouts[str(today)] = temp
    info.update_one({"name": username}, {
        "$set": {"workouts": workouts, "previous_weights": previous_weights, 'previous_reps': previous_reps,
                 "total_weight": total_weight, "total_reps": total_reps, "total_days": total_days+1}})

    print(temp)
    return temp



@app.route('/api/randomTimeAlternativeWorkout/')
def randomTimeAlternativeWorkout():
    global randomTime

    curr_hour = datetime.datetime.now().hour
    curr_minute = datetime.datetime.now().minute
    curr_second = datetime.datetime.now().second

    # curr_hour = 18
    # curr_minute = 50
    # curr_second = 0

    # if time is past 7 pm, return null_output
    if (curr_hour >= 19):
        randomTime = -1
        return ""


    p = random.random()
    start = str(datetime.date.today().strftime("%Y/%m/%d")) + f"T{curr_hour}:{curr_minute}:{curr_second}"


    end = str(datetime.date.today().strftime("%Y/%m/%d")) + "T19:00:00"
    time_format = '%Y/%m/%dT%H:%M:%S'

    start_time = time.mktime(time.strptime(start, time_format))
    end_time = time.mktime(time.strptime(end, time_format))

    ptime = start_time + p * (end_time - start_time)

    randomTime = time.strftime(time_format, time.localtime(ptime))

    return ""


@app.route('/api/findNearbyAlternativeWorkouts')
def findNearbyAlternativeWorkouts():  # username):
    '''Find nearby workouts to recommend based on live tracking information'''
    randomTimeAlternativeWorkout()
    global randomTime

    # if time is past 9 PM, do not suggest workouts
    if (randomTime == -1):
        none_output = {"LiveWorkouts": []}

        return none_output

    # Map client
    MAPS_API_KEY = "AIzaSyD-ld44eeW8LxC2PZfHa9m2p1cEfzaRleE"
    map_client = googlemaps.Client(MAPS_API_KEY)

    # Get current location (longitude and latitude)
    geo = geocoder.ip('me')
    curr_lat = geo.latlng[0]
    curr_lng = geo.latlng[1]
    curr_location = curr_lat, curr_lng

    # Get random alternative workout
    workout_types = ['hiking', 'yoga', 'dancing', 'swimming', 'rock climbing', 'boxing', 'martial arts']
    workout_type = workout_types[random.randrange(0, len(workout_types))]

    distance = 8046.7  # 5 miles in meters
    workout_list = list()
    response = map_client.places_nearby(
        location=curr_location,
        keyword=workout_type,
        radius=distance
    )

    workout_list.extend(response.get('results'))
    next_p = response.get('next_p')

    # Find nearby places according to workout type
    while next_p:
        time.sleep(2)
        response = map_client.places_nearby(
            location=curr_location,
            keyword=workout_type,
            radius=distance
        )
        workout_list.extend(response.get('results'))
        next_p = response.get('next_p')

    # Get alternative workout recommendation options and their attributes
    workout_recommendation = dict()
    curr_time = datetime.datetime.now()
    for w in workout_list:
        if len(workout_recommendation) >= 3:
            break

        end = 'https://www.google.com/maps/dir/?api=1&'
        dest_lat_lng = str(w['geometry']['location']['lat']) + "," + str(w['geometry']['location']['lng'])
        str_curr_location = str(curr_location[0]) + "," + str(curr_location[1])
        directions_request = f"origin={str_curr_location}&destination={dest_lat_lng}&key={MAPS_API_KEY}"
        maps_link = end + directions_request
        workout_recommendation[w['name']] = {'rating': w['rating'], 'address': w['vicinity'], 'directions': maps_link}

    # Get list of destination names
    t = []
    for key in workout_recommendation.keys():
        t.append(key)
    name1 = t[len(t) - 3]
    name2 = t[len(t) - 2]
    name3 = t[len(t) - 1]
    output = {"LiveWorkouts": [
        {
            "workout_type": workout_type,
            "name": name1,
            "address": workout_recommendation[name1]['address'],
            "rating": workout_recommendation[name1]['rating'],
            "maps_link": workout_recommendation[name1]['directions'],
            "time": randomTime
        },
        {
            "workout_type": workout_type,
            "name": name2,
            "address": workout_recommendation[name2]['address'],
            "rating": workout_recommendation[name2]['rating'],
            "maps_link": workout_recommendation[name2]['directions'],
            "time": randomTime
        },
        {
            "workout_type": workout_type,
            "name": name3,
            "address": workout_recommendation[name3]['address'],
            "rating": workout_recommendation[name3]['rating'],
            "maps_link": workout_recommendation[name3]['directions'],
            "time": randomTime
        }
    ]}

    return json.dumps(output)


if __name__ == '__main__':
    app.run()
