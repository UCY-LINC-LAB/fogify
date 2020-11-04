import argparse
import sys
from agent.agent import Agent
from controller.controller import Controller
from flask_api import FlaskAPI

app = FlaskAPI(__name__)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--agent', help='Run agent', default=False, action="store_true")
    parser.add_argument('--agent-ip', help='The IP of the agent', default="localhost")
    parser.add_argument('--controller', help='Run Controller', action="store_true")

    args = parser.parse_args()

    if args.agent:
        agent = Agent(args,app)
        sys.exit(0)

    if args.controller:
        controller = Controller(args, app)
        sys.exit(0)
