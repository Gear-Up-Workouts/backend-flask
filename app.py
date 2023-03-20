import json
from pymongo import MongoClient
import certifi

from flask import Flask
from flask import request
import requests

from datetime import date

app = Flask(__name__)

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
    info.delete_one({"name": username})
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
            if exercise in body_only or cardio:
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
    return temp


### CARDIO
@app.route('/cardio')
@app.route('/cardio/<difficulty>')
def getCardioWorkout(difficulty=''):
    difficultyURL = '&' + difficultyURLBase + difficulty
    response = requests.get(workoutAPIUrlBase + cardioURLBase + difficultyURL, headers={'X-Api-Key': workoutAPIKey})
    if response.status_code == requests.codes.ok:
        return response.text
    else:
        print("Error:", response.status_code, response.text)


### STRENGTH
@app.route('/strength')
@app.route('/strength/<difficulty>')
def getStrengthWorkout(difficulty=''):
    difficultyURL = '&' + difficultyURLBase + difficulty
    response = requests.get(workoutAPIUrlBase + strengthURLBase + difficultyURL, headers={'X-Api-Key': workoutAPIKey})
    if response.status_code == requests.codes.ok:
        return response.text
    else:
        print("Error:", response.status_code, response.text)


### STRETCHING
@app.route('/stretching')
@app.route('/stretching/<difficulty>')
def getStretchingWorkout(difficulty=''):
    difficultyURL = '&' + difficultyURLBase + difficulty
    response = requests.get(workoutAPIUrlBase + stretchingURLBase + difficultyURL, headers={'X-Api-Key': workoutAPIKey})
    if response.status_code == requests.codes.ok:
        return response.text
    else:
        print("Error:", response.status_code, response.text)


if __name__ == '__main__':
    app.run()
