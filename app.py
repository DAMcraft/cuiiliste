from flask import Flask, request
from dotenv import load_dotenv

import database
import middleware

load_dotenv()
resolvers = database.get_dns_resolvers()
app = Flask(__name__)


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'


@app.route('/test_domain')
def test_domain():
    domain = request.args.get('domain')
    return middleware.test_domain(domain, resolvers)


if __name__ == '__main__':
    app.run()
