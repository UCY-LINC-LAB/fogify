This assignment submission is comprised of 5 files:
- app.py: This is the Flask App
- templates/index.html: The index.html file houses the html page that the Flask app uses to display when accessing it using the browser/cli.
  It is placed in the directory "templates" as Flask only renders HTML files within a directory called templates.
- requirements.txt: This is a list of python dependencies needed for the container in order for the app to run
- Dockerfile: This is the Dockerfile used to build the container image, it uses the requirements.txt & the app.py to build the container image.
- README.txt: This file.

To run the app do the following:
    1. Enter the A5 directory/Project directory
    2. Run the command (in a linux terminal) "docker build . -t net4005_a5"
    3. Once it is finished building, run the command; "docker run -p 8080:8080 -d net4005_a5"
    4. Now you can access the app using your web browser, or command line (using the "curl" command)

When accessing the Flask app you will be greeted with a message "You are connecting from **Your IP Address**".
Since you are running it as well as accessing it locally, you will most likely see your:
    a. Localhost address (127.0.0.1)
    b. Docker Container network/proxy address (For me it was 172.17.0.1)

You can access the Flask app using the url "localhost:8080" as the app is on every network (0.0.0.0) open on port 8080