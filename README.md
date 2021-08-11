# Text Analyzer in Python
---
### Setup the enivronment and install all dependencies.
```bash
virtualenv env
source env/bin/activate
pip3 install -r requirements.txt
```
### Start development server.
```bash
python3 manage.py runserver 8000
```

Then open http://localhost:8000 to see your app.

# Text Analysis

It uses **Spacy** python library to analyze our data.
https://spacy.io/
### API ENDPOINT

http://localhost:8000/analyze-text/

### The app is hosted on Heroku app platform.

https://doc-add-on.herokuapp.com/

