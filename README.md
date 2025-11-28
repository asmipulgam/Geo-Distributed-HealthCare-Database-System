# G4-CSE512-GeoDistributedHealthcareDatabaseSystem
The commands have been provided with respecty to MacOS installation
Please follow the below steps for running the project:

0) Ensure you have Python 3.x, Node.js, and npm installed on your system.
1) Open terminal and navigate to central_server folder
2) Run the command: `python3 setup_cloud.py` - A method called setup_func is currently commented out. This is necessary if populating database clusters for the first time, like creating tables, etc. Since the provided cluster already has data, this is commented in the main block. The other code which executes is basically downloading of the server certificates for SSL connection to cockroachDB clusters. In case of issues, this can be run directly in the command line as well.
3) Run the command: `python3 app.py` - This will start the backend server at port 5000. Following the simplified architecture, this server will be communicating with the cockroachDB clusters directly.
4) Open another terminal and navigate to frontend folder
5) Run the command: `npm install` - This will install all the dependencies required for the frontend ReactJS application.
6) Run the command: `npm start` - This will start the frontend application at port 5173. This will automatically open a browser window. If not, open a browser and navigate to `http://localhost:5173/`