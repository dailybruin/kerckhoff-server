import requests
import datetime
import base64

#Test docker container credentials
#user = 'admin'
#pw = 'a89K 3ITg sEzs LjRC Txe4 ypIG'

#Test site URL
url = 'http://165.227.25.233'

#Test site credentials
user = 'dailybruinonline'
pw = 'HrVy ZOsL nMr7 Vhla V7qo VgDA'

headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
}

data = {
    'date': datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    'title': 'Kerckhoff test',
    'slug': 'rest-api-1',
    'status': 'publish',
    'content': 'Kerckhoff rest API post',
    'author': '2',
    'excerpt': 'Exceptional post!',
}

#JWT CODE: NOT IN USE RIGHT NOW
#JWT_kp = {
#    "api_key":"1E8kNlx624PoAVKwu9v5yeXLO",
#    "api_secret":"2F@jvcrnd0B2G0eOJ&NABL48jQNweM&s"
#}
#JWT_resp = requests.post("http://localhost:9000/wp-json/wp/v2/token", headers=headers, data=JWT_kp)
#JWT = JWT_resp.json()
#print(JWT)
#headers['Authorization'] = 'Bearer ' + JWT['access_token']
#response = requests.post("http://165.227.25.233/wp-json/wp/v2/posts", data=data, headers=headers)

#BASIC AUTH CODE
auth_string = f"{user}:{pw}"
auth_data = auth_string.encode('utf-8')
headers['Authorization'] = 'Basic ' + base64.b64encode(auth_data).decode('utf-8')

print(headers)
print(f"http://{url}/wp-json/wp/v2/posts")


response = requests.post(f"{url}/wp-json/wp/v2/posts", headers=headers, data=data)
json_response = response.json()
print(json_response)


