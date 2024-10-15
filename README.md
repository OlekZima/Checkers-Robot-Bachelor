# Checkers playing robot

B. Eng. Thesis

by Michał Nowicki

---

## Usage

There are 2 main usages for this project.

- Play checkers against Dobot Magician V2 using camera for board recognition
- Start a flask server and play Player vs Player or Player vs Computer online
---
### Play against robot

==== Quick start ====
Terminal in this directory

```bash
source robot-checkers-start.sh
```


==== Normal start ====
Requirements:
- Python 3.10
- pandas
- numpy
- opencv-contrib-python
- pyserial
- pydobot

Command (while being in main project directory):
```bash
python main_app.py
```

---
### Host a flask server

Requirements:
- Python 3.10
- flask
- flask-api
- flask-wtf
- wtforms
- numpy

Command (while being in main project directory):
```
python run_web_app.py
```
