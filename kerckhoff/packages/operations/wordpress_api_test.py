import requests
import datetime

#user = 'admin'
#pw = 'a89K 3ITg sEzs LjRC Txe4 ypIG'

user = 'dailybruinonline'
pw = 'LL%Vwcn96Lqz3cyLSDU^ZslP'

JWT_kp = {
    "api_key":"1E8kNlx624PoAVKwu9v5yeXLO",
    "api_secret":"2F@jvcrnd0B2G0eOJ&NABL48jQNweM&s"
}

headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
}

data = {
    'date': datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    'title': 'I am Jonathan Delacruz',
    'slug': 'rest-api-8',
    'status': 'publish',
    'content': 'this is the content post',
    'author': '1',
    'excerpt': 'Exceptional post!',
}

JWT_resp = requests.post("http://localhost:9000/wp-json/wp/v2/token", headers=headers, data=JWT_kp)
JWT = JWT_resp.json()
print(JWT)

headers['Authorization'] = 'Bearer ' + JWT['access_token']
print(headers)

response = requests.post("http://localhost:9000/wp-json/wp/v2/posts", data=data, headers=headers)
#response = requests.delete("http://localhost:9000/wp-json/wp/v2/posts/24", ,headers=headers)
json_response = response.json()
print(json_response)


