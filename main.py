import argparse
from agent.agent import Agent
from controller.controller import Controller
from flask_api import FlaskAPI

def initialize():
    app = FlaskAPI(__name__)
    parser = argparse.ArgumentParser()

    parser.add_argument('--agent', help='Run agent', default=False, action="store_true")
    parser.add_argument('--agent-ip', help='The IP of the agent', default="localhost")
    parser.add_argument('--controller', help='Run Controller', action="store_true")

    args = parser.parse_args()



    if args.agent:
        cmd = Agent(args, app)

    if args.controller:
        cmd = Controller(args, app)

    return cmd

cmd = initialize()
app = cmd.app
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5500 if type(cmd) == Agent else 5000)
