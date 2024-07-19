from flask import Flask, request
from dotenv import load_dotenv
import background_tasks
import database
import middleware
from textwrap import dedent

load_dotenv()
resolvers = database.get_dns_resolvers()
app = Flask(__name__)
background_tasks.launch(resolvers)


@app.route('/')
def index():
    return dedent('''
    <h1>Work in progress</h1>
    Diese Seite ist noch nicht fertig, eine UI kommt noch, die API sachen sind schon nutzbar.
    Aber auch die können sich noch ändern.
    <br>
    <br>
    <h2>API Endpoints</h2>
    <h3>GET /test_domain?domain=example.com</h3>
    <p>Testet ob eine Domain geblockt ist</p>
    <h3>GET /resolvers</h3>
    <p>Gibt alle DNS Resolver zurück, die wir zum testen von Domains benutzen</p>
    <h3>GET /blocked_domains</h3>
    <p>Gibt alle geblockten Domains zurück</p>
    ''')


@app.route('/test_domain')
def test_domain():
    domain = request.args.get('domain')
    return middleware.test_domain(domain, resolvers)


@app.route('/resolvers')
def get_resolvers():
    return middleware.get_resolvers()


@app.route('/blocked_domains')
def get_blocked_domains():
    return middleware.get_blocked_domains()


@app.after_request
def add_cors_headers(response):
    allowed_origins = [
        'https://cuiiliste.de',
        'https://www.cuiiliste.de',
        'http://localhost:3000'  # fuck it, we're testing in prod :333
    ]
    origin = request.headers.get('Origin')

    if origin in allowed_origins:
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Methods', 'GET')

    return response


if __name__ == '__main__':
    app.run()
