from flask import Flask, request
from dotenv import load_dotenv
import background_tasks
import database
import middleware
from textwrap import dedent

load_dotenv()
resolvers = database.get_dns_resolvers()
domain_ignorelist = database.get_ignorelist()
app = Flask(__name__)
background_tasks.launch(resolvers)


@app.route('/')
def index():
    return dedent('''
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
    return middleware.test_domain(domain, resolvers, domain_ignorelist)


@app.route('/add_domain')
def add_domain():
    domain = request.args.get('domain')
    key = request.args.get('key')
    return middleware.add_domain(domain, key)


@app.route('/resolvers')
def get_resolvers():
    return middleware.get_resolvers()


@app.route('/blocked_domains')
def get_blocked_domains():
    return middleware.get_blocked_domains()


@app.after_request
def add_cors_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Methods', 'GET')

    return response


if __name__ == '__main__':
    app.run()
