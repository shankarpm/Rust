import domino
import os
import sys

print("Domino python-wrapper version:", domino.__version__)
print("Minimum required python-wrapper version is 1.0.6")

from domino import Domino

action = sys.argv[1]

domino = Domino(os.environ['DOMINO_PROJECT_OWNER'] + "/" + os.environ['DOMINO_PROJECT_NAME'])
domino.authenticate(api_key=os.getenv("DOMINO_USER_API_KEY"))

if action == "on":
    domino.app_publish()
    print("publishing app")
elif action == "off":
    domino.app_unpublish()
    print("unpublishing app")
else:
     raise ValueError('This script uses the format: app.py [on]/[off]')