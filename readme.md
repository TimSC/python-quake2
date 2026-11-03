
Porting the Quake 2 engine to python. I did 25% manually and the rest with ChatGPT/claude.

The code is all licensed under the terms of the GPL (gnu public license).
You should read the entire license, but the gist of it is that you can do 
anything you want with the code, including sell your new version.  The catch 
is that if you distribute new binary versions, you are required to make the 
entire source code available for free to everyone.

All of the Q2 data files remain copyrighted and licensed under the 
original terms, so you cannot redistribute data from the original game, but if 
you do a true total conversion, you can create a standalone game based on 
this code.

   pip3 install -r requirements.txt

   pip3 install -e .

   python3 main.py +set basedir /path/to/quake2data/Data

